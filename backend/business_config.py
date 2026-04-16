"""
business_config.py — Agent World

Per-business configuration management.
Stores API keys, preferences, channel connections.
NOT in env vars — configured through dashboard wizard.
"""

import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

logger = logging.getLogger(__name__)


class BusinessConfig(Base):
    """Configuration for a business — API keys, preferences, channels"""
    __tablename__ = "business_configs"
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Contact & Business Info
    owner_email = Column(String(255))
    business_name = Column(String(255))
    business_type = Column(String(50))  # solo, llc, corp
    
    # Sales Channels (JSON configs)
    etsy_config = Column(Text)  # {"shop_id": "", "access_token": "", "connected": false}
    amazon_kdp_config = Column(Text)  # {"email": "", "password_encrypted": ""}
    shopify_config = Column(Text)  # {"shop_domain": "", "access_token": ""}
    gumroad_config = Column(Text)  # {"app_id": "", "access_token": ""}
    
    # Advertising Platforms
    meta_ads_config = Column(Text)  # {"ad_account_id": "", "access_token": ""}
    google_ads_config = Column(Text)  # {"customer_id": "", "developer_token": ""}
    amazon_ads_config = Column(Text)
    tiktok_ads_config = Column(Text)
    
    # Email/Communication
    email_provider = Column(String(50))  # sendgrid, mailchimp, convertkit
    email_config = Column(Text)  # API keys, list IDs
    
    # Payment Processing
    stripe_account_id = Column(String(255))
    paypal_email = Column(String(255))
    
    # Preferences
    preferred_design_provider = Column(String(50), default="dalle_3")
    auto_approve_threshold = Column(Integer, default=50)  # Auto-approve under $50
    notification_preferences = Column(Text)  # JSON
    
    # Relationships
    business = relationship("Business", back_populates="config")
    
    def get_etsy_config(self) -> Dict:
        return json.loads(self.etsy_config or "{}")
    
    def set_etsy_config(self, config: Dict):
        self.etsy_config = json.dumps(config)
    
    def get_meta_ads_config(self) -> Dict:
        return json.loads(self.meta_ads_config or "{}")
    
    def set_meta_ads_config(self, config: Dict):
        self.meta_ads_config = json.dumps(config)
    
    def to_dict(self) -> Dict:
        """Return safe config (without secrets) for API responses"""
        return {
            "id": self.id,
            "business_id": self.business_id,
            "owner_email": self.owner_email,
            "business_name": self.business_name,
            "business_type": self.business_type,
            "channels_connected": {
                "etsy": bool(self.get_etsy_config().get("connected")),
                "amazon_kdp": bool(self.amazon_kdp_config),
                "shopify": bool(self.shopify_config),
                "gumroad": bool(self.gumroad_config),
            },
            "ads_connected": {
                "meta": bool(self.get_meta_ads_config().get("connected")),
                "google": bool(self.google_ads_config),
                "amazon": bool(self.amazon_ads_config),
            },
            "email_provider": self.email_provider,
            "preferred_design_provider": self.preferred_design_provider,
            "auto_approve_threshold": self.auto_approve_threshold,
        }
    
    def to_full_dict(self) -> Dict:
        """Full config for internal use (with secrets)"""
        return {
            **self.to_dict(),
            "etsy": self.get_etsy_config(),
            "meta_ads": self.get_meta_ads_config(),
            # ... other configs
        }


class SetupWizardState(Base):
    """Tracks where a user is in the setup wizard"""
    __tablename__ = "setup_wizard_states"
    
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Wizard progress
    current_step = Column(String(50), default="welcome")  # welcome, business_info, channels, ads, email, review, complete
    completed_steps = Column(Text, default="[]")  # JSON list
    
    # Partial answers stored during wizard
    wizard_data = Column(Text, default="{}")  # JSON blob of answers so far
    
    def get_data(self) -> Dict:
        return json.loads(self.wizard_data or "{}")
    
    def set_data(self, data: Dict):
        self.wizard_data = json.dumps(data)
    
    def get_completed_steps(self) -> list:
        return json.loads(self.completed_steps or "[]")
    
    def mark_step_complete(self, step: str):
        completed = self.get_completed_steps()
        if step not in completed:
            completed.append(step)
        self.completed_steps = json.dumps(completed)


# Pydantic models for API
from pydantic import BaseModel, EmailStr
from typing import List, Optional as Opt


class BusinessInfoStep(BaseModel):
    owner_email: EmailStr
    business_name: str
    business_type: str = "solo"  # solo, llc, corp


class ChannelSelectionStep(BaseModel):
    enable_etsy: bool = False
    enable_amazon_kdp: bool = False
    enable_shopify: bool = False
    enable_gumroad: bool = False


class EtsyAuthStep(BaseModel):
    shop_id: str
    # OAuth flow would happen in frontend, we get token
    access_token: str
    token_secret: Opt[str] = None


class AdsSelectionStep(BaseModel):
    enable_meta: bool = False
    enable_google: bool = False
    enable_amazon_ads: bool = False
    enable_tiktok: bool = False


class MetaAdsAuthStep(BaseModel):
    ad_account_id: str
    access_token: str


class EmailSetupStep(BaseModel):
    provider: str  # sendgrid, mailchimp, convertkit
    api_key: str
    list_id: Opt[str] = None


