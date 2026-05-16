"""
Routing Rules — Phase 2
Task tiers and routing rule definitions for LLMRouter.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List


class TaskTier(Enum):
    HEAVYWEIGHT = "heavyweight"  # complex reasoning
    STANDARD = "standard"        # general tasks
    FAST = "fast"                # quick classification
    LOCAL = "local"              # free, private, batch


@dataclass
class RoutingRule:
    """A rule that maps a task type to a tier."""
    name: str
    tier: TaskTier
    keywords: List[str]         # matched against task description
    agents: List[str]           # matched against calling agent
    phases: List[str]           # matched against harness phase


# ─────────────────────────────────────────────────────────────
# ROUTING RULES (evaluated in order, first match wins)
# ─────────────────────────────────────────────────────────────

ROUTING_RULES: List[RoutingRule] = [

    # TIER 1: HEAVYWEIGHT
    RoutingRule(
        name="strategic_planning",
        tier=TaskTier.HEAVYWEIGHT,
        keywords=["strategize", "strategy", "plan quarterly",
                   "evaluate", "analyze market", "business decision",
                   "competitive analysis", "risk assessment",
                   "investor", "board", "vision", "OKR"],
        agents=["ceo", "coo"],
        phases=["plan", "verify"],
    ),
    RoutingRule(
        name="governance_decision",
        tier=TaskTier.HEAVYWEIGHT,
        keywords=["approve", "reject", "governance",
                   "compliance", "legal review", "audit"],
        agents=["ceo", "cipher"],
        phases=["verify"],
    ),
    RoutingRule(
        name="business_diagnosis",
        tier=TaskTier.HEAVYWEIGHT,
        keywords=["diagnose", "diagnosis", "bottleneck",
                   "health score", "what's wrong", "assess"],
        agents=["ceo", "coo", "nova"],
        phases=["plan"],
    ),

    # TIER 2: STANDARD
    RoutingRule(
        name="content_creation",
        tier=TaskTier.STANDARD,
        keywords=["write", "script", "blog", "caption",
                   "email", "listing", "description", "copy",
                   "hook", "post", "story", "article"],
        agents=["forge", "content", "merchant"],
        phases=["execute"],
    ),
    RoutingRule(
        name="research_synthesis",
        tier=TaskTier.STANDARD,
        keywords=["research", "analyze", "summarize",
                   "trends", "competitor", "keyword",
                   "find", "gather", "report"],
        agents=["nova", "growth", "crm"],
        phases=["execute"],
    ),
    RoutingRule(
        name="ad_campaign",
        tier=TaskTier.STANDARD,
        keywords=["campaign", "ad copy", "Facebook ad",
                   "TikTok ad", "A/B test", "creative",
                   "audience", "targeting", "ROAS"],
        agents=["promoter"],
        phases=["execute"],
    ),
    RoutingRule(
        name="code_generation",
        tier=TaskTier.STANDARD,
        keywords=["code", "implement", "build", "deploy",
                   "fix", "debug", "architecture", "API",
                   "function", "class"],
        agents=["developer"],
        phases=["execute"],
    ),
    RoutingRule(
        name="harness_plan_verify",
        tier=TaskTier.HEAVYWEIGHT,
        keywords=[],
        agents=[],
        phases=["plan", "verify"],
    ),
    RoutingRule(
        name="harness_execute",
        tier=TaskTier.STANDARD,
        keywords=[],
        agents=[],
        phases=["execute", "recover"],
    ),

    # TIER 3: FAST
    RoutingRule(
        name="routing_classification",
        tier=TaskTier.FAST,
        keywords=["route", "classify", "which agent",
                   "detect intent", "categorize"],
        agents=["ultron"],
        phases=[],
    ),
    RoutingRule(
        name="quality_check",
        tier=TaskTier.FAST,
        keywords=["check format", "safety check",
                   "brand check", "tone check", "verify format",
                   "grammar", "spell"],
        agents=["cipher"],
        phases=[],
    ),
    RoutingRule(
        name="short_form",
        tier=TaskTier.FAST,
        keywords=["subject line", "title", "tag", "hashtag", "label", "category",
                   "one sentence", "short"],
        agents=[],
        phases=[],
    ),
    RoutingRule(
        name="notification",
        tier=TaskTier.FAST,
        keywords=["notify", "alert", "slack message",
                   "email subject", "push notification"],
        agents=[],
        phases=[],
    ),

    # TIER 4: LOCAL
    RoutingRule(
        name="batch_processing",
        tier=TaskTier.LOCAL,
        keywords=["batch", "bulk", "100+", "all products",
                   "mass", "scheduled", "background"],
        agents=[],
        phases=[],
    ),
    RoutingRule(
        name="sensitive_data",
        tier=TaskTier.LOCAL,
        keywords=["customer data", "PII", "email list",
                   "personal information", "private",
                   "confidential", "internal"],
        agents=[],
        phases=[],
    ),
    RoutingRule(
        name="scheduled_job",
        tier=TaskTier.LOCAL,
        keywords=["morning briefing", "weekly report",
                   "daily summary", "scheduled", "cron"],
        agents=[],
        phases=[],
    ),
]


# ── Provider Tier Assignment ─────────────────────────────────

TIER_PROVIDERS: Dict[TaskTier, List[str]] = {
    TaskTier.HEAVYWEIGHT: [
        "anthropic",    # best reasoning
        "openai",       # strong fallback
        "deepseek",     # good reasoning, cheap
        "openrouter",   # access to frontier via one key
        "groq",         # fast, capable free tier
        "ollama",       # local fallback
    ],
    TaskTier.STANDARD: [
        "deepseek",     # cheap, capable
        "groq",         # fast free tier
        "openai",       # reliable
        "anthropic",    # overkill but available
        "openrouter",   # open models
        "ollama",       # local fallback
    ],
    TaskTier.FAST: [
        "groq",         # fastest inference available
        "deepseek",     # very cheap
        "openrouter",   # open models
        "ollama",       # local
        "anthropic",    # fallback
        "openai",       # fallback
    ],
    TaskTier.LOCAL: [
        "ollama",       # local only
        "groq",         # free tier fallback if ollama down
        "deepseek",     # cheap cloud fallback
    ],
}
