"""
Multica Client
Phase 4 Integration: Agent team orchestration
"""

import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class IssueStatus(str, Enum):
    """Multica issue/task status"""
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"


class IssuePriority(str, Enum):
    """Multica issue priority"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MulticaAgent:
    """Agent in Multica"""
    id: str
    name: str
    runtime_id: str
    provider: str  # claude, codex, openclaw, opencode
    status: str


@dataclass
class MulticaIssue:
    """Issue/Task in Multica"""
    id: str
    title: str
    description: Optional[str]
    status: IssueStatus
    priority: IssuePriority
    assignee_id: Optional[str]
    creator_id: str
    labels: List[str]
    created_at: str
    updated_at: str


class MulticaClient:
    """
    Client for Multica agent orchestration platform.
    
    Provides:
    - Task/Issue management (Kanban-style)
    - Agent assignment and tracking
    - Real-time progress via WebSocket
    - Skill reuse and compounding
    """
    
    def __init__(self, base_url: str = "http://localhost:8081", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    # ============ Agents ============
    
    async def create_agent(
        self,
        name: str,
        runtime_id: str,
        provider: str = "openclaw",
        description: Optional[str] = None
    ) -> MulticaAgent:
        """Create a new agent in Multica"""
        payload = {
            "name": name,
            "runtime_id": runtime_id,
            "provider": provider,
            "description": description
        }
        
        resp = await self.client.post(
            f"{self.base_url}/api/v1/agents",
            json=payload,
            headers=self._headers()
        )
        resp.raise_for_status()
        data = resp.json()
        
        return MulticaAgent(
            id=data["id"],
            name=data["name"],
            runtime_id=data["runtime_id"],
            provider=data["provider"],
            status=data.get("status", "idle")
        )
    
    async def list_agents(self) -> List[MulticaAgent]:
        """List all agents"""
        resp = await self.client.get(
            f"{self.base_url}/api/v1/agents",
            headers=self._headers()
        )
        resp.raise_for_status()
        data = resp.json()
        
        return [
            MulticaAgent(
                id=a["id"],
                name=a["name"],
                runtime_id=a["runtime_id"],
                provider=a["provider"],
                status=a.get("status", "idle")
            )
            for a in data.get("agents", [])
        ]
    
    async def get_agent(self, agent_id: str) -> Optional[MulticaAgent]:
        """Get agent by ID"""
        resp = await self.client.get(
            f"{self.base_url}/api/v1/agents/{agent_id}",
            headers=self._headers()
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        
        return MulticaAgent(
            id=data["id"],
            name=data["name"],
            runtime_id=data["runtime_id"],
            provider=data["provider"],
            status=data.get("status", "idle")
        )
    
    # ============ Issues ============
    
    async def create_issue(
        self,
        title: str,
        description: Optional[str] = None,
        priority: IssuePriority = IssuePriority.MEDIUM,
        assignee_id: Optional[str] = None,
        labels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MulticaIssue:
        """Create a new issue/task"""
        payload = {
            "title": title,
            "description": description,
            "priority": priority.value,
            "assignee_id": assignee_id,
            "labels": labels or []
        }
        if metadata:
            payload["metadata"] = metadata
        
        resp = await self.client.post(
            f"{self.base_url}/api/v1/issues",
            json=payload,
            headers=self._headers()
        )
        resp.raise_for_status()
        data = resp.json()
        
        return self._parse_issue(data)
    
    async def list_issues(
        self,
        status: Optional[IssueStatus] = None,
        assignee_id: Optional[str] = None,
        limit: int = 50
    ) -> List[MulticaIssue]:
        """List issues with optional filters"""
        params = {"limit": limit}
        if status:
            params["status"] = status.value
        if assignee_id:
            params["assignee_id"] = assignee_id
        
        resp = await self.client.get(
            f"{self.base_url}/api/v1/issues",
            params=params,
            headers=self._headers()
        )
        resp.raise_for_status()
        data = resp.json()
        
        return [self._parse_issue(i) for i in data.get("issues", [])]
    
    async def get_issue(self, issue_id: str) -> Optional[MulticaIssue]:
        """Get issue by ID"""
        resp = await self.client.get(
            f"{self.base_url}/api/v1/issues/{issue_id}",
            headers=self._headers()
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return self._parse_issue(resp.json())
    
    async def update_issue_status(
        self,
        issue_id: str,
        status: IssueStatus,
        comment: Optional[str] = None
    ) -> MulticaIssue:
        """Update issue status (progress tracking)"""
        payload = {"status": status.value}
        if comment:
            payload["comment"] = comment
        
        resp = await self.client.post(
            f"{self.base_url}/api/v1/issues/{issue_id}/status",
            json=payload,
            headers=self._headers()
        )
        resp.raise_for_status()
        return self._parse_issue(resp.json())
    
    async def assign_issue(
        self,
        issue_id: str,
        agent_id: str
    ) -> MulticaIssue:
        """Assign issue to an agent"""
        resp = await self.client.post(
            f"{self.base_url}/api/v1/issues/{issue_id}/assign",
            json={"agent_id": agent_id},
            headers=self._headers()
        )
        resp.raise_for_status()
        return self._parse_issue(resp.json())
    
    async def add_comment(
        self,
        issue_id: str,
        text: str,
        author_id: str = "system"
    ) -> Dict[str, Any]:
        """Add comment to issue (progress updates)"""
        resp = await self.client.post(
            f"{self.base_url}/api/v1/issues/{issue_id}/comments",
            json={
                "text": text,
                "author_id": author_id
            },
            headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()
    
    # ============ Skills ============
    
    async def create_skill(
        self,
        name: str,
        description: str,
        code: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        """Create reusable skill"""
        resp = await self.client.post(
            f"{self.base_url}/api/v1/skills",
            json={
                "name": name,
                "description": description,
                "code": code,
                "language": language
            },
            headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()
    
    async def list_skills(self) -> List[Dict[str, Any]]:
        """List all reusable skills"""
        resp = await self.client.get(
            f"{self.base_url}/api/v1/skills",
            headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json().get("skills", [])
    
    # ============ Utility ============
    
    def _parse_issue(self, data: Dict[str, Any]) -> MulticaIssue:
        """Parse issue from API response"""
        return MulticaIssue(
            id=data["id"],
            title=data["title"],
            description=data.get("description"),
            status=IssueStatus(data.get("status", "backlog")),
            priority=IssuePriority(data.get("priority", "medium")),
            assignee_id=data.get("assignee_id"),
            creator_id=data.get("creator_id", "system"),
            labels=data.get("labels", []),
            created_at=data["created_at"],
            updated_at=data["updated_at"]
        )
    
    async def health_check(self) -> bool:
        """Check if multica server is healthy"""
        try:
            resp = await self.client.get(
                f"{self.base_url}/health",
                timeout=5.0
            )
            return resp.status_code == 200
        except:
            return False
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class MulticaWorkflowTracker:
    """
    High-level workflow tracking using Multica.
    
    Tracks Scout → Maker → Merchant workflow as Multica issues.
    """
    
    def __init__(self, client: MulticaClient):
        self.client = client
        self._agent_cache: Dict[str, str] = {}  # name -> id
    
    async def ensure_agents(self):
        """Ensure workflow agents exist in Multica"""
        agents = await self.client.list_agents()
        existing = {a.name: a.id for a in agents}
        
        # Scout Agent
        if "Scout" not in existing:
            agent = await self.client.create_agent(
                name="Scout",
                runtime_id="agentverse-1",
                provider="openclaw",
                description="Discovers trending content on Reddit"
            )
            self._agent_cache["Scout"] = agent.id
        else:
            self._agent_cache["Scout"] = existing["Scout"]
        
        # Maker Agent
        if "Maker" not in existing:
            agent = await self.client.create_agent(
                name="Maker",
                runtime_id="agentverse-1",
                provider="openclaw",
                description="Creates viral content from trends"
            )
            self._agent_cache["Maker"] = agent.id
        else:
            self._agent_cache["Maker"] = existing["Maker"]
        
        # Merchant Agent
        if "Merchant" not in existing:
            agent = await self.client.create_agent(
                name="Merchant",
                runtime_id="agentverse-1",
                provider="openclaw",
                description="Publishes content and tracks revenue"
            )
            self._agent_cache["Merchant"] = agent.id
        else:
            self._agent_cache["Merchant"] = existing["Merchant"]
    
    async def create_content_task(
        self,
        trend_data: Dict[str, Any],
        priority: IssuePriority = IssuePriority.HIGH
    ) -> MulticaIssue:
        """
        Create a content creation task from discovered trend.
        
        Called by Scout when trending content is found.
        """
        title = f"Create content: {trend_data.get('title', 'Untitled')[:50]}"
        description = f"""
