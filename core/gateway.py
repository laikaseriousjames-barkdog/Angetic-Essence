"""
AngeticGateway - Native LLM Routing Engine

Provides a clean abstraction layer over LLM providers with permanent agent personas."""

import os
import json
import httpx
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from core.system_prompts import get_persona, AGENT_PERSONAS
from core.llm import LLMClient


class LLMProvider(ABC):
    """Standard interface for all LLM backends."""

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Return the model's raw text response."""
        pass


class OpenRouterProvider(LLMProvider):
    """OpenRouter (OpenAI-compatible) provider."""

    def __init__(self, model: str, api_key: str, base_url: str = "https://openrouter.ai/api/v1") -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=120.0)

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 4096,
            "temperature": 0.7,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://agentzero.ai",
            "X-Title": "AgentZero",
            "Content-Type": "application/json",
        }
        resp = await self.client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


class AnthropicProvider(LLMProvider):
    """Anthropic Messages API provider."""

    def __init__(self, model: str, api_key: str, base_url: str = "https://api.anthropic.com") -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=120.0)

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "temperature": 0.7,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        resp = await self.client.post(f"{self.base_url}/v1/messages", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()


class LocalProvider(LLMProvider):
    """Local model gateway (Ollama-style API)."""

    def __init__(self, model: str, base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=120.0)

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        payload = {
            "model": self.model,
            "prompt": f"{system_prompt}\n\n{prompt}",
            "stream": False,
        }
        resp = await self.client.post(f"{self.base_url}/api/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()


class ProviderShim:
    """Wraps an LLMProvider with a permanent system persona for a specific agent."""

    def __init__(self, provider: LLMProvider, agent_name: str):
        self.provider = provider
        self.agent_name = agent_name
        self.persona = get_persona(agent_name)

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        # The permanent persona takes precedence; any additional system_prompt is appended
        full_system = f"{self.persona}\n\n{system_prompt}" if system_prompt else self.persona
        return await self.provider.generate(prompt, full_system)

    # Compatibility with old LLMClient interface used by agents
    async def complete_async(self, prompt: str, max_tokens: int = 4096, temperature: float = 0.7) -> str:
        return await self.generate(prompt)

    def complete(self, prompt: str, max_tokens: int = 4096, temperature: float = 0.7) -> str:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.complete_async(prompt, max_tokens, temperature))
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            return pool.submit(asyncio.run, self.complete_async(prompt, max_tokens, temperature)).result()


class GatewayRouter:
    """Factory that builds an LLMProvider (wrapped with persona) based on config.yaml."""

    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.mode = cfg.get("system_mode", "cost_efficient")
        self._validate_mode()

    def _validate_mode(self) -> None:
        if self.mode not in {"deep_mind", "cost_efficient", "hack_mode"}:
            raise ValueError(f"Unsupported system_mode: {self.mode}")

    def _load_key(self, env_name: str) -> str:
        key = os.getenv(env_name)
        if not key:
            raise RuntimeError(f"Missing required environment variable: {env_name}")
        return key

    def _provider_instance(self, provider_name: str, model: str) -> LLMProvider:
        if provider_name == "openrouter":
            api_key = self._load_key("OPENROUTER_API_KEY")
            return OpenRouterProvider(model=model, api_key=api_key)
        if provider_name == "anthropic":
            api_key = self._load_key("ANTHROPIC_API_KEY")
            return AnthropicProvider(model=model, api_key=api_key)
        if provider_name == "local":
            return LocalProvider(model=model)
        raise ValueError(f"Unsupported provider: {provider_name}")

    def get_provider_for_agent(self, agent_name: str) -> ProviderShim:
        """Return a ProviderShim for the given agent, with persona prepended."""
        llm_cfg = self.cfg.get("llm", {})
        provider = llm_cfg.get("provider", "openrouter")
        model = llm_cfg.get("model", "openrouter/free")

        if self.mode == "deep_mind":
            provider, model = "openrouter", "gpt-4o"
        elif self.mode == "cost_efficient":
            provider, model = "openrouter", "gpt-4o-mini"
        elif self.mode == "hack_mode":
            routing = self.cfg.get("agent_routing", {})
            custom = routing.get(agent_name, {})
            if custom:
                provider = custom.get("provider", provider)
                model = custom.get("model", model)

        base_provider = self._provider_instance(provider, model)
        return ProviderShim(base_provider, agent_name)

    async def test_agent(self, agent_name: str, prompt: str = "Explain quicksort in three sentences.") -> str:
        """Quick sanity test for an agent."""
        shim = self.get_provider_for_agent(agent_name)
        return await shim.generate(prompt)


# Global reference for live reload (set by main.py)
_gateway_router_ref: Optional[GatewayRouter] = None


def set_gateway_router_ref(router: GatewayRouter) -> None:
    global _gateway_router_ref
    _gateway_router_ref = router


def get_gateway_router() -> Optional[GatewayRouter]:
    return _gateway_router_ref


def reload_gateway_router(cfg: Dict[str, Any]) -> None:
    global _gateway_router_ref
    _gateway_router_ref = GatewayRouter(cfg)
