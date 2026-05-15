#!/usr/bin/env python3
"""
Resolve git merge/rebase conflicts inside seen_jobs.json.

Handles standard <<<<<<< / ======= / >>>>>>> markers with a line-based split
(pretty-printed JSON is fine). No markers => valid JSON rewritten normalized.
"""

from __future__ import annotations

import json
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
    text = text.replace("\r\n", "\n")
    if "<<<<<<<" not in text:
        return _as_dict(json.loads(text))

    # Drop first line (<<<<<<< label)
    after_first = text.split("<<<<<<<", 1)[1]
    if "\n" in after_first:
        after_first = after_first.split("\n", 1)[1]
    else:
        print("Malformed conflict (no body after <<<<<<<)", file=sys.stderr)
        sys.exit(1)

    if "\n=======\n" not in after_first:
        print("Malformed conflict (no =======)", file=sys.stderr)
        sys.exit(1)
    left_s, right_rest = after_first.split("\n=======\n", 1)

    if "\n>>>>>>>" not in right_rest:
        print("Malformed conflict (no >>>>>>>)", file=sys.stderr)
        sys.exit(1)
    right_s = right_rest.split("\n>>>>>>>", 1)[0]

    left = _as_dict(json.loads(left_s.strip()))
    right = _as_dict(json.loads(right_s.strip()))
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
