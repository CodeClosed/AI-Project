"""
Unified Vision & Language AI Client.
Supports Google Gemini (including Gemini 3.7 Flash) as well as OpenAI/OpenRouter providers,
structured JSON schema output, base64 image parsing, exponential backoff,
and typed error classification.
"""

import json
import logging
import time
from typing import Dict, Any, Optional, Union, List
import requests

from .config import (
    get_gemini_api_key,
    get_gemini_model_name,
    is_gemini_available,
    get_groq_api_key,
    get_groq_model_name,
    is_groq_available,
    get_openrouter_api_key,
    get_openrouter_model_name,
    get_active_ai_provider,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_TEMPERATURE,
    FALLBACK_GEMINI_MODELS,
    FALLBACK_GROQ_MODELS,
    FALLBACK_OPENROUTER_MODELS,
)
from .gemini_client import (
    GeminiClient,
    GeminiAPIError,
    GeminiAuthError,
    GeminiRateLimitError,
    GeminiModelNotFoundError,
    GeminiTimeoutError,
    GeminiResponseParsingError,
)
from .groq_client import (
    GroqClient,
    GroqAPIError,
    GroqAuthError,
    GroqRateLimitError,
    GroqModelNotFoundError,
    GroqTimeoutError,
    GroqResponseParsingError,
)

logger = logging.getLogger(__name__)

# Base exception hierarchy for unified AI operations
AIClientError = GeminiAPIError
AIAuthError = GeminiAuthError
AIRateLimitError = GeminiRateLimitError
AIModelNotFoundError = GeminiModelNotFoundError
AITimeoutError = GeminiTimeoutError
AIResponseParsingError = GeminiResponseParsingError


class AIClient:
    """
    Unified AI client supporting both native Google Gemini (defaulting to Gemini 3.7 Flash)
    and OpenAI-compatible OpenRouter APIs.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        temperature: float = DEFAULT_TEMPERATURE,
        session: Optional[requests.Session] = None,
    ):
        self.raw_api_key = api_key
        self.raw_model = model_name
        self.timeout = timeout
        self.temperature = temperature
        self.session = session or requests.Session()

        # Check if Gemini is primary
        gemini_key = api_key or get_gemini_api_key()
        gemini_model = model_name or get_gemini_model_name()

        self.gemini_client = GeminiClient(
            api_key=gemini_key,
            model_name=gemini_model,
            timeout=timeout,
            temperature=temperature,
            session=self.session,
        )

        # Groq client attributes
        groq_key = api_key or get_groq_api_key()
        groq_model = model_name or get_groq_model_name()
        self.groq_client = GroqClient(
            api_key=groq_key,
            model_name=groq_model,
            timeout=timeout,
            temperature=temperature,
            session=self.session,
        )

        # OpenRouter client attributes
        self.openrouter_key = api_key or get_openrouter_api_key()
        self.openrouter_model = model_name or get_openrouter_model_name()
        self.base_url = (base_url or "https://openrouter.ai/api/v1").rstrip("/")

        active_provider = get_active_ai_provider()
        if active_provider == "groq":
            self.model_name = groq_model
        elif active_provider == "gemini":
            self.model_name = gemini_model
        elif active_provider == "openrouter":
            self.model_name = self.openrouter_model
        else:
            self.model_name = gemini_model

    def is_available(self) -> bool:
        """Returns True if Gemini, Groq, or OpenRouter is configured with a valid key."""
        return (
            self.gemini_client.is_available()
            or self.groq_client.is_available()
            or bool(self.openrouter_key and len(self.openrouter_key.strip()) >= 10 and not self.openrouter_key.startswith("mock_"))
        )

    def generate_json(
        self,
        prompt: str,
        image_b64: Optional[str] = None,
        image_mime_type: str = "image/jpeg",
        temperature: Optional[float] = None,
        timeout: Optional[int] = None,
        system_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes structured JSON generation with provider preference:
        Respects active provider setting (Groq vs Gemini) with automatic resilient fallback.
        """
        active_provider = get_active_ai_provider()
        raw_model_lower = (self.raw_model or "").lower()

        # Priority 1: Groq if explicitly chosen, if model indicates groq/llama/mixtral, or active provider is groq
        prefer_groq = (
            active_provider == "groq"
            or any(kw in raw_model_lower for kw in ["groq", "llama", "mixtral"])
        )

        if prefer_groq and self.groq_client.is_available():
            try:
                return self.groq_client.generate_json(
                    prompt=prompt,
                    image_b64=image_b64,
                    image_mime_type=image_mime_type,
                    temperature=temperature,
                    timeout=timeout,
                    system_instruction=system_instruction,
                )
            except Exception as e:
                logger.warning("[AIClient] Groq execution failed (%s), attempting Gemini / OpenRouter fallback.", e)

        # Priority 2: Gemini
        if self.gemini_client.is_available() or ("gemini" in raw_model_lower):
            try:
                return self.gemini_client.generate_json(
                    prompt=prompt,
                    image_b64=image_b64,
                    image_mime_type=image_mime_type,
                    temperature=temperature,
                    timeout=timeout,
                    system_instruction=system_instruction,
                )
            except Exception as e:
                logger.warning("[AIClient] Gemini execution failed (%s), attempting Groq / OpenRouter fallback.", e)

        # Priority 3: Groq (if not already tried as Priority 1)
        if not prefer_groq and self.groq_client.is_available():
            try:
                return self.groq_client.generate_json(
                    prompt=prompt,
                    image_b64=image_b64,
                    image_mime_type=image_mime_type,
                    temperature=temperature,
                    timeout=timeout,
                    system_instruction=system_instruction,
                )
            except Exception as e:
                logger.warning("[AIClient] Groq fallback failed (%s), attempting OpenRouter.", e)

        # Priority 4: OpenRouter fallback
        if self.openrouter_key and len(self.openrouter_key.strip()) >= 10:
            return self._generate_openrouter_json(
                prompt=prompt,
                image_b64=image_b64,
                image_mime_type=image_mime_type,
                temperature=temperature,
                timeout=timeout,
                system_instruction=system_instruction,
            )

        raise AIAuthError("No valid Gemini, Groq, or OpenRouter API key configured.")

    def _generate_openrouter_json(
        self,
        prompt: str,
        image_b64: Optional[str] = None,
        image_mime_type: str = "image/jpeg",
        temperature: Optional[float] = None,
        timeout: Optional[int] = None,
        system_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes OpenRouter / OpenAI chat completions request."""
        temp = self.temperature if temperature is None else temperature
        req_timeout = self.timeout if timeout is None else timeout
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/CodeClosed/AI-Project",
            "X-Title": "NutriMenu-AI",
        }

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})

        user_content: Union[str, List[Dict[str, Any]]] = prompt
        if image_b64:
            user_content = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{image_mime_type};base64,{image_b64}"},
                },
            ]
        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": self.openrouter_model,
            "messages": messages,
            "temperature": temp,
            "response_format": {"type": "json_object"},
        }

        resp = self.session.post(url, json=payload, headers=headers, timeout=req_timeout)
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)

        if resp.status_code in (401, 403):
            raise AIAuthError(f"Authentication failed: {resp.text}")
        if resp.status_code == 404:
            raise AIModelNotFoundError(f"Model not found: {resp.text}")
        if resp.status_code == 429:
            raise AIRateLimitError(f"Rate limited: {resp.text}")
        raise AIClientError(f"API error ({resp.status_code}): {resp.text}")
