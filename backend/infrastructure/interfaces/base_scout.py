from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from enum import Enum

class SourceType(str, Enum):
    REDDIT = "reddit"
    HACKERNEWS = "hackernews"
    PRODUCTHUNT = "producthunt"
    TWITTER = "twitter"

class BaseScout(ABC):
    @abstractmethod
    async def scrape(self, source: SourceType, query: str, limit: int = 20) -> List[Dict]:
        pass
    @abstractmethod
    async def schedule(self, query: str, interval: int, source: SourceType) -> str:
        pass
    @abstractmethod
    async def get_results(self, job_id: str) -> List[Dict]:
        pass
    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        pass
    @abstractmethod
    async def health_check(self, source: SourceType) -> bool:
        pass
