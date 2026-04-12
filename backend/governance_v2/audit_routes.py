"""
Audit Log API Routes
Web UI endpoints for audit log viewing and export
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional, List
from datetime import datetime, timedelta
import json
import io
import csv

from .auth import require_admin, require_viewer, UserPrincipal
from .audit_models import AuditLogEntry, AuditLogQuery, ActorType, ActionType, ResultType
from .audit_service import get_audit_service, AuditLogService

router = APIRouter(prefix="/governance/v2/audit", tags=["audit"])


@router.get("/logs", response_model=List[AuditLogEntry])
async def get_audit_logs(
    request: Request,
    user: UserPrincipal = Depends(require_viewer),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    actor_type: Optional[ActorType] = None,
    actor_id: Optional[str] = None,
    action: Optional[ActionType] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    business_id: Optional[int] = None,
    result: Optional[ResultType] = None,
    request_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    audit_service: AuditLogService = Depends(get_audit_service)
):
    """
    Query audit logs with filters.
    
    **Required Role:** viewer+
    
    **Query Parameters:**
    - `start_date`: Filter from date (ISO format)
    - `end_date`: Filter to date (ISO format)
    - `actor_type`: user, agent, or system
    - `actor_id`: Specific actor ID
    - `action`: Action type (login, execute, etc.)
    - `resource_type`: Type of resource accessed
    - `resource_id`: Specific resource ID
    - `business_id`: Business/tenant ID
    - `result`: success, failure, denied, error, timeout
    - `request_id`: Correlation ID
    - `limit`: Max results (1-1000, default 100)
    - `offset`: Pagination offset
    """
    query = AuditLogQuery(
        start_date=start_date or datetime.utcnow() - timedelta(days=7),
        end_date=end_date or datetime.utcnow(),
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        business_id=business_id,
        result=result,
        request_id=request_id,
        limit=limit,
        offset=offset
    )
    
    entries = await audit_service.query(query)
    
    # Log this query (meta-audit)
    from .audit_service import set_request_id
    set_request_id(request.state.request_id if hasattr(request.state, 'request_id') else None)
    
    return entries


@router.get("/logs/{log_id}", response_model=AuditLogEntry)
async def get_audit_log_by_id(
    log_id: int,
    user: UserPrincipal = Depends(require_viewer),
    audit_service: AuditLogService = Depends(get_audit_service)
):
    """
    Get a single audit log entry by ID.
    
    **Required Role:** viewer+
    """
    query = AuditLogQuery(limit=1)
    # Need to add ID filter to query - for now return error
    raise HTTPException(status_code=501, detail="Single log lookup not yet implemented")


@router.get("/stats")
async def get_audit_stats(
    user: UserPrincipal = Depends(require_viewer),
    days: int = Query(30, ge=1, le=90),
    audit_service: AuditLogService = Depends(get_audit_service)
):
    """
    Get audit log statistics for dashboard.
    
    **Required Role:** viewer+
    
    **Query Parameters:**
    - `days`: Number of days to include (1-90, default 30)
    
    **Returns:**
    - Total entries
    - Date range
    - Action breakdown
    - Result breakdown
    - Actor breakdown
    - Hourly activity
    """
    stats = await audit_service.get_stats(days)
    return stats


@router.get("/actions")
async def get_action_types(
    user: UserPrincipal = Depends(require_viewer)
):
    """
    Get list of available action types for filtering.
    
    **Required Role:** viewer+
    """
    return {
        "actions": [a.value for a in ActionType],
        "categories": {
            "authentication": ["login", "logout", "token_refresh"],
            "agent_management": ["agent_register", "agent_update", "agent_delete", "agent_heartbeat"],
            "governance": ["governance_execute", "governance_classify", "token_issue"],
            "control": ["killswitch_trigger", "killswitch_reset", "degradation_set"],
            "memory": ["memory_query", "memory_consolidate"],
            "business": ["business_create", "business_update"]
        }
    }


@router.get("/export/json")
async def export_audit_logs_json(
    request: Request,
    user: UserPrincipal = Depends(require_admin),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    actor_type: Optional[ActorType] = None,
    action: Optional[ActionType] = None,
    business_id: Optional[int] = None,
    audit_service: AuditLogService = Depends(get_audit_service)
):
    """
    Export audit logs as JSON file.
    
    **Required Role:** admin only
    
    **Note:** Large exports may take time. Consider using date filters.
    """
    query = AuditLogQuery(
        start_date=start_date or datetime.utcnow() - timedelta(days=7),
        end_date=end_date or datetime.utcnow(),
        actor_type=actor_type,
        action=action,
        business_id=business_id,
        limit=10000  # Cap export size
    )
    
    entries = await audit_service.query(query)
    
    # Convert to JSON
    json_data = json.dumps([entry.dict() for entry in entries], indent=2, default=str)
    
    # Stream response
    stream = io.BytesIO(json_data.encode())
    
    filename = f"audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    
    return StreamingResponse(
        stream,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/csv")
async def export_audit_logs_csv(
    request: Request,
    user: UserPrincipal = Depends(require_admin),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    actor_type: Optional[ActorType] = None,
    action: Optional[ActionType] = None,
    business_id: Optional[int] = None,
    audit_service: AuditLogService = Depends(get_audit_service)
):
    """
    Export audit logs as CSV file.
    
    **Required Role:** admin only
    
    **Note:** Large exports may take time. Consider using date filters.
    """
    query = AuditLogQuery(
        start_date=start_date or datetime.utcnow() - timedelta(days=7),
        end_date=end_date or datetime.utcnow(),
        actor_type=actor_type,
        action=action,
        business_id=business_id,
        limit=10000  # Cap export size
    )
    
    entries = await audit_service.query(query)
    
    # Convert to CSV
    output = io.StringIO()
    if entries:
        writer = csv.DictWriter(output, fieldnames=entries[0].dict().keys())
        writer.writeheader()
        for entry in entries:
            row = entry.dict()
            # Convert non-serializable values
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()
                elif value is None:
                    row[key] = ""
                elif not isinstance(value, (str, int, float, bool)):
                    row[key] = str(value)
            writer.writerow(row)
    
    # Stream response
    stream = io.BytesIO(output.getvalue().encode())
    
    filename = f"audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        stream,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/query")
async def query_audit_logs_post(
    request: Request,
    query: AuditLogQuery,
    user: UserPrincipal = Depends(require_viewer),
    audit_service: AuditLogService = Depends(get_audit_service)
):
    """
    Query audit logs with POST body (for complex filters).
    
    **Required Role:** viewer+
    """
    entries = await audit_service.query(query)
    return entries


@router.get("/dashboard")
async def get_audit_dashboard(
    user: UserPrincipal = Depends(require_viewer),
    audit_service: AuditLogService = Depends(get_audit_service)
):
    """
    Get dashboard summary for audit log viewer.
    
    **Required Role:** viewer+
    
    Returns pre-aggregated data for dashboard widgets.
    """
    stats = await audit_service.get_stats(days=7)
    
    return {
        "summary": {
            "total_entries_7d": stats.total_entries,
            "date_range": stats.date_range,
        },
        "charts": {
            "actions": stats.action_breakdown,
            "results": stats.result_breakdown,
            "actors": stats.actor_breakdown,
            "hourly": stats.hourly_activity
        },
        "filters": {
            "actions": [a.value for a in ActionType],
            "results": [r.value for r in ResultType],
            "actor_types": [a.value for a in ActorType]
        }
    }
