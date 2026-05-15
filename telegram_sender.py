import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_job(job):
    message = f"""
🆕 **{job.title}**
🏢 {job.company}
📍 {job.location}
⏰ {job.posted}

🔗 [Apply Here]({job.link})

#DotNet #CSharp #Hiring
    """.strip()

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)