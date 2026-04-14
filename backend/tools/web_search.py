"""
Tool: web_search
Uses DuckDuckGo (no API key required) to search the web.
"""

import asyncio
from typing import List, Dict, Any


async def web_search(
    query:        str,
    max_results:  int = 5,
    # injected by executor — ignored here
    _agent_id:    str = "",
    _task_id:     str = "",
    _room_id:     str = "",
) -> List[Dict[str, Any]]:
    """
    Search the web using DuckDuckGo.
    Returns a list of {title, snippet, url} dicts.
    """
    try:
        from duckduckgo_search import DDGS

        def _sync_search():
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title":   r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url":     r.get("href", ""),
                    })
            return results

        # Run the blocking call in a thread pool
        loop    = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _sync_search)
        return results

    except ImportError:
        return [{"error": "duckduckgo-search package not installed. Run: pip install duckduckgo-search"}]
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]
