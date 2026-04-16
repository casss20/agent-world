"""
merchant_executor.py — Agent World

Execution logic for Merchant agent (sales channel publishing).
Manages KDP, Etsy, Shopify, Gumroad integrations.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class PublishResult:
    """Result of a publishing operation"""
    success: bool
    platform: str
    listing_id: Optional[str]
    listing_url: Optional[str]
    status: str  # pending_review, live, rejected, draft
    message: str
    cost_usd: float
    estimated_live_at: Optional[datetime]
    platform_specific: Dict[str, Any]


class MerchantExecutor:
    """Executes Merchant agent publishing tasks"""
    
    def __init__(self, channel_registry, ledger_client):
        self.channels = channel_registry
        self.ledger = ledger_client
        self.publish_history: List[Dict] = []
    
    async def execute(self, agent_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a Merchant task.
        
        Task types:
        - publish_listing: Publish to specific channel
        - update_inventory: Update stock/status
        - sync_channels: Sync across multiple channels
        - check_status: Check listing status
        """
        task_type = task.get("task_type")
        payload = task.get("payload", {})
        
        logger.info(f"[Merchant:{agent_id}] Executing {task_type}")
        
        if task_type == "publish_listing":
            return await self._publish_listing(agent_id, payload)
        elif task_type == "update_inventory":
            return await self._update_inventory(agent_id, payload)
        elif task_type == "sync_channels":
            return await self._sync_channels(agent_id, payload)
        elif task_type == "check_status":
            return await self._check_status(agent_id, payload)
        elif task_type == "price_optimization":
            return await self._price_optimization(agent_id, payload)
        else:
            return {"error": f"Unknown task type: {task_type}"}
    
    async def _publish_listing(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Publish a listing to a sales channel"""
        channel = payload.get("channel")  # kdp, etsy, shopify, gumroad
        listing_data = payload.get("listing_data", {})
        
        # Get channel adapter from registry
        adapter = self.channels.get_adapter(channel)
        if not adapter:
            return {
                "success": False,
                "error": f"Channel {channel} not configured",
                "available_channels": self.channels.list_available()
            }
        
        # Check connection
        health = await adapter.test_connection()
        if not health.get("ok"):
            return {
                "success": False,
                "error": f"Channel {channel} not connected: {health.get('message')}"
            }
        
        # Platform-specific preparation
        if channel == "kdp":
            result = await self._publish_kdp(adapter, listing_data)
        elif channel == "etsy":
            result = await self._publish_etsy(adapter, listing_data)
        elif channel == "shopify":
            result = await self._publish_shopify(adapter, listing_data)
        elif channel == "gumroad":
            result = await self._publish_gumroad(adapter, listing_data)
        else:
            result = PublishResult(
                success=False,
                platform=channel,
                listing_id=None,
                listing_url=None,
                status="error",
                message=f"Unsupported channel: {channel}",
                cost_usd=0.0,
                estimated_live_at=None,
                platform_specific={}
            )
        
        # Log to history
        self.publish_history.append({
            "agent_id": agent_id,
            "timestamp": datetime.utcnow().isoformat(),
            "channel": channel,
            "result": result
        })
        
        return {
            "success": result.success,
            "platform": result.platform,
            "listing_id": result.listing_id,
            "listing_url": result.listing_url,
            "status": result.status,
            "message": result.message,
            "cost_usd": result.cost_usd,
            "estimated_live_at": result.estimated_live_at.isoformat() if result.estimated_live_at else None,
            "platform_specific": result.platform_specific
        }
    
    async def _publish_kdp(self, adapter, listing_data: Dict) -> PublishResult:
        """Publish to Amazon KDP"""
        try:
            # KDP-specific publishing logic
            # Would call adapter.create_listing() with KDP formatting
            
            title = listing_data.get("title", "")
            description = listing_data.get("description", "")
            keywords = listing_data.get("keywords", [])
            price = listing_data.get("price", 4.99)
            pdf_url = listing_data.get("pdf_url")
            cover_url = listing_data.get("cover_url")
            
            # Simulate API call (replace with real KDP API)
            await asyncio.sleep(2)  # Simulate network
            
            mock_asin = f"B0{hash(title) % 10000000000:010d}"
            
            return PublishResult(
                success=True,
                platform="kdp",
                listing_id=mock_asin,
                listing_url=f"https://amazon.com/dp/{mock_asin}",
                status="pending_review",
                message="KDP submission successful. Book in review queue (24-72 hours).",
                cost_usd=0.0,  # Free to publish, printing cost deducted from sales
                estimated_live_at=datetime.utcnow(),  # + 48 hours
                platform_specific={
                    "asin": mock_asin,
                    "royalty_rate": "60%",
                    "printing_cost": f"${listing_data.get('page_count', 32) * 0.012:.2f}",
                    "review_status": "in_queue"
                }
            )
        except Exception as e:
            logger.error(f"KDP publish failed: {e}")
            return PublishResult(
                success=False,
                platform="kdp",
                listing_id=None,
                listing_url=None,
                status="error",
                message=str(e),
                cost_usd=0.0,
                estimated_live_at=None,
                platform_specific={}
            )
    
    async def _publish_etsy(self, adapter, listing_data: Dict) -> PublishResult:
        """Publish to Etsy"""
        try:
            # Etsy-specific publishing
            await asyncio.sleep(1.5)
            
            mock_listing_id = f"{hash(listing_data.get('title', '')) % 1000000000:09d}"
            
            return PublishResult(
                success=True,
                platform="etsy",
                listing_id=mock_listing_id,
                listing_url=f"https://etsy.com/listing/{mock_listing_id}",
                status="live",  # Etsy is immediate
                message="Etsy listing published and live.",
                cost_usd=0.20,  # Listing fee
                estimated_live_at=datetime.utcnow(),
                platform_specific={
                    "listing_id": mock_listing_id,
                    "renewal_interval": "4 months",
                    "transaction_fee": "6.5%",
                    "processing_fee": "3% + $0.25"
                }
            )
        except Exception as e:
            logger.error(f"Etsy publish failed: {e}")
            return PublishResult(
                success=False, platform="etsy", listing_id=None,
                listing_url=None, status="error", message=str(e),
                cost_usd=0.0, estimated_live_at=None, platform_specific={}
            )
    
    async def _publish_shopify(self, adapter, listing_data: Dict) -> PublishResult:
        """Publish to Shopify"""
        try:
            await asyncio.sleep(1)
            
            mock_product_id = f"gid://shopify/Product/{hash(listing_data.get('title', '')) % 10000000000}"
            
            return PublishResult(
                success=True,
                platform="shopify",
                listing_id=mock_product_id,
                listing_url=f"https://store.myshopify.com/products/{mock_product_id.split('/')[-1]}",
                status="live",
                message="Shopify product created and published.",
                cost_usd=0.0,
                estimated_live_at=datetime.utcnow(),
                platform_specific={
                    "product_id": mock_product_id,
                    "inventory_policy": "deny",
                    "requires_shipping": listing_data.get("physical", False)
                }
            )
        except Exception as e:
            return PublishResult(
                success=False, platform="shopify", listing_id=None,
                listing_url=None, status="error", message=str(e),
                cost_usd=0.0, estimated_live_at=None, platform_specific={}
            )
    
    async def _publish_gumroad(self, adapter, listing_data: Dict) -> PublishResult:
        """Publish to Gumroad"""
        try:
            await asyncio.sleep(1)
            
            mock_id = f"{hash(listing_data.get('title', '')) % 1000000:06d}"
            slug = listing_data.get("title", "").lower().replace(" ", "-")[:50]
            
            return PublishResult(
                success=True,
                platform="gumroad",
                listing_id=mock_id,
                listing_url=f"https://gumroad.com/l/{slug}",
                status="live",
                message="Gumroad product created and ready for purchase.",
                cost_usd=0.0,
                estimated_live_at=datetime.utcnow(),
                platform_specific={
                    "product_id": mock_id,
                    "gumroad_fee": "10% + $0.30",
                    "stripe_fee": "2.9% + $0.30" if listing_data.get("use_stripe") else None
                }
            )
        except Exception as e:
            return PublishResult(
                success=False, platform="gumroad", listing_id=None,
                listing_url=None, status="error", message=str(e),
                cost_usd=0.0, estimated_live_at=None, platform_specific={}
            )
    
    async def _update_inventory(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Update inventory/stock across channels"""
        channel = payload.get("channel")
        listing_id = payload.get("listing_id")
        updates = payload.get("updates", {})
        
        adapter = self.channels.get_adapter(channel)
        if not adapter:
            return {"success": False, "error": f"Channel {channel} not configured"}
        
        # Execute updates
        results = {}
        for field, value in updates.items():
            try:
                # Would call adapter.update_listing()
                results[field] = {"success": True, "new_value": value}
            except Exception as e:
                results[field] = {"success": False, "error": str(e)}
        
        return {
            "success": all(r.get("success") for r in results.values()),
            "channel": channel,
            "listing_id": listing_id,
            "updates": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _sync_channels(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Sync listing across multiple channels"""
        source_channel = payload.get("source_channel")
        target_channels = payload.get("target_channels", [])
        listing_id = payload.get("listing_id")
        
        results = []
        for target in target_channels:
            if target == source_channel:
                continue
            
            # Fetch from source
            # Adapt format for target
            # Publish to target
            
            result = await self._publish_listing(agent_id, {
                "channel": target,
                "listing_data": payload.get("listing_data", {})
            })
            
            results.append({
                "target_channel": target,
                "result": result
            })
        
        return {
            "success": all(r["result"].get("success") for r in results),
            "source": source_channel,
            "sync_results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _check_status(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Check listing status across channels"""
        channel = payload.get("channel")
        listing_id = payload.get("listing_id")
        
        adapter = self.channels.get_adapter(channel)
        if not adapter:
            return {"success": False, "error": f"Channel {channel} not configured"}
        
        # Would call adapter.get_listing_status()
        return {
            "success": True,
            "channel": channel,
            "listing_id": listing_id,
            "status": "live",  # pending_review, live, rejected, draft
            "metrics": {
                "views": 127,
                "favorites": 12,
                "sales": 3,
                "revenue": 14.97
            }
        }
    
    async def _price_optimization(self, agent_id: str, payload: Dict) -> Dict[str, Any]:
        """Analyze and suggest price optimizations"""
        channel = payload.get("channel")
        current_price = payload.get("current_price")
        competitor_prices = payload.get("competitor_prices", [])
        
        # Simple algorithm (would be more sophisticated)
        avg_competitor = sum(competitor_prices) / len(competitor_prices) if competitor_prices else current_price
        
        suggestions = []
        if current_price < avg_competitor * 0.8:
            suggestions.append({
                "type": "increase",
                "reason": "Significantly underpriced vs competitors",
                "suggested_price": round(avg_competitor * 0.95, 2),
                "potential_revenue_impact": "+15-20%"
            })
        elif current_price > avg_competitor * 1.3:
            suggestions.append({
                "type": "decrease",
                "reason": "Premium pricing may limit volume",
                "suggested_price": round(avg_competitor * 1.1, 2),
                "potential_revenue_impact": "+10-30% volume"
            })
        else:
            suggestions.append({
                "type": "maintain",
                "reason": "Price is competitive with market",
                "confidence": "high"
            })
        
        return {
            "success": True,
            "current_price": current_price,
            "market_average": round(avg_competitor, 2),
            "suggestions": suggestions,
            "requires_approval": True  # Price changes need human approval
        }


# Singleton instance
_merchant_executor: Optional[MerchantExecutor] = None

def get_merchant_executor(channel_registry=None, ledger_client=None) -> MerchantExecutor:
    global _merchant_executor
    if _merchant_executor is None:
        _merchant_executor = MerchantExecutor(channel_registry, ledger_client)
    return _merchant_executor