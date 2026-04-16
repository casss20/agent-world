"""
promoter_executor.py — Agent World

Execution logic for Promoter agent (paid advertising).
Manages Meta Ads, Google Ads, Amazon Ads, TikTok Ads, Pinterest Ads.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class CampaignResult:
    """Result of a campaign operation"""
    success: bool
    platform: str
    campaign_id: Optional[str]
    campaign_name: str
    status: str  # draft, active, paused, completed
    message: str
    budget: Dict[str, Any]  # daily, lifetime, spent
    estimated_reach: int
    estimated_cpm: float


@dataclass
class CampaignMetrics:
    """Performance metrics for a campaign"""
    campaign_id: str
    platform: str
    spend: float
    impressions: int
    clicks: int
    ctr: float
    cpc: float
    conversions: int
    cpa: float
    roas: float
    status: str


class PromoterExecutor:
    """Executes Promoter agent advertising tasks"""
    
    def __init__(self, ledger_client):
        self.ledger = ledger_client
        self.active_campaigns: Dict[str, Dict] = {}
        self.performance_history: List[Dict] = []
        
        # Budget safety limits
        self.max_daily_spend = 1000.0
        self.max_campaign_budget = 10000.0
        self.auto_pause_threshold = {"roas": 0.5, "ctr": 0.5}  # Pause if ROAS < 0.5 or CTR < 0.5%
    
    async def execute(self, agent_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a Promoter task.
        
        Task types:
        - create_campaign: Create new ad campaign
        - modify_budget: Change budget (increase/decrease)
        - pause_campaign: Pause underperforming
        - get_metrics: Retrieve performance data
        - optimize: Auto-optimize based on rules
        """
        task_type = task.get("task_type")
        payload = task.get("payload", {})
        
        logger.info(f"[Promoter:{agent_id}] Executing {task_type}")
        
        if task_type == "create_campaign":
            return await self._create_campaign(agent_id, payload)
        elif task_type == "modify_budget":
            return await self._modify_budget(agent_id, payload)
        elif task_type == "pause_campaign":
            return await self._pause_campaign(agent_id, payload)
        elif task_type == "get_metrics":
            return await self._get_metrics(agent_id, payload)
        elif task_type == "optimize":
            return await self._optimize_campaign(agent_id, payload)
        elif task_type == "a_b_test":
            return await self._a_b_test(agent_id, payload)
        else:
            return {"error": f"Unknown task type: {task_type}"}
    
    async def _create_campaign(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Create a new ad campaign"""
        platform = payload.get("platform")  # meta, google, amazon, tiktok, pinterest
        campaign_config = payload.get("campaign", {})
        
        # Validate budget limits
        daily_budget = campaign_config.get("daily_budget", 10.0)
        lifetime_budget = campaign_config.get("lifetime_budget")
        
        if daily_budget > self.max_daily_spend:
            return {
                "success": False,
                "error": f"Daily budget ${daily_budget} exceeds maximum ${self.max_daily_spend}",
                "requires_human_approval": True
            }
        
        if lifetime_budget and lifetime_budget > self.max_campaign_budget:
            return {
                "success": False,
                "error": f"Lifetime budget ${lifetime_budget} exceeds maximum ${self.max_campaign_budget}",
                "requires_human_approval": True
            }
        
        # Platform-specific campaign creation
        if platform == "meta":
            result = await self._create_meta_campaign(campaign_config)
        elif platform == "google":
            result = await self._create_google_campaign(campaign_config)
        elif platform == "amazon":
            result = await self._create_amazon_campaign(campaign_config)
        elif platform == "tiktok":
            result = await self._create_tiktok_campaign(campaign_config)
        elif platform == "pinterest":
            result = await self._create_pinterest_campaign(campaign_config)
        else:
            return {"success": False, "error": f"Unsupported platform: {platform}"}
        
        if result.success:
            self.active_campaigns[result.campaign_id] = {
                "agent_id": agent_id,
                "platform": platform,
                "created_at": datetime.utcnow().isoformat(),
                "config": campaign_config,
                "status": "active"
            }
        
        return {
            "success": result.success,
            "platform": result.platform,
            "campaign_id": result.campaign_id,
            "campaign_name": result.campaign_name,
            "status": result.status,
            "message": result.message,
            "budget": result.budget,
            "estimated_reach": result.estimated_reach,
            "estimated_cpm": result.estimated_cpm
        }
    
    async def _create_meta_campaign(self, config: Dict) -> CampaignResult:
        """Create Meta (Facebook/Instagram) campaign"""
        try:
            await asyncio.sleep(2)  # Simulate API
            
            mock_campaign_id = f"campaign_{hash(config.get('name', '')) % 1000000000:09d}"
            daily_budget = config.get("daily_budget", 10.0)
            
            # Estimate reach (simplified)
            estimated_reach = int(daily_budget * 1000)  # $10 = ~10K reach
            estimated_cpm = 10.0  # $10 CPM typical for Meta
            
            return CampaignResult(
                success=True,
                platform="meta",
                campaign_id=mock_campaign_id,
                campaign_name=config.get("name", "Untitled Campaign"),
                status="active",
                message="Meta campaign created and active.",
                budget={
                    "daily": daily_budget,
                    "lifetime": config.get("lifetime_budget"),
                    "spent": 0.0,
                    "currency": "USD"
                },
                estimated_reach=estimated_reach,
                estimated_cpm=estimated_cpm
            )
        except Exception as e:
            logger.error(f"Meta campaign creation failed: {e}")
            return CampaignResult(
                success=False, platform="meta", campaign_id=None,
                campaign_name=config.get("name", ""), status="error",
                message=str(e), budget={}, estimated_reach=0, estimated_cpm=0
            )
    
    async def _create_google_campaign(self, config: Dict) -> CampaignResult:
        """Create Google Ads campaign"""
        try:
            await asyncio.sleep(2)
            
            mock_id = f"{hash(config.get('name', '')) % 1000000000:09d}"
            daily_budget = config.get("daily_budget", 10.0)
            
            return CampaignResult(
                success=True,
                platform="google",
                campaign_id=mock_id,
                campaign_name=config.get("name", "Untitled"),
                status="active",
                message="Google Ads campaign created and active.",
                budget={"daily": daily_budget, "lifetime": config.get("lifetime_budget"), "spent": 0.0, "currency": "USD"},
                estimated_reach=int(daily_budget * 500),  # Lower reach, higher intent
                estimated_cpm=20.0  # Higher CPM for search
            )
        except Exception as e:
            return CampaignResult(
                success=False, platform="google", campaign_id=None,
                campaign_name=config.get("name", ""), status="error",
                message=str(e), budget={}, estimated_reach=0, estimated_cpm=0
            )
    
    async def _create_amazon_campaign(self, config: Dict) -> CampaignResult:
        """Create Amazon Ads campaign"""
        try:
            await asyncio.sleep(2)
            mock_id = f"{hash(config.get('name', '')) % 100000000:08d}"
            
            return CampaignResult(
                success=True,
                platform="amazon",
                campaign_id=mock_id,
                campaign_name=config.get("name", "Untitled"),
                status="active",
                message="Amazon Ads campaign created.",
                budget={"daily": config.get("daily_budget", 10.0), "spent": 0.0, "currency": "USD"},
                estimated_reach=int(config.get("daily_budget", 10) * 300),
                estimated_cpm=15.0
            )
        except Exception as e:
            return CampaignResult(
                success=False, platform="amazon", campaign_id=None,
                campaign_name=config.get("name", ""), status="error",
                message=str(e), budget={}, estimated_reach=0, estimated_cpm=0
            )
    
    async def _create_tiktok_campaign(self, config: Dict) -> CampaignResult:
        """Create TikTok Ads campaign"""
        try:
            await asyncio.sleep(2)
            mock_id = f"{hash(config.get('name', '')) % 100000000:08d}"
            
            return CampaignResult(
                success=True,
                platform="tiktok",
                campaign_id=mock_id,
                campaign_name=config.get("name", "Untitled"),
                status="active",
                message="TikTok Ads campaign created.",
                budget={"daily": config.get("daily_budget", 10.0), "spent": 0.0, "currency": "USD"},
                estimated_reach=int(config.get("daily_budget", 10) * 2000),  # High reach
                estimated_cpm=5.0  # Lower CPM
            )
        except Exception as e:
            return CampaignResult(
                success=False, platform="tiktok", campaign_id=None,
                campaign_name=config.get("name", ""), status="error",
                message=str(e), budget={}, estimated_reach=0, estimated_cpm=0
            )
    
    async def _create_pinterest_campaign(self, config: Dict) -> CampaignResult:
        """Create Pinterest Ads campaign"""
        try:
            await asyncio.sleep(2)
            mock_id = f"{hash(config.get('name', '')) % 100000000:08d}"
            
            return CampaignResult(
                success=True,
                platform="pinterest",
                campaign_id=mock_id,
                campaign_name=config.get("name", "Untitled"),
                status="active",
                message="Pinterest Ads campaign created.",
                budget={"daily": config.get("daily_budget", 10.0), "spent": 0.0, "currency": "USD"},
                estimated_reach=int(config.get("daily_budget", 10) * 800),
                estimated_cpm=12.0
            )
        except Exception as e:
            return CampaignResult(
                success=False, platform="pinterest", campaign_id=None,
                campaign_name=config.get("name", ""), status="error",
                message=str(e), budget={}, estimated_reach=0, estimated_cpm=0
            )
    
    async def _modify_budget(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Modify campaign budget"""
        campaign_id = payload.get("campaign_id")
        new_daily = payload.get("new_daily_budget")
        new_lifetime = payload.get("new_lifetime_budget")
        
        # Safety checks
        if new_daily and new_daily > self.max_daily_spend:
            return {
                "success": False,
                "error": f"New daily budget ${new_daily} exceeds maximum ${self.max_daily_spend}",
                "requires_approval": True
            }
        
        if campaign_id in self.active_campaigns:
            campaign = self.active_campaigns[campaign_id]
            campaign["config"]["daily_budget"] = new_daily
            campaign["config"]["lifetime_budget"] = new_lifetime
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "new_daily_budget": new_daily,
                "new_lifetime_budget": new_lifetime,
                "message": f"Budget updated. Campaign will adjust within 15 minutes.",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return {"success": False, "error": f"Campaign {campaign_id} not found"}
    
    async def _pause_campaign(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Pause a campaign"""
        campaign_id = payload.get("campaign_id")
        reason = payload.get("reason", "Manual pause")
        
        if campaign_id in self.active_campaigns:
            self.active_campaigns[campaign_id]["status"] = "paused"
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "status": "paused",
                "reason": reason,
                "final_metrics": await self._get_campaign_summary(campaign_id),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return {"success": False, "error": f"Campaign {campaign_id} not found"}
    
    async def _get_metrics(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Get campaign performance metrics"""
        campaign_id = payload.get("campaign_id")
        platform = payload.get("platform")
        
        # Simulate metrics (would call platform APIs)
        mock_metrics = CampaignMetrics(
            campaign_id=campaign_id or "unknown",
            platform=platform or "unknown",
            spend=47.50,
            impressions=4750,
            clicks=142,
            ctr=2.99,
            cpc=0.33,
            conversions=8,
            cpa=5.94,
            roas=2.1,
            status="active"
        )
        
        return {
            "success": True,
            "campaign_id": mock_metrics.campaign_id,
            "platform": mock_metrics.platform,
            "metrics": {
                "spend": mock_metrics.spend,
                "impressions": mock_metrics.impressions,
                "clicks": mock_metrics.clicks,
                "ctr": mock_metrics.ctr,
                "cpc": mock_metrics.cpc,
                "conversions": mock_metrics.conversions,
                "cpa": mock_metrics.cpa,
                "roas": mock_metrics.roas
            },
            "status": mock_metrics.status,
            "recommendation": self._generate_recommendation(mock_metrics)
        }
    
    def _generate_recommendation(self, metrics: CampaignMetrics) -> str:
        """Generate optimization recommendation based on metrics"""
        if metrics.roas >= 3.0:
            return "scale: ROAS excellent, increase budget 20-30%"
        elif metrics.roas >= 2.0:
            return "maintain: ROAS healthy, optimize creative for better CTR"
        elif metrics.roas >= 1.0:
            return "optimize: Break-even, improve targeting or creative"
        else:
            return "pause: Unprofitable, pause and reassess"
    
    async def _optimize_campaign(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Auto-optimize campaign based on performance rules"""
        campaign_id = payload.get("campaign_id")
        
        # Get current metrics
        metrics_result = await self._get_metrics(agent_id, {"campaign_id": campaign_id})
        metrics = metrics_result.get("metrics", {})
        
        roas = metrics.get("roas", 0)
        ctr = metrics.get("ctr", 0)
        
        actions = []
        
        # Auto-pause rule
        if roas < self.auto_pause_threshold["roas"]:
            pause_result = await self._pause_campaign(agent_id, {
                "campaign_id": campaign_id,
                "reason": f"Auto-pause: ROAS {roas} below threshold {self.auto_pause_threshold['roas']}"
            })
            actions.append({"type": "auto_pause", "result": pause_result})
        
        # Scale rule
        elif roas > 2.5:
            current_budget = self.active_campaigns.get(campaign_id, {}).get("config", {}).get("daily_budget", 10)
            new_budget = min(current_budget * 1.2, self.max_daily_spend)
            
            modify_result = await self._modify_budget(agent_id, {
                "campaign_id": campaign_id,
                "new_daily_budget": new_budget
            })
            actions.append({"type": "auto_scale", "result": modify_result})
        
        return {
            "success": True,
            "campaign_id": campaign_id,
            "metrics": metrics,
            "actions_taken": actions,
            "recommendation": self._generate_recommendation(CampaignMetrics(
                campaign_id=campaign_id, platform="unknown", **metrics, status="active"
            ))
        }
    
    async def _a_b_test(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Set up A/B test for creative or targeting"""
        campaign_id = payload.get("campaign_id")
        test_type = payload.get("test_type")  # creative, audience, placement
        variants = payload.get("variants", [])
        
        if len(variants) < 2:
            return {"success": False, "error": "A/B test requires at least 2 variants"}
        
        # Split budget evenly
        test_duration_days = payload.get("duration_days", 7)
        
        return {
            "success": True,
            "test_id": f"ab_test_{hash(campaign_id) % 1000000:06d}",
            "campaign_id": campaign_id,
            "test_type": test_type,
            "variants": len(variants),
            "duration_days": test_duration_days,
            "budget_per_variant": payload.get("total_budget", 70) / len(variants),
            "start_date": datetime.utcnow().isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=test_duration_days)).isoformat(),
            "message": f"A/B test created. Will auto-report winner after {test_duration_days} days."
        }
    
    async def _get_campaign_summary(self, campaign_id: str) -> Dict:
        """Get summary of campaign performance"""
        metrics = await self._get_metrics("system", {"campaign_id": campaign_id})
        return metrics.get("metrics", {})


# Singleton instance
_promoter_executor: Optional[PromoterExecutor] = None

def get_promoter_executor(ledger_client=None) -> PromoterExecutor:
    global _promoter_executor
    if _promoter_executor is None:
        _promoter_executor = PromoterExecutor(ledger_client)
    return _promoter_executor