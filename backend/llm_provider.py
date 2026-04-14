"""
Unified LLM Provider — Agent World
Supports: Ollama (local), OpenAI, Anthropic, and LiteLLM (100+ models)

Configure via environment variables:
  LLM_PROVIDER = ollama | openai | anthropic | litellm   (default: ollama)
  LLM_MODEL    = llama3.2 | gpt-4o | claude-3-5-sonnet-20241022
  LLM_API_KEY  = your-api-key (or "ollama" for local)
  LLM_BASE_URL = http://localhost:11434/v1  (Ollama only)

Ollama models with tool support: llama3.1, llama3.2, mistral-nemo, qwen2.5

LiteLLM provider (LLM_PROVIDER=litellm) unlocks 100+ models via one model string:
  ollama/llama3.2          → local Ollama
  gpt-4o                   → OpenAI
  claude-3-5-sonnet-20241022 → Anthropic
  groq/llama3-8b-8192      → Groq (fast + free tier)
  mistral/mistral-large    → Mistral AI
  bedrock/claude-3-sonnet  → AWS Bedrock
  ... and 90+ more
"""

import os
import json
from typing import List, Dict, Any, Optional

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
LLM_MODEL    = os.getenv("LLM_MODEL", "llama3.2")
LLM_API_KEY  = os.getenv("LLM_API_KEY", "ollama")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")


class LLMResponse:
    """Standardized response from any LLM provider."""
    def __init__(self, content: str, tool_calls: list = None, raw=None):
        self.content    = content or ""
        self.tool_calls = tool_calls or []
        self.raw        = raw


class LLMProvider:
    """
    Single interface over OpenAI, Anthropic, Ollama, and LiteLLM.
    Ollama uses the OpenAI-compatible REST interface so the same
    openai SDK works — just point it at the local URL.
    LiteLLM routes to any of 100+ providers via a unified interface.
    """

    def __init__(self):
        self.provider = LLM_PROVIDER
        self.model    = LLM_MODEL
        self._client  = None

    def _get_client(self):
        if self._client:
            return self._client

        if self.provider in ("openai", "ollama"):
            from openai import AsyncOpenAI
            if self.provider == "ollama":
                self._client = AsyncOpenAI(
                    api_key="ollama",
                    base_url=LLM_BASE_URL,
                )
            else:
                self._client = AsyncOpenAI(api_key=LLM_API_KEY)

        elif self.provider == "anthropic":
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=LLM_API_KEY)

        return self._client

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def complete(
        self,
        messages:    List[Dict],
        tools:       List[Dict] = None,
        temperature: float = 0.7,
        max_tokens:  int   = 2048,
    ) -> LLMResponse:
        """Route to the right provider and return a normalised response."""

        # LiteLLM — handles 100+ providers, no manual client needed
        if self.provider == "litellm":
            return await self._litellm_complete(messages, tools, temperature, max_tokens)

        client = self._get_client()

        if self.provider in ("openai", "ollama"):
            return await self._openai_complete(client, messages, tools, temperature, max_tokens)
        elif self.provider == "anthropic":
            return await self._anthropic_complete(client, messages, tools, temperature, max_tokens)
        else:
            raise ValueError(
                f"Unknown LLM_PROVIDER: {self.provider!r}. "
                f"Valid options: ollama | openai | anthropic | litellm"
            )

    async def complete_text(self, prompt: str, temperature: float = 0.3) -> str:
        """Simple single-turn text completion. Returns raw string."""
        resp = await self.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return resp.content

    # ------------------------------------------------------------------ #
    # Provider implementations                                            #
    # ------------------------------------------------------------------ #

    async def _openai_complete(self, client, messages, tools, temperature, max_tokens):
        kwargs: Dict[str, Any] = {
            "model":       self.model,
            "messages":    messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }
        if tools:
            kwargs["tools"]       = [{"type": "function", "function": t} for t in tools]
            kwargs["tool_choice"] = "auto"

        response = await client.chat.completions.create(**kwargs)
        msg = response.choices[0].message

        tool_calls = []
        if getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}
                tool_calls.append({
                    "id":        tc.id,
                    "name":      tc.function.name,
                    "arguments": args,
                })

        return LLMResponse(content=msg.content, tool_calls=tool_calls, raw=response)

    async def _anthropic_complete(self, client, messages, tools, temperature, max_tokens):
        # Anthropic uses a separate "system" param
        system   = ""
        filtered = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                filtered.append({"role": m["role"], "content": m["content"]})

        kwargs: Dict[str, Any] = {
            "model":       self.model,
            "messages":    filtered,
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = [
                {
                    "name":         t["name"],
                    "description":  t.get("description", ""),
                    "input_schema": t.get("parameters", {"type": "object", "properties": {}}),
                }
                for t in tools
            ]

        response = await client.messages.create(**kwargs)

        content    = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id":        block.id,
                    "name":      block.name,
                    "arguments": block.input,
                })

        return LLMResponse(content=content, tool_calls=tool_calls, raw=response)

    async def _litellm_complete(self, messages, tools, temperature, max_tokens):
        """
        LiteLLM provider — routes to any of 100+ LLM providers.
        The model string encodes both provider and model:
          ollama/llama3.2, gpt-4o, groq/llama3-8b-8192, etc.
        Env vars used: LLM_MODEL, LLM_API_KEY (optional per-provider).
        """
        try:
            import litellm
            litellm.drop_params = True   # ignore unsupported params safely
        except ImportError:
            raise ImportError(
                "litellm not installed. Run: pip install litellm"
            )

        # Set API key if provided (LiteLLM also reads standard env vars)
        if LLM_API_KEY and LLM_API_KEY not in ("ollama", "none", ""):
            import os
            # Map to the right env var LiteLLM expects
            model_lower = self.model.lower()
            if model_lower.startswith("gpt") or "openai" in model_lower:
                os.environ.setdefault("OPENAI_API_KEY", LLM_API_KEY)
            elif "claude" in model_lower or "anthropic" in model_lower:
                os.environ.setdefault("ANTHROPIC_API_KEY", LLM_API_KEY)
            elif "groq" in model_lower:
                os.environ.setdefault("GROQ_API_KEY", LLM_API_KEY)
            elif "mistral" in model_lower:
                os.environ.setdefault("MISTRAL_API_KEY", LLM_API_KEY)

        kwargs: Dict[str, Any] = {
            "model":       self.model,
            "messages":    messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }
        if tools:
            kwargs["tools"]       = [{"type": "function", "function": t} for t in tools]
            kwargs["tool_choice"] = "auto"

        response = await litellm.acompletion(**kwargs)
        msg = response.choices[0].message

        # Parse tool calls (LiteLLM normalises these to OpenAI format)
        tool_calls = []
        if getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}
                tool_calls.append({
                    "id":        tc.id,
                    "name":      tc.function.name,
                    "arguments": args,
                })

        return LLMResponse(content=msg.content or "", tool_calls=tool_calls, raw=response)


# ------------------------------------------------------------------ #
# Module-level singleton                                               #
# ------------------------------------------------------------------ #

_provider: Optional[LLMProvider] = None


def get_llm() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = LLMProvider()
    return _provider
