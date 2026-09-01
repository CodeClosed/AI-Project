"""
OpenRouter Vision Menu Extractor for NutriMenu AI.

Provides modular vision-language menu digitization using the official OpenRouter API
(OpenAI-compatible /chat/completions endpoint), supporting open vision models
(e.g., meta-llama/llama-3.2-11b-vision-instruct:free, mistralai/pixtral-12b:free, etc.).

Strictly enforces food-only extraction, deterministic post-filtering, and returns
a fully compatible RecognizedMenu data object.
"""

from typing import List, Dict, Any, Optional, Union, Tuple
import os
import re
import json
import base64
import io
import logging
from pathlib import Path
import requests
import numpy as np
from PIL import Image
import cv2

from .config import (
    get_openrouter_api_key,
    get_openrouter_model_name,
    DEFAULT_OPENROUTER_MODEL,
    DEFAULT_OPENROUTER_BASE_URL,
    DEFAULT_TIMEOUT_SECONDS,
)
from .models import RecognizedMenu, MenuSection, MenuItem
from .noise_filter import is_valid_food_item, AdvancedNoiseFilter

logger = logging.getLogger(__name__)


class OpenRouterAPIError(Exception):
    """Base exception for OpenRouter API failures."""
    pass


class OpenRouterAuthError(OpenRouterAPIError):
    """Raised when OpenRouter API key is missing or unauthorized (HTTP 401 / 403)."""
    pass


class OpenRouterRateLimitError(OpenRouterAPIError):
    """Raised when rate limits or quotas are exceeded (HTTP 429)."""
    pass


class OpenRouterModelNotFoundError(OpenRouterAPIError):
    """Raised when the specified OpenRouter model is unavailable or unsupported (HTTP 404)."""
    pass


class OpenRouterTimeoutError(OpenRouterAPIError):
    """Raised when an OpenRouter API request times out."""
    pass


class OpenRouterResponseParsingError(OpenRouterAPIError):
    """Raised when OpenRouter returns malformed non-JSON responses."""
    pass


class OpenRouterMenuExtractor:
    """Extracts structured food dishes from menu images using OpenRouter Vision models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        allow_beverages: bool = False,
        session: Optional[requests.Session] = None,
    ):
        self.api_key = api_key if api_key is not None else get_openrouter_api_key()
        self.model_name = model_name or get_openrouter_model_name()
        self.base_url = base_url or DEFAULT_OPENROUTER_BASE_URL
        self.timeout = timeout
        self.allow_beverages = allow_beverages
        self.session = session or requests.Session()
        self.noise_filter = AdvancedNoiseFilter()

    def is_available(self) -> bool:
        """Returns True if a valid OpenRouter API key is configured."""
        return bool(self.api_key and self.api_key.strip() and not self.api_key.startswith("mock_") and len(self.api_key.strip()) >= 10)

    def _prepare_base64_image(self, image_input: Union[str, Path, np.ndarray, Image.Image, io.BytesIO, bytes]) -> Tuple[str, int, int]:
        """Converts diverse image input formats into a base64 JPEG string and returns (b64_str, width, height)."""
        if isinstance(image_input, Image.Image):
            pil_img = image_input.convert("RGB")
        elif isinstance(image_input, io.BytesIO):
            image_input.seek(0)
            pil_img = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, np.ndarray):
            if len(image_input.shape) == 2:
                rgb = cv2.cvtColor(image_input, cv2.COLOR_GRAY2RGB)
            elif image_input.shape[2] == 4:
                rgb = cv2.cvtColor(image_input, cv2.COLOR_BGRA2RGB)
            else:
                rgb = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
        elif isinstance(image_input, (bytes, bytearray)):
            pil_img = Image.open(io.BytesIO(image_input)).convert("RGB")
        elif isinstance(image_input, (str, Path)):
            pil_img = Image.open(str(image_input)).convert("RGB")
        else:
            raise TypeError(f"Unsupported image input type: {type(image_input)}")

        w, h = pil_img.size
        # Resize if very large for fast upload and model token efficiency
        if max(w, h) > 2000:
            scale = 2000.0 / max(w, h)
            pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        pil_img.save(buffer, format="JPEG", quality=90)
        b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return b64_str, w, h

    def _calculate_confidence(self, name: str, price: Optional[float], desc: Optional[str], section: Optional[str]) -> float:
        """Calibrates item extraction confidence."""
        score = 0.70
        if name and len(name) >= 3:
            score += 0.10
        if price is not None and 0.5 <= price <= 5000:
            score += 0.10
        if desc and len(desc) > 5:
            score += 0.05
        if section and section.lower() not in ("general", "other", "unknown"):
            score += 0.04
        return min(0.98, max(0.40, score))

    def _safe_parse_json(self, raw_text: str) -> Dict[str, Any]:
        """Safely parses JSON output from LLM, stripping markdown wrappers if present."""
        text = raw_text.strip()
        # Strip markdown ```json ... ``` wrappers if present
        if "```" in text:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if match:
                text = match.group(1).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Attempt regex extraction of the innermost JSON object
            obj_match = re.search(r"\{[\s\S]*\}", text)
            if obj_match:
                try:
                    return json.loads(obj_match.group(0))
                except Exception:
                    pass
            raise OpenRouterResponseParsingError(f"Failed to parse JSON response from OpenRouter: {e}")

    def extract_menu(self, image_input: Union[str, Path, np.ndarray, Image.Image, io.BytesIO, bytes]) -> RecognizedMenu:
        """
        Sends menu image to OpenRouter Vision API, parses the response, applies deterministic
        food filters, and returns a structured RecognizedMenu object.
        """
        if not self.is_available():
            raise OpenRouterAuthError(
                "OpenRouter API key is not configured. Set OPENROUTER_API_KEY in your .env file."
            )

        b64_img, img_w, img_h = self._prepare_base64_image(image_input)

        prompt = """
