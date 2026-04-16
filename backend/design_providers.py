"""
design_providers.py — Agent World

Pluggable design generation system.
Multiple providers: DALL-E 3, Nano Banana, Stable Diffusion, Canva, etc.
Human chooses which provider for each design task.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
import asyncio


class DesignProviderType(str, Enum):
    """Available design generation providers"""
    DALLE_3 = "dalle_3"           # OpenAI - high quality, $0.04/image
    NANO_BANANA = "nano_banana"    # Nano Banana - fast, cheap
    STABLE_DIFFUSION = "stable_diffusion"  # Self-hosted, $0.001/image
    CANVA_API = "canva_api"        # Templates + PDF export
    MIDJOURNEY = "midjourney"      # Manual (no API yet)
    MOCKUP_GENERATOR = "mockup_generator"  # Placeit-style
    MANUAL_UPLOAD = "manual_upload"  # Human creates, system stores


@dataclass
class DesignRequest:
    """Request for design generation"""
    prompt: str
    design_type: Literal["thumbnail", "product_image", "mockup", "social_post", "pdf_template"]
    dimensions: tuple[int, int]  # width, height
    style: Optional[str] = None  # "minimalist", "vibrant", "professional", etc.
    brand_colors: Optional[List[str]] = None
    content_text: Optional[str] = None  # For PDFs/planners
    reference_images: Optional[List[str]] = None  # URLs for style reference
    num_variants: int = 1


@dataclass
class DesignResult:
    """Result from design generation"""
    provider: DesignProviderType
    image_urls: List[str]  # Generated image URLs
    metadata: Dict[str, Any]  # Provider-specific metadata
    cost_usd: float
    generation_time_ms: int
    quality_score: Optional[float] = None  # Provider's confidence
    edit_url: Optional[str] = None  # Link to edit in provider's tool


# ═══════════════════════════════════════════════════════════════════
# Provider Interface
# ═══════════════════════════════════════════════════════════════════

class DesignProvider(ABC):
    """Abstract base class for design providers"""
    
    provider_type: DesignProviderType
    display_name: str
    description: str
    supports_dimensions: List[tuple[int, int]]
    average_cost_per_image: float
    average_generation_time_seconds: int
    supports_text_in_image: bool  # Can reliably render text
    supports_pdf_export: bool
    
    @abstractmethod
    async def generate(self, request: DesignRequest) -> DesignResult:
        """Generate design based on request"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available"""
        pass
    
    def estimate_cost(self, request: DesignRequest) -> float:
        """Estimate cost for request"""
        return self.average_cost_per_image * request.num_variants


# ═══════════════════════════════════════════════════════════════════
# Provider Implementations
# ═══════════════════════════════════════════════════════════════════

class Dalle3Provider(DesignProvider):
    """OpenAI DALL-E 3 - Best quality, good text rendering"""
    
    provider_type = DesignProviderType.DALLE_3
    display_name = "DALL-E 3"
    description = "OpenAI's latest. Excellent quality, understands prompts well, decent text rendering. $0.04-0.08/image."
    supports_dimensions = [(1024, 1024), (1024, 1792), (1792, 1024)]
    average_cost_per_image = 0.06
    average_generation_time_seconds = 10
    supports_text_in_image = True  # Best text rendering
    supports_pdf_export = False
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._client = None
    
    async def health_check(self) -> bool:
        return self.api_key is not None
    
    async def generate(self, request: DesignRequest) -> DesignResult:
        """Generate using DALL-E 3"""
        import openai
        
        start_time = asyncio.get_event_loop().time()
        
        # Enhance prompt for better results
        enhanced_prompt = self._enhance_prompt(request)
        
        # Map dimensions to DALL-E sizes
        size = self._map_dimensions(request.dimensions)
        
        response = await openai.images.generate(
            model="dall-e-3",
            prompt=enhanced_prompt,
            size=size,
            quality="standard",
            n=request.num_variants
        )
        
        elapsed_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        return DesignResult(
            provider=self.provider_type,
            image_urls=[img.url for img in response.data],
            metadata={
                "revised_prompt": response.data[0].revised_prompt if response.data else None,
                "size": size,
                "model": "dall-e-3"
            },
            cost_usd=self.average_cost_per_image * request.num_variants,
            generation_time_ms=elapsed_ms
        )
    
    def _enhance_prompt(self, request: DesignRequest) -> str:
        """Add context to make DALL-E results better"""
        base = request.prompt
        
        # Add style modifiers
        style_modifiers = {
            "thumbnail": "professional product photography, clean background, commercial lighting",
            "product_image": "lifestyle product photo, professional lighting, shallow depth of field",
            "mockup": "realistic mockup, natural lighting, high quality print texture",
            "social_post": "social media graphic, bold typography, eye-catching"
        }
        
        modifier = style_modifiers.get(request.design_type, "professional design")
        
        return f"{base}. {modifier}. High quality, detailed, 8k resolution."
    
    def _map_dimensions(self, dims: tuple[int, int]) -> str:
        """Map requested dimensions to DALL-E supported sizes"""
        w, h = dims
        aspect = w / h
        
        if aspect > 1.5:
            return "1792x1024"  # Landscape
        elif aspect < 0.7:
            return "1024x1792"  # Portrait
        else:
            return "1024x1024"  # Square


