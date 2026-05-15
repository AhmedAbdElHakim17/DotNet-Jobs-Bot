import re
import urllib.parse
import pandas as pd
import requests as http_requests
from datetime import date
from bs4 import BeautifulSoup
from jobspy import scrape_jobs
from models import Job
from config import (
    SEARCH_KEYWORDS,
    LOCATIONS,
    INCLUDE_KEYWORDS,
    LINKEDIN_EMAIL,
    LINKEDIN_PASSWORD,
    LINKEDIN_JOBSPY_RESULTS,
)
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Thread-safe lock for managing shared data structures
_jobs_lock = threading.Lock()

def _safe(val, default=""):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return str(val)

def _fetch_linkedin_single_search(keyword: str, location: str) -> list[Job]:
    """Fetch LinkedIn jobs for a single keyword+location combination."""
    jobs = []
    try:
        df = scrape_jobs(
            site_name=["linkedin"],
            search_term=keyword,
            location=location,
            results_wanted=LINKEDIN_JOBSPY_RESULTS,
            hours_old=48,
        )
        for _, row in df.iterrows():
            title   = _safe(row.get("title"))
            company = _safe(row.get("company"))
            jobs.append(Job(
                id=_safe(row.get("id")) or f"{title}_{company}",
                title=title,
                company=company,
                location=_safe(row.get("location")),
                link=_safe(row.get("job_url")),
                description=_safe(row.get("description")),
                posted=_safe(row.get("date_posted"), "Recently"),
                salary=_safe(row.get("min_amount")) or None,
            ))
    except Exception as e:
        print(f"[LinkedIn] Error scraping '{keyword}' in {location}: {e}")
    return jobs

def _fetch_linkedin_jobs() -> list[Job]:
    """Fetch LinkedIn jobs using parallel processing for multiple keyword+location combinations."""
    all_jobs = []
    max_workers = min(8, len(SEARCH_KEYWORDS) * len(LOCATIONS))  # Limit concurrent threads
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for keyword in SEARCH_KEYWORDS:
            for location in LOCATIONS:
                future = executor.submit(_fetch_linkedin_single_search, keyword, location)
                futures[future] = f"{keyword} in {location}"
        
        for future in as_completed(futures):
            try:
                jobs = future.result()
                all_jobs.extend(jobs)
            except Exception as e:
                print(f"[LinkedIn] Error: {e}")
    
    return all_jobs

def _fetch_wuzzuf_jobs() -> list[Job]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    all_jobs = []
    seen_links = set()
    for keyword in SEARCH_KEYWORDS:
        query = urllib.parse.quote_plus(keyword)
        url = f"https://wuzzuf.net/search/jobs/?q={query}&a=hpb"
        try:
            resp = http_requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"[Wuzzuf] Request failed for '{keyword}': {e}")
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
                    if any(c in text for c in ["Cairo", "Egypt", "Giza", "Alexandria", "Remote", "Hybrid"]):
                        location = text
                        break

            all_jobs.append(Job(
                id=link,
                title=title,
                company=company,
                location=location or "Egypt",
                link=link,
                description="",
                posted="Recently",
                salary=None,
            ))
    return all_jobs

def _fetch_linkedin_posts() -> list[Job]:
    """Search LinkedIn social posts for .NET hiring announcements."""
    if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
        print(
            "[LinkedIn Posts] Skipping: LINKEDIN_EMAIL / LINKEDIN_PASSWORD not set. "
            "Add both as repo secrets (or in .env locally) to enable post search."
        )
        return []
    try:
        from linkedin_api import Linkedin
    except ImportError:
        print("[LinkedIn Posts] linkedin-api not installed. Run: pip install linkedin-api")
        return []

    try:
        api = Linkedin(LINKEDIN_EMAIL, LINKEDIN_PASSWORD)
    except Exception as e:
        print(f"[LinkedIn Posts] Auth failed: {e}")
        return []

    posts = []
    seen_ids = set()
    search_terms = [".NET developer hiring", "C# developer hiring", "ASP.NET hiring"]

    for term in search_terms:
        try:
            results = api.search(keywords=term, result_types=["CONTENT"], limit=15)
            for item in results:
                if not isinstance(item, dict):
                    continue

                # Extract post text
                text = ""
                for path in [
                    ["commentary", "text", "text"],
                    ["title", "text"],
                    ["description", "text"],
                ]:
                    node = item
                    for key in path:
                        node = node.get(key) if isinstance(node, dict) else None
                    if isinstance(node, str) and node.strip():
                        text = node.strip()
                        break

                if not text:
                    continue

                # Filter for .NET relevance
                if not any(kw.lower() in text.lower() for kw in INCLUDE_KEYWORDS):
                    continue

                # Extract author
                author = ""
                for path in [["actor", "name", "text"], ["primarySubtitle", "text"]]:
                    node = item
                    for key in path:
                        node = node.get(key) if isinstance(node, dict) else None
                    if isinstance(node, str) and node.strip():
                        author = node.strip()
                        break

                # Build the post URL from navigationUrl or URN fields
                url = item.get("navigationUrl", "")
                if not url:
                    urn = (
                        item.get("trackingUrn")
                        or item.get("entityUrn")
                        or item.get("urn")
                    )
                    if urn and urn.startswith("urn:li:"):
                        url = f"https://www.linkedin.com/feed/update/{urn}/"
                post_id = url or text[:80]

                if post_id in seen_ids:
                    continue
                seen_ids.add(post_id)

                posts.append(Job(
                    id=post_id,
                    title=text.split("\n")[0][:120],
                    company=author,
                    location="",
                    link=url,
                    description=text,
                    posted="Recently",
                    is_post=True,
                ))
        except Exception as e:
            print(f"[LinkedIn Posts] Error searching '{term}': {e}")

    return posts


def _date_sort_key(job: Job) -> str:
    """Sort key: YYYY-MM-DD string. 'Recently' (Wuzzuf) treated as today."""
    posted = job.posted
    if not posted or posted == "Recently":
        return date.today().isoformat()
    return str(posted)[:10]  # handles both date objects and YYYY-MM-DD strings

def fetch_jobs() -> list[Job]:
    all_jobs = _fetch_linkedin_jobs() + _fetch_wuzzuf_jobs() + _fetch_linkedin_posts()

    # Remove duplicates
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        key = f"{job.id}_{job.link}"
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    # Sort by most recent first
    unique_jobs.sort(key=_date_sort_key, reverse=True)

    return unique_jobs