"""Persist seen job keys so we do not spam Telegram with duplicate listings."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

SEEN_FILE = "seen_jobs.json"
_MAX_AGE_HOURS = 72


def _load_raw():
    if not os.path.exists(SEEN_FILE):
        return {}
    try:
        with open(SEEN_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Could not read %s, starting fresh: %s", SEEN_FILE, e)
        return {}


def load_seen() -> set:
    data = _load_raw()
    if isinstance(data, list):
        return set(data)
    if not isinstance(data, dict):
        return set()
    return set(data.keys())


def save_seen(seen: set) -> None:
    existing = _load_raw()
    if isinstance(existing, list):
        existing = {k: datetime.utcnow().isoformat() for k in existing}
    if not isinstance(existing, dict):
        existing = {}

    now = datetime.utcnow()
    cutoff = now - timedelta(hours=_MAX_AGE_HOURS)

    updated: dict = {}
    for key, ts_str in existing.items():
        if key not in seen:
            continue
        try:
            if datetime.fromisoformat(ts_str) >= cutoff:
                updated[key] = ts_str
        except Exception:
            updated[key] = now.isoformat()

    for key in seen:
        if key not in updated:
            updated[key] = now.isoformat()

    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(updated, f, indent=2, ensure_ascii=False)
    logger.debug("Saved %d seen keys to %s", len(updated), SEEN_FILE)