class NanoBananaProvider(DesignProvider):
    """Nano Banana - Fast, cheap, good for volume"""
    
    provider_type = DesignProviderType.NANO_BANANA
    display_name = "Nano Banana"
    description = "Fast generation, lower cost than DALL-E. Good for rapid prototyping and volume. ~$0.01/image."
    supports_dimensions = [(512, 512), (768, 768), (1024, 1024)]
    average_cost_per_image = 0.01
    average_generation_time_seconds = 3
    supports_text_in_image = False  # Not reliable
    supports_pdf_export = False
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.nano-banana.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
    
    async def health_check(self) -> bool:
        # Would actually ping their API
        return self.api_key is not None
    
    async def generate(self, request: DesignRequest) -> DesignResult:
        """Generate using Nano Banana API"""
        import aiohttp
        
        start_time = asyncio.get_event_loop().time()
        
        payload = {
            "prompt": request.prompt,
            "width": request.dimensions[0],
            "height": request.dimensions[1],
            "num_images": request.num_variants,
            "style": request.style or "default"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/generate",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload
            ) as resp:
                data = await resp.json()
        
        elapsed_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        return DesignResult(
            provider=self.provider_type,
            image_urls=data.get("image_urls", []),
            metadata={
                "seed": data.get("seed"),
                "model_version": data.get("model_version")
            },
            cost_usd=self.average_cost_per_image * request.num_variants,
            generation_time_ms=elapsed_ms
        )


class StableDiffusionProvider(DesignProvider):
    """Self-hosted Stable Diffusion - Cheapest for high volume"""
    
    provider_type = DesignProviderType.STABLE_DIFFUSION
    display_name = "Stable Diffusion (Self-Hosted)"
    description = "Your own GPU server. $0.001/image at scale. Requires setup but cheapest long-term."
    supports_dimensions = [(512, 512), (768, 768), (1024, 1024), (1024, 1536)]
    average_cost_per_image = 0.001  # Just electricity
    average_generation_time_seconds = 5
    supports_text_in_image = False
    supports_pdf_export = False
    
    def __init__(self, endpoint_url: str, api_key: Optional[str] = None):
        self.endpoint_url = endpoint_url
        self.api_key = api_key
    
    async def health_check(self) -> bool:
        # Would ping the SD endpoint
        return True
    
    async def generate(self, request: DesignRequest) -> DesignResult:
        """Generate using local/self-hosted Stable Diffusion"""
        import aiohttp
        
        start_time = asyncio.get_event_loop().time()
        
        payload = {
            "prompt": request.prompt,
            "width": request.dimensions[0],
            "height": request.dimensions[1],
            "batch_size": request.num_variants,
            "steps": 30,
            "cfg_scale": 7.5
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.endpoint_url}/sdapi/v1/txt2img",
                json=payload
            ) as resp:
                data = await resp.json()
        
        elapsed_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        # Convert base64 to URLs (would upload to storage)
        image_urls = []  # Would process data["images"]
        
        return DesignResult(
            provider=self.provider_type,
            image_urls=image_urls,
            metadata={
                "model": "SDXL" or "SD 1.5",
                "steps": 30
            },
            cost_usd=self.average_cost_per_image * request.num_variants,
            generation_time_ms=elapsed_ms
        )


