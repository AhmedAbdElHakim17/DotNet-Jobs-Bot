"""
Scrapers for DotNet-Jobs-Bot.

Execution order (source priority):
  1. fetch_linkedin_posts_rss()  -- LinkedIn feed posts via rss.app (PRIMARY)
  2. fetch_linkedin_jobs_rss()   -- LinkedIn job listings via rss.app
  3. fetch_wuzzuf_jobs()         -- Wuzzuf HTML scrape (Egypt)
  4. fetch_jobspy_jobs()         -- python-jobspy LinkedIn (fallback)

fetch_jobs() aggregates all sources, deduplicates by id+link,
and returns entries sorted newest-first.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from time import mktime
from typing import Any

import feedparser
import pandas as pd
import requests
from bs4 import BeautifulSoup
from jobspy import scrape_jobs

from config import (
    DEFAULT_REQUEST_HEADERS,
    HTTP_TIMEOUT_SEC,
    JOBSPY_HOURS_OLD,
    JOBSPY_MAX_WORKERS,
    JOBSPY_RESULTS,
    LINKEDIN_COOKIE,
    LINKEDIN_EMAIL,
    LINKEDIN_JOBS_RSS_URLS,
    LINKEDIN_PASSWORD,
    LINKEDIN_POSTS_RSS_URLS,
    LOCATIONS,
    RSS_DELAY_SEC,
    SEARCH_KEYWORDS,
    WUZZUF_DELAY_SEC,
)
from models import Job

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _safe(val: Any, default: str = "") -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return str(val)


def _sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _parse_date(entry: Any) -> str:
    """Best-effort ISO date from an RSS/Atom feed entry."""
    try:
        if getattr(entry, "published_parsed", None):
            return datetime.fromtimestamp(mktime(entry.published_parsed)).date().isoformat()
        if getattr(entry, "updated_parsed", None):
            return datetime.fromtimestamp(mktime(entry.updated_parsed)).date().isoformat()
    except Exception:
        pass
    if getattr(entry, "published", None):
        try:
            return parsedate_to_datetime(entry.published).date().isoformat()
        except Exception:
            pass
    return "Recently"


def _fetch_rss(url: str) -> bytes | None:
    """Download an RSS feed, return raw bytes or None on failure."""
    try:
        r = requests.get(url, headers=DEFAULT_REQUEST_HEADERS, timeout=HTTP_TIMEOUT_SEC)
        r.raise_for_status()
        return r.content
    except Exception as e:
        logger.warning("RSS fetch failed (%s): %s", url, e)
        return None


def _parse_rss_to_jobs(content: bytes, source: str, is_post: bool) -> list[Job]:
    """
    Parse raw RSS/Atom bytes into Job objects.

    source  : one of 'linkedin_post_rss', 'linkedin_jobs_rss'
    is_post : True  -> LinkedIn hiring post (social feed)
              False -> LinkedIn job listing
    """
    parsed = feedparser.parse(content)
    if getattr(parsed, "bozo", False) and not parsed.entries:
        logger.warning("RSS parse error (%s): %s", source, getattr(parsed, "bozo_exception", ""))

    jobs: list[Job] = []
    for entry in parsed.entries:
        title = _safe(getattr(entry, "title", None))
        link = _safe(getattr(entry, "link", None))
        if not title or not link:
            continue

        # Description / summary
        desc = ""
        if hasattr(entry, "summary"):
            desc = _safe(entry.summary)
        elif hasattr(entry, "description"):
            desc = _safe(entry.description)
        # Strip HTML tags from description
        desc = re.sub(r"<[^>]+>", " ", desc).strip()

        # Stable ID
        entry_id = _safe(getattr(entry, "id", None)) or link
        stable_id = entry_id or _sha16(title + link)

        # Author / company
        company = ""
        if getattr(entry, "author", None):
            company = _safe(entry.author)
        elif getattr(entry, "author_detail", None):
            company = _safe(entry.author_detail.get("name", ""))

        # Location hint from tags
        location = ""
        for tag in getattr(entry, "tags", []):
            term = tag.get("term", "")
            if isinstance(term, str) and any(
                c in term.lower() for c in ("remote", "egypt", "uae", "dubai", "cairo", "riyadh")
            ):
                location = term
                break

        jobs.append(Job(
            id=stable_id,
            title=title.strip(),
            company=company,
            location=location,
            link=link.strip(),
            description=desc[:6000],
            posted=_parse_date(entry),
            source=source,
            is_post=is_post,
        ))

    logger.info("RSS (%s): parsed %d entries", source, len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Source 1 — LinkedIn Posts RSS  (PRIMARY)
# ---------------------------------------------------------------------------

def fetch_linkedin_posts_rss() -> list[Job]:
    """
    Fetch LinkedIn hiring posts from rss.app RSS feeds.

    These are social feed posts (not Jobs tab) where recruiters and companies
    post "We are hiring .NET developers!" type announcements.

    Configure via: LINKEDIN_POSTS_RSS_URLS=https://rss.app/feeds/XXX.xml,...
    """
    if not LINKEDIN_POSTS_RSS_URLS:
        logger.info(
            "LinkedIn Posts RSS: not configured. "
            "Set LINKEDIN_POSTS_RSS_URLS in .env (see README)."
        )
        return []

    all_jobs: list[Job] = []
    for url in LINKEDIN_POSTS_RSS_URLS:
        raw = _fetch_rss(url)
        if raw:
            all_jobs.extend(_parse_rss_to_jobs(raw, "linkedin_post_rss", is_post=True))
        time.sleep(RSS_DELAY_SEC)

    logger.info("LinkedIn Posts RSS: %d total entries", len(all_jobs))
    return all_jobs


# ---------------------------------------------------------------------------
# Source 2 — LinkedIn Jobs RSS
# ---------------------------------------------------------------------------

def fetch_linkedin_jobs_rss() -> list[Job]:
    """
    Fetch LinkedIn job listings from rss.app RSS feeds.

    These target the LinkedIn Jobs tab search results (structured listings).

    Configure via: LINKEDIN_JOBS_RSS_URLS=https://rss.app/feeds/YYY.xml,...
    """
    if not LINKEDIN_JOBS_RSS_URLS:
        logger.info(
            "LinkedIn Jobs RSS: not configured. "
            "Set LINKEDIN_JOBS_RSS_URLS in .env (see README)."
        )
        return []

    all_jobs: list[Job] = []
    for url in LINKEDIN_JOBS_RSS_URLS:
        raw = _fetch_rss(url)
        if raw:
            all_jobs.extend(_parse_rss_to_jobs(raw, "linkedin_jobs_rss", is_post=False))
        time.sleep(RSS_DELAY_SEC)

    logger.info("LinkedIn Jobs RSS: %d total entries", len(all_jobs))
    return all_jobs


# ---------------------------------------------------------------------------
# Source 3 — Wuzzuf (Egypt-focused HTML scrape)
# ---------------------------------------------------------------------------

def fetch_wuzzuf_jobs() -> list[Job]:
    """Scrape Wuzzuf job search results for each configured keyword."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    all_jobs: list[Job] = []
    seen_links: set[str] = set()

    for keyword in SEARCH_KEYWORDS:
        query = urllib.parse.quote_plus(keyword)
        url = f"https://wuzzuf.net/search/jobs/?q={query}&a=hpb"
        try:
            resp = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT_SEC)
            resp.raise_for_status()
        except Exception as e:
            logger.warning("Wuzzuf request failed for %r: %s", keyword, e)
            continue

        soup = BeautifulSoup(resp.text, "lxml")
        for a_tag in soup.find_all("a", href=re.compile(r"^/jobs/p/")):
            link = "https://wuzzuf.net" + a_tag["href"].split("?")[0]
            if link in seen_links:
                continue
            seen_links.add(link)

            title = a_tag.get_text(strip=True)
            if not title:
                continue

            company, location = "", ""
            card = a_tag.find_parent("div")
            if card:
                company_tag = card.find("a", href=re.compile(r"/company/"))
                if company_tag:
                    company = company_tag.get_text(strip=True)
                for span in card.find_all("span"):
                    text = span.get_text(strip=True)
                    if any(c in text for c in (
                        "Cairo", "Egypt", "Giza", "Alexandria", "Remote", "Hybrid",
                        "Dubai", "Riyadh", "Saudi", "Qatar",
                    )):
                        location = text
                        break

            all_jobs.append(Job(
                id=link,
                title=title,
                company=company,
                location=location or "Egypt",
                link=link,
                source="wuzzuf",
            ))

        time.sleep(WUZZUF_DELAY_SEC)

    logger.info("Wuzzuf: %d listings (pre-dedup)", len(all_jobs))
    return all_jobs


