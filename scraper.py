from jobspy import scrape_jobs
from models import Job
from config import SEARCH_KEYWORDS, LOCATIONS

def fetch_jobs() -> list[Job]:
    all_jobs = []
    
    for keyword in SEARCH_KEYWORDS:
        for location in LOCATIONS:
            try:
                jobs = scrape_jobs(
                    site_name=["linkedin", "indeed", "glassdoor", "remotely"],
                    search_term=keyword,
                    location=location,
                    results_wanted=20,
                    hours_old=24,           # Only recent jobs
                )
                
                for job in jobs:
                    job_obj = Job(
                        id=str(job.id) if job.id else f"{job.title}_{job.company}",
                        title=job.title,
                        company=job.company,
                        location=job.location,
                        link=job.link,
                        description=job.description or "",
                        posted=job.date_posted or "Recently",
                        salary=job.salary
                    )
                    all_jobs.append(job_obj)
            except Exception as e:
                print(f"Error scraping {keyword} in {location}: {e}")
    
    # Remove duplicates
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        key = f"{job.id}_{job.link}"
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)
    
    return unique_jobs