class CanvaProvider(DesignProvider):
    """Canva API - Best for PDFs, templates, structured designs"""
    
    provider_type = DesignProviderType.CANVA_API
    display_name = "Canva API"
    description = "Template-based design + PDF export. Perfect for planners, workbooks, structured layouts. Requires Canva Pro."
    supports_dimensions = [
        (1080, 1080),   # Instagram post
        (1080, 1920),   # Instagram story
        (1200, 630),    # Facebook/Twitter
        (2550, 3300),   # US Letter (PDF)
        (794, 1123),    # A4 (PDF)
    ]
    average_cost_per_image = 0.0  # Included in Canva Pro
    average_generation_time_seconds = 8
    supports_text_in_image = True  # Native text rendering
    supports_pdf_export = True  # KEY DIFFERENTIATOR
    
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token
    
    async def health_check(self) -> bool:
        return self.access_token is not None
    
    async def generate(self, request: DesignRequest) -> DesignResult:
        """Create design using Canva templates"""
        start_time = asyncio.get_event_loop().time()
        
        # Canva-specific logic would go here
        # 1. Find template by design_type
        # 2. Populate with content_text
        # 3. Apply brand_colors
        # 4. Export as PNG + PDF
        
        elapsed_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        return DesignResult(
            provider=self.provider_type,
            image_urls=["https://canva.com/design/.../preview.png"],
            metadata={
                "template_id": "template_123",
                "canva_edit_url": "https://canva.com/design/.../edit",
                "pdf_export_url": "https://canva.com/design/.../export/pdf",
                "supports_editing": True
            },
            cost_usd=0.0,
            generation_time_ms=elapsed_ms,
            edit_url="https://canva.com/design/.../edit"
        )


class ManualUploadProvider(DesignProvider):
    """Human creates design, uploads to system"""
    
    provider_type = DesignProviderType.MANUAL_UPLOAD
    display_name = "Manual Upload"
    description = "You create the design in your preferred tool (Photoshop, Figma, Canva manual), then upload. Most control, slowest."
    supports_dimensions = []  # Any dimensions
    average_cost_per_image = 0.0
    average_generation_time_seconds = 0
    supports_text_in_image = True
    supports_pdf_export = True
    
    async def health_check(self) -> bool:
        return True  # Always available
    
    async def generate(self, request: DesignRequest) -> DesignResult:
        """Returns placeholder - human will upload"""
        return DesignResult(
            provider=self.provider_type,
            image_urls=[],  # Empty - waiting for upload
            metadata={
                "status": "awaiting_upload",
                "upload_url": "/api/v1/assets/upload",
                "requested_dimensions": request.dimensions,
                "instructions": f"Please create: {request.design_type}. Prompt: {request.prompt}"
            },
            cost_usd=0.0,
            generation_time_ms=0
        )


# ═══════════════════════════════════════════════════════════════════
# Provider Registry & Selector
# ═══════════════════════════════════════════════════════════════════

class DesignProviderRegistry:
    """Registry of available design providers"""
    
    def __init__(self):
        self._providers: Dict[DesignProviderType, DesignProvider] = {}
        self._default_provider: Optional[DesignProviderType] = None
    
    def register(self, provider: DesignProvider, is_default: bool = False):
        """Register a provider"""
        self._providers[provider.provider_type] = provider
        if is_default:
            self._default_provider = provider.provider_type
    
    def get(self, provider_type: DesignProviderType) -> Optional[DesignProvider]:
        """Get provider by type"""
        return self._providers.get(provider_type)
    
    def get_default(self) -> Optional[DesignProvider]:
        """Get default provider"""
        if self._default_provider:
            return self._providers.get(self._default_provider)
        return None
    
    def list_available(self) -> List[Dict[str, Any]]:
        """List all registered providers with metadata"""
        return [
            {
                "type": p.provider_type.value,
                "display_name": p.display_name,
                "description": p.description,
                "cost_per_image": p.average_cost_per_image,
                "generation_time_seconds": p.average_generation_time_seconds,
                "supports_text": p.supports_text_in_image,
                "supports_pdf": p.supports_pdf_export,
                "is_default": p.provider_type == self._default_provider,
                "is_healthy": asyncio.run(p.health_check()) if asyncio.get_event_loop().is_running() else None
            }
            for p in self._providers.values()
        ]
    
    def recommend_for_task(self, request: DesignRequest) -> List[DesignProviderType]:
        """Recommend providers for a specific task"""
        recommendations = []
        
        # PDF/planner needed? → Canva
        if request.design_type == "pdf_template":
            recommendations.append(DesignProviderType.CANVA_API)
        
        # Has text that must be legible? → DALL-E 3 or Canva
        if request.content_text:
            recommendations.append(DesignProviderType.DALLE_3)
            recommendations.append(DesignProviderType.CANVA_API)
        
        # Fast/cheap bulk? → Nano Banana
        if request.num_variants > 5:
            recommendations.append(DesignProviderType.NANO_BANANA)
            recommendations.append(DesignProviderType.STABLE_DIFFUSION)
        
        # Fallback
        recommendations.append(DesignProviderType.MANUAL_UPLOAD)
        
        return list(dict.fromkeys(recommendations))  # Remove duplicates, preserve order


