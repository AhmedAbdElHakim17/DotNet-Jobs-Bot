from dataclasses import dataclass
from typing import List

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

    def is_relevant(self) -> bool:
        text = f"{self.title} {self.company} {self.description} {self.location}".lower()
        if any(ex in text for ex in [k.lower() for k in EXCLUDE_KEYWORDS]):
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