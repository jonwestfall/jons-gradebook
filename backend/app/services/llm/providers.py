from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.db.models import LLMProvider


@dataclass
class LLMResponse:
    output_text: str


class BaseLLMProvider:
    def generate(self, prompt: str, model: str) -> LLMResponse:
        raise NotImplementedError


class OpenAIProvider(BaseLLMProvider):
    def __init__(self) -> None:
        from openai import OpenAI

        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        self.client = OpenAI(api_key=settings.openai_api_key)

    def generate(self, prompt: str, model: str) -> LLMResponse:
        response = self.client.responses.create(
            model=model,
            input=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        )
        return LLMResponse(output_text=response.output_text)


class GeminiProvider(BaseLLMProvider):
    def __init__(self) -> None:
        import google.generativeai as genai

        settings = get_settings()
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        genai.configure(api_key=settings.gemini_api_key)
        self.genai = genai

    def generate(self, prompt: str, model: str) -> LLMResponse:
        model_client = self.genai.GenerativeModel(model)
        response = model_client.generate_content(prompt)
        return LLMResponse(output_text=response.text or "")


class OllamaProvider(BaseLLMProvider):
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.ollama_base_url.rstrip("/")

    def generate(self, prompt: str, model: str) -> LLMResponse:
        payload = {"model": model, "prompt": prompt, "stream": False}
        response = httpx.post(f"{self.base_url}/api/generate", json=payload, timeout=120)
        response.raise_for_status()
        body = response.json()
        return LLMResponse(output_text=body.get("response", ""))


def provider_factory(provider: LLMProvider) -> BaseLLMProvider:
    if provider == LLMProvider.openai:
        return OpenAIProvider()
    if provider == LLMProvider.gemini:
        return GeminiProvider()
    if provider == LLMProvider.ollama:
        return OllamaProvider()
    raise ValueError(f"Unsupported provider: {provider}")
