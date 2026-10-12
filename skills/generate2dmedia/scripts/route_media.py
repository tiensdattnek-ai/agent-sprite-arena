#!/usr/bin/env python3
"""The one media command of the Forge skills, Arena Edition.

The Arena agent's only image route is its own ``generate_image`` tool, and it
has NO image-to-video route at all. This script is the deterministic protocol
glue around that tool: it prepares every generation (prompt file, references,
job record), records every committed artifact (sha256, size, ledger line) and
answers capability questions - so the rest of the Forge pipeline keeps the
same one-line JSON contract it has always had.

The protocol, in three steps (images only):

  1. stage    route_media.py image --prompt-file p.txt --reference r.png --out-dir D
              -> stages prompt.txt and the references in D, writes D/job.json,
                 prints one JSON line with status "agent-request" and exits 4.
  2. agent    The Arena agent calls its own generate_image tool with that
              prompt (and those references in that order) and saves the result
              as D/generated.png. No script can do this step: the image tool
              belongs to the agent, not to Python.
  3. commit   route_media.py commit --out-dir D
              -> checks the artifact, records sha256/size, appends the ledger
                 line, prints the canonical one-line JSON (status ok, route
                 arena:generate_image) and exits 0.

Video: there is no route. `resolve --kind video` and `video ...` answer
no-route and exit 3, exactly like the classic no-route case, with the Arena
fallback named: sprite sheets from generate2dsprite, a user-supplied clip for
video2dsprite, or codeart2d on request.

Verbs:
  resolve       Which route would run (--kind image|video).
  image         Stage one image job (prompt + references) for the agent.
  commit        Verify and record the agent's generated artifact.
  video         Always no-route on Arena (exit 3); prints the fallback.

Every success prints one ASCII JSON line and exits 0; staging prints one JSON
line and exits 4 (agent action required); no-route prints one JSON line and
exits 3; errors print 'error: ...' and exit 1; usage errors exit 2.
Stdlib only (Pillow is used for the committed artifact's size when present).
The ledger lives at <project>/.forge/ledger.jsonl (append-only).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

TOOL_NAME = "route_media"
FORGE_PACKAGE_VERSION = "0.5.0-arena"
TOOL_VERSION = FORGE_PACKAGE_VERSION
IMAGE_ROUTE = "arena:generate_image"
LEDGER_PATH = Path(".forge") / "ledger.jsonl"
SIZE_RE = re.compile(r"^(\d{1,5})[xX](\d{1,5})$")

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_NO_ROUTE = 3
EXIT_AGENT_REQUIRED = 4

VIDEO_FALLBACK = ("Animate with sprite sheets from the approved master still "
                  "(generate2dsprite), process a user-supplied clip or frames "
                  "(video2dsprite), or code-drawn animation on request (codeart2d).")

GENERATED_NAME = "generated.png"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _image_size(path: Path) -> tuple[int | None, int | None]:
    try:
        from PIL import Image  # optional: a committed artifact still records without it
        with Image.open(path) as im:
            return im.width, im.height
    except Exception:
        return None, None


def _fail(message: str) -> int:
    print(json.dumps({"status": "error", "error": message}, ensure_ascii=True))
    print("error: " + message, file=sys.stderr)
    return EXIT_ERROR


def _append_ledger(record: dict[str, Any]) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")


def cmd_resolve(args: argparse.Namespace) -> int:
    if args.kind == "image":
        print(json.dumps({
            "status": "ok", "kind": "image", "route": IMAGE_ROUTE,
            "agentTool": "generate_image",
            "note": "The Arena agent calls its own generate_image tool; this script stages and commits.",
        }, ensure_ascii=True))
        return EXIT_OK
    print(json.dumps({
        "status": "no-route", "kind": "video", "route": None,
        "reason": "the Arena agent has no image-to-video tool",
        "fallback": VIDEO_FALLBACK,
    }, ensure_ascii=True))
    return EXIT_NO_ROUTE


def cmd_image(args: argparse.Namespace) -> int:
    out = Path(args.out_dir)
    if out.exists():
        return _fail(f"--out-dir must not exist yet: {out}")
    prompt_file = Path(args.prompt_file)
    if not prompt_file.is_file():
        return _fail(f"--prompt-file not found: {prompt_file}")
    prompt = prompt_file.read_text(encoding="utf-8").strip()
    if not prompt:
        return _fail(f"--prompt-file is empty: {prompt_file}")
    if args.size and not SIZE_RE.match(args.size):
        return _fail(f"--size must be WxH, e.g. 1024x1024; got {args.size!r}")

    references: list[str] = []
    for ref in args.reference or []:
        rp = Path(ref)
        if not rp.is_file():
            return _fail(f"--reference not found: {rp}")
        references.append(str(rp))

    out.mkdir(parents=True)
    (out / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    staged_refs: list[str] = []
    for i, ref in enumerate(references, 1):
        rp = Path(ref)
        dest = out / f"reference{i:02d}{rp.suffix.lower() or '.png'}"
        dest.write_bytes(rp.read_bytes())
        staged_refs.append(dest.name)

    job = {
        "schema": "generate2dmedia.job.v1",
        "kind": "image",
        "route": IMAGE_ROUTE,
        "status": "agent-request",
        "createdAt": _now(),
        "promptFile": "prompt.txt",
        "promptSha256": _sha256(out / "prompt.txt"),
        "references": staged_refs,
        "size": args.size,
        "expectedArtifact": GENERATED_NAME,
    }
    (out / "job.json").write_text(json.dumps(job, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": "agent-request",
        "kind": "image",
        "route": IMAGE_ROUTE,
        "job": str(out / "job.json"),
        "prompt": str(out / "prompt.txt"),
        "references": [str(out / name) for name in staged_refs] or references,
        "size": args.size,
        "next": ("Arena agent: call your generate_image tool with this prompt"
                 + (" and these references, in this order" if references else "")
                 + f"; save the result as {out / GENERATED_NAME}; then run: "
                   f"python route_media.py commit --out-dir {out}"),
    }, ensure_ascii=True))
    return EXIT_AGENT_REQUIRED


def cmd_commit(args: argparse.Namespace) -> int:
    out = Path(args.out_dir)
    job_path = out / "job.json"
    if not job_path.is_file():
        return _fail(f"no staged job: {job_path} (run 'route_media.py image' first)")
    job = json.loads(job_path.read_text(encoding="utf-8"))
    artifact = Path(args.artifact) if args.artifact else out / str(job.get("expectedArtifact") or GENERATED_NAME)
    if not artifact.is_file():
        return _fail(f"artifact missing: {artifact} (the agent must save its generate_image result there)")
    try:
        from PIL import Image
        with Image.open(artifact) as im:
            im.verify()
    except ImportError:
        pass
    except Exception as exc:
        return _fail(f"artifact is not a readable image: {artifact} ({exc})")

    sha = _sha256(artifact)
    width, height = _image_size(artifact)
    job.update(status="committed", committedAt=_now(), artifact=artifact.name, sha256=sha,
               width=width, height=height)
    job_path.write_text(json.dumps(job, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    _append_ledger({
        "ts": _now(), "tool": TOOL_NAME, "kind": job.get("kind", "image"), "route": IMAGE_ROUTE,
        "status": "done", "artifact": str(artifact), "sha256": sha,
        "promptSha256": job.get("promptSha256"), "estimateUsd": None,
    })
    print(json.dumps({
        "status": "ok", "route": IMAGE_ROUTE, "artifact": str(artifact),
        "sha256": sha, "width": width, "height": height, "estimateUsd": None,
    }, ensure_ascii=True))
    return EXIT_OK


def cmd_video(args: argparse.Namespace) -> int:
    print(json.dumps({
        "status": "no-route", "kind": "video", "route": None,
        "reason": "the Arena agent has no image-to-video tool",
        "fallback": VIDEO_FALLBACK,
        "promptFile": args.prompt_file,
    }, ensure_ascii=True))
    return EXIT_NO_ROUTE


def _add_legacy_compat(parser: argparse.ArgumentParser) -> None:
    """Flags upstream callers pass; accepted and recorded, but they select nothing on Arena."""
    parser.add_argument("--route", help="accepted for interface parity (the only route is arena:generate_image)")
    parser.add_argument("--model", help="accepted for interface parity (the agent's tool chooses)")
    parser.add_argument("--tier", help="accepted for interface parity (unused)")
    parser.add_argument("--provider-option", action="append", help="accepted for interface parity (unused)")
    parser.add_argument("--dry-run", action="store_true", help="accepted for interface parity (staging is free)")
    parser.add_argument("--budget-usd", help="accepted for interface parity (no money on Arena)")
    parser.add_argument("--max-calls", help="accepted for interface parity (unused)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="Arena route layer: stages image jobs for the agent's generate_image tool, "
                    "commits the results, and answers no-route for video.")
    parser.add_argument("--version", action="version", version=f"{TOOL_NAME} {TOOL_VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    pr = sub.add_parser("resolve", help="say which route would run")
    pr.add_argument("--kind", choices=("image", "video"), required=True)
    pr.add_argument("--references", type=int, default=0, help="accepted for interface parity (unused)")
    pr.set_defaults(func=cmd_resolve)

    pi = sub.add_parser("image", help="stage one image job for the agent (exits 4: agent action required)")
    pi.add_argument("--prompt-file", required=True, help="UTF-8 prompt text")
    pi.add_argument("--reference", action="append", help="reference image, repeatable, in prompt order")
    pi.add_argument("--size", help="requested size WxH (recorded; the agent's tool decides the real size)")
    pi.add_argument("--out-dir", required=True, help="new folder for the staged job (must not exist)")
    _add_legacy_compat(pi)
    pi.set_defaults(func=cmd_image)

    pc = sub.add_parser("commit", help="verify and record the agent's generated artifact")
    pc.add_argument("--out-dir", required=True, help="the staged job folder")
    pc.add_argument("--artifact", help=f"the image file (default: <out-dir>/{GENERATED_NAME})")
    pc.set_defaults(func=cmd_commit)

    pv = sub.add_parser("video", help="always no-route on Arena (exit 3)")
    pv.add_argument("--prompt-file", help="recorded in the answer for provenance")
    pv.add_argument("--reference", action="append", help="accepted for interface parity (unused)")
    pv.add_argument("--last-frame", help="accepted for interface parity (unused)")
    pv.add_argument("--duration", help="accepted for interface parity (unused)")
    pv.add_argument("--resolution", help="accepted for interface parity (unused)")
    pv.add_argument("--out-dir", help="accepted for interface parity (unused)")
    _add_legacy_compat(pv)
    pv.set_defaults(func=cmd_video)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _fail(str(exc))


if __name__ == "__main__":
    sys.exit(main())
