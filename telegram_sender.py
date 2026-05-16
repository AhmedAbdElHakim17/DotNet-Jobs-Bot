"""
Telegram notification sender for DotNet-Jobs-Bot.

Two message templates:
  - _send_post()    : LinkedIn hiring posts (social feed style)
  - _send_listing() : Structured job listings (LinkedIn Jobs / Wuzzuf)

Uses Markdown parse mode (MarkdownV1 — simpler escaping).
"""

from __future__ import annotations

import logging
from datetime import date, datetime

import requests

from config import HTTP_TIMEOUT_SEC, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from models import Job

logger = logging.getLogger(__name__)

_GEO_HASHTAGS = {
    "egypt": "#Egypt #Cairo",
    "gulf":  "#Gulf #UAE",
    "remote": "#Remote #Worldwide",
    "other": "",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _esc(text: str) -> str:
    """Escape characters that break Telegram MarkdownV1 formatting."""
    if not text:
        return ""
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, "\\" + ch)
    return text


def _relative_time(posted: str) -> str:
    if not posted or posted == "Recently":
        return "Just now"
    try:
        delta = (date.today() - datetime.strptime(str(posted)[:10], "%Y-%m-%d").date()).days
        if delta == 0:
            return "Today"
        if delta == 1:
            return "Yesterday"
        return f"{delta} days ago"
    except Exception:
        return str(posted)[:20]


def _source_label(job: Job) -> str:
    labels = {
        "linkedin_post_rss": "LinkedIn Posts",
        "linkedin_jobs_rss": "LinkedIn Jobs",
        "wuzzuf": "Wuzzuf",
        "linkedin_jobspy": "LinkedIn",
    }
    return labels.get(job.source, job.source.replace("_", " ").title())


def _geo_tags(job: Job) -> str:
    return _GEO_HASHTAGS.get(job.geo_bucket(), "")


def _send(text: str) -> None:
    """Send a Markdown message to the configured Telegram chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
            },
            timeout=HTTP_TIMEOUT_SEC,
        )
        if resp.status_code != 200:
            logger.error("Telegram error %s: %s", resp.status_code, resp.text[:400])
    except Exception as e:
        logger.exception("Telegram send failed: %s", e)


# ---------------------------------------------------------------------------
# Message templates
# ---------------------------------------------------------------------------

def _send_post(job: Job) -> None:
    """
    Template for LinkedIn hiring posts (social feed).

    Example:
      📢 Hiring Post — LinkedIn Posts

      We are hiring a .NET Backend Developer to join our team in Cairo!
      Strong C# and ASP.NET Core background required...

      👤 TechCorp Egypt
      🕒 Today
      🔗 View Post

      #DotNet #CSharp #Hiring #Egypt
    """
    preview = (job.description or job.title)[:600].strip()
    if len(job.description) > 600:
        preview += "..."

    # Urgency badge based on hiring score
    score = job.hiring_score()
    if score >= 3:
        badge = "🔥 *Urgent Hiring — " + _esc(_source_label(job)) + "*"
    elif score >= 1:
        badge = "📢 *Hiring Post — " + _esc(_source_label(job)) + "*"
    else:
        badge = "📌 *Post — " + _esc(_source_label(job)) + "*"

    parts = [badge, "", _esc(preview), ""]
    if job.company:
        parts.append(f"👤 {_esc(job.company)}")
    if job.location:
        parts.append(f"📍 {_esc(job.location)}")
    parts.append(f"🕒 {_relative_time(job.posted)}")
    if job.link:
        parts += ["", f"🔗 [View Post]({job.link})"]
    geo = _geo_tags(job)
    parts += ["", f"#DotNet #CSharp #Hiring {geo}".strip()]

    _send("\n".join(parts))


def _send_listing(job: Job) -> None:
    """
    Template for structured job listings (LinkedIn Jobs, Wuzzuf, JobSpy).

    Example:
      💼 Job Listing — Wuzzuf

      *Senior .NET Developer*
      🏢 SoftTech Solutions
      📍 Cairo, Egypt
      🕒 2 days ago
      💰 15,000 – 20,000 EGP

      🔗 Apply Now

      #DotNet #CSharp #Egypt
    """
    source = _esc(_source_label(job))
    parts = [f"💼 *Job Listing — {source}*", "", f"*{_esc(job.title)}*"]

    if job.company:
        parts.append(f"🏢 {_esc(job.company)}")
    if job.location:
        parts.append(f"📍 {_esc(job.location)}")
    parts.append(f"🕒 {_relative_time(job.posted)}")
    if job.salary:
        parts.append(f"💰 {_esc(job.salary)}")

    # Matched .NET keywords as a quick signal
    if job.matched_keywords:
        tags = " · ".join(job.matched_keywords[:4])
        parts.append(f"🔧 {_esc(tags)}")

    if job.link:
        parts += ["", f"➡️ [Apply Now]({job.link})"]

    geo = _geo_tags(job)
    parts += ["", f"#DotNet #CSharp #Hiring {geo}".strip()]

    _send("\n".join(parts))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_job(job: Job) -> None:
    """Route to the correct template based on job type."""
    if job.is_post:
        _send_post(job)
    else:
        _send_listing(job)
