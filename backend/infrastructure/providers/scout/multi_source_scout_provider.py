from typing import Dict, List
from infrastructure.interfaces.base_scout import BaseScout, SourceType

class MultiSourceScoutProvider(BaseScout):
    def initialize(self) -> bool:
        return True

    async def scrape(self, source: SourceType, query: str, limit: int = 20) -> List[Dict]:
        return [{"id": "1", "title": f"{source.value} result for {query}", "score": 100}]

    async def schedule(self, query: str, interval: int, source: SourceType) -> str:
        return f"job_{source.value}_{query}"

    async def get_results(self, job_id: str) -> List[Dict]:
        return []

    async def cancel_job(self, job_id: str) -> bool:
        return True

    async def health_check(self, source: SourceType) -> bool:
        return True
