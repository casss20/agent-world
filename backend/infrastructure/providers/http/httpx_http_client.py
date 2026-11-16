from typing import Dict, Any, Optional
import httpx
from infrastructure.interfaces.base_http_client import BaseHTTPClient

class HttpxHTTPClient(BaseHTTPClient):
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30)

    def initialize(self) -> bool:
        return True

    async def get(self, url: str, headers: Dict = None, params: Dict = None, timeout: int = 30) -> Dict:
        r = await self._client.get(url, headers=headers, params=params, timeout=timeout)
        return {"status": r.status_code, "data": r.json() if r.status_code == 200 else None}

    async def post(self, url: str, body: Any = None, headers: Dict = None, timeout: int = 30) -> Dict:
        r = await self._client.post(url, json=body, headers=headers, timeout=timeout)
        return {"status": r.status_code, "data": r.json() if r.status_code == 200 else None}

    async def put(self, url: str, body: Any = None, headers: Dict = None, timeout: int = 30) -> Dict:
        r = await self._client.put(url, json=body, headers=headers, timeout=timeout)
        return {"status": r.status_code, "data": r.json() if r.status_code == 200 else None}

    async def delete(self, url: str, headers: Dict = None, timeout: int = 30) -> Dict:
        r = await self._client.delete(url, headers=headers, timeout=timeout)
        return {"status": r.status_code, "data": r.json() if r.status_code == 200 else None}

    async def health_check(self, url: str) -> bool:
        try:
            r = await self._client.get(url, timeout=5)
            return r.status_code < 500
        except Exception:
            return False
