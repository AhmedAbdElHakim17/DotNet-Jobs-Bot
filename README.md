# DotNet-Jobs-Bot

Telegram job alerts for **.NET / C# / ASP.NET** roles—tuned for **Egypt**, the **Gulf**, and **remote**—with **LinkedIn-first** latency via **RSS** and free aggregation from **Indeed**, **Glassdoor**, **Remotive**, and **We Work Remotely**.

**Stack:** Python 3.11+ · `feedparser` · `python-jobspy` · `requests` · `python-dotenv`

---

## What it does

| Priority | Source | How |
|---------:|--------|-----|
| 1 | **LinkedIn** | **RSS feeds** you configure (e.g. [rss.app](https://rss.app/)—no LinkedIn login in code) |
| 2 | **Indeed · Glassdoor** | [python-jobspy](https://github.com/speedyapply/JobSpy) |
| 3 | **Remotive** | Free public JSON API |
| 4 | **We Work Remotely** | Category **RSS** (default: full-stack remote) |

- **Filtering:** keeps postings that match strong .NET signals (see `INCLUDE_KEYWORDS` in `config.py`) and drops obvious noise (non-.NET stacks, leadership titles in `TITLE_EXCLUDE_KEYWORDS`).
- **Dedup:** stable key `job_id + link`, persisted in `seen_jobs.json` (with a rolling time window in `dedup.py`).
- **Telegram:** Markdown messages with title, company, location, relative posted time, apply link, and hashtags.

**Cost:** no paid APIs required for the default setup.

---

## Screenshots

<!-- Add screenshots of Telegram notifications here -->

| Example alert | Description |
|---------------|-------------|
| _(placeholder)_ | Paste PNGs and link them here |

---

## Quick start (local)

```bash
git clone https://github.com/YOUR_USER/DotNet-Jobs-Bot.git
cd DotNet-Jobs-Bot
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

1. **`TELEGRAM_BOT_TOKEN`** — from [@BotFather](https://t.me/BotFather) (`/newbot`).
2. **`TELEGRAM_CHAT_ID`** — your channel or group ID (e.g. @RawDataBot, or Bot API `getUpdates` after you message the chat).
3. **`LINKEDIN_RSS_URLS`** — one or more **comma-separated** RSS URLs for your LinkedIn job search (see below).

Run:

```bash
python main.py
```

Commit `seen_jobs.json` so CI can persist state (use `{}` as the initial JSON object if the file does not exist yet).

---

## LinkedIn via RSS (recommended)

LinkedIn’s official APIs are restricted; **RSS bridges** give the fastest, most reliable “new job” signal without storing passwords in GitHub.

**Using rss.app (typical flow)**

1. Sign up at [rss.app](https://rss.app/) (free tier is enough to try).
2. Create a new **RSS feed** from a **LinkedIn job search** you care about (e.g. `.NET` + `Egypt` + `Past week`).
3. Copy the **RSS URL** they give you (often `https://rss.app/feeds/...xml`).
4. Put it in `.env`:

   ```env
   LINKEDIN_RSS_URLS=https://rss.app/feeds/XXXX.xml
   ```

   Multiple feeds:

   ```env
   LINKEDIN_RSS_URLS=https://feed-one.xml,https://feed-two.xml
   ```

5. Re-run `python main.py` and confirm logs show `Parsed N items from ...`.

**Notes**

- Third-party RSS URLs may include **opaque tokens**—treat them like secrets (GitHub **Secrets** in CI, not public issues).
- Respect **LinkedIn** and the RSS provider **terms of use**; this project is for personal job search automation.

---

## GitHub Actions (every 10 minutes)

Workflow: `.github/workflows/dotnet-jobs.yml`

**Repository → Settings → Secrets and variables → Actions**

| Secret | Required | Purpose |
|--------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token |
| `TELEGRAM_CHAT_ID` | Yes | Destination chat |
| `LINKEDIN_RSS_URLS` | **Strongly recommended** | Comma-separated RSS URLs |

**Permissions:** workflow uses `GITHUB_TOKEN` with `contents: write` so it can **commit** `seen_jobs.json`. Ensure **Settings → Actions → General → Workflow permissions** allows read/write.

`BOT_CI_FAST=1` in the workflow shortens JobSpy/Remotive work for quicker runs; locally omit it for full coverage.

---

## Configuration reference (`config.py` + env)

| Env var | Default | Role |
|---------|---------|------|
| `LINKEDIN_RSS_URLS` | — | Comma-separated RSS URLs |
| `WEWORKREMOTELY_RSS_URL` | WWR full-stack feed | Override category RSS |
| `REMOTIVE_SEARCH` | `.net,c#` | Remotive API `search` terms |
| `JOBSPY_RESULTS` | `25` | Max rows per JobSpy query |
| `JOBSPY_HOURS_OLD` | `72` | Freshness window |
| `JOBSPY_MAX_WORKERS` | `4` | Concurrent JobSpy cells |
| `RSS_DELAY_SEC` | `1.2` | Pause between RSS fetches |
| `BOT_CI_FAST` | off | CI: smaller search grid |

---

## Project layout

```
├── main.py              # CLI entry + logging
├── config.py            # Keywords, geo, limits, RSS list
├── models.py            # Job dataclass + relevance + geo bucket
├── scraper.py           # RSS + JobSpy + Remotive + WWR
├── dedup.py             # seen_jobs.json persistence
├── telegram_sender.py   # Telegram Markdown formatting
├── requirements.txt
├── .env.example
└── .github/workflows/dotnet-jobs.yml
```

**Extend with a new RSS source:** add a URL helper in `scraper.py` (mirror `fetch_weworkremotely_rss_jobs`), assign a `source` string, and register it in `SOURCE_PRIORITY` in `config.py`.

---

## Logging & errors

- `INFO` logs summarize each source (counts, skips).
- Per-source failures **do not** crash the whole run—other boards still run.
- Telegram non-200 responses are logged with the API body snippet.

---

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| No LinkedIn items | `LINKEDIN_RSS_URLS` empty, RSS URL expired, or feed has zero new entries |
| Duplicate Telegram spam | Delete bad keys from `seen_jobs.json` or wipe file (you’ll re-notify once) |
| JobSpy empty / errors | Indeed/Glassdoor rate limits, region strings, or upstream HTML changes—try fewer `JOBSPY_MAX_WORKERS` |
| `parse_mode` errors | Rare; titles are escaped—if it persists, open an issue with the raw title |

---

## Disclaimer

This tool is for **personal** job search automation. You are responsible for complying with **LinkedIn**, **Indeed**, **Glassdoor**, **Remotive**, **We Work Remotely**, **Telegram**, and any **RSS** provider terms. Scrapers can break when sites change layout—pin `python-jobspy` upgrades carefully.

---

## License

Use and modify freely for personal projects; add a license file if you redistribute.
