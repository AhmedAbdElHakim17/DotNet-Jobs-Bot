from scraper import fetch_jobs
from dedup import load_seen, save_seen
from telegram_sender import send_job
from models import Job

def main():
    print("🚀 Starting .NET Jobs Bot...")
    
    seen = load_seen()
    jobs = fetch_jobs()
    
    new_count = 0
    for job in jobs:
        if job.is_relevant() and f"{job.id}_{job.link}" not in seen:
            send_job(job)
            seen.add(f"{job.id}_{job.link}")
            new_count += 1
            print(f"✅ Sent: {job.title}")
    
    save_seen(seen)
    print(f"🎉 Done! Sent {new_count} new .NET jobs.")

if __name__ == "__main__":
    main()