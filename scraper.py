"""
Scrapers and aggregators for job boards and RSS feeds.

Priority (for alerting order):
  1. LinkedIn — RSS feeds only (no login; configure LINKEDIN_RSS_URLS).
  2. Indeed & Glassdoor — python-jobspy.
  3. Remotive — public JSON API.
  4. We Work Remotely — category RSS.

All functions are defensive: log and continue on per-source failures.
"""

from __future__ import annotations

import hashlib
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from time import mktime
from typing import Any

import feedparser
import pandas as pd
import requests
from jobspy import scrape_jobs

from config import (
    DEFAULT_REQUEST_HEADERS,
    HTTP_TIMEOUT_SEC,
    JOBSPY_HOURS_OLD,
    JOBSPY_MAX_WORKERS,
    JOBSPY_RESULTS,
    LINKEDIN_RSS_URLS,
    LOCATIONS,
    REMOTIVE_API_URL,
    REMOTIVE_QUERY_DELAY_SEC,
    REMOTIVE_SEARCH_TERMS,
    RSS_DELAY_SEC,
    SEARCH_KEYWORDS,
    WEWORKREMOTELY_RSS_URL,
    country_indeed_for_location,
)
from models import Job

logger = logging.getLogger(__name__)


def _safe(val: Any, default: str = "") -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return str(val)


def _sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _parse_date_from_feed_entry(entry: Any) -> str:
    """Best-effort published date for RSS/Atom entries."""
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


def _fetch_rss_bytes(url: str) -> bytes | None:
    try:
        r = requests.get(
            url,
            headers=DEFAULT_REQUEST_HEADERS,
            timeout=HTTP_TIMEOUT_SEC,
        )
        r.raise_for_status()
        return r.content
    except Exception as e:
        logger.warning("RSS fetch failed for %s: %s", url, e)
        return None


def _jobs_from_feed_body(
    content: bytes,
    source_key: str,
    feed_label: str,
) -> list[Job]:
    parsed = feedparser.parse(content)
    if getattr(parsed, "bozo", False) and not parsed.entries:
        logger.warning("RSS parse issue (%s): %s", feed_label, getattr(parsed, "bozo_exception", ""))

    jobs: list[Job] = []
    for entry in parsed.entries:
        title = _safe(getattr(entry, "title", None))
        link = _safe(getattr(entry, "link", None))
        summary = ""
        if hasattr(entry, "summary"):
            summary = _safe(entry.summary)
        elif hasattr(entry, "description"):
            summary = _safe(entry.description)

        if not title or not link:
            continue

        entry_id = _safe(getattr(entry, "id", None))
        if not entry_id and hasattr(entry, "guid"):
            g = entry.guid
            entry_id = _safe(getattr(g, "value", None) if g is not None else g)
        stable_id = entry_id or link or _sha16(title + link)

        company = ""
        # Atom author / RSS dc:creator heuristics
        if getattr(entry, "author", None):
            company = _safe(entry.author)
        elif getattr(entry, "author_detail", None) and entry.author_detail.get("name"):
            company = _safe(entry.author_detail.get("name"))

        location = ""
        if getattr(entry, "tags", None):
            for tag in entry.tags:
                term = tag.get("term", "")
                if isinstance(term, str) and any(
                    c in term.lower() for c in ("remote", "egypt", "uae", "dubai", "cairo")
                ):
                    location = term

        jobs.append(
            Job(
                id=stable_id,
                title=title.strip(),
                company=company,
                location=location,
                link=link.strip(),
                description=summary[:8000],
                posted=_parse_date_from_feed_entry(entry),
                salary=None,
                source=source_key,
            )
        )
    logger.info("Parsed %d items from %s", len(jobs), feed_label)
    return jobs


def fetch_linkedin_rss_jobs() -> list[Job]:
    """Highest-priority source: LinkedIn job search exposed as RSS (third-party or public feed)."""
    if not LINKEDIN_RSS_URLS:
        logger.info(
            "LinkedIn RSS: no LINKEDIN_RSS_URLS configured — see README for rss.app setup."
        )
        return []

    all_jobs: list[Job] = []
    for url in LINKEDIN_RSS_URLS:
        raw = _fetch_rss_bytes(url)
        if raw is None:
            continue
        all_jobs.extend(_jobs_from_feed_body(raw, "linkedin_rss", url))
        time.sleep(RSS_DELAY_SEC)
    return all_jobs


def fetch_weworkremotely_rss_jobs() -> list[Job]:
    if not WEWORKREMOTELY_RSS_URL:
        return []
    raw = _fetch_rss_bytes(WEWORKREMOTELY_RSS_URL)
    if raw is None:
        return []
    return _jobs_from_feed_body(raw, "weworkremotely", WEWORKREMOTELY_RSS_URL)


