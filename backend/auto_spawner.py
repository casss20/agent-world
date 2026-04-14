"""
Auto-Spawner — Natural Language → Agent Team

You say: "run a YouTube channel"
It creates: Room + Agents + initial tasks — ready to execute.

Uses the LLM to figure out:
  - What agents are needed (roles, names, capabilities)
  - What their system prompts should be
  - What the initial tasks are
"""

import os
import json
import uuid
import logging
from typing import Dict, Any, List
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from llm_provider import get_llm
from models import (
    Business, Agent, Room, RoomType, AgentRoom,
    AgentStatus, BusinessScope, TaskQueue, TaskStatus,
)

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/agentworld")
_engine      = create_engine(DATABASE_URL, pool_pre_ping=True)
_Session     = sessionmaker(bind=_engine)

# Map room purpose keywords to RoomType
_ROOM_TYPE_MAP = {
    "research":   RoomType.RESEARCH,
    "market":     RoomType.MARKET,
    "forge":      RoomType.FORGE,
    "strategy":   RoomType.RESEARCH,
    "creative":   RoomType.FORGE,
    "execution":  RoomType.MARKET,
}

AVAILABLE_TOOLS = [
    "web_search",
    "http_request",
    "read_file",
    "write_file",
    "save_memory",
    "load_memory",
    "broadcast_to_room",
]

SPAWN_PROMPT = """You are a business architect AI. Given a business goal, design the ideal AI agent team.

Return a JSON object with this exact structure:
{{
  "project_name": "Short descriptive name",
  "project_description": "What this project does",
  "room_name": "Main workspace name",
  "room_purpose": "research | market | forge | strategy | creative | execution",
  "agents": [
    {{
      "name": "Agent Name",
      "role": "role_slug",
      "description": "What this agent does",
      "system_prompt": "Detailed system prompt for this agent",
      "capabilities": ["web_search", "broadcast_to_room"],
      "priority": 1
    }}
  ],
  "initial_tasks": [
    {{
      "title": "Task title",
      "task_type": "research | design | write | analyze | execute",
      "description": "What to do",
      "assigned_role": "role_slug of the agent who should do this",
      "priority": 1,
      "payload": {{}}
    }}
  ]
}}

Available capabilities (tools): {tools}

Rules:
- Create 3-6 specialized agents (not too many)
- Each agent has a clear, focused role
- System prompts should be detailed and specific to the goal
- Initial tasks should be concrete and immediately actionable
- Priority 1 = highest, 5 = lowest
- Agents should work in parallel where possible
- ONLY return valid JSON, no markdown or explanation

Business Goal: {goal}
"""