# ---------------------------------------------------------------------------
# Source 4 — LinkedIn via JobSpy (fallback)
# ---------------------------------------------------------------------------

def _jobspy_single(keyword: str, location: str) -> list[Job]:
    """Run one JobSpy LinkedIn search for keyword + location."""
    jobs: list[Job] = []
    try:
        df = scrape_jobs(
            site_name=["linkedin"],
            search_term=keyword,
            location=location,
            results_wanted=JOBSPY_RESULTS,
            hours_old=JOBSPY_HOURS_OLD,
        )
    except Exception as e:
        logger.warning("JobSpy error for %r @ %r: %s", keyword, location, e)
        return jobs

    if df is None or df.empty:
        return jobs

    for _, row in df.iterrows():
        title = _safe(row.get("title"))
        company = _safe(row.get("company"))
        link = _safe(row.get("job_url"))
        if not link:
            continue
        jid = _safe(row.get("id")) or _sha16(f"{title}|{company}|{link}")
        jobs.append(Job(
            id=jid,
            title=title,
            company=company,
            location=_safe(row.get("location")),
            link=link,
            description=_safe(row.get("description"))[:6000],
            posted=_safe(row.get("date_posted"), "Recently"),
            salary=_safe(row.get("min_amount")) or None,
            source="linkedin_jobspy",
        ))
    return jobs


