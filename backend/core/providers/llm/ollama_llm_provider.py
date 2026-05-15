import os
from typing import List, Dict, AsyncGenerator
from core.interfaces.base_llm_provider import BaseLLMProvider


class OllamaLLMProvider(BaseLLMProvider):
    """Wraps Ollama local models. Free. No API key needed."""

    def __init__(self):
        super().__init__()
        self.name = "ollama"
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.base_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

    def initialize(self) -> bool:
        try:
            import requests
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    async def complete(self, messages, temperature=None, max_tokens=None) -> str:
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages, "stream": False},
                timeout=120
            )
            return r.json()["message"]["content"]

    async def embed(self, text: str) -> List[float]:
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text}
            )
            return r.json()["embedding"]

    async def stream(self, messages) -> AsyncGenerator[str, None]:
        import httpx
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages, "stream": True}
            ) as response:
                async for line in response.aiter_lines():
                    import json
                    data = json.loads(line)
                    if not data.get("done"):
                        yield data["message"]["content"]

    async def generate_image(self, prompt, size="1024x1024", quality="standard", n=1) -> List[str]:
        raise NotImplementedError("Ollama does not support image generation via this interface")

    async def health_check(self) -> bool:
        return self.initialize()
