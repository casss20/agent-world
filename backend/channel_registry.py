"""
channel_registry.py — Agent World

Pluggable adapter system for selling platforms.

Agents produce platform-agnostic outputs. The Ledger Router uses this
registry to find the right adapter and push the output to the right platform.

Supported out of the box:
  etsy     — Etsy Open API v3
  shopify  — Shopify Admin API
  gumroad  — Gumroad API
  generic  — Any REST endpoint (webhook)

To add a new channel:
  1. Subclass ChannelAdapter and set channel_id / display_name / icon
  2. Implement test_connection() and any of: create_draft_listing / get_orders / send_message
  3. Add to CHANNEL_DEFINITIONS and CHANNEL_META dicts
  4. That's it — the registry and router pick it up automatically.

Config is persisted as JSON at ./channels_config.json (path overridable via CHANNELS_CONFIG env var).
API keys are stored locally only — never in the source code.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from output_schema import ListingOutput, MessageOutput

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(os.getenv("CHANNELS_CONFIG", "./channels_config.json"))


# ── Base Adapter ───────────────────────────────────────────────── #

class ChannelAdapter(ABC):
    channel_id:        str       = "base"
    display_name:      str       = "Base Channel"
    icon:              str       = "🔌"
    description:       str       = ""
    supported_outputs: List[str] = ["listing"]

    def __init__(self, config: Dict[str, Any]):
        self.config    = config
        self.connected = bool(
            config.get("api_key") or config.get("access_token") or config.get("endpoint_url")
        )

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Verify credentials. Returns {ok: bool, message: str}."""

    async def create_draft_listing(self, listing: ListingOutput) -> Dict[str, Any]:
        raise NotImplementedError(f"{self.channel_id} does not implement create_draft_listing")

    async def publish_listing(self, listing_id: str) -> Dict[str, Any]:
        raise NotImplementedError(f"{self.channel_id} does not implement publish_listing")

    async def get_orders(self, limit: int = 50) -> List[Dict]:
        raise NotImplementedError(f"{self.channel_id} does not implement get_orders")

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        raise NotImplementedError(f"{self.channel_id} does not implement send_message")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":           self.channel_id,
            "name":         self.display_name,
            "icon":         self.icon,
            "description":  self.description,
            "connected":    self.connected,
            "supported":    self.supported_outputs,
            "configured_at": self.config.get("configured_at"),
        }


# ── Etsy Adapter ───────────────────────────────────────────────── #