def fetch_jobspy_jobs() -> list[Job]:
    """Scrape LinkedIn via JobSpy for each keyword/location pair (bounded concurrency)."""
    tasks = [(kw, loc) for kw in SEARCH_KEYWORDS for loc in LOCATIONS]
    if not tasks:
        return []

    all_jobs: list[Job] = []
    with ThreadPoolExecutor(max_workers=min(JOBSPY_MAX_WORKERS, len(tasks))) as ex:
        futures = {ex.submit(_jobspy_single, kw, loc): (kw, loc) for kw, loc in tasks}
        for fut in as_completed(futures):
            try:
                all_jobs.extend(fut.result())
            except Exception as e:
                kw, loc = futures[fut]
                logger.warning("JobSpy task failed %r @ %r: %s", kw, loc, e)

    logger.info("JobSpy: %d listings (pre-dedup)", len(all_jobs))
    return all_jobs


# ---------------------------------------------------------------------------
# Optional: LinkedIn unofficial API post search
# ---------------------------------------------------------------------------

def fetch_linkedin_api_posts() -> list[Job]:
    """
    Search LinkedIn social feed for .NET hiring posts via the unofficial linkedin-api.

    This is blocked by LinkedIn in most automated environments. Use RSS feeds instead.
    Only runs when LINKEDIN_COOKIE or LINKEDIN_EMAIL + LINKEDIN_PASSWORD are set.
    """
    if not LINKEDIN_COOKIE and not (LINKEDIN_EMAIL and LINKEDIN_PASSWORD):
        return []

    try:
        from linkedin_api import Linkedin  # type: ignore
    except ImportError:
        logger.warning("linkedin-api not installed. Run: pip install linkedin-api")
        return []

    try:
        if LINKEDIN_COOKIE:
            api = Linkedin("", "", cookies={"li_at": LINKEDIN_COOKIE})
        else:
            api = Linkedin(LINKEDIN_EMAIL, LINKEDIN_PASSWORD)
    except Exception as e:
        logger.warning(
            "LinkedIn API auth failed (checkpoint / 2FA / rate-limit): %s — "
            "use LINKEDIN_POSTS_RSS_URLS instead.", e,
        )
        return []

    posts: list[Job] = []
    seen_ids: set[str] = set()
    search_terms = [
        ".NET developer hiring", "C# developer hiring",
        "ASP.NET hiring Egypt", ".NET developer Gulf",
    ]

    for term in search_terms:
        try:
            results = api.search(keywords=term, result_types=["CONTENT"], limit=10)
            for item in results:
                if not isinstance(item, dict):
                    continue

                # Extract post text
                text = ""
                for path in (
                    ["commentary", "text", "text"],
                    ["title", "text"],
                    ["description", "text"],
                ):
                    node: Any = item
                    for key in path:
                        node = node.get(key) if isinstance(node, dict) else None
                    if isinstance(node, str) and node.strip():
                        text = node.strip()
                        break

                if not text:
                    continue

                # Author
                author = ""
                for path in (["actor", "name", "text"], ["primarySubtitle", "text"]):
                    node = item
                    for key in path:
                        node = node.get(key) if isinstance(node, dict) else None
                    if isinstance(node, str) and node.strip():
                        author = node.strip()
                        break

                # URL
                url = item.get("navigationUrl", "") or ""
                if not url:
                    urn = item.get("trackingUrn") or item.get("entityUrn") or ""
                    if isinstance(urn, str) and urn.startswith("urn:li:"):
                        url = f"https://www.linkedin.com/feed/update/{urn}/"
                post_id = url or _sha16(text[:80])

                if post_id in seen_ids:
                    continue
                seen_ids.add(post_id)

                posts.append(Job(
                    id=post_id,
                    title=text.split("\n")[0][:120],
                    company=author,
                    location="",
                    link=str(url),
                    description=text,
                    source="linkedin_post_rss",  # same priority bucket as RSS posts
                    is_post=True,
                ))
        except Exception as e:
            logger.warning("LinkedIn API search %r failed: %s", term, e)
        time.sleep(2.0)

    logger.info("LinkedIn API posts: %d items", len(posts))
    return posts


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def _posted_ts(posted: str) -> float:
    """Convert posted string to sortable timestamp (newer = higher)."""
    if not posted or posted == "Recently":
        return datetime.combine(date.today(), datetime.min.time()).timestamp()
    try:
        return datetime.fromisoformat(str(posted)[:10]).timestamp()
    except Exception:
        return 0.0


def fetch_jobs() -> list[Job]:
    """
    Collect from all sources, deduplicate, and return sorted newest-first.

    Sort key: posted date (desc) -> source priority -> geo (Egypt first)
    """
    geo_rank = {"egypt": 0, "gulf": 1, "remote": 2, "other": 3}

    combined: list[Job] = []
    combined.extend(fetch_linkedin_posts_rss())
    combined.extend(fetch_linkedin_jobs_rss())
    combined.extend(fetch_wuzzuf_jobs())
    combined.extend(fetch_jobspy_jobs())
    combined.extend(fetch_linkedin_api_posts())

    # Deduplicate by id + link
    seen: set[str] = set()
    unique: list[Job] = []
    for job in combined:
        key = f"{job.id}_{job.link}"
        if key not in seen:
            seen.add(key)
            unique.append(job)

    # Sort: newest first, then source priority, then Egypt > Gulf > Remote
    unique.sort(key=lambda j: (
        -_posted_ts(j.posted),
        j.source_priority(),
        geo_rank.get(j.geo_bucket(), 3),
    ))

    return unique
