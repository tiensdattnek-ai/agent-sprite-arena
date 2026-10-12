#!/usr/bin/env python3
"""Generation ledger of the Arena route layer.

Every committed generation (route_media.py commit) appends one ASCII JSON
line to <project>/.forge/ledger.jsonl. The file is append-only. This reader
summarizes it: counts per route and kind, and the newest artifacts. Stdlib
only; never reads credentials. There is no money on Arena: estimateUsd is
always null and counts are the currency.

  summary            counts per route/kind, first and last timestamp
  show [--last N]    the newest N ledger lines (default 10)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

TOOL_NAME = "media_ledger"
FORGE_PACKAGE_VERSION = "0.5.0-arena"
TOOL_VERSION = FORGE_PACKAGE_VERSION
LEDGER_PATH = Path(".forge") / "ledger.jsonl"


def read_lines() -> list[dict[str, Any]]:
    if not LEDGER_PATH.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def cmd_summary(_: argparse.Namespace) -> int:
    rows = read_lines()
    per: dict[str, int] = {}
    kinds: dict[str, int] = {}
    for row in rows:
        key = str(row.get("route") or "?")
        per[key] = per.get(key, 0) + 1
        kind = str(row.get("kind") or "?")
        kinds[kind] = kinds.get(kind, 0) + 1
    print(json.dumps({
        "status": "ok",
        "ledger": str(LEDGER_PATH),
        "entries": len(rows),
        "perRoute": per,
        "perKind": kinds,
        "firstTs": rows[0].get("ts") if rows else None,
        "lastTs": rows[-1].get("ts") if rows else None,
    }, ensure_ascii=True))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    rows = read_lines()
    tail = rows[-args.last:]
    for row in tail:
        print(json.dumps(row, ensure_ascii=True, sort_keys=True))
    if not tail:
        print(json.dumps({"status": "ok", "entries": 0, "note": "no committed generations yet"},
                         ensure_ascii=True))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=TOOL_NAME, description="Read the Arena generation ledger.")
    parser.add_argument("--version", action="version", version=f"{TOOL_NAME} {TOOL_VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("summary", help="counts per route and kind").set_defaults(func=cmd_summary)
    ps = sub.add_parser("show", help="print the newest ledger lines")
    ps.add_argument("--last", type=int, default=10)
    ps.set_defaults(func=cmd_show)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
