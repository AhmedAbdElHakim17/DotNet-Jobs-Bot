"""
DotNet-Jobs-Bot — entry point.

Run order:
  1. Load seen job keys from seen_jobs.json
  2. Fetch all sources (LinkedIn Posts RSS > LinkedIn Jobs RSS > Wuzzuf > JobSpy)
  3. Filter by .NET relevance and skip already-seen entries
  4. Send each new job/post to Telegram (newest first)
  5. Persist updated seen keys back to seen_jobs.json
"""

from __future__ import annotations

import logging
import sys

from dedup import load_seen, save_seen
from scraper import fetch_jobs
from telegram_sender import send_job


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def main() -> None:
    _setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=== DotNet-Jobs-Bot starting ===")

    seen = load_seen()
    jobs = fetch_jobs()

    new_posts = 0
    new_listings = 0

    for job in jobs:
        if not job.is_relevant():
            continue

        key = f"{job.id}_{job.link}"
        if key in seen:
            continue

        send_job(job)
        seen.add(key)

        if job.is_post:
            new_posts += 1
            logger.info("[POST]    %s (score=%d)", job.title[:80], job.hiring_score())
        else:
            new_listings += 1
            logger.info("[LISTING] %s @ %s", job.title[:60], job.company[:40])

    save_seen(seen)

    logger.info(
        "=== Done: %d new posts, %d new listings (total sent: %d) ===",
        new_posts, new_listings, new_posts + new_listings,
    )


if __name__ == "__main__":
    main()