class PreferencesStep(BaseModel):
    preferred_design_provider: str = "dalle_3"  # dalle_3, nano_banana, canva
    auto_approve_threshold: int = 50  # Auto-approve actions under $50
    notification_email: Opt[EmailStr] = None


class WizardCompleteRequest(BaseModel):
    business_id: int
    wizard_data: Dict[str, Any]


# Setup Wizard Questions Flow
SETUP_WIZARD_FLOW = {
    "welcome": {
        "title": "Welcome to Agent World",
        "description": "Let's set up your AI-powered business. This will take about 5 minutes.",
        "next_step": "business_info",
        "questions": []
    },
    "business_info": {
        "title": "Business Information",
        "description": "Tell us about your business so we can customize the experience.",
        "next_step": "channels",
        "questions": [
            {
                "id": "owner_email",
                "type": "email",
                "label": "Your Email",
                "placeholder": "you@example.com",
                "required": True,
                "help": "For notifications and approvals"
            },
            {
                "id": "business_name",
                "type": "text",
                "label": "Business Name",
                "placeholder": "Acme Products",
                "required": True
            },
            {
                "id": "business_type",
                "type": "select",
                "label": "Business Type",
                "options": [
                    {"value": "solo", "label": "Sole Proprietorship"},
                    {"value": "llc", "label": "LLC"},
                    {"value": "corp", "label": "Corporation"}
                ],
                "required": True
            }
        ]
    },
    "channels": {
        "title": "Sales Channels",
        "description": "Where do you want to sell your products? You can add more later.",
        "next_step": "channels_auth",
        "questions": [
            {
                "id": "enable_etsy",
                "type": "toggle",
                "label": "Etsy",
                "description": "Sell handmade, vintage, and craft supplies",
                "help": "Best for: Printables, digital downloads, physical products"
            },
            {
                "id": "enable_amazon_kdp",
                "type": "toggle",
                "label": "Amazon KDP",
                "description": "Self-publish books and ebooks",
                "help": "Best for: Children's books, planners, journals"
            },
            {
                "id": "enable_shopify",
                "type": "toggle",
                "label": "Shopify",
                "description": "Your own online store",
                "help": "Best for: Building a brand, higher margins"
            },
            {
                "id": "enable_gumroad",
                "type": "toggle",
                "label": "Gumroad",
                "description": "Sell digital products easily",
                "help": "Best for: Digital downloads, courses, memberships"
            }
        ]
    },
    "channels_auth": {
        "title": "Connect Your Accounts",
        "description": "Authorize Agent World to publish on your behalf.",
        "next_step": "ads",
        "dynamic": True,  # Content depends on selected channels
        "questions": []  # Generated dynamically based on channels selected
    },
    "ads": {
        "title": "Advertising (Optional)",
        "description": "Want to run paid ads? Connect your ad accounts. Skip if you want organic growth only.",
        "next_step": "ads_auth",
        "questions": [
            {
                "id": "enable_meta",
                "type": "toggle",
                "label": "Meta Ads (Facebook/Instagram)",
                "description": "Reach 2+ billion people",
                "help": "Best for: Visual products, targeted demographics"
            },
            {
                "id": "enable_google",
                "type": "toggle",
                "label": "Google Ads",
                "description": "Search and display advertising",
                "help": "Best for: High-intent searches, shopping campaigns"
            },
            {
                "id": "enable_tiktok",
                "type": "toggle",
                "label": "TikTok Ads",
                "description": "Viral short-form video ads",
                "help": "Best for: Younger audiences, viral potential"
            }
        ]
    },
    "ads_auth": {
        "title": "Connect Ad Accounts",
        "description": "Authorize ad spend management.",
        "next_step": "preferences",
        "dynamic": True,
        "questions": []
    },
    "preferences": {
        "title": "Preferences",
        "description": "Configure how Agent World makes decisions.",
        "next_step": "review",
        "questions": [
            {
                "id": "preferred_design_provider",
                "type": "select",
                "label": "Preferred Image Generator",
                "options": [
                    {"value": "dalle_3", "label": "DALL-E 3 — Best quality ($0.06/image)"},
                    {"value": "nano_banana", "label": "Nano Banana — Fast & cheap ($0.01/image)"},
                    {"value": "canva", "label": "Canva API — Templates & PDFs (Free)"}
                ],
                "required": True
            },
            {
                "id": "auto_approve_threshold",
                "type": "number",
                "label": "Auto-Approve Limit",
                "placeholder": "50",
                "help": "Actions under this amount won't require your approval (e.g., $5 listings). Set to $0 to approve everything."
            },
            {
                "id": "notification_preferences",
                "type": "multiselect",
                "label": "Notify Me When",
                "options": [
                    {"value": "sales", "label": "I make a sale"},
                    {"value": "approvals", "label": "Approval is needed"},
                    {"value": "campaigns", "label": "Ad campaign ends"},
                    {"value": "daily_digest", "label": "Daily summary"}
                ]
            }
        ]
    },
    "review": {
        "title": "Review & Launch",
        "description": "Here's what you've configured. Ready to go?",
        "next_step": "complete",
        "questions": []
    },
    "complete": {
        "title": "You're All Set!",
        "description": "Your AI business is ready. Create your first product or connect an existing one.",
        "next_step": None,
        "questions": []
    }
}
