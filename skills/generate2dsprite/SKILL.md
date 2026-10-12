---
name: generate2dsprite
description: Make game-ready 2D characters, creatures, props, icons and FX as master stills, sprite sheets or animation clips, on Arena. Art comes from the agent's own generate_image tool (staged and committed through generate2dmedia route_media.py); approve one master still per character, then animate it with one generated sprite sheet per action, keyed, sliced, registered, scaled, paletted, QA'd and exported (Aseprite JSON, Godot SpriteFrames or Sprite3D). HD finish by default, pixel finish on request. Also processes frames the user supplies. Use for sprites, masters, sheets, frame-by-frame animation and packaging. Not for maps, tiles or backgrounds (generate2dmap), supplied clips or frames needing motion finishing (video2dsprite), code-drawn art (codeart2d, only on request) or a bare generation call (generate2dmedia).
---

# Generate 2D Sprite (Arena Edition)

Make the smallest asset bundle the game needs, at its real display size, camera and style.
Game logic (collision, damage, timing) stays independent of the art.

## Use when

- A character, creature, prop, item, icon or FX is needed as a master still, a sheet or clips.
- Frames already exist (generated, painted, code-drawn) and need clips, palettes or an engine export.

## Do not use when

- Maps, tiles, terrain, parallax or scene plates: [generate2dmap](../generate2dmap/SKILL.md).
- A user-supplied clip or sliced frames need registration, loop picking, retiming or video packaging: [video2dsprite](../video2dsprite/SKILL.md).
- Code-drawn art the user asked for: [codeart2d](../codeart2d/SKILL.md). Only a bare generation call: [generate2dmedia](../generate2dmedia/SKILL.md).

## Capability check (once per session)

Run `python "<skill-dir>/../generate2dmedia/scripts/forge_doctor.py" --host-tools generate_image --save <output>/doctor.json` (`--host-tools none` if you have no image tool). Its `ROUTES` block shows `arena:generate_image` OK and no video route. If `encoding.stdout` fails, set `PYTHONUTF8=1`.

## Art source

The agent's own `generate_image` tool is the only image route; record it as `art_source: arena_image` and name it in your reply. `code` (codeart2d) is an art source only when the user asks for code-drawn art. Every generation follows the three-step protocol of [generate2dmedia](../generate2dmedia/SKILL.md): stage with `route_media.py image`, call `generate_image` with that prompt and references, save the result as `<out-dir>/generated.png`, then `route_media.py commit`. The commit line is the proof; report the route as "Arena generate_image" and the real returned size from it. Existing art the user supplies is always welcome.

- **Finish:** HD is the default: full colour, clean alpha, one registration and a premultiplied area downscale to the game height. The pixel finish (one shared palette, binary alpha, no dither) is an option when the user asks for pixel art. Never prompt the image model for a logical pixel grid; the pixel look comes from the finish.
- **Characters:** approve one master still per character, then animate it with one generated sheet per action (below). Keep every action's body height from the master's rest pose.

## Master still (every character animation starts here)

One approved master still per character. Wording: [prompt-rules.md](references/prompt-rules.md); the spec, framing and `master.json`: [master-still.md](references/master-still.md).

1. Spec (`--spec <json>` and/or flags): `--name`, `--subject`, `--identity` (long and precise), `--facing left|right|front|back`, `--class hero|mob|boss|prop`, `--finish hd|pixel` (HD default; pixel only when asked), `--identity-ref` (FIRST image, copied exactly), `--style-ref` (SECOND: an approved peer sprite, style and framing only), `--key` (default `#FF00FF`; green or blue for purple and pink designs).
2. Prompt: `python "<skill-dir>/scripts/master_still.py" prompt --spec <json> --output-dir <new>` writes `prompt.txt`, `spec.json` and `run.json`.
3. Takes: call your `generate_image` tool 1-3 times with that prompt (offer the user options when the look is open), save the results as `<run>/take1.png`, `take2.png`, ... and LOOK at each with `read_file`. Check identity, facing, nothing touching an edge, no text, flat key backdrop.
4. Fix a near-miss by edit, never by re-roll: `master_still.py edit --run <dir> --take N --change "<one change>" --prompt-only --output-dir <new>`, then generate the edited prompt with the chosen take as the FIRST reference of your `generate_image` call.
5. Approve: `master_still.py approve --run <dir> --still <take.png> --route arena:generate_image --output-dir <new>`. It keys the still, crops it with a 6 px margin, LANCZOS-scales it to the class framing on 1024x1024 (hero 788 px tall, top margin 138 px) and writes `master.png` (opaque, pure key), `master_rgba.png` and `master.json` (`generate2dsprite.master.v1`).
6. Action sheets read `master.json` (`identity_recap`, `facing`, `finish`, `class`, `framing`, `key`, `files`, `transform`) and never re-measure the still; every sheet prompt starts with "The same <identity_recap>".

