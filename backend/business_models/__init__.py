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
try:
    registry.register(EtsyPODModel())
except Exception as e:
    import logging
    logging.getLogger(__name__).warning("EtsyPODModel registration failed: %s", e)

try:
    registry.register(TikTokUGCModel())
except Exception as e:
    import logging
    logging.getLogger(__name__).warning("TikTokUGCModel registration failed: %s", e)

try:
    registry.register(YouTubeFacelessModel())
except Exception as e:
    import logging
    logging.getLogger(__name__).warning("YouTubeFacelessModel registration failed: %s", e)

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