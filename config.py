import os
from dotenv import load_dotenv

load_dotenv()

# === Strong .NET Focused Keywords ===
INCLUDE_KEYWORDS = [
    ".NET", "C#", "ASP.NET", "ASP.NET Core", "Entity Framework", "EF Core",
    "Microservices", "RabbitMQ", "Clean Architecture", "Blazor", "Hangfire",
    "MediatR", "CQRS", "Dapper", "SignalR", "Full Stack .NET", "Backend .NET"
]

EXCLUDE_KEYWORDS = ["Java", "Python", "PHP", "Node.js", "React Native", "Flutter", "GoLang"]

# Keywords matched against job TITLE only (word boundary) — senior leadership roles to skip
TITLE_EXCLUDE_KEYWORDS = ["lead", "manager", "director", "head of"]

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")   # Group or Channel ID

# Search Settings
SEARCH_KEYWORDS = [".NET Developer", "C# Developer", "ASP.NET", "Full Stack .NET"]
LOCATIONS = ["Egypt", "Remote", "UAE", "Dubai", "Saudi Arabia", "Riyadh", "Qatar"]

# In CI, set BOT_CI_FAST=1 (default in workflow) to cut JobSpy combinations + page size for faster runs (~3 min).
if os.getenv("BOT_CI_FAST") == "1":
    SEARCH_KEYWORDS = SEARCH_KEYWORDS[:2]
    LOCATIONS = LOCATIONS[:3]

LINKEDIN_JOBSPY_RESULTS = 10 if os.getenv("BOT_CI_FAST") == "1" else 20

# LinkedIn Credentials (for post scraping)
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

