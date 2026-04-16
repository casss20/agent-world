"""
business_models - Agent World

Business-specific diagnostic and strategy logic.
"""

from .base import (
    BusinessModel,
    BusinessModelRegistry,
    DiagnosticCheck,
    BusinessContext,
    ResourceConstraints,
    Diagnosis,
    Strategy,
    StrategyRecommendation,
    CheckResult,
    Bottleneck,
    BottleneckCategory,
    Severity,
    Evidence,
    KPITracking,
    BusinessStage,
    registry
)

from .etsy_pod import EtsyPODModel
from .tiktok_ugc import TikTokUGCModel
from .youtube_faceless import YouTubeFacelessModel

# Register available models
registry.register(EtsyPODModel())
registry.register(TikTokUGCModel())
registry.register(YouTubeFacelessModel())

__all__ = [
    "BusinessModel",
    "BusinessModelRegistry",
    "DiagnosticCheck",
    "BusinessContext",
    "ResourceConstraints",
    "Diagnosis",
    "Strategy",
    "StrategyRecommendation",
    "CheckResult",
    "Bottleneck",
    "BottleneckCategory",
    "Severity",
    "Evidence",
    "KPITracking",
    "BusinessStage",
    "EtsyPODModel",
    "TikTokUGCModel",
    "YouTubeFacelessModel",
    "registry"
]