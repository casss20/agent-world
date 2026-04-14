"""
Tool: http_request
Allows agents to make HTTP requests to any REST API.
This is how agents connect to Etsy, Shopify, etc.
"""

import httpx
from typing import Any, Dict, Optional


async def http_request(
    url:       str,
    method:    str             = "GET",
    headers:   Optional[Dict] = None,
    body:      Optional[Dict] = None,
    # injected by executor — ignored here
    _agent_id: str = "",
    _task_id:  str = "",
    _room_id:  str = "",
) -> Dict[str, Any]:
    """
    Make an async HTTP request.
    Returns {status_code, body, headers, success}.
    """
    try:
        method  = method.upper()
        headers = headers or {}

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            if method == "GET":
                resp = await client.get(url, headers=headers)
            elif method == "POST":
                resp = await client.post(url, headers=headers, json=body)
            elif method == "PUT":
                resp = await client.put(url, headers=headers, json=body)
            elif method == "DELETE":
                resp = await client.delete(url, headers=headers)
            elif method == "PATCH":
                resp = await client.patch(url, headers=headers, json=body)
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}

        # Try to parse JSON response
        try:
            body_data = resp.json()
        except Exception:
            body_data = resp.text[:2000]  # limit raw text

        return {
            "success":     resp.status_code < 400,
            "status_code": resp.status_code,
            "body":        body_data,
            "headers":     dict(resp.headers),
        }

    except httpx.TimeoutException:
        return {"success": False, "error": "Request timed out after 30 seconds"}
    except Exception as e:
        return {"success": False, "error": str(e)}
