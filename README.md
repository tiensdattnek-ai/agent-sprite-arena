# Agent Sprite Forge — Arena Edition

Bản fork của [0x0funky/agent-sprite-forge](https://github.com/0x0funky/agent-sprite-forge) (MIT)
đã được chỉnh lại để **hợp 100% với agent trên Arena.ai**: một bộ skill tạo sprite sheet, frame PNG
trong suốt, GIF động và gói xuất engine (Godot / Aseprite / web) từ prompt.

> Một ảnh tĩnh được duyệt → cả bộ sprite sẵn sàng cho game: vẫn là triết lý của bản gốc,
> nhưng mọi bước sinh ảnh đi qua đúng một công cụ mà agent Arena có — `generate_image`.

## Điểm khác biệt so với bản gốc (0.4.0)

| Bản gốc (Claude Code / Codex / Grok) | Arena Edition |
|---|---|
| Route ảnh: API key (OpenAI, Gemini, xAI, BytePlus, fal.ai) → CLI Codex/Grok → code art | **Chỉ một route: `generate_image` của agent**, staged + commit qua `route_media.py` (sha256, ledger) |
| Hoạt hình nhân vật: 1 clip **image-to-video** mỗi action (Grok/xAI video) | **Không có video**: 1 **sprite sheet** mỗi action sinh từ master still, pipeline xử lý frame giữ nguyên |
| `sprite_set.py` điều phối clip + retake tự động | Đã bỏ; thay bằng quy trình sheet trong `generate2dsprite` (hướng dẫn ở `sheet-set-handoff.md`) |
| `forge_doctor` dò API key, CLI, bậc thang VERIFIED | `forge_doctor` mới: python/numpy/Pillow/scipy, ffmpeg tuỳ chọn, route `arena:generate_image` |
| Ledger chi tiêu USD | Ledger số lượt sinh (Arena không trả tiền API): `.forge/ledger.jsonl` |
| Video2dsprite xử lý clip từ provider | Giữ nguyên cho **clip/frame người dùng đưa vào** + finishing (key, register, loop, retime, colour lock, đóng gói) |

Phần còn lại — toàn bộ toolchain Python tất định (keying soft-matte, cắt/đăng ký frame, chọn vòng
lặp, retime, palette/pixel finish, QC sheet, xuất engine, codeart2d, bản đồ/tilemap) — **giữ nguyên
không sửa**, vì nó chạy độc lập với nơi sinh ảnh.

## Năm skill

| Skill | Dùng khi |
|---|---|
| `generate2dsprite` | Nhân vật, creature, prop, icon, FX: master still + sheet theo action → frame → clip → xuất engine |
| `generate2dmap` | Map, level, tilemap, prop pack, parallax, plate HD-2D + dữ liệu collision/nav, xuất Tiled/Godot/LDtk |
| `video2dsprite` | Clip hoặc bộ frame **có sẵn** → key, đăng ký, loop/retime, finish, đóng gói (ffmpeg tuỳ chọn) |
| `generate2dmedia` | Lớp route Arena: stage job → agent gọi `generate_image` → commit (provenance, ledger), doctor |
| `codeart2d` | Vẽ art bằng code (PixelSpec/SVG/rig/FX/autotile) — chỉ khi người dùng yêu cầu hoặc không có image tool |

## Cài đặt trong workspace Arena

```bash
python -m pip install -r requirements.txt        # numpy, Pillow, scipy
python skills/generate2dmedia/scripts/forge_doctor.py --host-tools generate_image
```

Không cần "cài skill" vào thư mục host nào cả: agent Arena đọc trực tiếp các file `SKILL.md`
trong repo này và chạy tool bằng Bash từ thư mục project của người dùng.
(`tools/install_skills.py --dest <thư mục>` vẫn hoạt động nếu muốn copy bộ skill đi nơi khác.)

## Quy trình nhanh (nhân vật)

1. **Master still**: `master_still.py prompt --spec <json>` → agent gọi `generate_image` với
   prompt đó (nền magenta phẳng) → duyệt bằng mắt (`read_file`) →
   `master_still.py approve --run <dir> --still <take.png> --route arena:generate_image`
   → `master.png` + `master.json`.
2. **Mỗi action**: `plan_guide.py --frames N --cycle run` → sinh sheet với master + guide làm
   reference (stage/commit qua `route_media.py`) → `sheet_qc.py spill` →
   `generate2dsprite.py process` → `sheet_qc.py frames` → `scale_frames.py` (profile chung) →
   `build_animation_clips.py` → `export_engine.py`.
3. **Nhìn kết quả**: `preview_gif.py --frames <dir> --fps 12 --output loop.gif` rồi xem bằng `read_file`.
4. Chi tiết đầy đủ: [`skills/generate2dsprite/SKILL.md`](skills/generate2dsprite/SKILL.md) và
   [`references/sheet-set-handoff.md`](skills/generate2dsprite/references/sheet-set-handoff.md).

## Giới hạn đã biết trên Arena

- **Không sinh được video**: mọi yêu cầu "làm clip động" được trả lời bằng route sheet ở trên,
  hoặc đề nghị người dùng đưa clip có sẵn (xử lý bằng `video2dsprite`).
- **ffmpeg không có sẵn** trong sandbox: ảnh/GIF/atlas PNG/JSON engine không cần; chỉ clip đầu
  vào và đóng gói WebM/MP4 mới cần (cài theo yêu cầu, hoặc bỏ qua và nói rõ).
- Chất lượng sheet phụ thuộc model ảnh của `generate_image`; QC số (sheet_qc, matte report) chỉ
  bắt triệu chứng — identity/bố cục luôn phải kiểm tra bằng mắt.

## Kiểm thử

```bash
python -m pip install -r requirements-dev.txt
pytest                                   # bỏ qua các test cần ffmpeg/node/resvg khi thiếu
```

## Giấy phép & nguồn gốc

MIT — bản gốc của 0x0funky (các commit tới 5324342, 2026-10-06). Bản Arena Edition chỉnh lại
lớp route, tài liệu skill và bỏ các phần phụ thuộc provider; không sửa logic xử lý ảnh.
