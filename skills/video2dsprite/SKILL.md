---
name: video2dsprite
description: Motion finishing for frames and clips from any source, Arena Edition. The Arena agent cannot generate video, so this skill never generates - it keys supplied clips or frame directories with a soft matte, registers them by construction to an approved master, picks loops or retimes one-shots, finishes (HD by default, pixel on request) with the colour lock, and packages fixed-canvas frames, a PNG fallback with engine metadata and, when ffmpeg exists, alpha WebM and packed MP4. Use for user-supplied clips, frames sliced from generated sheets, code-drawn frames, still keying and engine video packaging. Not for generating the art itself (generate2dsprite makes sheets from the master; generate2dmedia is the route layer), maps (generate2dmap) or code-drawn animation (codeart2d, only on request).
---

# Video to 2D Animation (Arena Edition)

An approved still sets identity and geometry; frames from any source supply motion; deterministic
tools prepare it for the engine. **The Arena agent has no image-to-video tool and this skill never
generates anything**: it processes frames the user supplies, frames sliced from generated sheets
([generate2dsprite](../generate2dsprite/SKILL.md)), code-drawn frames, or a user-supplied video
clip.

## Use when

- A user-supplied clip must become transparent, registered, looped frames and engine packages.
- Sliced or code-drawn frames need registration to a master, loop picking, retiming or the HD/pixel finish with the colour lock.
- A still needs keying (`clean` keys one frame).
- animation.json packaging, verification or engine export of frames from any source.

## Do not use when

- Generating character art or action sheets: [generate2dsprite](../generate2dsprite/SKILL.md) (master still + one sheet per action).
- Maps, tiles, terrain, parallax or scene plates: [generate2dmap](../generate2dmap/SKILL.md).
- Code-drawn animation the user asked for: [codeart2d](../codeart2d/SKILL.md).

## Capability check (once per session)

`python "<skill-dir>/../generate2dmedia/scripts/forge_doctor.py" --host-tools generate_image --save <output>/doctor.json` covers the route table (no video route on Arena, by design). `python "<skill-dir>/scripts/video2dsprite.py" doctor` probes ffmpeg (5.1+, VP9 alpha round trip); without ffmpeg the answer is `{"png": true, "webm": false, "packed": false}` - sheets, GIFs and PNG packaging still work, only WebM/MP4 transports need ffmpeg. If `encoding.stdout` fails, set `PYTHONUTF8=1`.

## Inputs on Arena

| Source | Entry point |
|---|---|
| A user-supplied clip (mp4/mov/webm) | `video2dsprite.py extract` (needs ffmpeg), then the frame pipeline below |
| Frames sliced from a generated sheet | the frames directory from generate2dsprite `process`, straight into registration and finishing |
| Code-drawn frames (codeart2d rig/pixelspec) | same frame pipeline; keep `art_source: code` |
| A single still to key | `video2dsprite.py clean` on a one-frame directory |

Never claim generated motion: every frame this skill publishes came from the user, a sheet or code.

## Commands

Run each tool as one line from the user's project root: `python "<skill-dir>/scripts/<tool>.py" ...`. `<skill-dir>` is this skill's folder; sibling skills sit beside it. Keep inputs and outputs inside the project. Every verb writes a new `--output-dir`: it refuses an existing one and publishes only after its checks (`--strict` fails on residue). Success prints one JSON line; errors print `error: ...` and exit 1; usage errors exit 2. Needs Python 3.10+, numpy, Pillow; ffmpeg 5.1+ only for clips and WebM/MP4. `--help` lists every flag.

## Pipeline (frames from any source)

