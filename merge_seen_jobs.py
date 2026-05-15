#!/usr/bin/env python3
"""
Resolve git merge/rebase conflicts inside seen_jobs.json.

Expects standard conflict markers (<<<<<<<, =======, >>>>>>>) in the file,
or valid JSON (no-op rewrite normalized). Output is a single merged object
with the latest ISO timestamp kept per key.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SEEN = Path("seen_jobs.json")


def _as_dict(data: object) -> dict[str, str]:
    if isinstance(data, list):
        return {str(k): "1970-01-01T00:00:00" for k in data}
    if isinstance(data, dict):
        return {str(k): str(v) for k, v in data.items()}
    return {}


def _merge_dicts(a: dict[str, str], b: dict[str, str]) -> dict[str, str]:
    out = dict(a)
    for k, v in b.items():
        if k not in out or v > out[k]:
            out[k] = v
    return out


def _from_conflict(text: str) -> dict[str, str]:
    if "<<<<<<<" not in text:
        return _as_dict(json.loads(text))

    m = re.search(
        r"^<<<<<<<[^\n]*\n(.*?)^=======\n(.*?)^>>>>>>>[^\n]*\n?",
        text,
        re.S | re.M,
    )
    if not m:
        print("Could not parse conflict markers; aborting.", file=sys.stderr)
        sys.exit(1)
    left = _as_dict(json.loads(m.group(1).strip()))
    right = _as_dict(json.loads(m.group(2).strip()))
    return _merge_dicts(left, right)


def main() -> None:
    raw = SEEN.read_text(encoding="utf-8")
    merged = _from_conflict(raw)
    SEEN.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Resolved seen_jobs.json ({len(merged)} keys)")


if __name__ == "__main__":
    main()
