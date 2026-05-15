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

# LinkedIn Credentials (for post scraping)
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

