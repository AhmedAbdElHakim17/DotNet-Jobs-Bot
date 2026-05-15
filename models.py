import re
from dataclasses import dataclass
from typing import List
from config import INCLUDE_KEYWORDS, EXCLUDE_KEYWORDS, TITLE_EXCLUDE_KEYWORDS

@dataclass
class Job:
    id: str
    title: str
    company: str
    location: str
    link: str
    description: str = ""
    posted: str = ""
    salary: str = None
    is_post: bool = False  # True for LinkedIn social posts, False for job listings

    def is_relevant(self) -> bool:
        text = f"{self.title} {self.company} {self.description} {self.location}".lower()
        # Exclude by technology keywords (checked across full text)
        if any(ex in text for ex in [k.lower() for k in EXCLUDE_KEYWORDS]):
            return False
        # Exclude leadership/management roles by title only (word-boundary)
        title_lower = self.title.lower()
        if any(re.search(r'\b' + re.escape(kw) + r'\b', title_lower) for kw in TITLE_EXCLUDE_KEYWORDS):
            return False
        return any(kw.lower() in text for kw in INCLUDE_KEYWORDS)

    def get_priority_topics(self) -> List[str]:
        topics = ["General"]
        text = f"{self.title} {self.location}".lower()
        if any(x in text for x in ["egypt", "cairo", "giza"]):
            topics.append("Egypt")
        if any(x in text for x in ["uae", "dubai", "saudi", "riyadh", "qatar", "gulf"]):
            topics.append("Gulf")
        if "remote" in text:
            topics.append("Remote")
        if any(x in self.title.lower() for x in ["full stack", "fullstack"]):
            topics.append("FullStack")
        return topics