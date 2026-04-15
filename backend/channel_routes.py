"""
channel_routes.py — Agent World

FastAPI routes for the Channel Registry and Agent Templates system.

Channels:
  GET    /api/v1/channels                     List all channels + status
  GET    /api/v1/channels/routing             Ledger routing summary
  GET    /api/v1/channels/{id}/test           Test a channel connection
  POST   /api/v1/channels/{id}/connect        Configure + connect a channel
  DELETE /api/v1/channels/{id}                Disconnect a channel
  POST   /api/v1/outputs/route                Route an agent output (post-approval)

Agent Templates:
  GET    /api/v1/agent-templates              List the 5 named templates
  POST   /api/v1/agent-templates/{slug}/spawn Spawn a named agent into a room
"""

import logging
import os
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent_templates import get_template, list_templates
from channel_registry import CHANNEL_DEFINITIONS, get_channel_registry
from ledger_router import get_ledger_router
from output_schema import AgentOutput

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["channels"])


# ── Request / Response Models ──────────────────────────────────── #

class ConnectRequest(BaseModel):
    config: Dict[str, Any]


class RouteRequest(BaseModel):
    output:      Dict[str, Any]
    channel_id:  Optional[str] = None
    approved:    bool = False
    approved_by: Optional[str] = None


class SpawnTemplateRequest(BaseModel):
    room_id:     Optional[str] = None
    business_id: Optional[str] = None


# ── Channel Routes ─────────────────────────────────────────────── #

@router.get("/channels")
def list_channels():
    """List every channel with its connection status and capabilities."""
    registry = get_channel_registry()
    return {"channels": registry.list_channels()}


@router.get("/channels/routing")
def routing_summary():
    """
    Ledger routing summary: which channels are live, what rules apply,
    whether the system can publish to a real platform right now.
    """
    return get_ledger_router().get_routing_summary()


@router.get("/channels/{channel_id}/test")
async def test_channel(channel_id: str):
    """Ping a configured channel to verify credentials."""
    registry = get_channel_registry()
    adapter  = registry.get_adapter(channel_id)
    if not adapter:
        raise HTTPException(
            status_code=404,
            detail=f"Channel '{channel_id}' is not configured yet.",
        )
    return await adapter.test_connection()


