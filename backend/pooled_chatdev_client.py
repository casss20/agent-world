"""
Pooled HTTP Client for ChatDev Money API
Connection pooling + keep-alive for reduced latency
"""

import os
import uuid
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# ChatDev Money API configuration
CHATDEV_API_URL = os.getenv("CHATDEV_API_URL", "http://localhost:6400")
CHATDEV_API_KEY = os.getenv("CHATDEV_API_KEY", "")

# Endpoint mapping - centralized route definitions
ENDPOINTS = {
    "workflow_execute": "/api/workflow/execute",
    "workflow_run": "/api/workflow/run",
    "session_get": "/api/sessions/{session_id}",
    "session_artifacts": "/api/sessions/{session_id}/artifacts",
    "session_download": "/api/sessions/{session_id}/download",
    "workflows_list": "/api/workflows",
    "workflow_get": "/api/workflows/{filename}/get",
    "revenue_stats": "/revenue/stats",
    "revenue_entries": "/revenue/entries",
    "revenue_update": "/revenue/update",
    "health": "/health",
}


class PooledChatDevClient:
    """
    HTTP client for ChatDev Money API with connection pooling
    
    Features:
    - Connection pooling (reduces connection overhead)
    - Keep-alive (reuses connections)
    - Timeout configuration per operation
    - Response caching for health checks
    """
    
    def __init__(self, base_url: str = None, api_key: str = None, pool_size: int = 20):
        self.base_url = base_url or CHATDEV_API_URL
        self.api_key = api_key or CHATDEV_API_KEY
        self.pool_size = pool_size
        
        # Create pooled client with limits
        limits = httpx.Limits(
            max_connections=pool_size,
            max_keepalive_connections=pool_size // 2,
            keepalive_expiry=60.0  # Keep connections alive for 60s
        )
        
        timeout = httpx.Timeout(
            connect=5.0,      # Connection timeout
            read=60.0,        # Read timeout
            write=10.0,       # Write timeout
            pool=5.0          # Pool acquisition timeout
        )
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            limits=limits,
            headers={
                "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Connection": "keep-alive"
            }
        )
        
        # Simple cache for health checks
        self._health_cache = None
        self._health_cache_time = 0
        self._health_cache_ttl = 5.0  # Cache health for 5 seconds
    
    # ============== Workflow Execution ==============
    
    async def execute_workflow(
        self,
        yaml_file: str,
        task_prompt: str,
        variables: Dict[str, Any],
        session_name: str = None
    ) -> Dict[str, Any]:
        """Start a workflow execution in ChatDev Money"""
        if not session_name:
            session_name = f"session_{uuid.uuid4().hex[:8]}"
        
        payload = {
            "yaml_file": yaml_file,
            "task_prompt": task_prompt,
            "variables": variables,
            "session_name": session_name,
            "log_level": "INFO"
        }
        
        endpoints_to_try = [
            ENDPOINTS["workflow_execute"],
            ENDPOINTS["workflow_run"],
        ]
        
        last_error = None
        for endpoint in endpoints_to_try:
            try:
                response = await self.client.post(endpoint, json=payload)
                if response.status_code == 200:
                    result = response.json()
                    return self._normalize_execute_response(result, session_name)
                else:
                    last_error = f"HTTP {response.status_code}: {response.text}"
            except Exception as e:
                last_error = str(e)
                continue
        
        raise RuntimeError(f"ChatDev workflow start failed: {last_error}")
    
    def _normalize_execute_response(self, result: Dict[str, Any], session_name: str) -> Dict[str, Any]:
        """Normalize different response formats to canonical structure"""
        run_id = result.get("run_id") or result.get("session_id") or session_name
        
        return {
            "run_id": run_id,
            "session_id": result.get("session_id") or run_id,
            "status": result.get("status", "started"),
            "message": result.get("message", "Workflow started"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_response": result
        }
    
    # ============== Status Polling ==============
    
    async def get_workflow_status(self, run_id: str) -> Dict[str, Any]:
        """Get workflow execution status"""
        endpoint = ENDPOINTS["session_get"].format(session_id=run_id)
        
        try:
            response = await self.client.get(endpoint)
            if response.status_code == 200:
                result = response.json()
                return self._normalize_status_response(result, run_id)
        except Exception:
            pass
        
        return {
            "run_id": run_id,
            "status": "running",
            "progress": 50,
            "outputs": {},
            "error": None
        }
    
    def _normalize_status_response(self, result: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        """Normalize status response to canonical format"""
        status = result.get("status") or result.get("state") or "unknown"
        
        status_map = {
            "running": "running",
            "in_progress": "running",
            "pending": "pending",
            "completed": "completed",
            "finished": "completed",
            "success": "completed",
            "failed": "failed",
            "error": "failed",
            "cancelled": "cancelled",
            "canceled": "cancelled",
        }
        
        canonical_status = status_map.get(status.lower(), "running")
        
        outputs = result.get("outputs") or result.get("result") or {}
        
        progress = result.get("progress", 0)
        if canonical_status == "completed":
            progress = 100
        elif canonical_status == "running" and progress == 0:
            progress = 50
        
        return {
            "run_id": run_id,
            "status": canonical_status,
            "progress": progress,
            "current_step": result.get("current_step") or result.get("active_node"),
            "outputs": outputs,
            "error": result.get("error") or result.get("error_message"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_response": result
        }
    
    # ============== Cancellation ==============
    
    async def cancel_workflow(self, run_id: str) -> bool:
        """Cancel a running workflow"""
        cancel_endpoints = [
            f"/api/sessions/{run_id}/cancel",
            f"/api/workflow/{run_id}/cancel",
        ]
        
        for endpoint in cancel_endpoints:
            try:
                response = await self.client.post(endpoint)
                if response.status_code in [200, 204]:
                    return True
            except Exception:
                continue
        
        return False
    
    # ============== Revenue API ==============
    
    async def get_revenue_stats(self) -> Dict[str, Any]:
        """Get revenue statistics"""
        try:
            response = await self.client.get(ENDPOINTS["revenue_stats"])
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            return {"error": str(e)}
        
        return {}
    
    async def record_revenue(self, entry: Dict[str, Any]) -> bool:
        """Record a revenue entry"""
        try:
            response = await self.client.post(
                ENDPOINTS["revenue_entries"],
                json=entry
            )
            return response.status_code == 200
        except Exception:
            return False
    
    # ============== Health Check with Caching ==============
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if ChatDev Money is healthy (with caching)"""
        import time
        now = time.time()
        
        # Return cached health if still valid
        if self._health_cache and (now - self._health_cache_time) < self._health_cache_ttl:
            return self._health_cache
        
        try:
            response = await self.client.get(ENDPOINTS["health"])
            if response.status_code == 200:
                self._health_cache = response.json()
                self._health_cache_time = now
                return self._health_cache
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
        
        return {"status": "unknown"}
    
    # ============== Cleanup ==============
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Backwards compatibility alias
ChatDevMoneyClient = PooledChatDevClient

# Factory function
def create_chatdev_client(pool_size: int = 20) -> PooledChatDevClient:
    """Create a configured ChatDev Money client with pooling"""
    return PooledChatDevClient(pool_size=pool_size)
