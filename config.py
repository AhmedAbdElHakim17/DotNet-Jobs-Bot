"""
Central configuration for DotNet-Jobs-Bot.

Loads environment variables via python-dotenv for local runs; GitHub Actions
injects secrets as env vars directly.
"""

from __future__ import annotations

import os
from typing import List

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Filtering — target: .NET Full Stack / Backend (roughly 0–5 YOE)
# Must match at least one INCLUDE keyword in title/company/description/location.
# ---------------------------------------------------------------------------
INCLUDE_KEYWORDS: List[str] = [
    ".NET",
    "C#",
    "ASP.NET",
    "ASP.NET Core",
    "EF Core",
    "Entity Framework",
    "Microservices",
    "RabbitMQ",
    "Clean Architecture",
    "Full Stack .NET",
    "Blazor",
    "Hangfire",
    # Extra strong .NET signals (optional but helpful)
    "MediatR",
    "CQRS",
    "Dapper",
    "SignalR",
    "Backend .NET",
]

EXCLUDE_KEYWORDS: List[str] = [
    "Java",
    "Python",
    "PHP",
    "Node.js",
    "React Native",
    "Flutter",
    "GoLang",
    "Swift",
    "Kotlin",
    "Shopify",
    "WordPress",
]

# Title-only excludes (word boundaries) — skip obvious leadership layers
TITLE_EXCLUDE_KEYWORDS: List[str] = [
    "lead",
    "manager",
    "director",
    "head of",
    "vp ",
    "vice president",
    "chief ",
]

# Title-only stack / platform excludes (word boundaries in models.py)
TITLE_PLATFORM_EXCLUDE: List[str] = [
    "shopify",
    "wordpress",
    "ruby on rails",
    "rails developer",
    "salesforce",
    "magento",
    "drupal",
]

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ---------------------------------------------------------------------------
# LinkedIn — RSS only (rss.app, FetchRSS, or LinkedIn public job search RSS)
# Comma-separated list of feed URLs in env: LINKEDIN_RSS_URLS
# ---------------------------------------------------------------------------
def _parse_rss_urls(raw: str | None) -> List[str]:
    if not raw or not raw.strip():
        return []
    return [u.strip() for u in raw.split(",") if u.strip()]


LINKEDIN_RSS_URLS: List[str] = _parse_rss_urls(os.getenv("LINKEDIN_RSS_URLS", ""))

# LinkedIn feed posts (optional — unofficial API; often blocked without 2FA app password)
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# ---------------------------------------------------------------------------
# JobSpy (Indeed + Glassdoor) — Egypt + Gulf by default (no broad “Worldwide” noise)
# Set JOBSPY_INCLUDE_REMOTE=1 to add Remote + Worldwide rows back.
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
    "Manama, Bahrain",
]

if os.getenv("JOBSPY_INCLUDE_REMOTE", "0") == "1":
    LOCATIONS.extend(["Remote", "Worldwide"])


def country_indeed_for_location(location: str) -> str:
    """
    Map a human location string to JobSpy's country_indeed value.

    JobSpy expects lowercase full country names (see library error message),
    not ISO alpha-2 codes (e.g. egypt, not EG).
    """
    loc = location.lower()
    if any(x in loc for x in ("egypt", "cairo", "giza", "alexandria")):
        return "egypt"
    if any(x in loc for x in ("saudi", "riyadh", "jeddah")):
        return "saudi arabia"
    if any(x in loc for x in ("uae", "dubai", "abu dhabi", "emirates")):
        return "united arab emirates"
    if "qatar" in loc or "doha" in loc:
        return "qatar"
    if "kuwait" in loc:
        return "kuwait"
    if "bahrain" in loc or "manama" in loc:
        return "bahrain"
    # Remote-only strings (when JOBSPY_INCLUDE_REMOTE=1)
    return "usa"


# ---------------------------------------------------------------------------
# We Work Remotely — default programming / full-stack category RSS
# ---------------------------------------------------------------------------
WEWORKREMOTELY_RSS_URL = os.getenv(
    "WEWORKREMOTELY_RSS_URL",
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
)

# ---------------------------------------------------------------------------
# Remotive — free JSON API (no key)
# ---------------------------------------------------------------------------
REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"
REMOTIVE_SEARCH_TERMS: List[str] = [
    t.strip()
    for t in os.getenv("REMOTIVE_SEARCH", ".net,c#").split(",")
    if t.strip()
]
REMOTIVE_QUERY_DELAY_SEC = float(os.getenv("REMOTIVE_QUERY_DELAY_SEC", "0.5"))

# ---------------------------------------------------------------------------
# Rate limits & batch sizes
# ---------------------------------------------------------------------------
HTTP_TIMEOUT_SEC = 25
RSS_DELAY_SEC = float(os.getenv("RSS_DELAY_SEC", "1.2"))
JOBSPY_HOURS_OLD = int(os.getenv("JOBSPY_HOURS_OLD", "72"))
JOBSPY_RESULTS = int(os.getenv("JOBSPY_RESULTS", "25"))
JOBSPY_MAX_WORKERS = int(os.getenv("JOBSPY_MAX_WORKERS", "4"))

# ---------------------------------------------------------------------------
# CI fast mode (GitHub Actions) — fewer JobSpy combos
# ---------------------------------------------------------------------------
if os.getenv("BOT_CI_FAST") == "1":
    SEARCH_KEYWORDS = SEARCH_KEYWORDS[:2]
    LOCATIONS = LOCATIONS[:5]
    JOBSPY_RESULTS = min(JOBSPY_RESULTS, 12)
    REMOTIVE_SEARCH_TERMS = REMOTIVE_SEARCH_TERMS[:1]

# ---------------------------------------------------------------------------
# Source ordering for Telegram (lower = notified first)
# ---------------------------------------------------------------------------
SOURCE_PRIORITY: dict[str, int] = {
    "linkedin_post": 0,  # feed posts — highest trust / earliest signal
    "linkedin_rss": 1,
    "wuzzuf": 2,
    "indeed": 3,
    "glassdoor": 3,
    "zip_recruiter": 4,
    "google": 4,
    "remotive": 5,
    "weworkremotely": 6,
}

DEFAULT_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; DotNet-Jobs-Bot/1.0; "
        "+https://github.com/DotNet-Jobs-Bot; job alerts for developers)"
    ),
    "Accept": "application/rss+xml, application/xml, application/json, */*;q=0.8",
}

# Remotive + We Work Remotely add noise; enable only if you want global remote boards.
ENABLE_REMOTE_BOARDS = os.getenv("ENABLE_REMOTE_BOARDS", "0") == "1"

# Telegram: only Egypt/Gulf rows unless from trusted sources (posts, Wuzzuf) — see main.py
STRICT_REGION_FILTER = os.getenv("STRICT_REGION_FILTER", "1") == "1"

# Delay between Wuzzuf keyword hits (be polite to their HTML)
WUZZUF_DELAY_SEC = float(os.getenv("WUZZUF_DELAY_SEC", "1.5"))
