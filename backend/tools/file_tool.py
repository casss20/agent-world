"""
Tool: file_tool
Lets agents read and write files in a sandboxed workspace directory.
Each project gets its own folder: workspace/<room_id>/
"""

import os
import asyncio
from pathlib import Path
from typing import Any, Dict

WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", "./workspace")


def _safe_path(room_id: str, filename: str) -> Path:
    """Return a sandboxed path under workspace/<room_id>/. Prevents path traversal."""
    base     = Path(WORKSPACE_ROOT) / (room_id or "default")
    base.mkdir(parents=True, exist_ok=True)
    # Resolve to prevent ../../../etc/passwd attacks
    resolved = (base / Path(filename).name).resolve()
    if not str(resolved).startswith(str(base.resolve())):
        raise ValueError("Path traversal detected")
    return resolved


async def read_file(
    filename:  str,
    _agent_id: str = "",
    _task_id:  str = "",
    _room_id:  str = "",
) -> Dict[str, Any]:
    """Read a file from the project workspace."""
    try:
        path = _safe_path(_room_id, filename)

        def _read():
            if not path.exists():
                return None
            return path.read_text(encoding="utf-8")

        loop    = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, _read)

        if content is None:
            return {"success": False, "error": f"File not found: {filename}"}

        return {"success": True, "filename": filename, "content": content, "size_bytes": len(content)}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def write_file(
    filename:  str,
    content:   str,
    append:    bool = False,
    _agent_id: str  = "",
    _task_id:  str  = "",
    _room_id:  str  = "",
) -> Dict[str, Any]:
    """Write or append content to a file in the project workspace."""
    try:
        path = _safe_path(_room_id, filename)

        def _write():
            mode = "a" if append else "w"
            path.write_text(content, encoding="utf-8") if not append else \
                path.open("a", encoding="utf-8").write(content)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write)

        return {
            "success":    True,
            "filename":   filename,
            "bytes_written": len(content),
            "mode":       "append" if append else "overwrite",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
