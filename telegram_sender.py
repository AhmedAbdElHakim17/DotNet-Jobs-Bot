from datetime import date, datetime
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def _relative_time(posted: str) -> str:
    if not posted or posted in ("Recently", ""):
        return "Just now"
    try:
        post_date = datetime.strptime(str(posted)[:10], "%Y-%m-%d").date()
        delta = (date.today() - post_date).days
        if delta == 0:
            return "Today"
        elif delta == 1:
            return "1 day ago"
        else:
            return f"{delta} days ago"
    except Exception:
        return str(posted)


def send_job(job):
    if job.is_post:
        _send_post(job)
    else:
        _send_job_listing(job)


def _send_job_listing(job):
    source = "Wuzzuf" if "wuzzuf.net" in job.link else "LinkedIn Jobs"
    time_str = _relative_time(job.posted)
    parts = [f"*{job.title}*"]
    if job.company:
        parts.append(f"🏢 {job.company}")
    if job.location:
        parts.append(f"📍 {job.location}")
    parts.append(f"🕒 {time_str}")
    parts.append(f"📌 via {source}")
    parts.append("")
    parts.append(f"➡️ [Apply Here]({job.link})")
    parts.append("")
    parts.append("#DotNet #CSharp #Hiring")
    _send("\n".join(parts))


def _send_post(job):
    time_str = _relative_time(job.posted)
    preview = job.description[:700].strip() if job.description else job.title
    if len(job.description) > 700:
        preview += "..."
    parts = [
        "📢 *Hiring Post*",
        "",
        preview,
        "",
    ]
    if job.company:
        parts.append(f"👤 {job.company}")
    parts.append(f"🕒 {time_str}")
    parts.append("📌 via LinkedIn Posts")
    if job.link:
        parts.append("")
        parts.append(f"🔗 [View Post]({job.link})")
    parts.append("")
    parts.append("#DotNet #CSharp #Hiring")
    _send("\n".join(parts))


def _send(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }
    requests.post(url, json=payload)