You are a STRICT FOOD ITEM EXTRACTION SYSTEM.

Your ONLY job is to identify actual FOOD DISHES visible in the provided menu image.

You must return ONLY food items that can reasonably be eaten as dishes, meals, snacks, desserts, bakery items, or food products.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL RULE: EXTRACT FOOD ONLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DO NOT return any text that is not an actual food item.

STRICTLY IGNORE:
- Restaurant names
- Restaurant branding
- Logo text
- Template placeholders
- Person names
- Location text
- Address text
- Phone numbers
- Email addresses
- Website URLs
- Social media handles
- Promotional text
- Marketing slogans
- "ORDER NOW" text
- Section headers
- Category names
- Menu headings
- "MAIN COURSE"
- "APPETIZERS"
- "STARTERS"
- "DESSERTS"
- "DRINKS"
- "BEVERAGES"
- "MENU"
- "FOOD MENU"
- "RESTAURANT NAME"
- "INSERT YOUR LOCATION HERE"
- "NAME"
- Prices
- Currency symbols
- Numbers that are not part of the food name
- Item descriptions that are not the food name
- Decorative text
- Random OCR artifacts
- Placeholder text
- Repeated headings

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DRINK FILTER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The final output should contain FOOD ONLY.

Unless explicitly configured otherwise, EXCLUDE:
- Coffee
- Tea
- Iced Tea
- Milk Shake
- Milkshake
- Juice
- Orange Juice
- Soft drinks
- Soda
- Cocktails
- Alcoholic beverages
- Water
- Any other beverage

Do not return beverages.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FOOD VALIDATION & ANTI-HALLUCINATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Extract ONLY text visibly supported by the image.
2. NEVER invent a food item.
3. NEVER autocomplete an incomplete food name.
4. NEVER use outside knowledge to guess what blurry text might mean.
5. NEVER convert a category name into a food item.
6. NEVER interpret restaurant branding as food.
7. If the text is unclear, omit it.
8. Precision is more important than completeness. When in doubt, omit the text.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY valid JSON with this exact structure:
{
  "food_items": [
    {
      "name": "Food Name"
    }
  ]
}

