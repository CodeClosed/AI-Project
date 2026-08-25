"""
Gemini API Client Layer.
Handles HTTP communication, model resolution, JSON formatting, retries,
and robust error classification for Google Gemini models.
"""

from typing import Dict, Any, Optional, List, Union
import json
import logging
import requests

from .config import (
    get_gemini_api_key,
    get_gemini_model_name,
    get_candidate_models,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_TEMPERATURE,
)

logger = logging.getLogger(__name__)


class GeminiAPIError(Exception):
    """Base exception for Gemini API failures."""
    pass


class GeminiAuthError(GeminiAPIError):
    """Raised when API key is missing or invalid (HTTP 401 / 403)."""
    pass


class GeminiRateLimitError(GeminiAPIError):
    """Raised when API quota or rate limits are exceeded (HTTP 429)."""
    pass


class GeminiModelNotFoundError(GeminiAPIError):
    """Raised when the specified model does not exist or is unavailable (HTTP 404)."""
    pass


class GeminiTimeoutError(GeminiAPIError):
    """Raised when API request exceeds configured timeout."""
    pass


class GeminiResponseParsingError(GeminiAPIError):
    """Raised when Gemini returns malformed or non-JSON content."""
    pass


class GeminiClient:
    """
    Centralized client for communicating with Google Gemini Generative Language APIs.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        session: Optional[requests.Session] = None,
    ):
        self.api_key = api_key if api_key is not None else get_gemini_api_key()
        self.model_name = model_name or get_gemini_model_name()
        self.timeout = timeout
        self.session = session or requests.Session()

    def is_available(self) -> bool:
        """Returns True if a valid API key is present and configured."""
        return bool(self.api_key and self.api_key.strip() and not self.api_key.startswith("mock_"))

    def generate_json(
        self,
        prompt: str,
        image_b64: Optional[str] = None,
        image_mime_type: str = "image/jpeg",
        temperature: float = DEFAULT_TEMPERATURE,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sends a prompt (with optional image data) to Gemini requesting structured JSON output.
        
        Returns parsed dictionary or list wrapped in dict.
        Raises specific GeminiAPIError subclasses on failure.
        """
        if not self.is_available():
            raise GeminiAuthError(
                "Gemini API key is not configured. Set the GEMINI_API_KEY environment variable or Streamlit secrets."
            )

        # Build contents part payload
        parts: List[Dict[str, Any]] = []
        if image_b64:
            parts.append({
                "inlineData": {
                    "mimeType": image_mime_type,
                    "data": image_b64
                }
            })
        parts.append({"text": prompt})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": temperature,
            }
        }

        headers = {"Content-Type": "application/json"}
        candidate_models = get_candidate_models(model_name or self.model_name)

        last_exception: Optional[Exception] = None

        for model in candidate_models:
            url = f"{self.BASE_URL}/{model}:generateContent?key={self.api_key}"
            try:
                resp = self.session.post(url, json=payload, headers=headers, timeout=self.timeout)
            except requests.exceptions.Timeout as e:
                last_exception = GeminiTimeoutError(f"Request to model '{model}' timed out after {self.timeout}s.")
                continue
            except requests.exceptions.RequestException as e:
                last_exception = GeminiAPIError(f"Network error connecting to Gemini API ({model}): {e}")
                continue

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise GeminiResponseParsingError("Gemini returned empty response candidates.")

                    parts_content = candidates[0].get("content", {}).get("parts", [])
                    if not parts_content or "text" not in parts_content[0]:
                        raise GeminiResponseParsingError("Gemini candidate did not contain text content.")

                    raw_text = parts_content[0]["text"].strip()
                    parsed = json.loads(raw_text)
                    return parsed
                except json.JSONDecodeError as e:
                    last_exception = GeminiResponseParsingError(f"Failed to parse JSON returned by model '{model}': {e}")
                    continue
                except Exception as e:
                    last_exception = GeminiResponseParsingError(f"Error extracting response from '{model}': {e}")
                    continue

            elif resp.status_code in (401, 403):
                raise GeminiAuthError(f"Invalid or unauthorized Gemini API key (HTTP {resp.status_code}).")

            elif resp.status_code == 404:
                last_exception = GeminiModelNotFoundError(f"Model '{model}' not found or unsupported on this endpoint.")
                continue

            elif resp.status_code == 429:
                last_exception = GeminiRateLimitError(f"Gemini API rate limit or quota exceeded for '{model}' (HTTP 429).")
                continue

            elif resp.status_code >= 500:
                last_exception = GeminiAPIError(f"Gemini server error (HTTP {resp.status_code}): {resp.text}")
                continue

            else:
                last_exception = GeminiAPIError(f"Gemini API error (HTTP {resp.status_code}): {resp.text}")
                continue

        if last_exception:
            raise last_exception

        raise GeminiAPIError("Failed to generate content from any candidate Gemini model.")
