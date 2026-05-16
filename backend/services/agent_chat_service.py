"""
Agent Chat Service
Handles individual conversations with role-based agents,
task assignment, history retrieval, and context management.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from models import AgentConversation, Task
from agents.roles.role_definitions import get_role, AgentRole
from infrastructure.interfaces.base_storage_provider import BaseStorageProvider
from services.ultron_orchestrator import get_ultron_orchestrator, OrchestratorResult

logger = logging.getLogger(__name__)


class AgentChatService:
    """
    Service for chatting with individual role-based agents.
    - Send messages, get responses
    - Assign tasks to agents
    - Retrieve conversation history
    - Context-aware responses
    """

    def __init__(self, storage_provider: Optional[BaseStorageProvider] = None, queue_provider: Optional[Any] = None, auth_provider: Optional[Any] = None, repository: Optional[Any] = None):
        self._response_handlers: Dict[str, callable] = {}
        self.storage_provider = storage_provider
        self.queue_provider = queue_provider
        self.auth_provider = auth_provider
        self.repository = repository

    # ── Conversation ─────────────────────────────────────────────────────

    async def chat(
        self,
        db: AsyncSession,
        agent_id: str,
        user_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to an agent and get a response.
        Persists the conversation to the database.
        """
        role = get_role(agent_id)
        if not role:
            return {
                "success": False,
                "error": f"Agent '{agent_id}' not found",
                "available_agents": [r.id for r in list_all_roles()],
            }

        # Generate response via Ultron harness (Phase 2) or fallback placeholder
        response = await self._generate_response(role, message, context)

        # Persist conversation
        conv = AgentConversation(
            agent_id=agent_id,
            user_id=user_id,
            message=message,
            response=response,
            metadata={
                "context": context or {},
                "role": role.to_dict(),
            },
        )
        db.add(conv)
        await db.flush()

        return {
            "success": True,
            "conversation_id": conv.id,
            "agent": {
                "id": role.id,
                "name": role.name,
                "role": role.role,
                "emoji": role.avatar_emoji,
            },
            "message": message,
            "response": response,
            "timestamp": conv.created_at.isoformat() if conv.created_at else None,
        }

    async def get_history(
        self,
        db: AsyncSession,
        agent_id: str,
        user_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a user with a specific agent."""
        result = await db.execute(
            select(AgentConversation)
            .where(
                AgentConversation.agent_id == agent_id,
                AgentConversation.user_id == user_id,
            )
            .order_by(desc(AgentConversation.created_at))
            .limit(limit)
        )
        conversations = result.scalars().all()

        return [
            {
                "id": c.id,
                "message": c.message,
                "response": c.response,
                "task_assigned": c.task_assigned,
                "task_status": c.task_status,
                "timestamp": c.created_at.isoformat() if c.created_at else None,
            }
            for c in conversations
        ]

    async def get_all_conversations(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 100,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get all conversations grouped by agent."""
        result = await db.execute(
            select(AgentConversation)
            .where(AgentConversation.user_id == user_id)
            .order_by(desc(AgentConversation.created_at))
            .limit(limit)
        )
        conversations = result.scalars().all()

        by_agent: Dict[str, List[Dict[str, Any]]] = {}
        for c in conversations:
            agent_data = {
                "id": c.id,
                "message": c.message,
                "response": c.response,
                "task_assigned": c.task_assigned,
                "task_status": c.task_status,
                "timestamp": c.created_at.isoformat() if c.created_at else None,
            }
            if c.agent_id not in by_agent:
                by_agent[c.agent_id] = []
            by_agent[c.agent_id].append(agent_data)

        return by_agent

    # ── Task Assignment ──────────────────────────────────────────────────

    async def assign_task(
        self,
        db: AsyncSession,
        agent_id: str,
        user_id: str,
        task_description: str,
        priority: str = "medium",
    ) -> Dict[str, Any]:
        """
        Assign a task to a specific agent.
        Creates a Task record and links it to the agent conversation.
        """
        role = get_role(agent_id)
        if not role:
            return {
                "success": False,
                "error": f"Agent '{agent_id}' not found",
            }

        # Create conversation entry marking task assignment
        conv = AgentConversation(
            agent_id=agent_id,
            user_id=user_id,
            message=f"[TASK ASSIGNED] {task_description}",
            response=f"Task received. I'll work on: {task_description}",
            task_assigned=task_description,
            task_status="pending",
        )
        db.add(conv)
        await db.flush()

        # Also create a formal Task record
        task = Task(
            room_id="agent-chat-default",
            task_type="agent_task",
            title=task_description,
            description=task_description,
            status="pending",
            priority=priority,
            owner_agent_id=agent_id,
            metadata={
                "assigned_by": user_id,
                "conversation_id": conv.id,
                "agent_role": role.role,
            },
        )
        db.add(task)
        await db.flush()

        return {
            "success": True,
            "task_id": task.id,
            "conversation_id": conv.id,
            "agent": {
                "id": role.id,
                "name": role.name,
                "emoji": role.avatar_emoji,
            },
            "status": "pending",
        }

    async def get_agent_tasks(
        self,
        db: AsyncSession,
        agent_id: str,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get all tasks assigned to a specific agent."""
        query = select(Task).where(Task.owner_agent_id == agent_id)
        if status:
            query = query.where(Task.status == status)

        result = await db.execute(query.order_by(desc(Task.created_at)))
        tasks = result.scalars().all()

        return [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks
        ]

    # ── Internal ─────────────────────────────────────────────────────────

    async def _generate_response(
        self, role: AgentRole, message: str, context: Optional[Dict[str, Any]]
    ) -> str:
        """
        Generate a response from the agent.
        Phase 2: Routes through Ultron orchestrator when harness is enabled.
        Falls back to placeholder for non-enabled agents or simple queries.
        """
        # ── Phase 2: Ultron Routing ────────────────────────────────────────
        try:
            ultron = get_ultron_orchestrator()
            result = await ultron.analyze_message(role, message, context)

            if result.action == "route" and result.routing_plan:
                # Format Ultron's routing plan as the response
                routing_msg = await ultron.format_routing_response(result, role)
                if routing_msg:
                    return (
                        f"[{role.name} | {role.role}]\n\n"
                        f"I analyzed your request and coordinated with Ultron.\n\n"
                        f"{routing_msg}\n\n"
                        f"---\n"
                        f"Original message: '{message}'"
                    )

            elif result.action == "escalate" and result.escalate_to:
                escalate_role = get_role(result.escalate_to)
                escalate_name = escalate_role.name if escalate_role else result.escalate_to
                return (
                    f"[{role.name} | {role.role}]\n\n"
                    f"This request is best handled by {escalate_name}. "
                    f"I'm transferring you now...\n\n"
                    f"(Ultron escalation: {result.reason})"
                )

            # Fall through to direct response for "direct" action or empty routing
        except Exception as e:
            logger.warning(f"Ultron routing failed for {role.id}: {e}. Falling back.")

        # ── Fallback Placeholder ─────────────────────────────────────────
        return (
            f"[{role.name} | {role.role}]\n\n"
            f"I received your message: '{message}'\n\n"
            f"As {role.role}, my responsibilities include: {', '.join(role.responsibilities[:3])}.\n"
            f"How can I help you further?"
        )


# ── Singleton ────────────────────────────────────────────────────────────

_agent_chat_service: Optional[AgentChatService] = None


def get_agent_chat_service() -> AgentChatService:
    global _agent_chat_service
    if _agent_chat_service is None:
        _agent_chat_service = AgentChatService()
    return _agent_chat_service


# Re-export for convenience
from agents.roles.role_definitions import list_roles as list_all_roles
