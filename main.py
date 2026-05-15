"""
DotNet-Jobs-Bot — aggregate .NET/C# jobs and notify Telegram.

Entry point for local runs and GitHub Actions.
"""

from __future__ import annotations

import logging
import sys

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, STRICT_REGION_FILTER
from dedup import load_seen, save_seen
from models import Job
from scraper import fetch_jobs
from telegram_sender import send_job

logger = logging.getLogger(__name__)


def _notify_region_ok(job: Job) -> bool:
    """
    When STRICT_REGION_FILTER is on, Telegram only gets:
    - Egypt / Gulf rows, or
    - Trusted local sources: Wuzzuf, LinkedIn posts.
    Everything else (generic remote boards, foreign Indeed, etc.) is skipped for alerts.
    """
    if not STRICT_REGION_FILTER:
        return True
    if job.is_post or job.source == "linkedin_post":
        return True
    if job.source == "linkedin_rss":
        return True  # you curate the RSS URL (Egypt/Gulf searches)
    if "wuzzuf.net" in job.link.lower():
        return True
    return job.geo_bucket() in ("egypt", "gulf")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error(
            "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID — set env vars or .env file."
        )
        sys.exit(1)

    logger.info("Starting DotNet-Jobs-Bot run")
    seen = load_seen()
    jobs = fetch_jobs()

    new_count = 0
    for job in jobs:
        key = f"{job.id}_{job.link}"
        if key in seen:
            continue
        if not job.is_relevant():
            continue
        if not _notify_region_ok(job):
            # Still persist so we do not re-fetch / re-check every 10 minutes.
            seen.add(key)
            continue
        send_job(job)
        seen.add(key)
        new_count += 1
        logger.info("Sent: %s | %s", job.source, job.title[:80])

    save_seen(seen)
    logger.info("Finished — sent %s new relevant job(s).", new_count)


if __name__ == "__main__":
    main()
