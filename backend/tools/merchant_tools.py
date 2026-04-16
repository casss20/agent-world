"""
merchant_tools.py — Agent World

Tools for Merchant agent to publish to sales channels.
"""

import logging
from typing import Dict, Any
from mcp_registry import register_tool

logger = logging.getLogger(__name__)


async def publish_listing(
    channel: str,
    listing_data: Dict[str, Any],
    require_approval: bool = True
) -> Dict[str, Any]:
    """
    Publish a product listing to a sales channel.
    
    Args:
        channel: One of: kdp, etsy, shopify, gumroad
        listing_data: Product details (title, description, price, images, etc.)
        require_approval: Whether to require human approval first
    
    Returns:
        Publish result with listing_id, url, status, cost
    """
    from merchant_executor import get_merchant_executor
    from channel_registry import get_channel_registry
    
    registry = get_channel_registry()
    executor = get_merchant_executor(registry, None)
    
    result = await executor._publish_listing("merchant", {
        "channel": channel,
        "listing_data": listing_data
    })
    
    return result


async def update_inventory(
    channel: str,
    listing_id: str,
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update inventory or listing details on a sales channel.
    
    Args:
        channel: Sales channel (kdp, etsy, shopify, gumroad)
        listing_id: The listing/product ID
        updates: Fields to update (price, stock, status, etc.)
    
    Returns:
        Update result
    """
    from merchant_executor import get_merchant_executor
    from channel_registry import get_channel_registry
    
    registry = get_channel_registry()
    executor = get_merchant_executor(registry, None)
    
    return await executor._update_inventory("merchant", {
        "channel": channel,
        "listing_id": listing_id,
        "updates": updates
    })


async def check_listing_status(
    channel: str,
    listing_id: str
) -> Dict[str, Any]:
    """
    Check the status of a published listing.
    
    Args:
        channel: Sales channel
        listing_id: The listing ID to check
    
    Returns:
        Status, metrics, and recommendations
    """
    from merchant_executor import get_merchant_executor
    from channel_registry import get_channel_registry
    
    registry = get_channel_registry()
    executor = get_merchant_executor(registry, None)
    
    return await executor._check_status("merchant", {
        "channel": channel,
        "listing_id": listing_id
    })


async def sync_channels(
    source_channel: str,
    target_channels: list,
    listing_id: str,
    listing_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Sync a listing from source channel to multiple target channels.
    
    Args:
        source_channel: Source platform
        target_channels: List of platforms to sync to
        listing_id: Source listing ID
        listing_data: Full listing data
    
    Returns:
        Sync results for each target channel
    """
    from merchant_executor import get_merchant_executor
    from channel_registry import get_channel_registry
    
    registry = get_channel_registry()
    executor = get_merchant_executor(registry, None)
    
    return await executor._sync_channels("merchant", {
        "source_channel": source_channel,
        "target_channels": target_channels,
        "listing_id": listing_id,
        "listing_data": listing_data
    })


def register_merchant_tools():
    """Register all merchant tools in the MCP registry"""
    
    register_tool(
        name="publish_listing",
        description="Publish a product listing to Amazon KDP, Etsy, Shopify, or Gumroad. Returns listing ID, URL, and status. Requires human approval for new listings.",
        parameters={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Sales channel: kdp, etsy, shopify, or gumroad",
                    "enum": ["kdp", "etsy", "shopify", "gumroad"]
                },
                "listing_data": {
                    "type": "object",
                    "description": "Product details including title, description, price, images, etc.",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "price": {"type": "number"},
                        "images": {"type": "array", "items": {"type": "string"}},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "category": {"type": "string"},
                        "pdf_url": {"type": "string"},
                        "cover_url": {"type": "string"}
                    }
                }
            },
            "required": ["channel", "listing_data"]
        },
        fn=publish_listing
    )
    
    register_tool(
        name="update_inventory",
        description="Update inventory, price, or status of an existing listing on a sales channel.",
        parameters={
            "type": "object",
            "properties": {
                "channel": {"type": "string", "enum": ["kdp", "etsy", "shopify", "gumroad"]},
                "listing_id": {"type": "string"},
                "updates": {
                    "type": "object",
                    "properties": {
                        "price": {"type": "number"},
                        "stock": {"type": "integer"},
                        "status": {"type": "string", "enum": ["active", "inactive", "sold_out"]},
                        "title": {"type": "string"},
                        "description": {"type": "string"}
                    }
                }
            },
            "required": ["channel", "listing_id", "updates"]
        },
        fn=update_inventory
    )
    
    register_tool(
        name="check_listing_status",
        description="Check the current status and metrics of a published listing (views, favorites, sales).",
        parameters={
            "type": "object",
            "properties": {
                "channel": {"type": "string"},
                "listing_id": {"type": "string"}
            },
            "required": ["channel", "listing_id"]
        },
        fn=check_listing_status
    )
    
    register_tool(
        name="sync_channels",
        description="Sync a listing from one channel to multiple other channels (e.g., KDP to Etsy).",
        parameters={
            "type": "object",
            "properties": {
                "source_channel": {"type": "string"},
                "target_channels": {"type": "array", "items": {"type": "string"}},
                "listing_id": {"type": "string"},
                "listing_data": {"type": "object"}
            },
            "required": ["source_channel", "target_channels", "listing_id", "listing_data"]
        },
        fn=sync_channels
    )
    
    logger.info("[Merchant Tools] Registered 4 tools: publish_listing, update_inventory, check_listing_status, sync_channels")