**Trend Discovered**
- Source: {trend_data.get('source', 'reddit')}
- Subreddit: {trend_data.get('subreddit', 'unknown')}
- Upvotes: {trend_data.get('upvotes', 0)}
- URL: {trend_data.get('url', 'N/A')}

**Original Content**
{trend_data.get('content', 'No content')[:500]}

**Task**
Create viral content based on this trend for publishing.
"""
        
        issue = await self.client.create_issue(
            title=title,
            description=description,
            priority=priority,
            assignee_id=self._agent_cache.get("Maker"),
            labels=["content-arbitrage", "maker", "trend"],
            metadata={
                "trend_data": trend_data,
                "workflow": "content-arbitrage",
                "stage": "create"
            }
        )
        
        return issue
    
    async def mark_content_created(
        self,
        issue_id: str,
        content_result: Dict[str, Any]
    ):
        """Mark content creation complete, trigger publishing"""
        # Update status
        await self.client.update_issue_status(
            issue_id=issue_id,
            status=IssueStatus.DONE,
            comment=f"Content created: {content_result.get('title', 'Untitled')}"
        )
        
        # Create publishing task for Merchant
        title = f"Publish: {content_result.get('title', 'Untitled')[:50]}"
        description = f"""
**Content Ready for Publishing**
- Platform: {content_result.get('platform', 'twitter')}
- Format: {content_result.get('format', 'text')}