## Character animation: one sheet per action (the Arena route)

Arena has no image-to-video, so each action is one generated sprite sheet from the master, then the deterministic pipeline below. Per action ([action-recipes.md](references/action-recipes.md) has grids, phases and presets; [animation-planning.md](references/animation-planning.md) has poses and timing):

1. Guide: `python "<skill-dir>/scripts/plan_guide.py" --frames N --cycle run --facing right --output-dir <new>` writes `guide.png` and `prompt.txt` (grid, margins, feet line). Looping actions: idle 4-6 frames, walk 6-8, run 6. One-shots: attack 4-6, jump 4-6, hurt 3-4 (`--cycle none`).
2. Prompt: the guide's `prompt.txt` + the master's identity: "The same <identity_recap>, sprite sheet, N frames in one row, <absolute phase per frame> ..."; ban text, borders and background props.
3. Generate with master + guide as references (master FIRST for identity, guide SECOND for layout), then stage/commit through `route_media.py` (Art source above).
4. Process it like any sheet (Pipeline below). One action family per sheet; keep wide slashes, trails and projectiles out of the body sheet.
5. Cross-action consistency: write the scale profile from the grounded reference (`process --write-scale-profile`), reuse it for the other actions (`--scale-profile`, drift <= 0.08).
6. If a sheet fails identity or spacing after one fix-by-edit, regenerate it; a duplicated half-cycle means regenerate the second half.

## Commands

Run each tool as one line from the user's project root: `python "<skill-dir>/scripts/<tool>.py" ...`. `<skill-dir>` is this skill's folder; sibling skills sit beside it (`<skill-dir>/../video2dsprite`). Keep inputs and outputs inside the project. Every tool writes a new `--output-dir`: it refuses an existing one, stages beside it and publishes only after its checks (`--strict-qc` / `--strict` publish nothing on failure). Success prints one JSON line; errors print `error: ...` and exit 1; usage errors exit 2. Needs Python 3.10+, numpy and Pillow (scipy recommended). `--help` lists every flag.

## Plan the asset

Record identity and reference, camera and facing, style, game display size, finish (HD by default, pixel on request), action list and phases, loop or one-shot, motion envelope, shared root and output format. Keep one accepted master and one source-to-display scale per character; mobs are no taller than the hero unless planned. A grid is not smoothness: pose spacing, timing, the loop seam and ground contact matter more. Poses, NEAR/FAR legs and timing: [animation-planning.md](references/animation-planning.md).

- Alpha: `native_alpha` keeps real transparency (a painted checkerboard is not alpha); `chroma_key` uses flat magenta only when the subject has none; `opaque` keeps whole images (`assemble_frames.py`).
- Sampling: `lanczos` or a premultiplied area resize for generated art; `nearest` only for a verified pixel grid. A high-resolution pixel-like painting is not clean 32 px art.
- A shared root is not a per-frame alpha-bbox bottom: keep intentional flight, jumps, bob and recoil.

## Generate (image route)

Write the prompt yourself ([prompt-rules.md](references/prompt-rules.md)). Attach references through the staged job's `--reference` flags and your `generate_image` call's image list, in the same order; a path in prose is not a reference. Keep the accepted master in every generation and describe absolute phases, not chained edits; a fix is an edit of the approved art that names the only change. Verify the real returned size from the commit line; never claim it from the prompt.

## Pipeline

Sheets (characters actions, FX, icons, props): `sheet_qc.py spill` on the raw sheet, then `generate2dsprite.py process`, then `sheet_qc.py frames`, then `scale_frames.py`, then `build_animation_clips.py`, then `export_engine.py`.

