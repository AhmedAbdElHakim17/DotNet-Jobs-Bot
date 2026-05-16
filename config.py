"""
Central configuration for DotNet-Jobs-Bot.

Source priority (fastest hiring signal first):
  1. LinkedIn Posts RSS  -- rss.app feeds watching LinkedIn feed posts (.NET hiring)
  2. LinkedIn Jobs RSS   -- rss.app feeds watching LinkedIn Jobs tab results
  3. Wuzzuf              -- Egypt-focused job board (HTML scrape)
  4. LinkedIn JobSpy     -- python-jobspy LinkedIn scrape (fallback)

All secrets loaded via python-dotenv locally; GitHub Actions injects them directly.
"""

from __future__ import annotations

import os
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# .NET keyword filtering
# A post or listing must match at least one INCLUDE_KEYWORD to be forwarded.
# ---------------------------------------------------------------------------
INCLUDE_KEYWORDS: List[str] = [
    ".NET", "C#", "ASP.NET", "ASP.NET Core", "EF Core", "Entity Framework",
    "Microservices", "RabbitMQ", "Clean Architecture", "Full Stack .NET",
    "Blazor", "Hangfire", "MediatR", "CQRS", "Dapper", "SignalR", "Backend .NET",
    "dotnet", "dot net",  # common LinkedIn post variants of ".NET"
]

EXCLUDE_KEYWORDS: List[str] = [
    "Java", "Python", "PHP", "Node.js", "React Native", "Flutter",
    "GoLang", "Swift", "Kotlin", "Shopify", "WordPress",
]

# Checked against job/post title only (word boundaries)
TITLE_EXCLUDE_KEYWORDS: List[str] = [
    "lead", "manager", "director", "head of", "vp ", "vice president", "chief ",
]

TITLE_PLATFORM_EXCLUDE: List[str] = [
    "shopify", "wordpress", "ruby on rails", "rails developer",
    "salesforce", "magento", "drupal",
]

# ---------------------------------------------------------------------------
# Hiring-intent signals
# Posts containing at least one of these are treated as active hiring announcements
# and given top priority. Higher match count = higher urgency score.
# ---------------------------------------------------------------------------
HIRING_SIGNALS: List[str] = [
    # English
    "hiring", "we're hiring", "we are hiring", "now hiring",
    "open position", "open role", "open vacancy",
    "join our team", "join us",
    "looking for", "seeking a", "seeking an",
    "vacancy", "vacancies",
    "new opportunity", "exciting opportunity",
    "apply now", "apply today", "applications open",
    "immediate opening", "urgent hiring",
    # Arabic
    "matlub", "metah", "forsa amal",
]

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")


# ---------------------------------------------------------------------------
# LinkedIn Posts RSS  <-- PRIMARY SOURCE
#
# rss.app feeds that watch LinkedIn content/feed search results for
# .NET / C# hiring posts (regular posts by recruiters, not the Jobs tab).
#
# How to generate:
#   1. Search LinkedIn for:  ".NET developer hiring"  or  #dotnet #hiring
#      URL: https://www.linkedin.com/search/results/content/?keywords=.NET+developer+hiring
#   2. Paste that URL at https://rss.app -> New Feed -> Generate
#   3. Copy the feed URL (e.g. https://rss.app/feeds/XXXXXXXXXXXXXXXX.xml)
#   4. Set: LINKEDIN_POSTS_RSS_URLS=<url>   (comma-separate multiple feeds)
# ---------------------------------------------------------------------------
def _parse_urls(raw: str | None) -> List[str]:
    if not raw or not raw.strip():
        return []
    return [u.strip() for u in raw.split(",") if u.strip()]


LINKEDIN_POSTS_RSS_URLS: List[str] = _parse_urls(os.getenv("LINKEDIN_POSTS_RSS_URLS", ""))

# ---------------------------------------------------------------------------
# LinkedIn Jobs RSS  <-- SECONDARY SOURCE
#
# rss.app feeds watching the LinkedIn Jobs tab for .NET listings.
#
# How to generate:
#   1. Search LinkedIn Jobs:  .NET Developer  Egypt  (or any keyword/location)
#      URL: https://www.linkedin.com/jobs/search/?keywords=.NET+Developer&location=Egypt
#   2. Paste that URL at https://rss.app -> New Feed -> Generate
#   3. Set: LINKEDIN_JOBS_RSS_URLS=<url>
# ---------------------------------------------------------------------------
LINKEDIN_JOBS_RSS_URLS: List[str] = _parse_urls(os.getenv("LINKEDIN_JOBS_RSS_URLS", ""))

