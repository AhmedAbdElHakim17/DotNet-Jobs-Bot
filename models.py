"""Domain model for a normalized job posting or LinkedIn hiring post."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from config import (
    EXCLUDE_KEYWORDS,
    HIRING_SIGNALS,
    INCLUDE_KEYWORDS,
    SOURCE_PRIORITY,
    TITLE_EXCLUDE_KEYWORDS,
    TITLE_PLATFORM_EXCLUDE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _exclude_keyword_present(text: str) -> bool:
    """Return True if a hard-exclude technology is found (with word-boundary logic)."""
    t = text.lower()
    for w in EXCLUDE_KEYWORDS:
        wl = w.lower()
        if wl == "java":
            # Avoid matching "JavaScript"
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
    """Return True if the title matches leadership or unrelated-platform patterns."""
    tl = title.lower()
    for kw in TITLE_EXCLUDE_KEYWORDS:
        if re.search(r"\b" + re.escape(kw.lower()) + r"\b", tl):
            return True
    for kw in TITLE_PLATFORM_EXCLUDE:
        if re.search(r"\b" + re.escape(kw.lower()) + r"\b", tl):
            return True
    if re.search(r"\bco[- ]?founder\b", tl) or re.search(r"\bcofounder\b", tl):
        return True
    return False


# ---------------------------------------------------------------------------
# Job / Post model
# ---------------------------------------------------------------------------

@dataclass
class Job:
    """
    Unified model for both structured job listings and LinkedIn hiring posts.

    Fields
    ------
    id          : stable identifier (URL, feed entry ID, or hash)
    title       : job title or first line of a post
    company     : hiring company / post author
    location    : free-text location string
    link        : direct URL to apply or view
    description : full text (used for .NET + hiring-signal matching)
    posted      : ISO date (YYYY-MM-DD) or humanized fallback ("Recently")
    salary      : optional salary string
    source      : one of linkedin_post_rss / linkedin_jobs_rss / wuzzuf / linkedin_jobspy
    is_post     : True  -> LinkedIn social post (use post Telegram template)
                  False -> structured job listing
    matched_keywords : .NET keywords found in this entry (computed on init)
    """

    id: str
    title: str
    company: str
    location: str
    link: str
    description: str = ""
    posted: str = ""
    salary: str | None = None
    source: str = "unknown"
    is_post: bool = False
    matched_keywords: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.matched_keywords:
            self.matched_keywords = self._compute_matched_keywords()

    # ------------------------------------------------------------------
    # Keyword helpers
    # ------------------------------------------------------------------

    def _compute_matched_keywords(self) -> List[str]:
        text = f"{self.title} {self.company} {self.description} {self.location}"
        found = {kw for kw in INCLUDE_KEYWORDS if kw.lower() in text.lower()}
        return sorted(found, key=len, reverse=True)

    def hiring_score(self) -> int:
        """
        Count how many hiring-intent signals appear in title + description.

        Score guide:
          0  -> no visible hiring intent  (filter out posts, pass listings)
          1  -> weak signal
          2+ -> active hiring announcement  (high priority)
        """
        text = f"{self.title} {self.description}".lower()
        return sum(1 for sig in HIRING_SIGNALS if sig.lower() in text)

    # ------------------------------------------------------------------
    # Relevance filter
    # ------------------------------------------------------------------

    def is_relevant(self) -> bool:
        """
        Two-pass filter:
          1. Must contain at least one .NET keyword anywhere.
             (Skipped for apify_linkedin — the search query already guarantees .NET relevance.)
          2. Must not be a hard-excluded technology.
          3. Job listings: title must pass leadership / platform exclusion.
          4. LinkedIn posts: must have at least one hiring signal.
        """
        text = f"{self.title} {self.company} {self.description} {self.location}"

        # Apify queries are pre-filtered for .NET, so trust the query result.
        # For all other sources, require at least one .NET keyword in the text.
        if self.source != "apify_linkedin":
            if not any(kw.lower() in text.lower() for kw in INCLUDE_KEYWORDS):
                return False

        # Reject hard-excluded stacks
        if _exclude_keyword_present(text):
            return False

        if self.is_post:
            # Posts must show hiring intent to avoid generic .NET discussion noise
            return self.hiring_score() > 0
        else:
            # Job listings must not be leadership/platform roles
            return not _title_excluded(self.title)

    # ------------------------------------------------------------------
    # Sorting helpers
    # ------------------------------------------------------------------

    def geo_bucket(self) -> str:
        """Coarse geo label for sorting. Egypt > Gulf > Remote > other."""
        text = f"{self.title} {self.location}".lower()
        if any(x in text for x in ("egypt", "cairo", "giza", "alexandria")):
            return "egypt"
        if any(x in text for x in (
            "uae", "dubai", "abu dhabi", "saudi", "riyadh",
            "qatar", "doha", "bahrain", "kuwait", "gulf",
        )):
            return "gulf"
        if any(x in text for x in ("remote", "worldwide", "anywhere")):
            return "remote"
        return "other"

    def source_priority(self) -> int:
        return SOURCE_PRIORITY.get(self.source.lower(), 99)