# ═══════════════════════════════════════════════════════════════════
# Design Service (Main Interface)
# ═══════════════════════════════════════════════════════════════════

class DesignService:
    """Main service for design generation with provider selection"""
    
    def __init__(self, registry: DesignProviderRegistry):
        self.registry = registry
    
    async def generate(
        self,
        request: DesignRequest,
        provider_type: Optional[DesignProviderType] = None,
        allow_fallback: bool = True
    ) -> DesignResult:
        """
        Generate design using specified or recommended provider.
        
        Args:
            request: Design requirements
            provider_type: Specific provider to use (or None for auto-select)
            allow_fallback: If specified provider fails, try alternatives
        
        Returns:
            DesignResult with generated images
        """
        
        # Determine provider
        if provider_type is None:
            recommendations = self.registry.recommend_for_task(request)
            provider_type = recommendations[0]
        
        provider = self.registry.get(provider_type)
        
        if not provider:
            raise ValueError(f"Provider {provider_type} not found")
        
        # Check health
        if not await provider.health_check():
            if not allow_fallback:
                raise RuntimeError(f"Provider {provider_type} not available")
            
            # Try fallbacks
            for fallback_type in self.registry.recommend_for_task(request):
                if fallback_type == provider_type:
                    continue
                fallback = self.registry.get(fallback_type)
                if fallback and await fallback.health_check():
                    provider = fallback
                    provider_type = fallback_type
                    break
            else:
                # Last resort: manual upload
                provider = self.registry.get(DesignProviderType.MANUAL_UPLOAD)
                provider_type = DesignProviderType.MANUAL_UPLOAD
        
        # Generate
        result = await provider.generate(request)
        
        # Add provider metadata
        result.metadata["requested_provider"] = provider_type.value
        result.metadata["available_providers"] = [p.value for p in self.registry.recommend_for_task(request)]
        
        return result
    
    async def generate_with_preview(
        self,
        request: DesignRequest,
        provider_type: DesignProviderType
    ) -> Dict[str, Any]:
        """
        Generate low-res preview first, then human approves full generation.
        
        Returns preview with cost estimate for approval.
        """
        # Create preview request (lower cost)
        preview_request = DesignRequest(
            prompt=f"{request.prompt}. (Preview quality, draft mode)",
            design_type=request.design_type,
            dimensions=(512, 512),  # Smaller = faster/cheaper
            style=request.style,
            num_variants=1  # Just one for preview
        )
        
        preview_result = await self.generate(preview_request, provider_type)
        
        # Estimate full cost
        provider = self.registry.get(provider_type)
        full_cost = provider.estimate_cost(request) if provider else 0.0
        
        return {
            "preview": preview_result,
            "full_request": request,
            "estimated_cost_usd": full_cost,
            "provider": provider_type.value,
            "approval_required": True  # Always require approval for full
        }


# ═══════════════════════════════════════════════════════════════════
# FastAPI Integration
# ═══════════════════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/design", tags=["design"])


class GenerateRequest(BaseModel):
    prompt: str
    design_type: str = "thumbnail"
    width: int = 1024
    height: int = 1024
    style: Optional[str] = None
    brand_colors: Optional[List[str]] = None
    content_text: Optional[str] = None
    num_variants: int = 1
    preferred_provider: Optional[str] = None  # "dalle_3", "nano_banana", etc.


class ProviderOption(BaseModel):
    type: str
    display_name: str
    description: str
    cost_per_image: float
    generation_time_seconds: int
    supports_text: bool
    supports_pdf: bool
    recommended: bool