If no valid food items are found:
{
  "food_items": []
}
"""

        endpoint = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/nutrimenu-ai",
            "X-Title": "NutriMenu AI",
        }

        candidate_models = [self.model_name]
        for m in [
            "meta-llama/llama-3.2-11b-vision-instruct:free",
            "mistralai/pixtral-12b:free",
            "qwen/qwen-2.5-vl-72b-instruct:free",
        ]:
            if m not in candidate_models:
                candidate_models.append(m)

        parsed_json = None
        last_exception = None

        for model in candidate_models:
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{b64_img}"
                                }
                            }
                        ]
                    }
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
            }

            logger.info(f"[OPENROUTER] Sending vision extraction request to model '{model}'...")

            try:
                resp = self.session.post(endpoint, json=payload, headers=headers, timeout=self.timeout)
            except requests.exceptions.Timeout:
                last_exception = OpenRouterTimeoutError(f"Request to OpenRouter model '{model}' timed out after {self.timeout}s.")
                continue
            except requests.exceptions.RequestException as e:
                last_exception = OpenRouterAPIError(f"Network error connecting to OpenRouter API: {e}")
                continue

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if not choices:
                        last_exception = OpenRouterResponseParsingError("OpenRouter returned empty choices list.")
                        continue

                    raw_content = choices[0].get("message", {}).get("content", "")
                    if not raw_content:
                        last_exception = OpenRouterResponseParsingError("OpenRouter choice contained empty message content.")
                        continue

                    parsed_json = self._safe_parse_json(raw_content)
                    self.model_name = model
                    break
                except Exception as e:
                    if isinstance(e, OpenRouterAPIError):
                        last_exception = e
                    else:
                        last_exception = OpenRouterResponseParsingError(f"Error parsing response from OpenRouter ({model}): {e}")
                    continue

            elif resp.status_code in (401, 403):
                raise OpenRouterAuthError(f"Invalid or unauthorized OpenRouter API key (HTTP {resp.status_code}): {resp.text}")

            elif resp.status_code == 404:
                last_exception = OpenRouterModelNotFoundError(f"OpenRouter model '{model}' not found or unavailable (HTTP 404).")
                continue

            elif resp.status_code == 429:
                last_exception = OpenRouterRateLimitError(f"OpenRouter rate limit or credit quota exceeded for '{model}' (HTTP 429).")
                continue

            elif resp.status_code >= 500:
                last_exception = OpenRouterAPIError(f"OpenRouter server error (HTTP {resp.status_code}): {resp.text}")
                continue

            else:
                last_exception = OpenRouterAPIError(f"OpenRouter API error (HTTP {resp.status_code}): {resp.text}")
                continue

        if parsed_json is None:
            if last_exception:
                raise last_exception
            raise OpenRouterAPIError("Failed to extract menu using candidate OpenRouter vision models.")

        # Parse extracted items into standardized MenuItem objects
        parsed_items: List[Dict[str, Any]] = []

        if "food_items" in parsed_json:
            for it in parsed_json["food_items"]:
                if isinstance(it, dict) and "name" in it:
                    parsed_items.append(it)
                elif isinstance(it, str):
                    parsed_items.append({"name": it})
        elif "sections" in parsed_json:
            for sec in parsed_json["sections"]:
                cat = sec.get("category", "Main Dishes")
                for it in sec.get("items", []):
                    if isinstance(it, dict):
                        it["section"] = cat
                        parsed_items.append(it)

        # Apply deterministic Filter 1 (placeholders/metadata) and Filter 2 (food vs beverage/noise)
        valid_items: List[MenuItem] = []
        seen_items = set()

        for it_data in parsed_items:
            raw_name = str(it_data.get("name", "")).strip()
            if not raw_name:
                continue

            is_valid, reason = is_valid_food_item(raw_name, allow_beverages=self.allow_beverages)
            if not is_valid:
                logger.info(f"[OPENROUTER FILTER] Excluded non-food candidate '{raw_name}': {reason}")
                continue

            norm_key = raw_name.lower()
            if norm_key in seen_items:
                continue
            seen_items.add(norm_key)

            price_val = it_data.get("price")
            if price_val is not None:
                try:
                    price_val = float(price_val)
                except (ValueError, TypeError):
                    price_val = None

            raw_price = it_data.get("raw_price")
            currency = it_data.get("currency")
            desc = it_data.get("description")
            section = it_data.get("section", "Main Dishes")
            dietary = it_data.get("dietary_tags", []) or []

            conf = self._calculate_confidence(raw_name, price_val, desc, section)

            valid_items.append(
                MenuItem(
                    name=raw_name,
                    price=price_val,
                    raw_price=raw_price,
                    currency=currency,
                    description=desc,
                    section=section,
                    dietary_tags=dietary,
                    confidence=conf,
                )
            )

        logger.info(f"[OPENROUTER] Successfully extracted {len(valid_items)} verified food items.")

        sections = [MenuSection(title="Main Dishes", items=valid_items)] if valid_items else []
        image_path_str = str(image_input) if isinstance(image_input, (str, Path)) else "in_memory_image"
        return RecognizedMenu(
            image_path=image_path_str,
            image_width=img_w,
            image_height=img_h,
            num_columns=1,
            sections=sections,
            unclassified_items=[],
            raw_blocks=[],
            metadata={"extractor": "OpenRouter", "model": self.model_name},
        )
