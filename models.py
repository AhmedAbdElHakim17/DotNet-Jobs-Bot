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
)


def _contains_any(text: str, words: List[str]) -> bool:
    t = text.lower()
    return any(w.lower() in t for w in words)


def _title_excluded(title: str) -> bool:
    tl = title.lower()
    for kw in TITLE_EXCLUDE_KEYWORDS:
        if re.search(r"\b" + re.escape(kw.lower()) + r"\b", tl):
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

    def is_relevant(self) -> bool:
        """Strong .NET filter + light tech exclusions + title gating."""
        text = f"{self.title} {self.company} {self.description} {self.location}".lower()
        if _contains_any(text, EXCLUDE_KEYWORDS):
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
