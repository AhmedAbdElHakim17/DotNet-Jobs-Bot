"""
Telegram notifications — classic (older) template: Job/Post badges, “via” line,
[Apply Here], and simple hashtags.
"""

from __future__ import annotations

import logging
from datetime import date, datetime

import requests

from config import HTTP_TIMEOUT_SEC, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from models import Job

logger = logging.getLogger(__name__)


def _escape_markdown(text: str) -> str:
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
        return "Just now"
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


def _badge_via_line(job: Job) -> tuple[str, str]:
    """
    Return (Markdown badge line, plain “via” label) matching the legacy bot style.
    Wuzzuf vs LinkedIn were the originals; other boards follow the same pattern.
    """
    link_l = job.link.lower()
    src = job.source.lower().replace(" ", "_")

    if "wuzzuf.net" in link_l:
        return "🟠 *Job — Wuzzuf*", "Wuzzuf"
    if "linkedin.com" in link_l or src == "linkedin_rss":
        return "🔵 *Job — LinkedIn*", "LinkedIn Jobs"
    if src == "indeed":
        return "🟦 *Job — Indeed*", "Indeed"
    if src == "glassdoor":
        return "🟩 *Job — Glassdoor*", "Glassdoor"
    if src == "remotive":
        return "🌍 *Job — Remotive*", "Remotive"
    if src == "weworkremotely":
        return "🏝 *Job — We Work Remotely*", "We Work Remotely"

    label = job.source.replace("_", " ").title()
    return f"📋 *Job — {_escape_markdown(label)}*", label


def _send(payload_text: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": payload_text,
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


def _send_job_listing(job: Job) -> None:
    badge, source = _badge_via_line(job)
    time_str = _relative_time(job.posted)
    title_e = _escape_markdown(job.title)
    company_e = _escape_markdown(job.company) if job.company else ""
    loc_e = _escape_markdown(job.location) if job.location else ""

    parts = [badge, "", f"*{title_e}*"]
    if job.company:
        parts.append(f"🏢 {company_e}")
    if job.location:
        parts.append(f"📍 {loc_e}")
    parts.append(f"🕒 {time_str}")
    if job.salary:
        parts.append(f"💰 {_escape_markdown(job.salary)}")
    parts.append(f"📌 via {source}")
    parts.append("")
    parts.append(f"➡️ [Apply Here]({job.link})")
    parts.append("")
    parts.append("#DotNet #CSharp #Hiring")
    _send("\n".join(parts))


def _send_post(job: Job) -> None:
    """Legacy layout for social-style postings (e.g. LinkedIn feed)."""
    time_str = _relative_time(job.posted)
    preview_raw = job.description[:700].strip() if job.description else job.title
    if job.description and len(job.description) > 700:
        preview_raw += "..."
    preview_e = _escape_markdown(preview_raw)

    parts = [
        "📢 *Post — LinkedIn*",
        "",
        preview_e,
        "",
    ]
    if job.company:
        parts.append(f"👤 {_escape_markdown(job.company)}")
    parts.append(f"🕒 {time_str}")
    parts.append("📌 via LinkedIn Posts")
    if job.link:
        parts.append("")
        parts.append(f"🔗 [View Post]({job.link})")
    parts.append("")
    parts.append("#DotNet #CSharp #Hiring")
    _send("\n".join(parts))


def send_job(job: Job) -> None:
    if job.is_post:
        _send_post(job)
    else:
        _send_job_listing(job)
