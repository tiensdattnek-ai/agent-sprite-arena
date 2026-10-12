# Demo: live validation of the Arena Edition

Chạy thật 2026-10-12 bằng chính bộ công cụ của agent Arena (route `arena:generate_image`),
không mock:

1. `master_still.py prompt` -> `generate_image` (nền magenta) -> duyệt bằng mắt ->
   `master_still.py approve --route arena:generate_image` => `art/master/fox/` (framing hero
   788 px, 1 warning: subject upscale x1.15).
2. `plan_guide.py --frames 4 --cycle run` -> sinh sheet 2x2 với master + guide làm reference.
   - take 1 (2x5 sai grid) bị `sheet_qc.py spill` bắt `cross_cell_components`;
   - take 2 (3x3 sai grid) bị bắt tiếp;
   - take 4 pass: spill warn `safe_frame`, `process` qa_status **pass**, root shifts [0,0].
3. `scale_frames.py` (thân 96 px, anchor chân) -> `build_animation_clips.py` ->
   `export_engine.py --target all` => Aseprite JSON + Godot SpriteFrames + Sprite3D
   (`art/set/run/export4/`).
4. `preview_gif.py` => `run-loop-v2.gif` (loop walk trong suốt, sạch).

Provenance: mọi generation đều có dòng commit sha256 trong `art/**/job.json`
(ledger `.forge/` bị .gitignore theo đúng thiết kế upstream).
