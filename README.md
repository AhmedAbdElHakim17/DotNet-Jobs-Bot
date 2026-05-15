# .NET Jobs Telegram Bot

Specialized bot for **.NET / C# Developers** (Egypt • Gulf • Remote). Sends new jobs quickly to help you apply first.

## Features
- Strong focus on .NET, C#, ASP.NET Core, Microservices, etc.
- Sources: LinkedIn, Indeed, Glassdoor, We Work Remotely (via JobSpy)
- Runs every 5-15 minutes on GitHub Actions (Free)
- Smart filtering + deduplication

## Setup (5-10 minutes)

1. **Fork** this repository
2. Create a Telegram Bot:
   - Talk to [@BotFather](https://t.me/BotFather) → `/newbot`
   - Copy the token
3. Create a Telegram Group or Channel and get its ID (send message to @userinfobot or @RawDataBot)
4. Go to **Repository Settings → Secrets and variables → Actions**
5. Add these secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
6. Create `seen_jobs.json` file (empty array `[]`) and commit it
7. Enable GitHub Actions

## Local Testing

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
python main.py