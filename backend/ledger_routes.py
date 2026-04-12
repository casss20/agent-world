"""
Ledger API Routes
FastAPI endpoints for Ledger sovereign integration
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import asyncio

from ledger_sovereign import get_ledger_sovereign, LedgerSovereign


router = APIRouter(prefix="/ledger", tags=["ledger"])


# ==================== REQUEST/RESPONSE MODELS ====================

class CommandRequest(BaseModel):
    command: str
    business_id: Optional[str] = None
    room_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = {}


class CommandResponse(BaseModel):
    status: str
    approved: bool
    reason: Optional[str] = None
    governance_checks: Optional[Dict[str, Any]] = None
    opportunity_note: Optional[Dict[str, Any]] = None
    requires_human: bool = False


class ConstitutionCheckRequest(BaseModel):
    action_type: str
    irreversible: bool = False
    expands_scope: bool = False
    external: bool = False


class MemoryUpdateRequest(BaseModel):
    memory_type: str  # fact, preference, decision, lesson
    content: str
    business_id: Optional[str] = None
    confidence: float = 1.0


# ==================== DEPENDENCY ====================

def get_ledger() -> LedgerSovereign:
    return get_ledger_sovereign()


# ==================== ROUTES ====================

@router.get("/status")
async def ledger_status(ledger: LedgerSovereign = Depends(get_ledger)):
    """Get Ledger sovereign status"""
    return ledger.get_status()


@router.get("/constitution")
async def get_constitution(ledger: LedgerSovereign = Depends(get_ledger)):
    """Get constitution summary"""
    return ledger.get_constitution_summary()


@router.post("/command", response_model=CommandResponse)
async def process_command(
    request: CommandRequest,
    ledger: LedgerSovereign = Depends(get_ledger)
):
    """
    Process a command through Ledger governance.
    
    Runs through full stack:
    1. Constitution check
    2. Alignment check
    3. Governor check
    4. Focus check
    5. Opportunity scan
    """
    result = await ledger.process_command(
        request.command,
        request.context or {}
    )
    
    return CommandResponse(
        status=result["status"],
        approved=result.get("approved", False),
        reason=result.get("reason"),
        governance_checks=result.get("governance_checks"),
        opportunity_note=result.get("opportunity_note"),
        requires_human=result.get("requires_human", False)
    )


@router.post("/check-constitution")
async def check_constitution(
    request: ConstitutionCheckRequest,
    ledger: LedgerSovereign = Depends(get_ledger)
):
    """Check if an action violates constitution"""
    action = {
        "type": request.action_type,
        "irreversible": request.irreversible,
        "expands_scope": request.expands_scope,
        "external": request.external
    }
    
    result = ledger.check_constitution(action)
    return result


@router.get("/memory")
async def get_memory_context(ledger: LedgerSovereign = Depends(get_ledger)):
    """Get Ledger's memory context"""
    return ledger.get_memory_context()


@router.get("/world")
async def get_world_context(ledger: LedgerSovereign = Depends(get_ledger)):
    """Get current world context (goals, projects)"""
    return {
        "world_md_length": len(ledger.world),
        "goals": ledger._extract_goals(),
        "current_focus": ledger._extract_current_focus()
    }


@router.get("/decisions")
async def get_decision_history(ledger: LedgerSovereign = Depends(get_ledger)):
    """Get recent sovereign decisions"""
    return {
        "count": len(ledger.decision_history),
        "decisions": [
            {
                "timestamp": d.timestamp,
                "type": d.decision_type,
                "approved": d.approved,
                "reasoning": d.reasoning[:100] + "..." if len(d.reasoning) > 100 else d.reasoning
            }
            for d in ledger.decision_history[-10:]  # Last 10
        ]
    }


@router.post("/governor/level")
async def check_governor_level(
    command: str,
    pattern_count: int = 0,
    ledger: LedgerSovereign = Depends(get_ledger)
):
    """Check governor escalation level for a command"""
    context = {"pattern_repetitions": pattern_count}
    result = ledger.check_governor(command, context)
    return result


@router.get("/identity/modes")
async def get_identity_modes(ledger: LedgerSovereign = Depends(get_ledger)):
    """Get available identity modes"""
    return {
        "modes": ["Default", "Tactical", "Red Team"],
        "current": "Default",  # Would track current mode
        "switching_rules": "See IDENTITY.md for triggers"
    }


@router.get("/files/list")
async def list_ledger_files(ledger: LedgerSovereign = Depends(get_ledger)):
    """List all loaded Ledger files"""
    return {
        "governance_core": [
            "CONSTITUTION.md", "SOUL.md", "IDENTITY.md",
            "ALIGNMENT.md", "GOVERNOR.md", "SELF-MOD.md",
            "START.md", "RUNTIME.md"
        ],
        "execution": [
            "PLANNER.md", "CRITIC.md", "EXECUTOR.md", "FAILURE.md"
        ],
        "context": [
            "WORLD.md", "USER.md", "MEMORY.md", "DECISIONS.md"
        ],
        "protection": [
            "FOCUS.md", "OPPORTUNITY.md", "ADAPTATION.md", "PRUNE.md"
        ],
        "operational": [
            "AGENTS.md", "TOOLS.md", "HEARTBEAT.md",
            "AUDIT.md", "CHANGELOG.md"
        ]
    }


# ==================== WEBSOCKET FOR REAL-TIME ====================

from fastapi import WebSocket

@router.websocket("/ws")
async def ledger_websocket(websocket: WebSocket):
    """WebSocket for real-time Ledger communication"""
    await websocket.accept()
    ledger = get_ledger_sovereign()
    
    await websocket.send_json({
        "type": "connection",
        "message": "Ledger sovereign connected",
        "version": ledger.version
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "command":
                result = await ledger.process_command(
                    data.get("command", ""),
                    data.get("context", {})
                )
                await websocket.send_json({
                    "type": "command_result",
                    "result": result
                })
            
            elif data.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "status": ledger.get_status()
                })
    
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        await websocket.close()
