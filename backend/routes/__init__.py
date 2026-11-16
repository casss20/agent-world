"""
AgentVerse Routes
REST API routes for all platform resources.
"""

from .rooms_router import router as rooms_router
from .tasks_router import router as tasks_router
from .agents_router import router as agents_router
from .messages_router import router as messages_router
from .projects_router import router as projects_router
from .governance_router import router as governance_router

__all__ = [
    "rooms_router",
    "tasks_router",
    "agents_router",
    "messages_router",
    "projects_router",
    "governance_router",
]