1. **Key plan.** `video2dsprite.py key-plan --master <master.png>`: it names background colours to avoid and `design_colours_at_risk`; protect or recolour them before generating the source sheet.
2. **Registration by construction (optional but recommended).** `prepare_i2v_input.py prepare --master <art> --action <idle|walk|run|attack|cast|guard|hurt|victory|defeat|ambient|fx> --output-dir <job>` places the master on a canvas at one recorded scale and writes `registration_job.json` (the transform `register_clip.py apply` will invert). Its `input.png` doubles as a layout reference for the sheet prompt; its `prompt.txt` is written for a video provider, so on Arena take the placement rules, not the motion wording. `prepare_i2v_input.py lint` checks a hand-written prompt.
3. **Key.** A clip: `video2dsprite.py extract`, then `process --video` (soft matte). Frames already decoded or sliced (`frame_*.png` or `raw_*.png`): `video2dsprite.py clean --raw-dir <dir> --output-dir <new>` (one frame keys a still). Read `frames-clean/matte-report.json` and look at frames over light and dark. Same keying for every action of a character: `--matte-profile <character-profile.json>`. A design colour near the key: `--protect-color #rrggbb`. `--matte binary --despill-mode off` reproduces the legacy keyer.
4. **Register.** `register_clip.py apply --job <job>/registration_job.json --frames <out>/frames-clean --output-dir <new>`; feet drift or jumps: `--lock feet`; spell or hit FX: `--profile fx`; one scale per character: `register_clip.py profile`, then `--character-profile`, then `validate-profile`. Judge a raw take before keying: `register_clip.py qc --job <job> --video <take>` (clip path, needs ffmpeg).
5. **Loop or retime.** Walks, runs, idles: `gait_loop.py select --frames-dir <reg>/frames --fps N --output-dir <new>` (`--kind idle` or `hover`); play `aids/loop3x.gif` and confirm by eye. Attacks, casts, FX: `retime.py --frames-dir <reg>/frames --fps N --output-dir <new> --spans <spans>` (impact, hold, ticks), or `--duration`, `--selection`, `--range`. Walks never ping-pong; attacks never recover backwards.
6. **Finish.** `finish_frames.py hd` (default; one scale per clip from the rest pose, premultiplied area downscale pinned to the anchor) or `finish_frames.py pixel` (crisp downscale, spaced palette, selective outline, binary alpha). Colour lock to the master is part of the finish (`colour_lock.py measure` reports hue flips; the lock holds every design colour on the master's OKLab chroma).
7. **Package.** `engine_export.py package ... --output-dir <new>` writes animation.json 3.0 plus the PNG atlas fallback always; alpha WebM (VP9) and packed-alpha MP4 only when the doctor says `webm`/`packed` true. `engine_export.py verify` decodes what it wrote; `validate_animation.py` gates the bundle.
8. **Preview and review.** `python "<skill-dir>/../generate2dsprite/scripts/preview_gif.py" --frames <frames> --fps N --output <loop.gif>` to LOOK at motion; `animation_review.py review|cut|select` for filmstrips and intervals.

## Quality gates

- Numeric gates are the same as upstream: area, feet, identity, zoom, turning around, edges, background, extra objects, motion, end pose, colour bleed - but they are run by you on the frames (sheet_qc, matte report, register_clip qc), not by a clip generator's retake loop.
- Quote the matte report's numbers for keying claims and keep them `needs-visual-review`.
- Choose cycles with `gait_loop.py select`, never by eye alone, then confirm by eye. Walks ship cadence and stride.

## Runtime and acceptance

- Acceptance order: package, then verify, then `validate_animation.py`. Deliver `animation.json` (3.0, keeps every 2.0 key; whole-ms `durationsMs`, exact `fpsRational`), QA, poster, PNG fallback and only the transports the doctor proves. Geometry stays in source units (`sourceSize`, `sourceAnchor`, `sourceRect`).
- Packed H.264 stores RGB left and alpha right; it is not a transparent MP4. Draw the compositor's `lease.drawable` ([packed-alpha-runtime.js](references/packed-alpha-runtime.js) over `references/runtime/packed-alpha-webgl.mjs`); show the poster until a decoded frame exists. Distance-driven walks, hit-stop and transitions: `references/runtime/forge-runtime.mjs`.
- Inspect at game scale: face and silhouette stability, contact, moving alpha edges over light and dark, loop seam, readability.

## Arena host notes

- `<skill-dir>` is this skill's folder inside the workspace; run every tool from the user's project root with Bash; look at every review image with `read_file`.
- ffmpeg is not installed by default in the sandbox: sheets/GIFs/PNG never need it; for a supplied clip install it first (e.g. `pip install imageio-ffmpeg` and use its binary) or ask the user for frames instead.
- The upstream image-to-video route, `sprite_set.py` and the clip retake loop are gone from this edition: there is nothing to generate video with. The sheet route in generate2dsprite replaces it.

Data contracts: `references/schemas/video.schema.json`.
