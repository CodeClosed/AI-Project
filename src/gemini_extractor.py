"""
Intelligent Menu Extractor powered by Google Gemini Flash Vision API.
Provides zero-shot semantic understanding, automatic OCR typo correction,
and structured menu hierarchy extraction.
"""

from typing import List, Dict, Any, Optional, Union, Tuple
import os
import re
import json
import base64
import io
from pathlib import Path
import requests
import numpy as np
from PIL import Image
import cv2

from .models import RecognizedMenu, MenuSection, MenuItem, BoundingBox


class GeminiMenuExtractor:
    """Extracts structured menu items, categories, and prices using Google Gemini Flash."""

    # Models prioritized by availability and speed
    CANDIDATE_MODELS = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-3.7-flash",
    ]


    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or self._load_api_key()
        self.model_name = model_name or "gemini-3.6-flash"


    def _load_api_key(self) -> Optional[str]:
        """Loads API key from environment variable or .env file."""
        if "GEMINI_API_KEY" in os.environ and os.environ["GEMINI_API_KEY"].strip():
            return os.environ["GEMINI_API_KEY"].strip()

        current = Path.cwd()
        for path in [current / ".env", current.parent / ".env", Path(__file__).resolve().parent.parent / ".env"]:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("GEMINI_API_KEY=") and not line.startswith("#"):
                                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                                if key:
                                    os.environ["GEMINI_API_KEY"] = key
                                    return key
                except Exception:
                    pass
        return None

    def is_available(self) -> bool:
        """Returns True if a valid Gemini API key is configured."""
        return bool(self.api_key and self.api_key.strip())

    def _prepare_base64_image(self, image_input: Union[str, np.ndarray, Image.Image]) -> Tuple[str, int, int]:
        """Converts image input to base64 JPEG string and returns (b64_string, width, height)."""
        if isinstance(image_input, Image.Image):
            pil_img = image_input.convert("RGB")
        elif isinstance(image_input, np.ndarray):
            if len(image_input.shape) == 2:
                rgb = cv2.cvtColor(image_input, cv2.COLOR_GRAY2RGB)
            elif image_input.shape[2] == 4:
                rgb = cv2.cvtColor(image_input, cv2.COLOR_BGRA2RGB)
            else:
                rgb = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
        elif isinstance(image_input, (str, Path)):
            pil_img = Image.open(str(image_input)).convert("RGB")
        else:
            raise TypeError(f"Unsupported image input type: {type(image_input)}")

        w, h = pil_img.size
        # Resize if huge to speed up upload
        if max(w, h) > 2000:
            scale = 2000.0 / max(w, h)
            pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        pil_img.save(buffer, format="JPEG", quality=90)
        b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return b64_str, w, h

    def extract_menu(self, image_input: Union[str, np.ndarray, Image.Image]) -> RecognizedMenu:
        """
        Processes a restaurant menu image with Gemini Flash and returns a structured RecognizedMenu object.
        """
        if not self.is_available():
            raise ValueError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in your .env file or pass --api-key."
            )

        b64_img, img_w, img_h = self._prepare_base64_image(image_input)

        prompt = """
You are an expert culinary AI specializing in restaurant menu digitization.
Analyze this menu image and extract ALL genuine food and beverage dishes with complete accuracy.

CRITICAL EXTRACTION RULES:
1. Extract ALL REAL food & beverage dishes (starters, burgers, pizzas, rolls, sandwiches, mains, combos, sides, desserts, drinks).
2. Group items into their proper section categories (e.g. Fries, Burgers, Rolls, Sandwiches, Chinese, Noodles, Appetizers, Entrées, Pasta, Dinner Specials, Combos, Desserts, Beverages).
3. If an item name has stylized/misrecognized characters or OCR typos in the image (e.g. 'Sniley's' -> 'Smiley's', 'Hasala French Fries' -> 'Masala French Fries', 'Panner' -> 'Paneer', 'Ohicken' -> 'Chicken', 'Mloo' -> 'Aloo', 'Kadurai' -> 'Madurai'), fix and return the CORRECT culinary spelling.
4. Distinguish category headers from dish names (e.g., 'Burger', 'Sandwich', 'Roll', 'Fries', 'Bun', 'Appetizers', 'Entrées', 'Dinner Specials' are section categories, NOT food items).
5. If an item has an add-on or customization note (e.g. '(with cheese additional Rs 10)'), attach it to the item's 'description' field.
6. For combo meals (e.g. 'Chicken Burger Combo' with 'Burger, Fries and spl lemon juice'), set 'name' to the combo title and 'description' to the inclusions.
7. Exclude all non-food noise (restaurant branding, slogans, logos, table numbers, phone numbers, addresses, GST/tax notices, opening hours, footer text).

Return ONLY valid JSON with this exact structure:
{
  "sections": [
    {
      "category": "Category Title",
      "items": [
        {
          "name": "Exact Correct Food Name",
          "price": 60.0,
          "raw_price": "Rs 60",
          "currency": "Rs",
          "description": "Optional description or add-on details",
          "dietary_tags": ["Vegetarian", "Spicy"]
        }
      ]
    }
  ]
}
"""

        payload = {
            "contents": [{
                "parts": [
                    {"inlineData": {"mimeType": "image/jpeg", "data": b64_img}},
                    {"text": prompt}
                ]
            }],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1
            }
        }

        headers = {"Content-Type": "application/json"}
        models_to_try = [self.model_name] if self.model_name else self.CANDIDATE_MODELS
        
        last_error = None
        response_json = None

        for model in models_to_try:
            if not model:
                continue
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=25)
                if resp.status_code == 200:
                    result = resp.json()
                    candidates = result.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {}).get("parts", [])
                        if content and "text" in content[0]:
                            response_json = json.loads(content[0]["text"])
                            break
                elif resp.status_code == 404:
                    last_error = f"Model '{model}' not found on endpoint."
                    continue
                else:
                    last_error = f"API Error {resp.status_code}: {resp.text}"
            except Exception as e:
                last_error = str(e)
                continue

        if response_json is None:
            raise RuntimeError(f"Gemini API menu extraction failed: {last_error}")

        # Build RecognizedMenu object
        sections: List[MenuSection] = []
        for sec_data in response_json.get("sections", []):
            cat_title = sec_data.get("category", "General").strip()
            sec_items: List[MenuItem] = []

            for it_data in sec_data.get("items", []):
                name = it_data.get("name", "").strip()
                if not name:
                    continue

                price_val = it_data.get("price")
                if price_val is not None:
                    try:
                        price_val = float(price_val)
                    except (ValueError, TypeError):
                        price_val = None

                raw_price = it_data.get("raw_price")
                currency = it_data.get("currency")
                desc = it_data.get("description")
                dietary = it_data.get("dietary_tags", []) or []

                menu_item = MenuItem(
                    name=name,
                    price=price_val,
                    raw_price=raw_price,
                    currency=currency,
                    description=desc,
                    section=cat_title,
                    dietary_tags=dietary,
                    confidence=1.0,
                )
                sec_items.append(menu_item)

            if sec_items:
                sections.append(MenuSection(title=cat_title, items=sec_items))

        image_path_str = str(image_input) if isinstance(image_input, (str, Path)) else ""
        return RecognizedMenu(
            image_path=image_path_str,
            image_width=img_w,
            image_height=img_h,
            num_columns=1,
            sections=sections,
            unclassified_items=[],
            raw_blocks=[],
            metadata={"extractor": "Gemini-Flash", "model": model},
        )