@router.post("/channels/{channel_id}/connect")
async def connect_channel(channel_id: str, req: ConnectRequest):
    """
    Save credentials for a channel and verify the connection immediately.
    Credentials are stored locally in channels_config.json — never in source code.
    """
    if channel_id not in CHANNEL_DEFINITIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown channel '{channel_id}'. Valid: {list(CHANNEL_DEFINITIONS.keys())}",
        )

    registry = get_channel_registry()
    try:
        registry.configure_channel(channel_id, req.config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    adapter     = registry.get_adapter(channel_id)
    test_result = await adapter.test_connection()

    return {
        "ok":      test_result.get("ok", False),
        "message": test_result.get("message", ""),
        "channel": adapter.to_dict(),
    }


@router.delete("/channels/{channel_id}")
def disconnect_channel(channel_id: str):
    """Remove channel configuration (credentials are wiped from disk)."""
    registry = get_channel_registry()
    registry.disconnect_channel(channel_id)
    return {"ok": True, "message": f"Channel '{channel_id}' disconnected and credentials removed."}


# ── Output Routing ─────────────────────────────────────────────── #

@router.post("/outputs/route")
async def route_output(req: RouteRequest):
    """
    Route an agent output to the appropriate channel.

    For HARD-approval outputs (listings, messages, assets):
      - Call first WITHOUT approved=true to get the routing decision
      - Show decision to human via the approval queue
      - Call again WITH approved=true after human sign-off

    For SOFT/NONE outputs (research, tasks):
      - Proceed automatically; this endpoint records the routing.
    """
    try:
        output_data              = req.output.copy()
        target_channel           = req.channel_id
        if target_channel:
            output_data["target_channel"] = target_channel

        output = AgentOutput(**output_data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid output schema: {e}")

    ledger_router = get_ledger_router()
    decision      = ledger_router.decide(output)

    # Hard-approval outputs are held until explicitly approved
    if decision.requires_approval and not req.approved:
        return {
            "ok":      False,
            "held":    True,
            "reason":  decision.reason,
            "risk":    decision.risk_level,
            "routing": decision.to_dict(),
            "next_step": (
                "Present this routing decision to the human via the approval queue. "
                "Resubmit with approved=true after sign-off."
            ),
        }

    # Stamp approval
    if req.approved:
        from datetime import datetime
        output.approved_by = req.approved_by or "human"
        output.approved_at = datetime.utcnow().isoformat()

    result = await ledger_router.execute(decision)
    return {
        "ok":      result.get("ok"),
        "result":  result,
        "routing": decision.to_dict(),
    }


# ── Agent Template Routes ──────────────────────────────────────── #

@router.get("/agent-templates")
def get_agent_templates():
    """List the 5 named agent templates (Nova/Forge/Pixel/Cipher/Ultron)."""
    return {"templates": list_templates()}


@router.post("/agent-templates/{slug}/spawn")
async def spawn_template_agent(slug: str, req: SpawnTemplateRequest):
    """
    Spawn one of the pre-defined named agents into a room.
    If the agent already exists for this business, it is re-used (idempotent).
    """
    tmpl = get_template(slug)
    if not tmpl:
        raise HTTPException(
            status_code=404,
            detail=f"No template found for slug '{slug}'. "
                   f"Valid slugs: nova, forge, pixel, cipher, ultron",
        )

    database_url = os.getenv("DATABASE_URL", "sqlite:///./agentworld.db")

    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from models import Agent, AgentRoom, AgentStatus, Business, BusinessScope, Room

        engine  = create_engine(database_url, pool_pre_ping=True)
        Session = sessionmaker(bind=engine)
        db      = Session()

        try:
            # Resolve business
            if req.business_id:
                business = db.query(Business).filter(
                    Business.id == uuid.UUID(req.business_id)
                ).first()
            else:
                business = db.query(Business).filter(Business.slug == "default").first()

            if not business:
                raise HTTPException(status_code=404, detail="No business found to attach the agent to.")

            # Find or create the named agent
            agent = (
                db.query(Agent)
                .filter(Agent.business_id == business.id, Agent.agent_type == slug)
                .first()
            )

            if not agent:
                agent = Agent(
                    business_id    = business.id,
                    scope          = BusinessScope.BUSINESS,
                    name           = tmpl["name"],
                    agent_type     = slug,
                    description    = tmpl["description"],
                    status         = AgentStatus.IDLE,
                    desired_status = AgentStatus.ONLINE,
                    capabilities   = tmpl["capabilities"],
                    max_load       = 5,
                    current_load   = 0,
                    config         = {
                        "system_prompt":         tmpl["system_prompt"],
                        "temperature":           0.7,
                        "max_tokens":            2048,
                        "icon":                  tmpl["icon"],
                        "color":                 tmpl["color"],
                        "output_types":          tmpl["output_types"],
                        "approval_required_for": tmpl["approval_required_for"],
                        "autonomous_allowed":    tmpl["autonomous_allowed"],
                        "is_named_template":     True,
                    },
                )
                db.add(agent)
                db.commit()
                db.refresh(agent)
                created = True
            else:
                created = False

            # Join room if provided
            joined_room = None
            if req.room_id:
                room = db.query(Room).filter(Room.id == uuid.UUID(req.room_id)).first()
                if room:
                    existing_link = (
                        db.query(AgentRoom)
                        .filter(
                            AgentRoom.agent_id  == agent.id,
                            AgentRoom.room_id   == room.id,
                            AgentRoom.is_active == True,
                        )
                        .first()
                    )
                    if not existing_link:
                        db.add(AgentRoom(
                            agent_id  = agent.id,
                            room_id   = room.id,
                            role      = "member",
                            is_active = True,
                        ))
                        db.commit()
                    joined_room = str(room.id)

            return {
                "ok":         True,
                "created":    created,
                "joined_room": joined_room,
                "agent": {
                    "id":          str(agent.id),
                    "name":        agent.name,
                    "slug":        slug,
                    "icon":        tmpl["icon"],
                    "color":       tmpl["color"],
                    "role":        tmpl["role"],
                    "description": tmpl["description"],
                },
            }

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[channel_routes] spawn_template_agent error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
