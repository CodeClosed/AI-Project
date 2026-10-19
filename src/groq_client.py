"""
Groq Ultra-Low-Latency Inference AI Client for NutriMenu AI.

Provides direct OpenAI-compatible API interaction with Groq's high-speed LPU infrastructure
(https://api.groq.com/openai/v1), supporting high-speed reasoning models (e.g. llama-3.3-70b-versatile,
llama-3.1-8b-instant) and vision models (llama-3.2-11b-vision-preview) with native JSON mode.
"""

import json
import logging
import re
import time
from typing import Dict, Any, Optional, Union, List
import requests

from .config import (
    get_groq_api_key,
    get_groq_model_name,
    DEFAULT_GROQ_MODEL,
    DEFAULT_GROQ_VISION_MODEL,
    DEFAULT_GROQ_BASE_URL,
    FALLBACK_GROQ_MODELS,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_TEMPERATURE,
)

logger = logging.getLogger(__name__)


class GroqAPIError(Exception):
    """Base exception for Groq API communication failures."""
    pass


class GroqAuthError(GroqAPIError):
    """Raised when Groq API key is missing, invalid, or unauthorized (HTTP 401/403)."""
    pass


class GroqRateLimitError(GroqAPIError):
    """Raised when encountering HTTP 429 rate limits or token quota exhaustion on Groq."""
    pass


class GroqModelNotFoundError(GroqAPIError):
    """Raised when requested Groq model is deprecated, not found, or unsupported (HTTP 404)."""
    pass


class GroqTimeoutError(GroqAPIError):
    """Raised when Groq API request exceeds configured timeout duration."""
    pass


class GroqResponseParsingError(GroqAPIError):
    """Raised when Groq response does not contain valid structured JSON."""
    pass


class GroqClient:
    """
    Ultra-low-latency Groq client executing OpenAI-compatible structured JSON generation
    with multimodal image support and automated fallback model resilience.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        vision_model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        temperature: float = DEFAULT_TEMPERATURE,
        session: Optional[requests.Session] = None,
    ):
        self.api_key = get_groq_api_key() if api_key is None else api_key
        self.model_name = get_groq_model_name() if model_name is None else model_name
        self.vision_model = vision_model or DEFAULT_GROQ_VISION_MODEL
        self.base_url = (base_url or DEFAULT_GROQ_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.temperature = temperature
        self.session = session or requests.Session()

    def is_available(self) -> bool:
        """Returns True if a valid non-mock Groq API key is configured."""
        if not self.api_key:
            return False
        clean = self.api_key.strip()
        return len(clean) >= 10 and not clean.startswith("mock_")

    def _get_candidate_models(self, has_image: bool = False) -> List[str]:
        """Returns ordered candidate models based on whether vision input is present."""
        if has_image:
            candidates = [self.vision_model, "llama-3.2-11b-vision-preview", "llama-3.2-90b-vision-preview"]
        else:
            candidates = [self.model_name]
            for m in FALLBACK_GROQ_MODELS:
                if m not in candidates:
                    candidates.append(m)
        # Deduplicate preserving order
        seen = set()
        return [c for c in candidates if not (c in seen or seen.add(c))]

    def _clean_json_text(self, text: str) -> str:
        """Strips markdown code fences and cleans raw JSON text."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            first_nl = cleaned.find("\n")
            if first_nl != -1:
                cleaned = cleaned[first_nl + 1:]
        if cleaned.endswith("```"):
            last_fence = cleaned.rfind("```")
            if last_fence != -1:
                cleaned = cleaned[:last_fence]
        return cleaned.strip()

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
        Generates structured JSON using Groq's high-speed inference API.
        Automatically selects vision model if image_b64 is provided.
        """
        if not self.is_available():
            raise GroqAuthError("Groq API key is not configured or invalid. Set GROQ_API_KEY in your environment.")

        temp = self.temperature if temperature is None else temperature
        req_timeout = self.timeout if timeout is None else timeout
        endpoint = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        has_image = bool(image_b64)
        candidates = self._get_candidate_models(has_image=has_image)

        # Assemble messages
        messages: List[Dict[str, Any]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})

        user_content: Union[str, List[Dict[str, Any]]]
        if has_image:
            user_content = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{image_mime_type};base64,{image_b64}"},
                },
            ]
        else:
            user_content = prompt

        messages.append({"role": "user", "content": user_content})

        last_error = None
        for model in candidates:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temp,
                "response_format": {"type": "json_object"},
            }

            try:
                resp = self.session.post(endpoint, json=payload, headers=headers, timeout=req_timeout)
            except requests.Timeout as e:
                logger.warning("[Groq] Model '%s' request timed out after %ss: %s", model, req_timeout, e)
                last_error = GroqTimeoutError(f"Groq request to '{model}' timed out after {req_timeout}s.")
                continue
            except requests.RequestException as e:
                logger.warning("[Groq] Network error connecting to Groq for model '%s': %s", model, e)
                last_error = GroqAPIError(f"Network error connecting to Groq API: {e}")
                continue

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if not choices:
                        raise GroqResponseParsingError("Groq returned empty choices list.")
                    message_obj = choices[0].get("message", {})
                    content = message_obj.get("content", "")
                    if not content or not content.strip():
                        raise GroqResponseParsingError("Groq returned empty content string.")

                    cleaned = self._clean_json_text(content)
                    return json.loads(cleaned)
                except json.JSONDecodeError as e:
                    logger.warning("[Groq] Model '%s' returned invalid JSON (%s): %s", model, e, resp.text[:200])
                    last_error = GroqResponseParsingError(f"Failed to parse JSON response from Groq: {e}")
                    continue
                except GroqResponseParsingError as e:
                    last_error = e
                    continue

            # Handle error status codes
            if resp.status_code in (401, 403):
                raise GroqAuthError(f"Groq authentication failed (HTTP {resp.status_code}): {resp.text}")

            if resp.status_code == 429:
                logger.warning("[Groq] Rate limit or TPM quota exceeded for model '%s'. Trying fallback.", model)
                last_error = GroqRateLimitError(f"Groq rate limit exceeded for '{model}' (HTTP 429).")
                continue

            if resp.status_code == 404:
                logger.warning("[Groq] Model '%s' not found (HTTP 404). Trying next fallback.", model)
                last_error = GroqModelNotFoundError(f"Groq model '{model}' not found (HTTP 404).")
                continue

            # Other 4xx / 5xx
            logger.warning("[Groq] Model '%s' failed with HTTP %s: %s", model, resp.status_code, resp.text[:200])
            last_error = GroqAPIError(f"Groq API error (HTTP {resp.status_code}): {resp.text}")

        if last_error:
            raise last_error

        raise GroqAPIError("Failed to generate JSON using candidate Groq models.")