| Need | Route |
|---|---|
| Plan a sheet for the image tool (aspect, grid, guide, prompt) | `plan_guide.py --frames N --cycle run --output-dir <new>`; use `guide.png` + `prompt.txt` as references/text of your generate_image call. Fixed scale and feet line: `make_anchor_layout.py`; empty safe frame: `make_layout_guide.py` |
| Check a raw sheet before slicing | `sheet_qc.py spill --input <sheet> --rows R --cols C --output-dir <new>`; crossing parts mean regenerate with more margin or slice by ownership, never a largest-component filter |
| Key, slice and register a sheet | `generate2dsprite.py process --input <sheet> --target asset --mode <mode> --rows R --cols C --output-dir <new> --strict-qc` (geometry v2; [processing.md](references/processing.md)) |
| Pixel art drawn at M source px per art px | `process --resampler nearest --logical-pixel M --pixel-scale N` (whole scales only) |
| Jumps, bob or recoil on one registration point | `process --scale-strategy registered` (or `--anchor-px X,Y`) |
| One character's scale across actions | `process --write-scale-profile <p.json>` on the grounded reference, then `--scale-profile <p.json> --max-profile-scale-drift 0.08` |
| Canvas does not divide into the grid; other row order | `process --grid-rounding nearest` or `--pad-to-grid`; `--direction-order down,up,left,right` ([modes.md](references/modes.md)) |
| Identity, NEAR/FAR alternation, drift, baselines | `sheet_qc.py frames --sheet <sheet> --rows R --cols C --cycle run --output-dir <new>`; a duplicated half-cycle means regenerate the second half. On code-drawn frames (`art_source=code`) `identity_residual` and `torso_drift` are advisory |
| Game size on one canvas and root, never clamped | `scale_frames.py --frames <pngs> --root-lock torso-x --row-baseline --emit-clips --ticks N --output-dir <new>`; later actions add `--profile <first>/scale-frames.json --action-padding L,T,R,B` |
| Clips with timing, events, transitions | `build_animation_clips.py --manifest clips.json --output-dir <new>`; read the lints and `review/` ([frames-and-clips.md](references/frames-and-clips.md)) |
| Whole frames or a scene loop (no keying) | `assemble_frames.py` (`--key chroma`, `--slice ownership`; `--loop-overlap K --ambient` for ambient loops only) |
| Shared palette, locks, variants, flicker (pixel finish) | `palette_tool.py build`, `apply`, `lock`, `quantize-seq`, `variants`, `luts`; strict logical grid: `pixel_reduce.py` ([palette-and-pixels.md](references/palette-and-pixels.md)) |
| Motion preview to LOOK at | `preview_gif.py --frames <dir-or-pngs> --fps N --output <loop.gif>` (Pillow GIF; watch it with read_file) |
| Engine export | `export_engine.py --clips <animation-clips.json> --target all --output-dir <new>`; Sprite3D: `--target godot-sprite3d --world-height <units>` ([engine-export.md](references/engine-export.md)) |
| Play clips in a game (gait, hit-stop, transitions) | [runtime-integration.md](references/runtime-integration.md) |
| Code-drawn sprites, rigs or FX, only on request | codeart2d `render_pixelspec.py`, `rig_animate.py` or `fx_build.py` with `--build-clips` (never `process`), then `export_engine.py`; disclose them as code-drawn |

## Acceptance

- Review at game size: silhouette and identity, contact and flight, loop seam or one-shot recovery, alpha over light and dark, extremities, scale across actions, root and collider.
- Quote numbers for quality claims: `pipeline-meta.json` `matte.qa` (a `key_ring_spill` warning: add `--despill-radius 1` or `--key-quality soft`), `sheet-qc.json`, the clip builder's lints. Numeric QC finds symptoms; it never approves anatomy or motion.
- Report every WARN or FAIL check verbatim (id, value, threshold, files) from each published QA envelope; never say "all checks passed" when any published envelope has a warn.
- Deliver accepted source art, runtime frames or clips, preview, prompt and provenance (route "Arena generate_image", commit sha256, real size), QA and remaining limits. Keep the last accepted bundle when revising.

## Arena host notes

- `<skill-dir>` is this skill's folder inside the workspace; run every tool from the user's project root with Bash.
- Look at every PNG you generate or QA with `read_file` before reporting; numbers cannot see identity, facing or text.
- `generate_image` makes ONE image per call and takes references through its `images` parameter; sprite sheets are single images containing a grid. Use `offer_options` when the look is open (master stills, key art).
- There is no video route: character motion comes from action sheets as above; a user-supplied clip goes to [video2dsprite](../video2dsprite/SKILL.md).

## References

[processing.md](references/processing.md) (process flags, legacy switches), [modes.md](references/modes.md), [prompt-rules.md](references/prompt-rules.md), [action-recipes.md](references/action-recipes.md), [character-animation.md](references/character-animation.md) (animation index), [frames-and-clips.md](references/frames-and-clips.md), [palette-and-pixels.md](references/palette-and-pixels.md), [engine-export.md](references/engine-export.md), [runtime-integration.md](references/runtime-integration.md), [sheet-set-handoff.md](references/sheet-set-handoff.md); data contracts in `references/schemas/sprite.schema.json`.
