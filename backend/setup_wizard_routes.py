"""
setup_wizard_routes.py — Agent World

Interactive setup wizard API.
Guides users through business configuration step-by-step.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json

from business_config import (
    BusinessConfig, SetupWizardState, SETUP_WIZARD_FLOW,
    BusinessInfoStep, ChannelSelectionStep, EtsyAuthStep,
    AdsSelectionStep, MetaAdsAuthStep, PreferencesStep
)
from models import Business, get_db

router = APIRouter(prefix="/setup", tags=["setup-wizard"])


# ============ API Models ============

class WizardStepResponse(BaseModel):
    step: str
    title: str
    description: str
    questions: list
    progress: dict  # {current: 3, total: 7, percentage: 43}


class WizardAnswerRequest(BaseModel):
    business_id: int
    step: str
    answers: Dict[str, Any]


class WizardProgressResponse(BaseModel):
    current_step: str
    completed_steps: list
    can_proceed: bool
    can_go_back: bool
    data_so_far: Dict[str, Any]


# ============ Routes ============

@router.get("/wizard/{business_id}", response_model=WizardProgressResponse)
def get_wizard_progress(business_id: int, db=Depends(get_db)):
    """Get current wizard state for a business"""
    wizard_state = db.query(SetupWizardState).filter(
        SetupWizardState.business_id == business_id
    ).first()
    
    if not wizard_state:
        # Create new wizard state
        wizard_state = SetupWizardState(business_id=business_id)
        db.add(wizard_state)
        db.commit()
    
    flow_steps = list(SETUP_WIZARD_FLOW.keys())
    current_idx = flow_steps.index(wizard_state.current_step)
    
    return {
        "current_step": wizard_state.current_step,
        "completed_steps": wizard_state.get_completed_steps(),
        "can_proceed": _can_proceed(wizard_state),
        "can_go_back": current_idx > 0,
        "data_so_far": wizard_state.get_data()
    }


@router.get("/wizard/{business_id}/step/{step_name}", response_model=WizardStepResponse)
def get_step(step_name: str, business_id: int, db=Depends(get_db)):
    """Get questions for a specific wizard step"""
    if step_name not in SETUP_WIZARD_FLOW:
        raise HTTPException(status_code=404, detail="Step not found")
    
    wizard_state = db.query(SetupWizardState).filter(
        SetupWizardState.business_id == business_id
    ).first()
    
    if not wizard_state:
        raise HTTPException(status_code=404, detail="Wizard not started")
    
    step_config = SETUP_WIZARD_FLOW[step_name]
    flow_steps = list(SETUP_WIZARD_FLOW.keys())
    current_idx = flow_steps.index(step_name)
    
    # Get questions (handle dynamic steps)
    questions = step_config.get("questions", [])
    
    if step_config.get("dynamic"):
        questions = _generate_dynamic_questions(step_name, wizard_state)
    
    return {
        "step": step_name,
        "title": step_config["title"],
        "description": step_config["description"],
        "questions": questions,
        "progress": {
            "current": current_idx + 1,
            "total": len(flow_steps),
            "percentage": int((current_idx / len(flow_steps)) * 100)
        }
    }


@router.post("/wizard/{business_id}/answer")
def submit_answer(business_id: int, request: WizardAnswerRequest, db=Depends(get_db)):
    """Submit answers for a wizard step"""
    wizard_state = db.query(SetupWizardState).filter(
        SetupWizardState.business_id == business_id
    ).first()
    
    if not wizard_state:
        raise HTTPException(status_code=404, detail="Wizard not found")
    
    # Validate step
    if request.step != wizard_state.current_step:
        raise HTTPException(status_code=400, detail="Not on this step")
    
    # Store answers
    data = wizard_state.get_data()
    data[request.step] = request.answers
    wizard_state.set_data(data)
    
    # Mark step complete
    wizard_state.mark_step_complete(request.step)
    
    # Move to next step
    step_config = SETUP_WIZARD_FLOW[request.step]
    if step_config["next_step"]:
        wizard_state.current_step = step_config["next_step"]
    
    db.commit()
    
    return {
        "success": True,
        "next_step": wizard_state.current_step,
        "progress": _get_progress(wizard_state)
    }


@router.post("/wizard/{business_id}/back")
def go_back(business_id: int, db=Depends(get_db)):
    """Go back to previous step"""
    wizard_state = db.query(SetupWizardState).filter(
        SetupWizardState.business_id == business_id
    ).first()
    
    if not wizard_state:
        raise HTTPException(status_code=404, detail="Wizard not found")
    
    flow_steps = list(SETUP_WIZARD_FLOW.keys())
    current_idx = flow_steps.index(wizard_state.current_step)
    
    if current_idx > 0:
        wizard_state.current_step = flow_steps[current_idx - 1]
        db.commit()
    
    return {
        "success": True,
        "current_step": wizard_state.current_step,
        "progress": _get_progress(wizard_state)
    }


@router.post("/wizard/{business_id}/complete")
def complete_wizard(business_id: int, db=Depends(get_db)):
    """Complete the wizard and create BusinessConfig"""
    wizard_state = db.query(SetupWizardState).filter(
        SetupWizardState.business_id == business_id
    ).first()
    
    if not wizard_state:
        raise HTTPException(status_code=404, detail="Wizard not found")
    
    data = wizard_state.get_data()
    
    # Create or update BusinessConfig
    config = db.query(BusinessConfig).filter(
        BusinessConfig.business_id == business_id
    ).first()
    
    if not config:
        config = BusinessConfig(business_id=business_id)
        db.add(config)
    
    # Apply all wizard answers to config
    _apply_wizard_data(config, data)
    
    # Mark wizard complete
    wizard_state.current_step = "complete"
    db.commit()
    
    return {
        "success": True,
        "message": "Setup complete! Your business is ready.",
        "config_summary": config.to_dict()
    }


@router.get("/wizard/{business_id}/summary")
def get_wizard_summary(business_id: int, db=Depends(get_db)):
    """Get full summary of wizard answers so far"""
    wizard_state = db.query(SetupWizardState).filter(
        SetupWizardState.business_id == business_id
    ).first()
    
    if not wizard_state:
        raise HTTPException(status_code=404, detail="Wizard not found")
    
    data = wizard_state.get_data()
    
    return {
        "current_step": wizard_state.current_step,
        "completed_steps": wizard_state.get_completed_steps(),
        "summary": _generate_summary(data),
        "ready_to_complete": wizard_state.current_step == "review"
    }


# ============ Helper Functions ============

def _can_proceed(wizard_state: SetupWizardState) -> bool:
    """Check if user can proceed to next step"""
    current_step = wizard_state.current_step
    data = wizard_state.get_data()
    
    # Require answers for current step
    if current_step in ["welcome", "review", "complete"]:
        return True
    
    return current_step in data


def _get_progress(wizard_state: SetupWizardState) -> dict:
    """Calculate progress percentage"""
    flow_steps = list(SETUP_WIZARD_FLOW.keys())
    current_idx = flow_steps.index(wizard_state.current_step)
    
    return {
        "current": current_idx + 1,
        "total": len(flow_steps),
        "percentage": int((current_idx / len(flow_steps)) * 100),
        "completed": len(wizard_state.get_completed_steps())
    }


def _generate_dynamic_questions(step_name: str, wizard_state: SetupWizardState) -> list:
    """Generate questions for dynamic steps based on previous answers"""
    data = wizard_state.get_data()
    questions = []
    
    if step_name == "channels_auth":
        channels = data.get("channels", {})
        
        if channels.get("enable_etsy"):
            questions.append({
                "id": "etsy_shop_id",
                "type": "text",
                "label": "Etsy Shop ID",
                "placeholder": "YourShopName",
                "required": True,
                "help": "Found in your Etsy shop URL: etsy.com/shop/YOUR_SHOP_ID"
            })
            questions.append({
                "id": "etsy_auth",
                "type": "oauth_button",
                "label": "Connect Etsy Account",
                "oauth_url": "/auth/etsy",  # Would be real OAuth flow
                "required": True
            })
        
        if channels.get("enable_amazon_kdp"):
            questions.append({
                "id": "kdp_email",
                "type": "email",
                "label": "KDP Account Email",
                "required": True,
                "help": "Your Amazon KDP login email"
            })
    
    elif step_name == "ads_auth":
        ads = data.get("ads", {})
        
        if ads.get("enable_meta"):
            questions.append({
                "id": "meta_ad_account",
                "type": "text",
                "label": "Meta Ad Account ID",
                "placeholder": "act_123456789",
                "required": True
            })
            questions.append({
                "id": "meta_auth",
                "type": "oauth_button",
                "label": "Connect Meta Business Account",
                "oauth_url": "/auth/meta",
                "required": True
            })
    
    return questions


def _apply_wizard_data(config: BusinessConfig, data: Dict[str, Any]):
    """Apply all wizard answers to BusinessConfig"""
    # Business Info
    if "business_info" in data:
        info = data["business_info"]
        config.owner_email = info.get("owner_email")
        config.business_name = info.get("business_name")
        config.business_type = info.get("business_type")
    
    # Channels
    if "channels" in data:
        channels = data["channels"]
        if channels.get("enable_etsy"):
            auth = data.get("channels_auth", {})
            config.set_etsy_config({
                "shop_id": auth.get("etsy_shop_id"),
                "connected": True,
                "connected_at": "2026-04-16T00:00:00Z"
            })
    
    # Ads
    if "ads" in data:
        ads = data["ads"]
        if ads.get("enable_meta"):
            auth = data.get("ads_auth", {})
            config.set_meta_ads_config({
                "ad_account_id": auth.get("meta_ad_account"),
                "connected": True
            })
    
    # Preferences
    if "preferences" in data:
        prefs = data["preferences"]
        config.preferred_design_provider = prefs.get("preferred_design_provider", "dalle_3")
        config.auto_approve_threshold = prefs.get("auto_approve_threshold", 50)


def _generate_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate human-readable summary of wizard data"""
    summary = {
        "business_info": {},
        "channels": [],
        "advertising": [],
        "preferences": {}
    }
    
    if "business_info" in data:
        info = data["business_info"]
        summary["business_info"] = {
            "name": info.get("business_name"),
            "email": info.get("owner_email"),
            "type": info.get("business_type", "solo").upper()
        }
    
    if "channels" in data:
        channels = data["channels"]
        if channels.get("enable_etsy"):
            summary["channels"].append("Etsy")
        if channels.get("enable_amazon_kdp"):
            summary["channels"].append("Amazon KDP")
        if channels.get("enable_shopify"):
            summary["channels"].append("Shopify")
        if channels.get("enable_gumroad"):
            summary["channels"].append("Gumroad")
    
    if "ads" in data:
        ads = data["ads"]
        if ads.get("enable_meta"):
            summary["advertising"].append("Meta Ads")
        if ads.get("enable_google"):
            summary["advertising"].append("Google Ads")
        if ads.get("enable_tiktok"):
            summary["advertising"].append("TikTok Ads")
    
    if "preferences" in data:
        prefs = data["preferences"]
        summary["preferences"] = {
            "design_provider": prefs.get("preferred_design_provider", "dalle_3"),
            "auto_approve_limit": f"${prefs.get('auto_approve_threshold', 50)}"
        }
    
    return summary