# ---------------------------------------------------------------------------
# Apify LinkedIn Posts Scraper  <-- RECOMMENDED for reliable post search
#
# Uses actor: apimaestro/linkedin-posts-search-scraper-no-cookies
# No LinkedIn login required. Searches LinkedIn posts by keyword + date.
#
# Setup:
#   1. Sign up at https://apify.com (free tier: $5/month credits)
#   2. Go to Settings -> Integrations -> API tokens -> copy your token
#   3. Set: APIFY_API_TOKEN=apify_api_XXXX
#
# Cost note: ~0.001 CU per 10 posts. Running every 10 min = ~$0.40/day.
#   Reduce APIFY_POSTS_PER_QUERY or run less frequently if on free tier.
# ---------------------------------------------------------------------------
APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "")
APIFY_POSTS_PER_QUERY: int = int(os.getenv("APIFY_POSTS_PER_QUERY", "5"))

# Targeted search queries sent to the Apify actor (one API call each)
APIFY_SEARCH_QUERIES: List[str] = [
    '(".NET" OR "C#" OR "ASP.NET") AND ("hiring" OR "looking for" OR "vacancy") AND "Egypt"',
    '(".NET" OR "C#" OR "ASP.NET") AND ("hiring" OR "looking for" OR "vacancy") AND ("UAE" OR "Dubai" OR "Saudi")',
    '(".NET developer" OR "C# developer") AND ("hiring" OR "open position" OR "open role")',
]

# ---------------------------------------------------------------------------
# LinkedIn unofficial API  (optional -- frequently blocked by LinkedIn)
# Prefer LINKEDIN_COOKIE (li_at session cookie) over email/password.
#   Get it: linkedin.com -> DevTools (F12) -> Application -> Cookies -> li_at
# ---------------------------------------------------------------------------
LINKEDIN_EMAIL: str = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD: str = os.getenv("LINKEDIN_PASSWORD", "")
LINKEDIN_COOKIE: str = os.getenv("LINKEDIN_COOKIE", "")

# ---------------------------------------------------------------------------
# JobSpy  <-- FALLBACK (LinkedIn scrape via python-jobspy)
# ---------------------------------------------------------------------------
SEARCH_KEYWORDS: List[str] = [
    ".NET Developer",
    "C# Developer",
    "ASP.NET Core Developer",
    "Full Stack .NET Developer",
]

LOCATIONS: List[str] = [
    "Cairo, Egypt",
    "Giza, Egypt",
    "Alexandria, Egypt",
    "Egypt",
    "Dubai, United Arab Emirates",
    "Abu Dhabi, United Arab Emirates",
    "Riyadh, Saudi Arabia",
    "Doha, Qatar",
    "Kuwait City, Kuwait",
]

# ---------------------------------------------------------------------------
# Timeouts, delays, batch sizes
# ---------------------------------------------------------------------------
HTTP_TIMEOUT_SEC: int = 25
RSS_DELAY_SEC: float = float(os.getenv("RSS_DELAY_SEC", "1.0"))
WUZZUF_DELAY_SEC: float = float(os.getenv("WUZZUF_DELAY_SEC", "1.5"))
JOBSPY_HOURS_OLD: int = int(os.getenv("JOBSPY_HOURS_OLD", "24"))
JOBSPY_RESULTS: int = int(os.getenv("JOBSPY_RESULTS", "25"))
JOBSPY_MAX_WORKERS: int = int(os.getenv("JOBSPY_MAX_WORKERS", "4"))

# ---------------------------------------------------------------------------
# Source priority -- lower value = sent to Telegram first
# ---------------------------------------------------------------------------
SOURCE_PRIORITY: Dict[str, int] = {
    "apify_linkedin": 0,      # Apify LinkedIn post scrape  <- no-cookie, date-filtered
    "linkedin_post_rss": 0,   # LinkedIn feed posts via RSS
    "linkedin_jobs_rss": 1,   # LinkedIn job listings via RSS
    "wuzzuf": 2,              # Wuzzuf Egypt board
    "linkedin_jobspy": 3,     # JobSpy LinkedIn fallback
}

DEFAULT_REQUEST_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; DotNet-Jobs-Bot/2.0; "
        "+https://github.com/DotNet-Jobs-Bot; job alerts for .NET developers)"
    ),
    "Accept": "application/rss+xml, application/xml, */*;q=0.8",
}

# ---------------------------------------------------------------------------
# CI fast mode -- reduce JobSpy load in GitHub Actions
# ---------------------------------------------------------------------------
if os.getenv("BOT_CI_FAST") == "1":
    SEARCH_KEYWORDS = SEARCH_KEYWORDS[:2]
    LOCATIONS = LOCATIONS[:4]
    JOBSPY_RESULTS = min(JOBSPY_RESULTS, 10)
