# DotNet-Jobs-Bot

Telegram job alert bot for **.NET / C# / ASP.NET** developers — focused on **Egypt**, the **Gulf**, and remote.

**Primary goal:** catch LinkedIn hiring posts (social feed posts by recruiters) *before* they become formal job listings, so you are among the first applicants.

---

## How it works

| Priority | Source | What it captures |
|---------:|--------|-----------------|
| 1 | **LinkedIn Posts RSS** | Social feed posts: "We are hiring a .NET developer!" |
| 2 | **LinkedIn Jobs RSS** | LinkedIn Jobs tab listings |
| 3 | **Wuzzuf** | Egypt-focused job board |
| 4 | **LinkedIn (JobSpy)** | Fallback LinkedIn job scrape |

Every 10 minutes (GitHub Actions) the bot:
1. Fetches all RSS feeds and scrapes all boards
2. Filters for .NET / C# signals (`INCLUDE_KEYWORDS` in `config.py`)
3. For LinkedIn Posts: also requires a hiring-intent signal ("hiring", "open position", etc.)
4. Skips already-seen entries (`seen_jobs.json`)
5. Sends clean Telegram notifications sorted **newest first**

---

## Quick start (local)

```bash
git clone https://github.com/YOUR_USER/DotNet-Jobs-Bot.git
cd DotNet-Jobs-Bot
python -m venv .venv
# Windows:    .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your tokens and RSS URLs (see below)
python main.py
```

---

## Setting up LinkedIn Posts RSS (Primary Source)

This is the most important step. LinkedIn posts RSS gives you the *fastest* signal — before jobs are even formally posted.

### Step 1 — Create LinkedIn post search URLs

Open LinkedIn and search the feed for hiring posts. Use these searches:

| Search term | LinkedIn URL |
|-------------|-------------|
| `.NET developer hiring Egypt` | `https://www.linkedin.com/search/results/content/?keywords=.NET+developer+hiring+Egypt` |
| `C# developer hiring Cairo` | `https://www.linkedin.com/search/results/content/?keywords=C%23+developer+hiring+Cairo` |
| `ASP.NET hiring` | `https://www.linkedin.com/search/results/content/?keywords=ASP.NET+hiring` |
| `#dotnet #hiring` | `https://www.linkedin.com/search/results/content/?keywords=%23dotnet+%23hiring` |

### Step 2 — Convert to RSS with rss.app

1. Go to [rss.app](https://rss.app) and sign up (free tier is enough)
2. Click **New Feed** → paste the LinkedIn search URL → click **Generate**
3. Copy the RSS feed URL (e.g. `https://rss.app/feeds/XXXXXXXXXXXXXXXX.xml`)
4. Repeat for each search you want to monitor

### Step 3 — Add to .env

```env
LINKEDIN_POSTS_RSS_URLS=https://rss.app/feeds/feed1.xml,https://rss.app/feeds/feed2.xml
```

> **Tip:** Create 3–5 feeds with different keyword combinations for best coverage.

---

## Setting up LinkedIn Jobs RSS (Secondary)

Same flow, but using LinkedIn **Jobs** search URLs:

```
https://www.linkedin.com/jobs/search/?keywords=.NET+Developer&location=Egypt&f_TPR=r86400
```

(`f_TPR=r86400` = past 24 hours)

Add to `.env`:
```env
LINKEDIN_JOBS_RSS_URLS=https://rss.app/feeds/jobs_feed1.xml
```

---

## Configuration (.env)

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | From [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | Yes | Channel/group ID (use @RawDataBot to find it) |
| `LINKEDIN_POSTS_RSS_URLS` | **Recommended** | Comma-separated rss.app feed URLs for posts |
| `LINKEDIN_JOBS_RSS_URLS` | Optional | Comma-separated rss.app feed URLs for job listings |
| `LINKEDIN_COOKIE` | Optional | `li_at` cookie for unofficial LinkedIn API |
| `LINKEDIN_EMAIL` | Optional | LinkedIn login (often blocked) |
| `LINKEDIN_PASSWORD` | Optional | LinkedIn login (often blocked) |

---

## GitHub Actions setup

**Settings → Secrets and variables → Actions** — add these secrets:

| Secret | Value |
|--------|-------|
| `TELEGRAM_BOT_TOKEN` | Your bot token |
| `TELEGRAM_CHAT_ID` | Your chat/channel ID |
| `LINKEDIN_POSTS_RSS_URLS` | Your rss.app Posts feed URL(s) |
| `LINKEDIN_JOBS_RSS_URLS` | Your rss.app Jobs feed URL(s) |

The workflow runs every 10 minutes and commits `seen_jobs.json` back to the repo automatically.

---

## Telegram message format

**Hiring Post (LinkedIn feed post):**
```
🔥 Urgent Hiring — LinkedIn Posts

We are hiring a .NET Backend Developer to join our team in Cairo!
Strong C# and ASP.NET Core required...

👤 TechCorp Egypt
🕒 Today
🔗 View Post

#DotNet #CSharp #Hiring #Egypt #Cairo
```

**Job Listing (structured):**
```
💼 Job Listing — Wuzzuf

*Senior .NET Developer*
🏢 SoftTech Solutions
📍 Cairo, Egypt
🕒 2 days ago
🔧 ASP.NET Core · C# · EF Core

➡️ Apply Now

#DotNet #CSharp #Hiring #Egypt #Cairo
```

---

## Adding more RSS feeds

Just add more comma-separated URLs to `LINKEDIN_POSTS_RSS_URLS` or `LINKEDIN_JOBS_RSS_URLS` in `.env` / GitHub Secrets. The bot handles any number of feeds automatically.

**Ideas for additional feeds:**
- Arabic hiring keywords: `مطلوب مطور دوت نت` 
- Specific companies: paste a company LinkedIn page into rss.app
- Gulf region: `.NET developer hiring Dubai`
- Remote: `.NET developer hiring remote`

---

## Project structure

```
config.py          # Keywords, RSS URLs, credentials, timeouts
models.py          # Job dataclass with .NET filter + hiring-signal scoring
scraper.py         # All data sources (RSS, Wuzzuf, JobSpy)
dedup.py           # Seen-jobs persistence (seen_jobs.json)
telegram_sender.py # Telegram message templates
main.py            # Entry point
.env.example       # Template for environment variables
seen_jobs.json     # Auto-updated dedup store (committed by CI)
.github/workflows/dotnet-jobs.yml
```