def fetch_remotive_api_jobs() -> list[Job]:
    """Public API, multiple search terms; dedupe by application URL."""
    jobs_by_link: dict[str, Job] = {}
    terms = REMOTIVE_SEARCH_TERMS or [".net"]

    for term in terms:
        try:
            r = requests.get(
                REMOTIVE_API_URL,
                params={"search": term},
                headers=DEFAULT_REQUEST_HEADERS,
                timeout=HTTP_TIMEOUT_SEC,
            )
            r.raise_for_status()
            payload = r.json()
        except Exception as e:
            logger.warning("Remotive API failed for search %r: %s", term, e)
            continue

        for row in payload.get("jobs", []):
            title = _safe(row.get("title"))
            link = _safe(row.get("url"))
            if not title or not link or link in jobs_by_link:
                continue
            jid = _safe(row.get("id")) or link
            company = _safe(row.get("company_name"))
            category = _safe(row.get("category"))
            loc = _safe(row.get("candidate_required_location")) or category
            posted = _safe(row.get("publication_date"), "Recently")[:10]
            desc = _safe(row.get("description"))[:8000]
            jobs_by_link[link] = Job(
                id=jid,
                title=title,
                company=company,
                location=loc,
                link=link,
                description=desc,
                posted=posted,
                salary=None,
                source="remotive",
            )
        time.sleep(REMOTIVE_QUERY_DELAY_SEC)

    jobs = list(jobs_by_link.values())
    logger.info("Remotive: fetched %d unique listings", len(jobs))
    return jobs


def _jobspy_single_search(keyword: str, location: str) -> list[Job]:
    jobs: list[Job] = []
    country = country_indeed_for_location(location)
    try:
        df = scrape_jobs(
            site_name=["indeed", "glassdoor"],
            search_term=keyword,
            location=location,
            results_wanted=JOBSPY_RESULTS,
            hours_old=JOBSPY_HOURS_OLD,
            country_indeed=country,
        )
    except Exception as e:
        logger.warning("JobSpy error for %r @ %r: %s", keyword, location, e)
        return jobs

    if df is None or df.empty:
        return jobs

    for _, row in df.iterrows():
        site_raw = _safe(row.get("site")).lower() or "indeed"
        if site_raw not in ("indeed", "glassdoor"):
            # Normalize JobSpy site labels
            site_key = site_raw.replace(" ", "_")
        else:
            site_key = site_raw

        title = _safe(row.get("title"))
        company = _safe(row.get("company"))
        link = _safe(row.get("job_url"))
        if not link:
            continue
        jid = _safe(row.get("id")) or _sha16(f"{title}|{company}|{link}")

        jobs.append(
            Job(
                id=jid,
                title=title,
                company=company,
                location=_safe(row.get("location")),
                link=link,
                description=_safe(row.get("description"))[:8000],
                posted=_safe(row.get("date_posted"), "Recently"),
                salary=_safe(row.get("min_amount")) or None,
                source=site_key,
            )
        )
    return jobs


def fetch_jobspy_jobs() -> list[Job]:
    """Indeed + Glassdoor in one go per keyword/location cell (bounded concurrency)."""
    tasks: list[tuple[str, str]] = [
        (kw, loc) for kw in SEARCH_KEYWORDS for loc in LOCATIONS
    ]
    if not tasks:
        return []

    all_jobs: list[Job] = []
    max_workers = min(JOBSPY_MAX_WORKERS, len(tasks))
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_jobspy_single_search, k, l): (k, l) for k, l in tasks}
        for fut in as_completed(futures):
            k, loc = futures[fut]
            try:
                batch = fut.result()
                all_jobs.extend(batch)
            except Exception as e:
                logger.warning("JobSpy task failed %r @ %r: %s", k, loc, e)
    logger.info("JobSpy: collected %d listings (pre-dedup)", len(all_jobs))
    return all_jobs


def _geo_sort_rank(job: Job) -> int:
    return {"egypt": 0, "gulf": 1, "remote": 2, "other": 3}.get(job.geo_bucket(), 3)


def _date_sort_val(posted: str) -> str:
    if not posted or posted == "Recently":
        return date.today().isoformat()
    return str(posted)[:10]


def _posted_timestamp(posted: str) -> float:
    """For sort ordering: newer postings first within the same source/geo band."""
    try:
        return datetime.fromisoformat(_date_sort_val(posted)).timestamp()
    except Exception:
        return 0.0


def fetch_jobs() -> list[Job]:
    """
    Aggregate all sources, dedupe by id+link, sort for outbound order:
    source priority → geo (Egypt first) → newest first.
    """
    combined: list[Job] = []
    combined.extend(fetch_linkedin_rss_jobs())
    combined.extend(fetch_jobspy_jobs())
    combined.extend(fetch_remotive_api_jobs())
    combined.extend(fetch_weworkremotely_rss_jobs())

    seen_keys: set[str] = set()
    unique: list[Job] = []
    for job in combined:
        key = f"{job.id}_{job.link}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique.append(job)

    unique.sort(
        key=lambda j: (
            j.source_priority(),
            _geo_sort_rank(j),
            -_posted_timestamp(j.posted),
        ),
    )
    return unique