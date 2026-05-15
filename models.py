"""Domain model for a normalized job posting."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from config import (
    EXCLUDE_KEYWORDS,
    INCLUDE_KEYWORDS,
    SOURCE_PRIORITY,
    TITLE_EXCLUDE_KEYWORDS,
    TITLE_PLATFORM_EXCLUDE,
)


def _exclude_keyword_present(text: str) -> bool:
    """Substring excludes with word boundaries where needed (avoid Java→JavaScript)."""
    t = text.lower()
    for w in EXCLUDE_KEYWORDS:
        wl = w.lower()
        if wl == "java":
            if re.search(r"\bjava(?!script)\b", t):
                return True
            continue
        if wl == "node.js":
            if "node.js" in t or re.search(r"\bnode\b", t):
                return True
            continue
        if " " in wl or "." in wl:
            if wl in t:
                return True
            continue
        if re.search(r"\b" + re.escape(wl) + r"\b", t):
            return True
    return False


def _title_excluded(title: str) -> bool:
    tl = title.lower()
    for kw in TITLE_EXCLUDE_KEYWORDS:
        if re.search(r"\b" + re.escape(kw.lower()) + r"\b", tl):
            return True
    for kw in TITLE_PLATFORM_EXCLUDE:
        if re.search(r"\b" + re.escape(kw.lower()) + r"\b", tl):
            return True
    # Non-engineering / founder spam common on general “tech” boards
    if re.search(r"\bco[- ]?founder\b", tl) or re.search(r"\bcofounder\b", tl):
        return True
    if re.search(r"\bfundraising\b", tl):
        return True
    return False


@dataclass
class Job:
    """Single job alert, regardless of upstream board or RSS feed."""

    id: str
    title: str
    company: str
    location: str
    link: str
    description: str = ""
    posted: str = ""  # ISO date (YYYY-MM-DD) or humanized fallback
    salary: str | None = None
    source: str = "unknown"  # e.g. linkedin_rss, indeed, remotive
    is_post: bool = False  # True → older “LinkedIn post” style notification

    matched_keywords: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.matched_keywords:
            self.matched_keywords = self._compute_match_keywords()

    def _compute_match_keywords(self) -> List[str]:
        text = f"{self.title} {self.company} {self.description} {self.location}"
        out: List[str] = []
        for kw in INCLUDE_KEYWORDS:
            if kw.lower() in text.lower():
                out.append(kw)
        return sorted(set(out), key=len, reverse=True)

    def _noisy_board_has_dotnet_signal(self) -> bool:
        """Remote job boards often need an explicit stack hint beyond fuzzy keyword matches."""
        if self.source not in ("weworkremotely", "remotive"):
            return True
        blob = f"{self.title} {self.description}".lower()
        hints = (
            ".net",
            "dotnet",
            "c#",
            "c-sharp",
            "asp.net",
            "aspnet",
            "ef core",
            "entity framework",
            "blazor",
            "full stack .net",
        )
        return any(h in blob for h in hints)

    def is_relevant(self) -> bool:
        """Strong .NET filter + light tech exclusions + title gating."""
        text = f"{self.title} {self.company} {self.description} {self.location}".lower()
        if not self._noisy_board_has_dotnet_signal():
            return False
        if _exclude_keyword_present(text):
            return False
        if _title_excluded(self.title):
            return False
        return any(kw.lower() in text for kw in INCLUDE_KEYWORDS)

    def geo_bucket(self) -> str:
        """
        Coarse geo label for sorting / hashtags.
        Egypt > Gulf > Remote/worldwide > other.
        """
        text = f"{self.title} {self.location}".lower()
        if any(
            x in text
            for x in (
                "egypt",
                "cairo",
                "giza",
                "alexandria",
                "مصر",
            )
        ):
            return "egypt"
        if any(
            x in text
            for x in (
                "uae",
                "dubai",
                "abu dhabi",
                "saudi",
                "riyadh",
                "qatar",
                "doha",
                "bahrain",
                "kuwait",
                "oman",
                "gulf",
            )
        ):
            return "gulf"
        if any(x in text for x in ("remote", "worldwide", "anywhere", "work from home")):
            return "remote"
        return "other"

    def source_priority(self) -> int:
        key = self.source.lower().replace(" ", "_")
        return SOURCE_PRIORITY.get(key, 99)
