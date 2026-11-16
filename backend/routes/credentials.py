"""
Credential Routes
API endpoints for credential status and management.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.credential_manager import get_credential_manager

router = APIRouter(prefix="/api/credentials", tags=["credentials"])


@router.get("/status", response_model=dict)
async def get_credential_status():
    """Get status of all known credentials."""
    manager = get_credential_manager()
    return {
        "credentials": manager.get_all_status(),
    }


@router.get("/validate/{provider}", response_model=dict)
async def validate_provider_credentials(provider: str):
    """Validate credentials for a specific provider."""
    manager = get_credential_manager()

    provider_creds = {
        "dalle": ["OPENAI_API_KEY"],
        "runway": ["RUNWAY_API_KEY"],
        "slack": ["SLACK_BOT_TOKEN"],
        "sendgrid": ["SENDGRID_API_KEY"],
        "stripe": ["STRIPE_SECRET_KEY"],
    }

    required = provider_creds.get(provider, [])
    if not required:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    return manager.validate_provider_credentials(provider, required)


@router.post("/set/{name}", response_model=dict)
async def set_credential(name: str, payload: dict):
    """
    Set a credential in memory (dev only).
    In production, use a vault or secrets manager.
    """
    manager = get_credential_manager()
    value = payload.get("value")
    if not value:
        raise HTTPException(status_code=400, detail="Missing 'value' in body")

    manager.set(name, value)
    return {"success": True, "credential": name, "set": True}
