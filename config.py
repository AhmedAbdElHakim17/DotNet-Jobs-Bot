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

# ---------------------------------------------------------------------------
# JobSpy (Indeed + Glassdoor) — locations &Indeed country hint
# Geo priority: Egypt metros, Gulf, remote-friendly strings
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
    "Remote",
    "Worldwide",
]


def country_indeed_for_location(location: str) -> str:
    """Map a human location string to an Indeed country code (JobSpy)."""
    loc = location.lower()
    if any(x in loc for x in ("egypt", "cairo", "giza", "alexandria")):
        return "EG"
    if any(x in loc for x in ("saudi", "riyadh", "jeddah")):
        return "SA"
    if any(x in loc for x in ("uae", "dubai", "abu dhabi", "emirates")):
        return "AE"
    if "qatar" in loc or "doha" in loc:
        return "QA"
    # Remote / worldwide — Indeed US index has many remote listings
    return "USA"


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
    LOCATIONS = LOCATIONS[:4]
    JOBSPY_RESULTS = min(JOBSPY_RESULTS, 12)
    REMOTIVE_SEARCH_TERMS = REMOTIVE_SEARCH_TERMS[:1]

# ---------------------------------------------------------------------------
# Source ordering for Telegram (lower = notified first)
# ---------------------------------------------------------------------------
SOURCE_PRIORITY: dict[str, int] = {
    "linkedin_rss": 0,
    "indeed": 1,
    "glassdoor": 1,
    "zip_recruiter": 2,
    "google": 2,
    "remotive": 3,
    "weworkremotely": 4,
}

DEFAULT_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; DotNet-Jobs-Bot/1.0; "
        "+https://github.com/DotNet-Jobs-Bot; job alerts for developers)"
    ),
    "Accept": "application/rss+xml, application/xml, application/json, */*;q=0.8",
}
