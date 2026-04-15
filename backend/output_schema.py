"""
output_schema.py — Agent World
Standard typed output schemas for all agents.

Every agent produces one of these. The Ledger Router inspects the type
to decide which channel adapter receives it and what approval is required.

OutputType     → Producing agent   → Approval level
-----------      ----------------    ---------------
RESEARCH       → Nova              → SOFT  (informational, auto-queue)
LISTING        → Forge             → HARD  (must not publish without approval)
ASSET          → Pixel             → HARD  (must not use in listing without approval)
MESSAGE        → Cipher            → HARD  (must not send without approval)
TASK           → Ultron            → NONE  (internal orchestration, auto-proceed)
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────── #

class OutputType(str, Enum):
    RESEARCH  = "research"
    LISTING   = "listing"
    ASSET     = "asset"
    MESSAGE   = "message"
    TASK      = "task"
    GENERIC   = "generic"


class ApprovalLevel(str, Enum):
    NONE   = "none"    # auto-proceed
    SOFT   = "soft"    # queue for review, can auto-continue
    HARD   = "hard"    # blocked until human explicitly approves


# ── Base Output ────────────────────────────────────────────────── #

class AgentOutput(BaseModel):
    id:           str = Field(default_factory=lambda: str(uuid.uuid4()))
    output_type:  OutputType
    agent_id:     str
    agent_name:   str
    room_id:      Optional[str] = None
    task_id:      Optional[str] = None
    created_at:   str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    # Routing state — filled in by LedgerRouter
    target_channel:  Optional[str] = None   # "etsy" | "shopify" | None
    approval_level:  ApprovalLevel = ApprovalLevel.HARD
    routed_at:       Optional[str] = None
    approved_at:     Optional[str] = None
    approved_by:     Optional[str] = None

    # Raw payload
    data:    Dict[str, Any] = {}
    summary: str = ""


# ── Research Output (Nova) ─────────────────────────────────────── #

class Opportunity(BaseModel):
    title:                 str
    niche:                 str
    demand_score:          float   # 0.0 – 1.0
    competition:           float   # 0.0 – 1.0  (lower = easier)
    fit_score:             float   # 0.0 – 1.0
    reasoning:             str
    keywords:              List[str] = []
    estimated_price_range: Optional[str] = None


class ResearchOutput(AgentOutput):
    output_type:    OutputType    = OutputType.RESEARCH
    approval_level: ApprovalLevel = ApprovalLevel.SOFT

    opportunities:  List[Opportunity] = []
    top_pick:       Optional[Opportunity] = None
    market_summary: str = ""
    niche_analyzed: str = ""


# ── Listing Output (Forge) ─────────────────────────────────────── #

class ListingOutput(AgentOutput):
    output_type:    OutputType    = OutputType.LISTING
    approval_level: ApprovalLevel = ApprovalLevel.HARD   # always blocked

    title:          str = ""
    description:    str = ""
    tags:           List[str] = []
    price:          Optional[float] = None
    currency:       str = "USD"
    sku:            Optional[str] = None
    category:       Optional[str] = None
    asset_ids:      List[str] = []          # references to AssetOutput IDs
    platform_hints: Dict[str, Any] = {}    # adapter-specific overrides
    policy_passed:  bool = False
    quality_score:  Optional[float] = None  # 0-100


# ── Asset Output (Pixel) ───────────────────────────────────────── #

class AssetOutput(AgentOutput):
    output_type:    OutputType    = OutputType.ASSET
    approval_level: ApprovalLevel = ApprovalLevel.HARD

    asset_type:  str = "image"   # image | mockup | thumbnail | video
    urls:        List[str] = []
    prompt_used: str = ""
    style_notes: str = ""
    variants:    int = 1


# ── Message Output (Cipher) ────────────────────────────────────── #

class ClassifiedMessage(BaseModel):
    original:    str
    sender:      Optional[str] = None
    category:    str   # support | pre-sale | spam | complaint | praise | escalate
    priority:    str   # low | medium | high | urgent
    draft_reply: Optional[str] = None
    sentiment:   Optional[str] = None


class MessageOutput(AgentOutput):
    output_type:    OutputType    = OutputType.MESSAGE
    approval_level: ApprovalLevel = ApprovalLevel.HARD   # never auto-send

    messages:             List[ClassifiedMessage] = []
    high_priority_count:  int = 0
    requires_reply_count: int = 0


# ── Task Output (Ultron) ───────────────────────────────────────── #

class TaskOutput(AgentOutput):
    output_type:    OutputType    = OutputType.TASK
    approval_level: ApprovalLevel = ApprovalLevel.NONE   # internal only

    subtasks_created:  List[str] = []
    agents_dispatched: List[str] = []
    status_updates:    List[str] = []
