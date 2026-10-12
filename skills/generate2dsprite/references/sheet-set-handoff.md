# Sheet-set handoff: one master still -> a whole action set (Arena route)

Arena has no image-to-video tool, so a character's animated set comes from **one generated
sprite sheet per action**, each made from the same approved master still
([master-still.md](master-still.md)). The master fixes identity and geometry; the sheet prompts
supply the motion; the deterministic pipeline keys, slices, registers, times and packages it.

## Why sheets still win here

- Identity is enforced by construction: every sheet prompt starts with "The same
  `<identity_recap>`" and attaches `master.png` as the FIRST reference.
- Timing is authored, not recovered: loops and one-shots get exactly the frames and ticks the
  game needs (`build_animation_clips.py`), with no slow-motion retiming step.
- Every frame is inspectable and fixable: a bad frame means regenerate that sheet (or fix by
  edit), never re-roll a whole clip.

## The set, action by action

Defaults for a side-view character (adjust to the game):

| Action | Frames | Cycle | Notes |
|---|---|---|---|
| idle | 4-6 | loop | breathing bob only; first == last pose |
| walk | 6-8 | loop | contact + passing poses, NEAR/FAR leg alternation |
| run | 6 | loop | wider stride, forward lean, flight frame |
| attack | 4-6 | one-shot | anticipation, big impact frame, recovery |
| jump | 4-6 | one-shot | launch, apex, fall, land |
| hurt | 3-4 | one-shot | recoil, no mirrored recovery |

Grids, phases and presets: [action-recipes.md](action-recipes.md). Poses and timing:
[animation-planning.md](animation-planning.md).

## Per-action recipe

1. **Guide.** `python "<skill-dir>/scripts/plan_guide.py" --frames N --cycle run --facing right --output-dir <set>/<action>/guide`
   writes `guide.png` (empty grid, feet line, margins) and `prompt.txt`.
2. **Prompt.** Extend the guide's prompt with the master's identity and the absolute phase of
   every frame: "The same `<identity_recap>`, sprite sheet, N frames in one row, frame 1 ...
   frame 2 ... ; same side view and body size in every frame; solid flat pure magenta
   background; no text, no borders."
3. **Generate + commit.** Stage through `route_media.py image --prompt-file <prompt>
   --reference <master>/master.png --reference <guide>/guide.png --out-dir <set>/<action>/raw`,
   call `generate_image` with that prompt and those two references (master FIRST), save the
   result as `<out-dir>/generated.png`, then `route_media.py commit`. LOOK at the sheet with
   `read_file` before processing: identity, facing, frame count, nothing touching cell borders.
4. **Gate.** `sheet_qc.py spill` on the raw sheet; on spill, regenerate with more margin (never
   filter by largest component).
5. **Key, slice, register.** `generate2dsprite.py process --input <sheet> --target asset
   --mode <mode> --rows 1 --cols N --output-dir <set>/<action>/proc --strict-qc`.
6. **Identity + cadence.** `sheet_qc.py frames --sheet <sheet> --rows 1 --cols N --cycle run`;
   a duplicated half-cycle means regenerate the second half.
7. **Scale across the set.** Write the profile once on the grounded action
   (`process --write-scale-profile profiles/<char>.json`), then reuse it for every other action
   (`--scale-profile profiles/<char>.json --max-profile-scale-drift 0.08`).
8. **Game size + root.** `scale_frames.py --frames <proc frames> --root-lock torso-x
   --row-baseline --emit-clips --ticks N --output-dir <set>/<action>/scaled`, later actions add
   `--profile <first>/scale-frames.json --action-padding L,T,R,B`.
9. **Clips.** `build_animation_clips.py --manifest clips.json --output-dir <set>/<action>/clips`
   (timing, loop flags, events like the attack hit).
10. **Look.** `preview_gif.py --frames <scaled frames> --fps 12 --output <set>/<action>/loop.gif`
    (plus `--on-light` / `--on-dark` variants), and watch it with `read_file`.
11. **Export.** `export_engine.py --clips <clips>/animation-clips.json --target all
    --output-dir <set>/<action>/export` (Aseprite JSON, Godot SpriteFrames or Sprite3D).

A set-level lineup GIF (all actions side by side) is made by scaling every action onto one
shared canvas with `scale_frames.py`, then `assemble_frames.py` and `preview_gif.py`.

## Registration and identity rules

- One body scale per character: the master's framing decides it; sheets never re-measure it.
- Registration comes from the pipeline (`process` geometry v2, `--scale-strategy registered` for
  jumps/bob), not from per-frame bounding boxes.
- Facing is stated three ways in every prompt and checked by eye afterwards.
- Keep wide slashes, trails and projectiles OUT of the body sheet; they are separate FX sheets.

## When a sheet keeps failing

- Identity drift: re-state the identity recap verbatim, attach the master again, and if it
  still drifts, lower the ambition of the pose spacing before lowering the identity.
- Frame bleed across cells: ask for wider gutters or fewer frames per row, or slice by
  ownership (`assemble_frames.py --slice ownership`).
- After one fix-by-edit and one regeneration of the same action, tell the user what fails and
  offer codeart2d for that action only ("code-drawn, no image model").