class AutoSpawner:

    def __init__(self):
        self.llm = get_llm()

    async def spawn(self, goal: str, business_slug: str = "default") -> Dict[str, Any]:
        """
        Given a plain-English goal, provision the full agent team.
        Returns a spawn report with all created entity IDs.
        """
        logger.info(f"[Spawner] Goal: {goal!r}")

        # Step 1: Ask LLM to plan the team
        plan = await self._plan(goal)
        if not plan:
            return {"success": False, "error": "LLM failed to generate a valid plan"}

        logger.info(f"[Spawner] Plan: {plan.get('project_name')} with {len(plan.get('agents', []))} agents")

        # Step 2: Provision in DB
        db = _Session()
        try:
            report = await self._provision(db, plan, goal, business_slug)
            return {"success": True, **report}
        except Exception as e:
            logger.error(f"[Spawner] Provision failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    # ------------------------------------------------------------------ #

    async def _plan(self, goal: str) -> Dict | None:
        prompt = SPAWN_PROMPT.format(
            tools=", ".join(AVAILABLE_TOOLS),
            goal=goal,
        )
        try:
            raw = await self.llm.complete_text(prompt, temperature=0.3)

            # Strip markdown code fences if present
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip().rstrip("```").strip()

            return json.loads(raw)
        except Exception as e:
            logger.error(f"[Spawner] Plan parse error: {e}\nRaw: {raw[:300]}")
            return None

    async def _provision(self, db, plan: Dict, goal: str, business_slug: str) -> Dict:
        # ---- Ensure Business exists ----
        business = db.query(Business).filter(Business.slug == business_slug).first()
        if not business:
            business = Business(
                name      = business_slug.title(),
                slug      = business_slug,
                is_active = True,
                config    = {},
            )
            db.add(business)
            db.commit()
            db.refresh(business)

        # ---- Create Room ----
        room_purpose = plan.get("room_purpose", "forge")
        room_type    = _ROOM_TYPE_MAP.get(room_purpose, RoomType.FORGE)

        room = Room(
            business_id = business.id,
            scope       = BusinessScope.BUSINESS,
            name        = plan.get("room_name", plan.get("project_name", "Main Room")),
            room_type   = room_type,
            description = plan.get("project_description", goal),
            max_agents  = 20,
            policy_config = {
                "join_rule":         "open",
                "blackboard_write":  "all",
                "message_broadcast": True,
                "goal":              goal,
                "spawned_at":        datetime.utcnow().isoformat(),
            },
        )
        db.add(room)
        db.commit()
        db.refresh(room)

        # ---- Create Agents & join room ----
        created_agents = []
        role_to_agent  = {}

        for a_def in plan.get("agents", []):
            caps = [c for c in a_def.get("capabilities", []) if c in AVAILABLE_TOOLS]
            if "broadcast_to_room" not in caps:
                caps.append("broadcast_to_room")  # always give this

            agent = Agent(
                business_id   = business.id,
                scope         = BusinessScope.BUSINESS,
                name          = a_def.get("name", "Agent"),
                agent_type    = a_def.get("role", "specialist"),
                description   = a_def.get("description", ""),
                status        = AgentStatus.IDLE,
                desired_status= AgentStatus.ONLINE,
                capabilities  = caps,
                max_load      = 5,
                current_load  = 0,
                config        = {
                    "system_prompt": a_def.get("system_prompt", f"You are a {a_def.get('role')} agent."),
                    "temperature":   0.7,
                    "max_tokens":    2048,
                },
            )
            db.add(agent)
            db.commit()
            db.refresh(agent)

            # Join room
            membership = AgentRoom(
                agent_id  = agent.id,
                room_id   = room.id,
                role      = "member",
                is_active = True,
            )
            db.add(membership)
            db.commit()

            created_agents.append({
                "id":   str(agent.id),
                "name": agent.name,
                "role": agent.agent_type,
                "capabilities": caps,
            })
            role_to_agent[a_def.get("role")] = agent

        # ---- Seed Initial Tasks ----
        created_tasks = []
        for t_def in plan.get("initial_tasks", []):
            assigned_agent = role_to_agent.get(t_def.get("assigned_role"))
            task = TaskQueue(
                room_id     = room.id,
                business_id = business.id,
                agent_id    = assigned_agent.id if assigned_agent else None,
                task_type   = t_def.get("task_type", "general"),
                priority    = t_def.get("priority", 3),
                payload     = {
                    "title":       t_def.get("title", "Task"),
                    "description": t_def.get("description", ""),
                    "goal":        goal,
                    **t_def.get("payload", {}),
                },
                status      = TaskStatus.PENDING,
                max_retries = 3,
            )
            db.add(task)
            db.commit()
            db.refresh(task)

            created_tasks.append({
                "id":           str(task.id),
                "title":        t_def.get("title"),
                "task_type":    task.task_type,
                "assigned_to":  t_def.get("assigned_role"),
            })

        return {
            "project_name":    plan.get("project_name"),
            "room_id":         str(room.id),
            "business_id":     str(business.id),
            "agents_created":  created_agents,
            "tasks_seeded":    created_tasks,
            "agent_count":     len(created_agents),
            "task_count":      len(created_tasks),
            "spawned_at":      datetime.utcnow().isoformat(),
        }


# ---- Module-level singleton ----
_spawner: AutoSpawner | None = None


def get_spawner() -> AutoSpawner:
    global _spawner
    if _spawner is None:
        _spawner = AutoSpawner()
    return _spawner
