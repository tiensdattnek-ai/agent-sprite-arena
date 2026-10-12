#!/usr/bin/env python3
"""Report what the Arena agent's Forge skills can do on this machine.

Stdlib only and read-only: it sends no request and generates nothing. Run it
once per session from the project root and declare the media tools YOU (the
calling agent) actually have; a script cannot see them:

  python "<skill-dir>/scripts/forge_doctor.py" --host-tools generate_image
  python "<skill-dir>/scripts/forge_doctor.py" --host-tools none --json --save outputs/doctor.json

On Arena the route table is short by design:
  1. arena:generate_image - the agent's own generate_image tool (images only).
     OK when declared via --host-tools generate_image; AGENT otherwise.
  2. video - MISSING: the Arena agent has no image-to-video tool. Remedy:
     sprite sheets from the master still (generate2dsprite), a user-supplied
     clip (video2dsprite), or code-drawn animation on request (codeart2d).

Checks: python version, numpy, Pillow, scipy (WARN when absent), optional
ffmpeg 5.1+ (needed only for user-supplied clips and WebM/MP4 packaging),
stdout encoding. Every check has one status: OK; WARN; FAIL (with remedy);
MISSING; AGENT (only the calling agent knows). Exit status 1 when any check
FAILs (the report is still printed).
"""
from __future__ import annotations

import argparse
import codecs
import json
import locale
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

TOOL_NAME = "forge_doctor"
FORGE_PACKAGE_VERSION = "0.5.0-arena"
TOOL_VERSION = FORGE_PACKAGE_VERSION
DOCTOR_SCHEMA = "generate2dmedia.doctor.arena.v1"
SKILLS = ("generate2dsprite", "generate2dmap", "video2dsprite", "generate2dmedia", "codeart2d")
PYTHON_MIN = (3, 10)
FFMPEG_MIN = (5, 1)
KNOWN_HOST_TOOLS = ("generate_image", "none")


def _check_python() -> dict[str, Any]:
    ok = sys.version_info >= PYTHON_MIN
    return {"name": "python", "status": "OK" if ok else "FAIL",
            "found": platform.python_version(),
            "required": ".".join(map(str, PYTHON_MIN)) + "+",
            "remedy": None if ok else "run these skills on Python 3.10+"}


def _check_module(module: str, required: bool) -> dict[str, Any]:
    try:
        mod = __import__(module)
        return {"name": module, "status": "OK", "found": getattr(mod, "__version__", "present")}
    except ImportError:
        if required:
            return {"name": module, "status": "FAIL", "found": None,
                    "remedy": f'python -m pip install "{module}"'}
        return {"name": module, "status": "WARN", "found": None,
                "remedy": f'optional but recommended: python -m pip install "{module}"'}


def _ffmpeg_version(exe: str) -> str | None:
    try:
        out = subprocess.run([exe, "-version"], capture_output=True, text=True, timeout=20,
                             stdin=subprocess.DEVNULL)
        m = re.search(r"ffmpeg version (\d+)\.(\d+)", out.stdout or "")
        return f"{m.group(1)}.{m.group(2)}" if m else None
    except Exception:
        return None


def _check_ffmpeg() -> dict[str, Any]:
    exe = shutil.which("ffmpeg")
    if not exe:
        return {"name": "ffmpeg", "status": "WARN", "found": None,
                "remedy": "optional: only user-supplied clips (extract) and WebM/MP4 packaging need it; "
                          "sheets, GIFs, PNG atlases and engine JSON never do"}
    version = _ffmpeg_version(exe)
    if version is None:
        return {"name": "ffmpeg", "status": "WARN", "found": exe, "remedy": "cannot read the version"}
    nums = tuple(int(p) for p in version.split("."))
    ok = nums >= FFMPEG_MIN
    return {"name": "ffmpeg", "status": "OK" if ok else "FAIL", "found": version,
            "required": ".".join(map(str, FFMPEG_MIN)) + "+",
            "remedy": None if ok else "upgrade ffmpeg"}