**Content**
{content_result.get('content', 'No content')[:500]}
"""
        
        publish_issue = await self.client.create_issue(
            title=title,
            description=description,
            priority=IssuePriority.HIGH,
            assignee_id=self._agent_cache.get("Merchant"),
            labels=["content-arbitrage", "merchant", "publish"],
            metadata={
                "original_issue": issue_id,
                "content_result": content_result,
                "workflow": "content-arbitrage",
                "stage": "publish"
            }
        )
        
        return publish_issue
    
    async def mark_published(
        self,
        issue_id: str,
        publish_result: Dict[str, Any]
    ):
        """Mark publishing complete with tracking info"""
        await self.client.update_issue_status(
            issue_id=issue_id,
            status=IssueStatus.DONE,
            comment=f"Published to {publish_result.get('platform', 'unknown')}"
        )
        
        # Create revenue tracking task
        title = f"Track revenue: {publish_result.get('title', 'Untitled')[:40]}"
        description = f"""
**Published Content**
- Platform: {publish_result.get('platform', 'unknown')}
- URL: {publish_result.get('url', 'N/A')}
- Published: {publish_result.get('published_at', 'unknown')}

**Task**
Track revenue metrics for this content.
"""
        
        track_issue = await self.client.create_issue(
            title=title,
            description=description,
            priority=IssuePriority.MEDIUM,
            assignee_id=self._agent_cache.get("Merchant"),
            labels=["content-arbitrage", "merchant", "revenue", "tracking"],
            metadata={
                "publish_result": publish_result,
                "workflow": "content-arbitrage",
                "stage": "track"
            }
        )
        
        return track_issue
