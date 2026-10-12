# Route media — Arena Edition

The Arena route layer in full. One image route (the agent's own `generate_image` tool), no video
route, and a three-step protocol that keeps provenance exact. Everything here is deterministic
Python except step 2, which belongs to the agent.

## Why a protocol around a tool call?

The Forge pipeline gates, keys, registers and packages art; it must be able to prove where every
artifact came from. `route_media.py` therefore brackets the agent's tool call:

1. **Stage** — the owning skill writes the prompt file; `route_media.py image` copies it and the
   references into a new `--out-dir` and freezes a `job.json` (`generate2dmedia.job.v1`) with the
   prompt hash and the reference list. It prints one JSON line and exits **4** ("agent action
   required"), which is neither success nor failure.
2. **Generate** — the Arena agent calls `generate_image` with that prompt (and those references,
   in order, through the tool's `images` parameter) and saves the result as
   `<out-dir>/generated.png`. Python cannot do this step and never pretends to.
3. **Commit** — `route_media.py commit --out-dir <staged>` verifies the artifact is a readable
   image, records `sha256`, width and height, updates `job.json` to `committed`, appends the
   ledger line and prints the canonical one-line JSON (exit 0). That line is the only accepted
   proof of a generation.

Exit codes: `0` committed/resolved, `1` error (`error: ...` on stderr), `2` usage, `3` no route
(video, always), `4` staged, agent action required.

## Commands

```text
python "<skill-dir>/scripts/route_media.py" resolve --kind image
python "<skill-dir>/scripts/route_media.py" resolve --kind video
python "<skill-dir>/scripts/route_media.py" image --prompt-file p.txt [--reference r.png ...] \
       [--size 1024x1024] --out-dir media/take1
python "<skill-dir>/scripts/route_media.py" commit --out-dir media/take1 [--artifact path.png]
python "<skill-dir>/scripts/route_media.py" video --prompt-file p.txt        # always no-route
```

### JSON lines

Staged image (exit 4):

```json
{"status": "agent-request", "kind": "image", "route": "arena:generate_image",
 "job": "media/take1/job.json", "prompt": "media/take1/prompt.txt",
 "references": ["media/take1/reference01.png"], "size": "1024x1024", "next": "..."}
```

Committed image (exit 0):

```json
{"status": "ok", "route": "arena:generate_image", "artifact": "media/take1/generated.png",
 "sha256": "...", "width": 1024, "height": 1024, "estimateUsd": null}
```

Video or `resolve --kind video` (exit 3):

```json
{"status": "no-route", "kind": "video", "route": null,
 "reason": "the Arena agent has no image-to-video tool",
 "fallback": "Animate with sprite sheets from the approved master still (generate2dsprite), process a user-supplied clip or frames (video2dsprite), or code-drawn animation on request (codeart2d)."}
```

## Rules for the agent

- One `generate_image` call per staged job. A sprite sheet is one image that contains a grid;
  never ask for several separate images in one call.
- Pass staged references through the tool's `images` parameter in the same order; for a fix-by-
  edit, the approved image is FIRST and the prompt says "Reproduce the FIRST image exactly ...
  THE ONLY CHANGE: ...".
- Always `read_file` the generated PNG before approving; identity, facing and text artifacts are
  visual checks.
- Commit before processing. Anything uncommitted has no provenance and must not be reported as a
  finished generation.
- `--size` is a request recorded for the prompt; the commit line carries the real size. Report
  the real one.
- The ledger is append-only; never edit it by hand. `estimateUsd` is always null (no money on
  Arena) — counts are the currency.

## forge_doctor

`forge_doctor.py --host-tools generate_image` prints CHECKS (python, numpy, Pillow, scipy,
optional ffmpeg, stdout encoding) and ROUTES (`arena:generate_image` OK when declared, video
MISSING with the fallback as remedy). Exit 1 when a check FAILs. `--save <dir>/doctor.json`
keeps the machine-readable report; `--no-exec` skips the ffmpeg probe.

## What this edition removed

The paid-API providers (OpenAI, Gemini, xAI, BytePlus, fal.ai), the Codex/Grok CLI routes, the
config file with API keys, the price table and the image-to-video route are all gone: none of
them exist for an Arena agent. The deterministic pipeline of the other skills is unchanged.