def _check_encoding() -> dict[str, Any]:
    enc = (sys.stdout.encoding or "").lower()
    probe = codecs.lookup("utf-8")
    ok = probe is not None
    roundtrip = None
    try:
        roundtrip = "forge-\u00e9\u00fc".encode(sys.stdout.encoding or "utf-8", "replace").decode(
            sys.stdout.encoding or "utf-8", "replace")
    except Exception:
        pass
    status = "OK" if (enc.replace("-", "") in ("utf8", "utf8sig") or roundtrip) else "WARN"
    return {"name": "encoding.stdout", "status": status, "found": sys.stdout.encoding,
            "locale": locale.getlocale(),
            "remedy": None if status == "OK" else "set PYTHONUTF8=1"}


def build_report(host_tools: Sequence[str], do_exec: bool) -> dict[str, Any]:
    declared = {t.strip() for t in host_tools if t.strip() and t.strip() != "none"}
    checks = [_check_python(), _check_module("numpy", True), _check_module("PIL", True),
              _check_module("scipy", False)]
    if do_exec:
        checks.append(_check_ffmpeg())
    else:
        checks.append({"name": "ffmpeg", "status": "WARN", "found": None,
                       "remedy": "re-run without --no-exec to probe ffmpeg"})
    checks.append(_check_encoding())

    has_image_tool = "generate_image" in declared
    routes = [
        {"route": "arena:generate_image", "kind": "image",
         "status": "OK" if has_image_tool else "AGENT",
         "detail": ("declared by the calling agent" if has_image_tool else
                    "declare it with --host-tools generate_image if your tool list has it")},
        {"route": None, "kind": "video", "status": "MISSING",
         "detail": "the Arena agent has no image-to-video tool",
         "remedy": ("animate with sprite sheets from the master still (generate2dsprite), "
                    "a user-supplied clip (video2dsprite), or code-drawn animation (codeart2d)")},
    ]
    failed = [c for c in checks if c["status"] == "FAIL"]
    return {
        "schema": DOCTOR_SCHEMA,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "hostTools": sorted(declared) or ["none"],
        "checks": checks,
        "routes": routes,
        "routeOrder": ["arena:generate_image"] if has_image_tool else [],
        "skills": list(SKILLS),
        "exitStatus": 1 if failed else 0,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [f"Agent Sprite Forge (Arena Edition) doctor {report['tool']['version']}",
             f"python {report['python']} on {report['platform']}",
             f"host tools: {', '.join(report['hostTools'])}", "", "CHECKS"]
    for c in report["checks"]:
        found = c.get("found") or "-"
        line = f"  [{c['status']:7s}] {c['name']}: {found}"
        if c.get("required"):
            line += f" (needs {c['required']})"
        if c.get("remedy"):
            line += f" -> {c['remedy']}"
        lines.append(line)
    lines += ["", "ROUTES"]
    for r in report["routes"]:
        name = r["route"] or f"({r['kind']} route)"
        line = f"  [{r['status']:7s}] {name}: {r.get('detail', '')}"
        if r.get("remedy"):
            line += f" -> {r['remedy']}"
        lines.append(line)
    lines += ["", f"route order: {' > '.join(report['routeOrder']) or 'none declared'}"]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=TOOL_NAME, description=__doc__.splitlines()[0])
    parser.add_argument("--host-tools", default="none",
                        help="comma list of media tools in the calling agent's tool list "
                             "(generate_image, or none)")
    parser.add_argument("--json", action="store_true", help="print the JSON report")
    parser.add_argument("--save", help="also write the JSON report to this path")
    parser.add_argument("--no-exec", action="store_true", help="skip the ffmpeg probe")
    parser.add_argument("--version", action="version", version=f"{TOOL_NAME} {TOOL_VERSION}")
    args = parser.parse_args(argv)

    unknown = [t for t in (args.host_tools or "").split(",")
               if t.strip() and t.strip() != "none" and t.strip() not in KNOWN_HOST_TOOLS]
    if unknown:
        print(f"error: unknown host tools: {', '.join(unknown)} (known: {', '.join(KNOWN_HOST_TOOLS)})",
              file=sys.stderr)
        return 2

    report = build_report(args.host_tools.split(","), do_exec=not args.no_exec)
    if args.save:
        save_path = Path(args.save)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True) if args.json else render_text(report))
    return report["exitStatus"]


if __name__ == "__main__":
    sys.exit(main())
