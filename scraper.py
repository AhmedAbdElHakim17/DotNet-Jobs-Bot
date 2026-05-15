import re
import urllib.parse
import pandas as pd
import requests as http_requests
from bs4 import BeautifulSoup
from jobspy import scrape_jobs
from models import Job
from config import SEARCH_KEYWORDS, LOCATIONS

def _safe(val, default=""):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return str(val)

def _fetch_linkedin_jobs() -> list[Job]:
    all_jobs = []
    for keyword in SEARCH_KEYWORDS:
        for location in LOCATIONS:
            try:
                df = scrape_jobs(
                    site_name=["linkedin"],
                    search_term=keyword,
                    location=location,
                    results_wanted=20,
                    hours_old=6,
                )
                for _, row in df.iterrows():
                    title   = _safe(row.get("title"))
                    company = _safe(row.get("company"))
                    all_jobs.append(Job(
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

def fetch_jobs() -> list[Job]:
    all_jobs = _fetch_linkedin_jobs() + _fetch_wuzzuf_jobs()
    
    # Remove duplicates
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        key = f"{job.id}_{job.link}"
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)
    
    return unique_jobs