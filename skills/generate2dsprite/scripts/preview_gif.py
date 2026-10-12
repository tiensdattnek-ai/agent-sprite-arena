#!/usr/bin/env python3
"""A quick animated GIF preview of frames, to LOOK at motion before approving.

  preview_gif.py --frames <dir-or-png ...> --fps 12 --output <loop.gif> [--scale 2]
                 [--loop 0] [--on-light] [--on-dark]

Frames are read in name order from a directory, or taken as explicit PNG paths.
`--scale` is nearest-neighbour (pixel-safe). `--on-light` / `--on-dark` composite
the transparent frames over a flat backdrop so alpha edges are visible in a GIF
(viewers ignore alpha). Prints one JSON line: {"status":"ok","gif":...,"frames":N,
"fps":N,"size":[w,h]}. Errors print 'error: ...' and exit 1; usage errors exit 2.
Needs Pillow only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

TOOL_NAME = "preview_gif"


def collect_frames(paths: Sequence[str]) -> list[Path]:
    frames: list[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            frames.extend(sorted(x for x in path.iterdir()
                                  if x.suffix.lower() == ".png" and x.is_file()))
        elif path.is_file():
            frames.append(path)
        else:
            raise ValueError(f"not a frame or a directory of frames: {path}")
    return frames


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=TOOL_NAME, description="GIF preview of frames.")
    parser.add_argument("--frames", nargs="+", required=True,
                        help="a directory of PNGs and/or explicit PNG paths")
    parser.add_argument("--fps", type=float, default=12.0, help="playback speed (default 12)")
    parser.add_argument("--output", required=True, help="the GIF to write (must not exist)")
    parser.add_argument("--scale", type=int, default=1, help="nearest-neighbour upscale (default 1)")
    parser.add_argument("--loop", type=int, default=0, help="GIF loop count (0 = forever)")
    parser.add_argument("--on-light", action="store_true", help="composite over light grey")
    parser.add_argument("--on-dark", action="store_true", help="composite over dark grey")
    args = parser.parse_args(argv)

    try:
        from PIL import Image
    except ImportError:
        print("error: Pillow is required: python -m pip install Pillow", file=sys.stderr)
        return 1

    out = Path(args.output)
    if out.exists():
        print(f"error: --output must not exist yet: {out}", file=sys.stderr)
        return 1
    if args.fps <= 0:
        print("error: --fps must be positive", file=sys.stderr)
        return 1
    if args.on_light and args.on_dark:
        print("error: pick at most one of --on-light / --on-dark", file=sys.stderr)
        return 1

    try:
        frame_paths = collect_frames(args.frames)
        if not frame_paths:
            raise ValueError("no PNG frames found")
        ims = [Image.open(p).convert("RGBA") for p in frame_paths]
        if args.scale > 1:
            ims = [im.resize((im.width * args.scale, im.height * args.scale), Image.NEAREST)
                   for im in ims]
        if args.on_light or args.on_dark:
            bg = (235, 235, 235, 255) if args.on_light else (32, 32, 32, 255)
            flat = []
            for im in ims:
                base = Image.new("RGBA", im.size, bg)
                base.alpha_composite(im)
                flat.append(base)
            ims = flat
        gifs = [im.convert("P", palette=Image.ADAPTIVE, colors=255) for im in ims]
        duration = max(20, round(1000.0 / args.fps))
        out.parent.mkdir(parents=True, exist_ok=True)
        gifs[0].save(out, save_all=True, append_images=gifs[1:], duration=duration,
                     loop=args.loop, disposal=2, transparency=255)
        print(json.dumps({"status": "ok", "gif": str(out), "frames": len(gifs),
                          "fps": args.fps, "size": [ims[0].width, ims[0].height]},
                         ensure_ascii=True))
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
