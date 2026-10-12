# Changelog

## 0.5.0-arena — Arena Edition

Fork của 0.4.0 chỉnh lại cho agent trên Arena.ai: route layer, tài liệu skill và các phần phụ
thuộc provider được thay bằng chính bộ công cụ của agent; toolchain xử lý ảnh tất định giữ nguyên.

### Added

- `generate2dmedia/scripts/route_media.py` (viết lại): giao thức ba bước cho route ảnh duy nhất
  `arena:generate_image` — `image` stage job (exit 4, `agent-request`), agent gọi `generate_image`,
  `commit` ghi sha256/kích thước và dòng ledger chuẩn; `resolve`/`video` trả `no-route` (exit 3)
  kèm fallback. Các cờ legacy (`--route`, `--model`, `--tier`, `--dry-run`, ...) được chấp nhận
  để tương thích interface.
- `generate2dmedia/scripts/forge_doctor.py` (viết lại): CHECKS (python, numpy, Pillow, scipy,
  ffmpeg tuỳ chọn, encoding) + ROUTES (`arena:generate_image`, video MISSING kèm remedy).
- `generate2dmedia/scripts/media_ledger.py` (viết lại): `summary`/`show` cho ledger lượt sinh.
- `generate2dsprite/scripts/preview_gif.py`: xem nhanh chuyển động bằng GIF (Pillow).
- `generate2dsprite/references/sheet-set-handoff.md`: quy trình master still → bộ action bằng sheet.
- `tests/test_arena_route.py` cho toàn bộ route layer mới.

### Changed

- `generate2dsprite/SKILL.md`: route ảnh = `generate_image`; master still theo flow
  `prompt` → agent sinh take → `approve --still --route arena:generate_image`; hoạt hình nhân vật
  bằng một sheet mỗi action.
- `video2dsprite/SKILL.md`: skill chỉ xử lý (không bao giờ sinh) — clip/frame người dùng đưa vào,
  frame từ sheet, frame code-drawn; ffmpeg tuỳ chọn.
- `generate2dmap/SKILL.md`, `codeart2d/SKILL.md`, các reference (master-still, prompt-rules,
  character-animation): route Arena thay cho API/CLI.
- README viết lại (tiếng Việt); CHANGELOG mới; bỏ tài liệu validation cũ và showcase media.

### Removed

- Các provider API (OpenAI, Gemini, xAI, BytePlus, fal.ai): `generate_media.py`,
  `media_providers.py`, `media_config.py`, `media_mp4.py`, `cli_media.py`, bảng giá, capabilities.
- Route image-to-video và bộ điều phối clip `video2dsprite/scripts/sprite_set.py`
  (không có gì để sinh video trên Arena).
- `.claude-plugin/`, `skills/*/agents/openai.yaml`, các README ngôn ngữ khác, `docs/`, `src/` media.
- Tests của các phần đã bỏ (`test_generate2dmedia`, `test_route_media`, `test_cli_media`,
  `test_forge_doctor`, `test_media_ledger`, `test_media_providers_*`, `test_sprite_set`).

## 0.4.0 — 2026-10-06 — bản gốc

Xem lịch sử tại repo thượng nguồn
[0x0funky/agent-sprite-forge](https://github.com/0x0funky/agent-sprite-forge) (commit 5324342).