# Global service instance (initialized in main.py)
design_service: Optional[DesignService] = None


def initialize_design_service(service: DesignService):
    """Called by main.py to set the service instance"""
    global design_service
    design_service = service


@router.get("/providers", response_model=List[ProviderOption])
async def list_providers(design_type: Optional[str] = None):
    """List available design providers with recommendations"""
    if not design_service:
        raise HTTPException(status_code=503, detail="Design service not initialized")
    
    all_providers = design_service.registry.list_available()
    
    # If design_type provided, mark recommendations
    if design_type:
        request = DesignRequest(
            prompt="dummy",
            design_type=design_type,
            dimensions=(1024, 1024)
        )
        recommendations = design_service.registry.recommend_for_task(request)
        rec_types = [r.value for r in recommendations]
        
        for provider in all_providers:
            provider["recommended"] = provider["type"] in rec_types
    
    return all_providers


@router.post("/generate")
async def generate_design(request: GenerateRequest):
    """Generate design with specified or auto-selected provider"""
    if not design_service:
        raise HTTPException(status_code=503, detail="Design service not initialized")
    
    design_request = DesignRequest(
        prompt=request.prompt,
        design_type=request.design_type,
        dimensions=(request.width, request.height),
        style=request.style,
        brand_colors=request.brand_colors,
        content_text=request.content_text,
        num_variants=request.num_variants
    )
    
    # Parse preferred provider
    provider_type = None
    if request.preferred_provider:
        try:
            provider_type = DesignProviderType(request.preferred_provider)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {request.preferred_provider}")
    
    # Generate with preview mode if human approval needed
    if provider_type:
        result = await design_service.generate_with_preview(design_request, provider_type)
        return {
            "status": "preview_generated",
            "preview_image_url": result["preview"].image_urls[0] if result["preview"].image_urls else None,
            "estimated_cost_usd": result["estimated_cost_usd"],
            "provider": result["provider"],
            "next_step": "POST /design/generate/approve to generate full variants"
        }
    else:
        # Auto-select and generate immediately
        result = await design_service.generate(design_request)
        return {
            "status": "generated",
            "image_urls": result.image_urls,
            "provider": result.provider.value,
            "cost_usd": result.cost_usd,
            "generation_time_ms": result.generation_time_ms,
            "metadata": result.metadata
        }


@router.post("/generate/approve")
async def approve_full_generation(
    preview_token: str,
    approve: bool = True,
    selected_provider: Optional[str] = None
):
    """Approve full generation after preview"""
    if not design_service:
        raise HTTPException(status_code=503, detail="Design service not initialized")
    
    if not approve:
        return {"status": "cancelled", "message": "Generation cancelled by user"}
    
    # Would retrieve stored preview request and generate full
    # For now, placeholder
    return {
        "status": "generating",
        "message": "Full generation in progress",
        "provider": selected_provider
    }


# ═══════════════════════════════════════════════════════════════════
# Example Setup (for main.py)
# ═══════════════════════════════════════════════════════════════════

def create_design_service_with_all_providers(
    openai_key: Optional[str] = None,
    nano_banana_key: Optional[str] = None,
    sd_endpoint: Optional[str] = None,
    canva_token: Optional[str] = None
) -> DesignService:
    """Create service with all available providers"""
    
    registry = DesignProviderRegistry()
    
    # Register providers based on available API keys
    if openai_key:
        registry.register(Dalle3Provider(api_key=openai_key), is_default=True)
    
    if nano_banana_key:
        registry.register(NanoBananaProvider(api_key=nano_banana_key))
    
    if sd_endpoint:
        registry.register(StableDiffusionProvider(endpoint_url=sd_endpoint))
    
    if canva_token:
        registry.register(CanvaProvider(access_token=canva_token))
    
    # Always have manual fallback
    registry.register(ManualUploadProvider())
    
    return DesignService(registry)


__all__ = [
    'DesignProvider',
    'DesignProviderType',
    'DesignRequest',
    'DesignResult',
    'Dalle3Provider',
    'NanoBananaProvider',
    'StableDiffusionProvider',
    'CanvaProvider',
    'ManualUploadProvider',
    'DesignProviderRegistry',
    'DesignService',
    'router',
    'initialize_design_service',
    'create_design_service_with_all_providers'
]