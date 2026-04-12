"""
Input Validation - Ticket 3: Security Hardening
Validate and sanitize all user inputs
"""

import re
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator


# Validation patterns
PATTERNS = {
    "room_id": re.compile(r"^[a-zA-Z0-9_-]{1,64}$"),
    "user_id": re.compile(r"^[a-zA-Z0-9_-]{1,64}$"),
    "workflow_id": re.compile(r"^[a-zA-Z0-9_-]{1,128}$"),
    "task_prompt": re.compile(r"^[\s\S]{1,10000}$"),  # Up to 10KB
}


class LaunchRequest(BaseModel):
    """Validated launch request"""
    room_id: str = Field(..., min_length=1, max_length=64)
    user_id: str = Field(..., min_length=1, max_length=64)
    workflow_id: str = Field(default="demo_simple_memory", max_length=128)
    task_prompt: str = Field(..., min_length=1, max_length=10000)
    variables: Optional[Dict[str, Any]] = Field(default=None)
    webhook_url: Optional[str] = Field(default=None, max_length=2048)
    
    @validator("room_id", "user_id", "workflow_id")
    def validate_id(cls, v):
        """Validate ID format"""
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Only alphanumeric, underscore, and hyphen allowed")
        return v
    
    @validator("webhook_url")
    def validate_webhook(cls, v):
        """Validate webhook URL"""
        if v is None:
            return v
        
        # Check for valid URL format
        if not re.match(r"^https?://", v):
            raise ValueError("Webhook URL must be HTTP or HTTPS")
        
        # Block localhost/private IPs in production
        blocked_patterns = [
            r"^http://localhost",
            r"^http://127\.",
            r"^http://192\.168\.",
            r"^http://10\.",
            r"^http://172\.(1[6-9]|2[0-9]|3[01])\.",
            r"^file://",
            r"^ftp://",
        ]
        
        for pattern in blocked_patterns:
            if re.match(pattern, v):
                raise ValueError("Invalid webhook URL")
        
        return v
    
    @validator("task_prompt")
    def validate_prompt(cls, v):
        """Sanitize task prompt"""
        # Remove null bytes
        v = v.replace("\x00", "")
        
        # Check for obvious injection attempts
        dangerous = ["<script", "javascript:", "data:text/html", "onerror", "onload"]
        lower_v = v.lower()
        for d in dangerous:
            if d in lower_v:
                raise ValueError(f"Potentially dangerous content detected: {d}")
        
        return v
    
    @validator("variables")
    def validate_variables(cls, v):
        """Validate variables dict"""
        if v is None:
            return v
        
        # Limit size
        import json
        if len(json.dumps(v)) > 10000:
            raise ValueError("Variables too large (max 10KB)")
        
        return v


class CancelRequest(BaseModel):
    """Validated cancel request"""
    reason: Optional[str] = Field(default=None, max_length=256)
    
    @validator("reason")
    def validate_reason(cls, v):
        if v and len(v) > 256:
            raise ValueError("Reason too long")
        return v


def sanitize_string(value: str, max_length: int = 256) -> str:
    """Sanitize a string value"""
    if not isinstance(value, str):
        raise ValueError("Expected string value")
    
    # Remove null bytes
    value = value.replace("\x00", "")
    
    # Trim whitespace
    value = value.strip()
    
    # Truncate if too long
    if len(value) > max_length:
        value = value[:max_length]
    
    return value


def validate_json_schema(data: Dict[str, Any], required_fields: List[str]) -> bool:
    """Validate JSON has required fields"""
    for field in required_fields:
        if field not in data:
            return False
    return True


class InputValidator:
    """Central input validation utility"""
    
    @staticmethod
    def validate_room_id(room_id: str) -> str:
        """Validate room ID"""
        if not room_id or len(room_id) > 64:
            raise ValueError("Room ID must be 1-64 characters")
        
        if not PATTERNS["room_id"].match(room_id):
            raise ValueError("Invalid room ID format")
        
        return room_id
    
    @staticmethod
    def validate_user_id(user_id: str) -> str:
        """Validate user ID"""
        if not user_id or len(user_id) > 64:
            raise ValueError("User ID must be 1-64 characters")
        
        if not PATTERNS["user_id"].match(user_id):
            raise ValueError("Invalid user ID format")
        
        return user_id
    
    @staticmethod
    def validate_workflow_id(workflow_id: str) -> str:
        """Validate workflow ID"""
        if not workflow_id or len(workflow_id) > 128:
            raise ValueError("Workflow ID must be 1-128 characters")
        
        if not PATTERNS["workflow_id"].match(workflow_id):
            raise ValueError("Invalid workflow ID format")
        
        return workflow_id
