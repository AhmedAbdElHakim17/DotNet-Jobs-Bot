"""
Send formatted job alerts to Telegram (Markdown).

User-facing strings are escaped so titles containing _ * ` [ do not break parse_mode.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime

import requests

from config import HTTP_TIMEOUT_SEC, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from models import Job

logger = logging.getLogger(__name__)


def _escape_markdown(text: str) -> str:
    """Escape Telegram classic Markdown reserved characters."""
    if not text:
        return ""
    out: list[str] = []
    for ch in str(text):
        if ch in r"_*`[":
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def _relative_time(posted: str) -> str:
    if not posted or posted in ("Recently", ""):
        return "Just now / unknown"
    try:
        post_date = datetime.strptime(str(posted)[:10], "%Y-%m-%d").date()
        delta = (date.today() - post_date).days
        if delta == 0:
            return "Today"
        if delta == 1:
            return "1 day ago"
        return f"{delta} days ago"
    except Exception:
        return str(posted)[:32]


def _source_badge(job: Job) -> str:
    src = job.source.lower().replace(" ", "_")
    labels = {
        "linkedin_rss": "🔗 *LinkedIn · RSS*",
        "indeed": "🟦 *Indeed*",
        "glassdoor": "🟩 *Glassdoor*",
        "remotive": "🌍 *Remotive*",
        "weworkremotely": "🏝 *We Work Remotely*",
    }
    return labels.get(src, f"📋 *{_escape_markdown(job.source.replace('_', ' ').title())}*")


def _build_hashtags(job: Job) -> str:
    """Compact hashtag line from geo + matched stack keywords."""
    tags = ["#DotNetJobs", "#CSharpJobs", "#JobAlert"]
    bucket = job.geo_bucket()
    if bucket == "egypt":
        tags.extend(["#Egypt", "#CairoTech"])
    elif bucket == "gulf":
        tags.append("#GulfJobs")
    elif bucket == "remote":
        tags.append("#RemoteDeveloper")

    for kw in job.matched_keywords[:4]:
        slug = re.sub(r"[^A-Za-z0-9]+", "", kw)
        if len(slug) >= 3 and slug.lower() not in ("net",):
            tags.append("#" + slug)
    # de-dupe preserve order
    seen: set[str] = set()
    uniq = []
    for t in tags:
        tl = t.lower()
        if tl not in seen:
            seen.add(tl)
            uniq.append(t)
    return " ".join(uniq)


def send_job(job: Job) -> None:
    """Push a single job message to the configured Telegram chat."""
    time_str = _relative_time(job.posted)
    title_e = _escape_markdown(job.title)
    company_e = _escape_markdown(job.company or "—")
    loc_e = _escape_markdown(job.location or "—")

    lines = [
        _source_badge(job),
        "",
        f"*{title_e}*",
        f"🏢 {company_e}",
        f"📍 {loc_e}",
        f"🕒 {_escape_markdown(time_str)}",
        "",
        f"➡️ [Apply / view]({job.link})",
        "",
    ]
    if job.salary:
        lines.insert(-3, f"💰 {_escape_markdown(job.salary)}")

    lines.append(_build_hashtags(job))

    text = "\n".join(lines)
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=HTTP_TIMEOUT_SEC)
        if resp.status_code != 200:
            logger.error(
                "Telegram send failed (%s): %s",
                resp.status_code,
                resp.text[:800],
            )
    except Exception as e:
        logger.exception("Telegram request error: %s", e)
