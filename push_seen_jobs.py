#!/usr/bin/env python3
"""
GitHub Actions helper: after `git commit` of seen_jobs.json, pull --rebase,
resolve the common seen_jobs.json conflict, and push.

Always clears stuck rebase/merge state first so retries do not hit
"rebase-merge directory already exists".
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

BRANCH = os.environ.get("GITHUB_REF_NAME", "main")


def _run(cmd: list[str], *, check: bool = False, env: dict | None = None) -> int:
    return subprocess.run(cmd, check=check, env=env).returncode


def _abort_stale_git_state() -> None:
    subprocess.run(["git", "rebase", "--abort"], capture_output=True)
    subprocess.run(["git", "merge", "--abort"], capture_output=True)


def _try_resolve_seen_conflict() -> bool:
    """If seen_jobs.json has conflict markers, merge and continue rebase."""
    path = Path("seen_jobs.json")
    if not path.is_file():
        return False
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return False
    if "<<<<<<<" not in raw:
        return False
    if _run([sys.executable, "merge_seen_jobs.py"]) != 0:
        return False
    if _run(["git", "add", "seen_jobs.json"]) != 0:
        return False
    e = {**os.environ, "GIT_EDITOR": "true"}
    return _run(["git", "rebase", "--continue"], env=e) == 0


def main() -> int:
    for attempt in range(1, 6):
        _abort_stale_git_state()
        if _run(["git", "fetch", "origin", BRANCH]) != 0:
            time.sleep(attempt)
            continue
        pr = _run(["git", "pull", "--rebase", "--no-edit", f"origin/{BRANCH}"])
        if pr != 0:
            if _try_resolve_seen_conflict():
                pass  # rebase finished; fall through to push
            else:
                _abort_stale_git_state()
                time.sleep(attempt)
                continue

        if _run(["git", "push", "origin", BRANCH]) == 0:
            print("Push OK")
            return 0
        time.sleep(attempt)

    print("Push failed after retries", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