class EtsyAdapter(ChannelAdapter):
    channel_id        = "etsy"
    display_name      = "Etsy"
    icon              = "🧶"
    description       = "Sell handmade and print-on-demand products on Etsy marketplace."
    supported_outputs = ["listing", "message"]

    BASE_URL = "https://openapi.etsy.com/v3"

    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key":     self.config.get("api_key", ""),
            "Authorization": f"Bearer {self.config.get('access_token', '')}",
        }

    async def test_connection(self) -> Dict[str, Any]:
        if not self.config.get("api_key"):
            return {"ok": False, "message": "No API key configured"}
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.get(
                    f"{self.BASE_URL}/application/openapi-ping",
                    headers=self._headers(),
                )
                if r.status_code == 200:
                    return {"ok": True, "message": "Etsy API connection verified ✓"}
                return {"ok": False, "message": f"Etsy returned HTTP {r.status_code}"}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    async def create_draft_listing(self, listing: ListingOutput) -> Dict[str, Any]:
        shop_id = self.config.get("shop_id")
        if not shop_id:
            return {"ok": False, "error": "shop_id not configured"}
        payload = {
            "title":       listing.title[:140],
            "description": listing.description,
            "tags":        listing.tags[:13],
            "price":       listing.price or 0,
            "quantity":    999,
            "who_made":    "i_did",
            "when_made":   "made_to_order",
            "is_supply":   False,
            "state":       "draft",            # ← always draft first
        }
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                r = await client.post(
                    f"{self.BASE_URL}/application/shops/{shop_id}/listings",
                    headers={**self._headers(), "Content-Type": "application/json"},
                    json=payload,
                )
                return {"ok": r.status_code in (200, 201), "data": r.json()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def get_orders(self, limit: int = 50) -> List[Dict]:
        shop_id = self.config.get("shop_id")
        if not shop_id:
            return []
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                r = await client.get(
                    f"{self.BASE_URL}/application/shops/{shop_id}/receipts",
                    headers=self._headers(),
                    params={"limit": limit},
                )
                return r.json().get("results", [])
        except Exception as e:
            logger.error(f"[Etsy] get_orders failed: {e}")
            return []


# ── Shopify Adapter ────────────────────────────────────────────── #

class ShopifyAdapter(ChannelAdapter):
    channel_id        = "shopify"
    display_name      = "Shopify"
    icon              = "🛍️"
    description       = "Run your own branded online store via Shopify Admin API."
    supported_outputs = ["listing", "message"]

    API_VERSION = "2024-01"

    def _base(self) -> str:
        domain = self.config.get("store_domain", "")
        return f"https://{domain}/admin/api/{self.API_VERSION}"

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Shopify-Access-Token": self.config.get("access_token", ""),
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> Dict[str, Any]:
        if not self.config.get("access_token"):
            return {"ok": False, "message": "No access token configured"}
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.get(f"{self._base()}/shop.json", headers=self._headers())
                if r.status_code == 200:
                    name = r.json().get("shop", {}).get("name", "unknown")
                    return {"ok": True, "message": f"Connected to Shopify store: {name} ✓"}
                return {"ok": False, "message": f"Shopify returned HTTP {r.status_code}"}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    async def create_draft_listing(self, listing: ListingOutput) -> Dict[str, Any]:
        payload = {
            "product": {
                "title":      listing.title,
                "body_html":  listing.description,
                "tags":       ", ".join(listing.tags),
                "status":     "draft",
                "variants":   [{"price": str(listing.price or 0)}],
            }
        }
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                r = await client.post(
                    f"{self._base()}/products.json",
                    headers=self._headers(),
                    json=payload,
                )
                return {"ok": r.status_code in (200, 201), "data": r.json()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def get_orders(self, limit: int = 50) -> List[Dict]:
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                r = await client.get(
                    f"{self._base()}/orders.json",
                    headers=self._headers(),
                    params={"limit": limit, "status": "any"},
                )
                return r.json().get("orders", [])
        except Exception as e:
            logger.error(f"[Shopify] get_orders failed: {e}")
            return []


# ── Gumroad Adapter ────────────────────────────────────────────── #

class GumroadAdapter(ChannelAdapter):
    channel_id        = "gumroad"
    display_name      = "Gumroad"
    icon              = "📦"
    description       = "Sell digital products, downloads, and memberships instantly."
    supported_outputs = ["listing"]

    BASE_URL = "https://api.gumroad.com/v2"

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.config.get('access_token', '')}"}

    async def test_connection(self) -> Dict[str, Any]:
        if not self.config.get("access_token"):
            return {"ok": False, "message": "No access token configured"}
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.get(f"{self.BASE_URL}/user", headers=self._headers())
                if r.status_code == 200:
                    email = r.json().get("user", {}).get("email", "")
                    return {"ok": True, "message": f"Gumroad account: {email} ✓"}
                return {"ok": False, "message": f"Gumroad returned HTTP {r.status_code}"}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    async def create_draft_listing(self, listing: ListingOutput) -> Dict[str, Any]:
        payload = {
            "name":        listing.title,
            "description": listing.description,
            "price":       int((listing.price or 0) * 100),  # cents
            "published":   False,  # draft
        }
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                r = await client.post(
                    f"{self.BASE_URL}/products",
                    headers=self._headers(),
                    data=payload,
                )
                return {"ok": r.status_code == 200, "data": r.json()}
        except Exception as e:
            return {"ok": False, "error": str(e)}


# ── Amazon Adapter (stub — SP-API is complex) ──────────────────── #

class AmazonAdapter(ChannelAdapter):
    channel_id        = "amazon"
    display_name      = "Amazon"
    icon              = "📦"
    description       = "List products on Amazon marketplace via SP-API."
    supported_outputs = ["listing"]

    async def test_connection(self) -> Dict[str, Any]:
        if not self.config.get("refresh_token"):
            return {"ok": False, "message": "No refresh token configured"}
        return {
            "ok": False,
            "message": "Amazon SP-API integration coming soon — configure your credentials to be ready.",
        }

    async def create_draft_listing(self, listing: ListingOutput) -> Dict[str, Any]:
        return {"ok": False, "error": "Amazon SP-API integration is not yet implemented"}


# ── Generic Webhook Adapter ────────────────────────────────────── #

class GenericAdapter(ChannelAdapter):
    channel_id        = "generic"
    display_name      = "Custom Webhook"
    icon              = "🔗"
    description       = "Push agent outputs to any REST endpoint or custom service."
    supported_outputs = ["listing", "message", "research", "asset"]

    async def test_connection(self) -> Dict[str, Any]:
        url = self.config.get("endpoint_url")
        if not url:
            return {"ok": False, "message": "No endpoint URL configured"}
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.get(url)
                return {"ok": r.status_code < 400, "message": f"HTTP {r.status_code} ✓"}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    async def create_draft_listing(self, listing: ListingOutput) -> Dict[str, Any]:
        url = self.config.get("endpoint_url")
        if not url:
            return {"ok": False, "error": "No endpoint URL configured"}
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                r = await client.post(url, json=listing.dict())
                return {"ok": r.status_code < 400, "data": r.text}
        except Exception as e:
            return {"ok": False, "error": str(e)}


# ── Registry ───────────────────────────────────────────────────── #

CHANNEL_DEFINITIONS: Dict[str, type] = {
    "etsy":    EtsyAdapter,
    "shopify": ShopifyAdapter,
    "gumroad": GumroadAdapter,
    "amazon":  AmazonAdapter,
    "generic": GenericAdapter,
}


class ChannelRegistry:
    """
    Runtime registry for platform adapters.
    Config (credentials) is persisted to channels_config.json.
    Never put API keys in source code — they live only in the config file.
    """

    def __init__(self):
        self._configs:  Dict[str, Dict]          = {}
        self._adapters: Dict[str, ChannelAdapter] = {}
        self._load()

    # ── Persistence ─────────────────────────────────────── #

    def _load(self):
        if CONFIG_PATH.exists():
            try:
                self._configs = json.loads(CONFIG_PATH.read_text())
                logger.info(f"[ChannelRegistry] Loaded {len(self._configs)} channel configs")
            except Exception as e:
                logger.error(f"[ChannelRegistry] Config load failed: {e}")
                self._configs = {}
        for ch_id, cfg in self._configs.items():
            if ch_id in CHANNEL_DEFINITIONS:
                self._adapters[ch_id] = CHANNEL_DEFINITIONS[ch_id](cfg)

    def _save(self):
        try:
            CONFIG_PATH.write_text(json.dumps(self._configs, indent=2))
        except Exception as e:
            logger.error(f"[ChannelRegistry] Config save failed: {e}")

    # ── Public API ──────────────────────────────────────── #

    def list_channels(self) -> List[Dict]:
        result = []
        for ch_id, AdapterCls in CHANNEL_DEFINITIONS.items():
            cfg     = self._configs.get(ch_id, {})
            adapter = self._adapters.get(ch_id)
            dummy   = AdapterCls({})
            result.append({
                "id":           ch_id,
                "name":         dummy.display_name,
                "icon":         dummy.icon,
                "description":  dummy.description,
                "connected":    adapter.connected if adapter else False,
                "configured":   bool(cfg),
                "supported":    dummy.supported_outputs,
                "configured_at": cfg.get("configured_at"),
            })
        return result

    def get_adapter(self, channel_id: str) -> Optional[ChannelAdapter]:
        return self._adapters.get(channel_id)

    def get_connected(self) -> List[ChannelAdapter]:
        return [a for a in self._adapters.values() if a.connected]

    def configure_channel(self, channel_id: str, config: Dict[str, Any]):
        if channel_id not in CHANNEL_DEFINITIONS:
            raise ValueError(f"Unknown channel: {channel_id}")
        config["configured_at"] = datetime.utcnow().isoformat()
        self._configs[channel_id]  = config
        self._adapters[channel_id] = CHANNEL_DEFINITIONS[channel_id](config)
        self._save()
        logger.info(f"[ChannelRegistry] Configured: {channel_id}")

    def disconnect_channel(self, channel_id: str):
        self._configs.pop(channel_id, None)
        self._adapters.pop(channel_id, None)
        self._save()
        logger.info(f"[ChannelRegistry] Disconnected: {channel_id}")


# ── Singleton ──────────────────────────────────────────────────── #

_registry: Optional[ChannelRegistry] = None


def get_channel_registry() -> ChannelRegistry:
    global _registry
    if _registry is None:
        _registry = ChannelRegistry()
    return _registry
