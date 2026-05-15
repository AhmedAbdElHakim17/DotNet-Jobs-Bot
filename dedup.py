import json
import os
from datetime import datetime, timedelta

SEEN_FILE = "seen_jobs.json"
_MAX_AGE_HOURS = 72  # Trim entries older than 3 days


def _load_raw():
    if not os.path.exists(SEEN_FILE):
        return {}
    try:
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def load_seen() -> set:
    data = _load_raw()
    # Support old flat-list format
    if isinstance(data, list):
        return set(data)
    return set(data.keys())


def save_seen(seen: set):
    existing = _load_raw()
    # Migrate old flat-list format to timestamped dict
    if isinstance(existing, list):
        existing = {k: datetime.utcnow().isoformat() for k in existing}

    now = datetime.utcnow()
    cutoff = now - timedelta(hours=_MAX_AGE_HOURS)

    updated = {}
    # Keep non-expired entries that are still in the active seen set
    for key, ts_str in existing.items():
        if key not in seen:
            continue
        try:
            if datetime.fromisoformat(ts_str) >= cutoff:
                updated[key] = ts_str
        except Exception:
            updated[key] = now.isoformat()

    # Stamp new entries with current time
    for key in seen:
        if key not in updated:
            updated[key] = now.isoformat()

    with open(SEEN_FILE, "w") as f:
        json.dump(updated, f, indent=2)
