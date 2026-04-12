"""
Governance v2 Health Checks
Kubernetes-ready liveness, readiness, and startup probes
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

router = APIRouter(tags=["health"])

# This will be set by main.py
governance_system_instance = None

def set_governance_system(gs):
    global governance_system_instance
    governance_system_instance = gs

def get_governance_system():
    return governance_system_instance


@router.get("/live")
async def health_live() -> Dict[str, str]:
    """
    Liveness probe - process is alive and can answer requests.
    
    Kubernetes uses this to know if the pod should be restarted.
    Should be lightweight and always return 200 if process is running.
    """
    return {
        "status": "alive",
        "service": "governance-v2",
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
    }


@router.get("/ready")
async def health_ready() -> Dict[str, Any]:
    """
    Readiness probe - service is ready to handle traffic.
    
    Kubernetes uses this to know if the pod should receive traffic.
    Returns 503 if service is not ready (traffic is routed away).
    """
    gs = get_governance_system()
    
    # Critical checks for governance service
    checks = {
        "governance_initialized": gs is not None,
        "phase1_core": hasattr(gs, 'governance') if gs else False,
        "phase2_orchestration": hasattr(gs, 'registry') if gs else False,
        "phase3_memory": hasattr(gs, 'event_stream') if gs else False,
        "phase4_hardening": hasattr(gs, 'degradation') if gs else False,
    }
    
    # Additional checks if system is initialized
    if gs:
        checks.update({
            "agent_registry": hasattr(gs, 'registry'),
            "kill_switches": hasattr(gs, 'kill_switches'),
            "memory_consolidator": hasattr(gs, 'memory_consolidator'),
        })
    
    ready = all(checks.values())
    
    if not ready:
        failed = [k for k, v in checks.items() if not v]
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "checks": checks,
                "failed": failed,
                "service": "governance-v2"
            }
        )
    
    # Count registered agents if available
    agent_count = 0
    if gs and hasattr(gs, 'registry') and gs.registry:
        agent_count = len(getattr(gs.registry, 'agents', {}))
    
    return {
        "status": "ready",
        "service": "governance-v2",
        "checks": checks,
        "agents_count": agent_count,
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
    }


@router.get("/startup")
async def health_startup() -> Dict[str, Any]:
    """
    Startup probe - initialization progress.
    
    Kubernetes uses this during slow startup to know when to begin
    liveness/readiness checks. Prevents premature restarts.
    """
    gs = get_governance_system()
    
    if gs is None:
        return {
            "status": "initializing",
            "progress": 0,
            "message": "Governance system not yet initialized"
        }
    
    # Calculate startup progress based on component initialization
    components = [
        hasattr(gs, 'governance'),
        hasattr(gs, 'registry'),
        hasattr(gs, 'event_stream'),
        hasattr(gs, 'memory_consolidator'),
        hasattr(gs, 'degradation'),
        hasattr(gs, 'kill_switches'),
    ]
    
    progress = sum(components) / len(components) * 100
    
    return {
        "status": "startup_complete" if progress >= 100 else "initializing",
        "progress": round(progress, 1),
        "components_ready": sum(components),
        "components_total": len(components),
        "timestamp": __import__('datetime').datetime.utcnow().isoformat()
    }


@router.get("/deep")
async def health_deep() -> Dict[str, Any]:
    """
    Deep health check - comprehensive system status.
    
    Use this for detailed monitoring, not for Kubernetes probes.
    Includes dependency checks and performance metrics.
    """
    gs = get_governance_system()
    
    if gs is None:
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "reason": "governance_system_not_initialized"}
        )
    
    # Gather detailed status
    status_info = {
        "status": "healthy",
        "service": "governance-v2",
        "version": "2.0.0",
        "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # Phase 1: Core
    if hasattr(gs, 'governance'):
        status_info["components"]["phase1_core"] = {
            "status": "healthy",
            "feature_flags": len(getattr(gs.governance, 'feature_flags', {}).flags) if hasattr(gs.governance, 'feature_flags') else 0
        }
    
    # Phase 2: Orchestration
    if hasattr(gs, 'registry'):
        agents = getattr(gs.registry, 'agents', {})
        status_info["components"]["phase2_orchestration"] = {
            "status": "healthy",
            "registered_agents": len(agents),
            "healthy_agents": sum(1 for a in agents.values() if getattr(a, 'health_status', None) and a.health_status.value == 'healthy')
        }
    
    # Phase 3: Memory
    if hasattr(gs, 'event_stream'):
        events = getattr(gs.event_stream, 'events', [])
        status_info["components"]["phase3_memory"] = {
            "status": "healthy",
            "events_tracked": len(events)
        }
    
    # Phase 4: Hardening
    if hasattr(gs, 'degradation'):
        status_info["components"]["phase4_hardening"] = {
            "status": "healthy",
            "degradation_level": getattr(gs.degradation, 'current_level', 'unknown'),
            "kill_switches_active": sum(1 for v in getattr(getattr(gs, 'kill_switches', {}), 'switches', {}).values() if v) if hasattr(gs, 'kill_switches') else 0
        }
    
    return status_info
