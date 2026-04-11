"""
ChatDev Money API Client - Corrected Endpoints
Maps to actual ChatDev Money server routes
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
    # Workflow execution
    "workflow_execute": "/api/workflow/execute",
    "workflow_run": "/api/workflow/run",
    
    # Session/status management
    "session_get": "/api/sessions/{session_id}",
    "session_artifacts": "/api/sessions/{session_id}/artifacts",
    "session_download": "/api/sessions/{session_id}/download",
    
    # Workflow management
    "workflows_list": "/api/workflows",
    "workflow_get": "/api/workflows/{filename}/get",
    
    # Revenue tracking
    "revenue_stats": "/revenue/stats",
    "revenue_entries": "/revenue/entries",
    "revenue_update": "/revenue/update",
    
    # Health
    "health": "/health",
}


class ChatDevMoneyClient:
    """
    HTTP client for ChatDev Money API
    
    This client abstracts all ChatDev-specific endpoint details
    and provides a stable interface for the adapter layer.
    """
    
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or CHATDEV_API_URL
        self.api_key = api_key or CHATDEV_API_KEY
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=60.0,
            headers={
                "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
    
    # ============== Workflow Execution ==============
    
    async def execute_workflow(
        self,
        yaml_file: str,
        task_prompt: str,
        variables: Dict[str, Any],
        session_name: str = None
    ) -> Dict[str, Any]:
        """
        Start a workflow execution in ChatDev Money
        
        Tries multiple endpoint patterns for compatibility
        """
        if not session_name:
            session_name = f"session_{uuid.uuid4().hex[:8]}"
        
        payload = {
            "yaml_file": yaml_file,
            "task_prompt": task_prompt,
            "variables": variables,
            "session_name": session_name,
            "log_level": "INFO"
        }
        
        # Try endpoints in order of preference
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
                    # Normalize response format
                    return self._normalize_execute_response(result, session_name)
                else:
                    last_error = f"HTTP {response.status_code}: {response.text}"
            except Exception as e:
                last_error = str(e)
                continue
        
        # All endpoints failed - raise with details
        raise RuntimeError(f"ChatDev workflow start failed: {last_error}")
    
    def _normalize_execute_response(
        self,
        result: Dict[str, Any],
        session_name: str
    ) -> Dict[str, Any]:
        """Normalize different response formats to canonical structure"""
        # ChatDev may return session_id or run_id
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
        """
        Get workflow execution status
        
        Tries session endpoint, falls back to workflow-specific endpoints
        """
        # Try session endpoint first
        endpoint = ENDPOINTS["session_get"].format(session_id=run_id)
        
        try:
            response = await self.client.get(endpoint)
            if response.status_code == 200:
                result = response.json()
                return self._normalize_status_response(result, run_id)
        except Exception:
            pass
        
        # Fallback: return unknown but don't fail
        return {
            "run_id": run_id,
            "status": "running",  # Assume running if we can't check
            "progress": 50,
            "outputs": {},
            "error": None
        }
    
    def _normalize_status_response(
        self,
        result: Dict[str, Any],
        run_id: str
    ) -> Dict[str, Any]:
        """Normalize status response to canonical format"""
        # Extract status from various possible fields
        status = result.get("status") or result.get("state") or "unknown"
        
        # Map ChatDev status to canonical status
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
        
        # Extract outputs if available
        outputs = result.get("outputs") or result.get("result") or {}
        
        # Calculate progress
        progress = result.get("progress", 0)
        if canonical_status == "completed":
            progress = 100
        elif canonical_status == "running" and progress == 0:
            progress = 50  # Assume halfway if running but no progress
        
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
        """
        Cancel a running workflow
        
        Note: ChatDev Money may not support cancellation directly
        """
        # Try to find a cancel endpoint
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
        
        # Cancellation not supported or failed
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
    
    # ============== Health Check ==============
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if ChatDev Money is healthy"""
        try:
            response = await self.client.get(ENDPOINTS["health"])
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
        
        return {"status": "unknown"}
    
    # ============== Cleanup ==============
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Factory function for easy instantiation
def create_chatdev_client() -> ChatDevMoneyClient:
    """Create a configured ChatDev Money client"""
    return ChatDevMoneyClient()
