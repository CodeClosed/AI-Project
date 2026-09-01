"""
Google Gemini Generative AI Client.
Implements direct Google Generative Language API HTTP communication with Gemini 3.7 Flash,
structured JSON schema decoding, multimodal base64 image parsing, exponential backoff,
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
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_TEMPERATURE,
    FALLBACK_GEMINI_MODELS,
)

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiAPIError(Exception):
    """Base exception for Gemini API communication failures."""
    pass


class GeminiAuthError(GeminiAPIError):
    """Raised when Gemini API key is missing, invalid, or unauthorized (HTTP 401/403)."""
    pass


class GeminiRateLimitError(GeminiAPIError):
    """Raised when encountering HTTP 429 rate limits or resource exhaustion."""
    pass


class GeminiModelNotFoundError(GeminiAPIError):
    """Raised when requested Gemini model is not found or unsupported (HTTP 404)."""
    pass


class GeminiTimeoutError(GeminiAPIError):
    """Raised when API request exceeds configured timeout duration."""
    pass


class GeminiResponseParsingError(GeminiAPIError):
    """Raised when API response does not contain valid structured JSON."""
    pass


class GeminiClient:
    """
    Resilient Google Gemini client communicating with Gemini 3.7 Flash
    via Google's REST API endpoint with retry backoff and fallback models.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        temperature: float = DEFAULT_TEMPERATURE,
        session: Optional[requests.Session] = None,
    ):
        self.api_key = get_gemini_api_key() if api_key is None else api_key
        self.model_name = get_gemini_model_name() if model_name is None else model_name
        self.timeout = timeout
        self.temperature = temperature
        self.session = session or requests.Session()

    def is_available(self) -> bool:
        """Returns True if a valid non-mock Gemini API key is present."""
        if not self.api_key:
            return False
        clean = self.api_key.strip()
        return len(clean) >= 10 and not clean.startswith("mock_")

    def _get_candidate_models(self) -> List[str]:
        """Returns ordered candidate models starting with primary (gemini-3.7-flash)."""
        candidates = [self.model_name]
        for m in FALLBACK_GEMINI_MODELS:
            if m not in candidates:
                candidates.append(m)
        return candidates

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
        Sends structured JSON prompt to Gemini 3.7 Flash and returns parsed dictionary.
        Supports multimodal image inputs.
        """
        if not self.is_available():
            raise GeminiAuthError("Gemini API key is missing or not configured.")

        temp = self.temperature if temperature is None else temperature
        req_timeout = self.timeout if timeout is None else timeout
        models_to_try = self._get_candidate_models()

        last_err: Optional[Exception] = None

        for model in models_to_try:
            url = f"{GEMINI_API_BASE}/{model}:generateContent?key={self.api_key}"

            # Construct Gemini parts
            parts: List[Dict[str, Any]] = []
            if image_b64:
                parts.append({
                    "inlineData": {
                        "mimeType": image_mime_type,
                        "data": image_b64,
                    }
                })
            parts.append({"text": prompt})

            payload: Dict[str, Any] = {
                "contents": [
                    {
                        "role": "user",
                        "parts": parts,
                    }
                ],
                "generationConfig": {
                    "temperature": temp,
                    "responseMimeType": "application/json",
                }
            }

            if system_instruction:
                payload["systemInstruction"] = {
                    "parts": [{"text": system_instruction}]
                }

            # Retry loop for transient issues
            for attempt in range(1, 4):
                try:
                    resp = self.session.post(
                        url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=req_timeout,
                    )

                    if resp.status_code == 200:
                        return self._parse_gemini_json_response(resp.json())

                    if resp.status_code in (401, 403):
                        raise GeminiAuthError(f"Gemini API authentication failed (HTTP {resp.status_code}): {resp.text}")

                    if resp.status_code == 404:
                        logger.warning("Gemini model '%s' not found (HTTP 404), trying next model.", model)
                        last_err = GeminiModelNotFoundError(f"Model '{model}' not found.")
                        break

                    if resp.status_code == 429:
                        last_err = GeminiRateLimitError(f"Gemini rate limit exceeded (HTTP 429): {resp.text}")
                        wait = 0.5 * attempt
                        logger.warning("Gemini rate limit (HTTP 429). Retrying in %.1fs...", wait)
                        time.sleep(wait)
                        continue

                    # Server error (5xx)
                    if 500 <= resp.status_code < 600:
                        last_err = GeminiAPIError(f"Gemini server error (HTTP {resp.status_code}): {resp.text}")
                        wait = 0.5 * attempt
                        logger.warning("Gemini server error %s. Retrying in %.1fs...", resp.status_code, wait)
                        time.sleep(wait)
                        continue

                    raise GeminiAPIError(f"Gemini API returned error {resp.status_code}: {resp.text}")

                except (requests.Timeout, requests.exceptions.ConnectTimeout) as e:
                    last_err = GeminiTimeoutError(f"Gemini API request timed out after {req_timeout}s.")
                    if attempt < 3:
                        time.sleep(1.0 * attempt)
                    continue
                except requests.RequestException as e:
                    last_err = GeminiAPIError(f"Gemini network request failed: {e}")
                    if attempt < 3:
                        time.sleep(1.0 * attempt)
                    continue

        if isinstance(last_err, GeminiAPIError):
            raise last_err
        raise GeminiAPIError("All Gemini model attempts failed.")

    def _parse_gemini_json_response(self, resp_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts and parses JSON string from Gemini generateContent response."""
        try:
            candidates = resp_data.get("candidates", [])
            if not candidates:
                raise GeminiResponseParsingError("Gemini response contained no candidates.")

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                raise GeminiResponseParsingError("Gemini candidate contained no content parts.")

            raw_text = parts[0].get("text", "").strip()
            if not raw_text:
                raise GeminiResponseParsingError("Gemini returned empty text response.")

            # Strip markdown fences if present
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()

            return json.loads(raw_text)
        except json.JSONDecodeError as e:
            raise GeminiResponseParsingError(f"Failed to parse JSON from Gemini response: {e}")
