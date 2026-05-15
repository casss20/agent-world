"""Auth compatibility stub"""
from typing import Dict, Any

def get_current_user() -> Dict[str, Any]:
    return {"id": "anonymous", "role": "viewer"}
