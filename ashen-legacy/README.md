# Ashen Legacy — ashen-fox run cycle (pixel)

Tạo bằng skill Agent Sprite Forge — Arena Edition (route `arena:generate_image`), 2026-10-12.
Game tham chiếu: Ashen Legacy (pixel action RPG, dark fantasy) => `finish: pixel`, thân 80 px,
palette chung 24 màu (OKLab k-means), alpha binary.

## Pipeline (mỗi bước 1 dòng JSON, xem job.json để có sha256 provenance)

1. `master_still.py prompt` (spec `fox-spec.json`) -> generate_image -> duyệt bằng mắt ->
   `approve --route arena:generate_image` (0 warnings) => `art/master/ashen/`.
2. `plan_guide.py --frames 4 --cycle run` (grid 2x2).
3. Sheet attempts:
   - take1: spill FAIL `sheet_edge` (đuôi chạm mép) -> fix-by-edit;
   - take2: spill pass, nhưng `sheet_qc frames` FAIL `leg_alternation` (FAR limbs không tối hơn);
   - take3 (chốt): spill warn `safe_frame`; process qa **pass**; frames **không còn fail**
     (warns: phase_coverage, torso_drift, row_baseline).
4. `scale_frames.py` (80 px, box, root-lock torso-x, shifts <= 2 px) -> `palette_tool build/apply`
   (24 màu) -> `build_animation_clips.py` (8 ticks @60Hz, loop cycle) ->
   `export_engine.py --target all` => Aseprite JSON + Godot SpriteFrames + Sprite3D.
5. `preview_gif.py` => `ashen-fox-run-final.gif` (xem trên nền tối: `--on-dark`).

## File chính

- `art/master/ashen/master.png|master.json` — master đã duyệt
- `art/set/run/pixelset3/frames/walk-1..4.png` — frame runtime (palette chung)
- `art/set/run/palette3/palette.gpl` — palette dùng chung cho các action sau
- `art/set/run/export3/` — aseprite/, godot/, godot-sprite3d/
- `art/set/run/ashen-fox-run-final.gif` — preview loop

## Giới hạn đã biết (QC warns giữ nguyên văn)

- `safe_frame` (spill), `phase_coverage`, `torso_drift`, `row_baseline` (frames): chu kỳ 4 pose
  thưa; bước chạy đọc ổn ở 10 fps nhưng muốn mượt hơn nên sinh sheet 8 pose rồi chọn vòng lặp
  bằng `gait_loop.py`.
- Không có route video: đây là route sheet theo thiết kế Arena Edition.
