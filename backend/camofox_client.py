"""
Camofox Browser Client
Phase 4 Integration: Anti-detection browser for agent web tasks
"""

import httpx
import base64
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class CamofoxTab:
    """Represents a browser tab"""
    id: str
    user_id: str
    session_key: str
    url: str
    title: Optional[str] = None


@dataclass
class CamofoxSnapshot:
    """Accessibility snapshot with element refs"""
    snapshot: str
    screenshot: Optional[str] = None
    truncated: bool = False
    total_chars: int = 0


class CamofoxClient:
    """
    Client for Camofox Browser anti-detection browser server.
    
    Provides:
    - Stealth browsing (bypasses Cloudflare, bot detection)
    - Element refs (e1, e2, e3) for stable interaction
    - Accessibility snapshots (90% smaller than HTML)
    - Search macros (@google_search, @reddit_search)
    - YouTube transcript extraction
    """
    
    def __init__(self, base_url: str = "http://localhost:9377", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=120.0)
    
    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def create_tab(
        self,
        user_id: str,
        url: str,
        session_key: str = "default",
        cookies: Optional[List[Dict]] = None
    ) -> CamofoxTab:
        """Create a new browser tab"""
        payload = {
            "userId": user_id,
            "sessionKey": session_key,
            "url": url
        }
        if cookies:
            payload["cookies"] = cookies
        
        resp = await self.client.post(
            f"{self.base_url}/tabs",
            json=payload,
            headers=self._headers()
        )
        resp.raise_for_status()
        data = resp.json()
        
        return CamofoxTab(
            id=data["tabId"],
            user_id=user_id,
            session_key=session_key,
            url=url,
            title=data.get("title")
        )
    
    async def get_snapshot(
        self,
        tab_id: str,
        user_id: str,
        include_screenshot: bool = False,
        offset: int = 0
    ) -> CamofoxSnapshot:
        """
        Get accessibility snapshot with element refs.
        
        Example snapshot:
        "[button e1] Submit  [link e2] Learn more"
        """
        params = {"userId": user_id}
        if include_screenshot:
            params["includeScreenshot"] = "true"
        if offset > 0:
            params["offset"] = str(offset)
        
        resp = await self.client.get(
            f"{self.base_url}/tabs/{tab_id}/snapshot",
            params=params,
            headers=self._headers()
        )
        resp.raise_for_status()
        data = resp.json()
        
        return CamofoxSnapshot(
            snapshot=data["snapshot"],
            screenshot=data.get("screenshot"),
            truncated=data.get("truncated", False),
            total_chars=data.get("totalChars", 0)
        )
    
    async def click(self, tab_id: str, user_id: str, ref: str) -> Dict[str, Any]:
        """Click element by ref (e.g., 'e1')"""
        resp = await self.client.post(
            f"{self.base_url}/tabs/{tab_id}/click",
            json={"userId": user_id, "ref": ref},
            headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()
    
    async def type_text(
        self,
        tab_id: str,
        user_id: str,
        ref: str,
        text: str,
        press_enter: bool = False
    ) -> Dict[str, Any]:
        """Type text into element by ref"""
        payload = {
            "userId": user_id,
            "ref": ref,
            "text": text,
            "pressEnter": press_enter
        }
        resp = await self.client.post(
            f"{self.base_url}/tabs/{tab_id}/type",
            json=payload,
            headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()
    
    async def navigate(
        self,
        tab_id: str,
        user_id: str,
        url: Optional[str] = None,
        macro: Optional[str] = None,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Navigate to URL or execute search macro.
        
        Macros: @google_search, @youtube_search, @reddit_search,
                @reddit_subreddit, @amazon_search, etc.
        """
        payload: Dict[str, Any] = {"userId": user_id}
        
        if url:
            payload["url"] = url
        elif macro:
            payload["macro"] = macro
            if query:
                payload["query"] = query
        
        resp = await self.client.post(
            f"{self.base_url}/tabs/{tab_id}/navigate",
            json=payload,
            headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()
    
    async def scroll(
        self,
        tab_id: str,
        user_id: str,
        direction: str = "down",
        amount: int = 3
    ) -> Dict[str, Any]:
        """Scroll page (up/down/left/right)"""
        resp = await self.client.post(
            f"{self.base_url}/tabs/{tab_id}/scroll",
            json={
                "userId": user_id,
                "direction": direction,
                "amount": amount
            },
            headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()
    
    async def screenshot(self, tab_id: str, user_id: str) -> str:
        """Take screenshot and return base64 PNG"""
        resp = await self.client.get(
            f"{self.base_url}/tabs/{tab_id}/screenshot?userId={user_id}",
            headers=self._headers()
        )
        resp.raise_for_status()
        data = resp.json()
        return data["screenshot"]
    
    async def get_youtube_transcript(
        self,
        url: str,
        languages: List[str] = None
    ) -> Dict[str, Any]:
        """
        Extract YouTube captions.
        Uses yt-dlp (fast) or browser fallback.
        """
        payload = {"url": url}
        if languages:
            payload["languages"] = languages
        
        resp = await self.client.post(
            f"{self.base_url}/youtube/transcript",
            json=payload,
            headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()
    
    async def close_tab(self, tab_id: str, user_id: str) -> None:
        """Close browser tab"""
        await self.client.delete(
            f"{self.base_url}/tabs/{tab_id}?userId={user_id}",
            headers=self._headers()
        )
    
    async def list_tabs(self, user_id: str) -> List[Dict[str, Any]]:
        """List all open tabs for user"""
        resp = await self.client.get(
            f"{self.base_url}/tabs?userId={user_id}",
            headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json().get("tabs", [])
    
    async def health_check(self) -> bool:
        """Check if camofox server is healthy"""
        try:
            resp = await self.client.get(
                f"{self.base_url}/health",
                timeout=10.0
            )
            return resp.status_code == 200
        except:
            return False
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class CamofoxRedditScraper:
    """
    Specialized Reddit scraping using Camofox.
    Designed for content arbitrage Scout agent.
    """
    
    def __init__(self, client: CamofoxClient):
        self.client = client
    
    async def scrape_subreddit(
        self,
        subreddit: str,
        user_id: str = "agent_scout",
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Scrape posts from a subreddit.
        
        Uses @reddit_subreddit macro which returns JSON directly.
        """
        # Create tab
        tab = await self.client.create_tab(
            user_id=user_id,
            url="about:blank",
            session_key=f"reddit_{subreddit}"
        )
        
        try:
            # Navigate using macro
            result = await self.client.navigate(
                tab_id=tab.id,
                user_id=user_id,
                macro="@reddit_subreddit",
                query=subreddit
            )
            
            # Reddit macro returns JSON directly
            posts = result.get("data", {}).get("posts", [])
            
            # Limit results
            return posts[:limit]
            
        finally:
            await self.client.close_tab(tab.id, user_id)
    
    async def search_reddit(
        self,
        query: str,
        user_id: str = "agent_scout",
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Search Reddit for trending content.
        
        Uses @reddit_search macro which returns JSON.
        """
        tab = await self.client.create_tab(
            user_id=user_id,
            url="about:blank",
            session_key=f"reddit_search_{query[:20]}"
        )
        
        try:
            result = await self.client.navigate(
                tab_id=tab.id,
                user_id=user_id,
                macro="@reddit_search",
                query=query
            )
            
            posts = result.get("data", {}).get("posts", [])
            return posts[:limit]
            
        finally:
            await self.client.close_tab(tab.id, user_id)
