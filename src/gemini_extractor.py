"""
Gemini Multimodal Vision Menu Extractor for NutriMenu AI.
Performs end-to-end vision transcription, OCR typo correction, table grid parsing,
and noise filtering using Google Gemini (defaulting to Gemini 3.7 Flash).
"""

import io
import re
import json
import base64
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
from PIL import Image
import numpy as np
import requests

from .gemini_client import GeminiClient, GeminiAPIError
from .noise_filter import AdvancedNoiseFilter, is_valid_food_item
from .models import RecognizedMenu, MenuSection, MenuItem, BoundingBox
from .config import get_gemini_api_key, get_gemini_model_name

logger = logging.getLogger(__name__)


def tokenize_food_item(raw_name: str) -> List[str]:
    """
    Splits compound food strings (separated by commas, slashes, or 'and')
    into individual clean food item strings, filtering out non-food headers.
    """
    if not raw_name:
        return []

    # Strip bracketed text
    text = re.sub(r'\([^)]*\)', '', raw_name)
    parts = re.split(r'[,/;\n]', text)

    excluded_headers = {
        "BREAKFAST", "LUNCH", "SNACKS", "DINNER",
        "SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY",
        "NOTE", "TIMINGS", "MENU", "TODAY", "SPECIAL", "NAME", "LOCATION",
        "INSERT YOUR LOCATION HERE", "RESTAURANT NAME", "ORDER NOW"
    }

    clean_items = []
    for part in parts:
        item = part.strip()
        item = re.sub(r'^[\-\*\•\.\d\:\s]+', '', item).strip()

        if not item or item.upper() in excluded_headers:
            continue

        # Strip time ranges like 7:30 AM - 9:15 AM
        if re.search(r'\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)', item):
            continue

        # Split 'and' if multiple distinct dishes are joined
        if ' and ' in item.lower() and not any(k in item.lower() for k in ['rice and', 'dal and', 'mac and', 'bread and', 'chips and']):
            sub_parts = re.split(r'\s+and\s+', item, flags=re.IGNORECASE)
            for sp in sub_parts:
                sp_clean = sp.strip()
                valid, _ = is_valid_food_item(sp_clean, allow_beverages=True)
                if valid and len(sp_clean) > 1:
                    clean_items.append(sp_clean.title())
        else:
            valid, _ = is_valid_food_item(item, allow_beverages=True)
            if valid and len(item) > 1:
                clean_items.append(item.title())

    return clean_items


class GeminiMenuExtractor:
    """
    Multimodal Vision Menu Extractor powered by Google Gemini (Gemini 3.7 Flash).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        gemini_client: Optional[GeminiClient] = None,
        allow_beverages: bool = True,
    ):
        self.gemini_client = gemini_client or GeminiClient(api_key=api_key, model_name=model_name)
        self.allow_beverages = allow_beverages
        self.noise_filter = AdvancedNoiseFilter()

    def is_available(self) -> bool:
        """Returns True if a valid Gemini API key is configured."""
        return self.gemini_client.is_available()

    def _prepare_base64_image(self, image_input: Union[str, np.ndarray, Image.Image, io.BytesIO, Path]) -> Tuple[str, int, int]:
        """Converts image input to base64 JPEG string and returns (b64_string, width, height)."""
        if isinstance(image_input, Image.Image):
            pil_img = image_input.convert("RGB")
        elif isinstance(image_input, io.BytesIO):
            image_input.seek(0)
            pil_img = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, np.ndarray):
            import cv2
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
        # Resize if huge to optimize latency
        if max(w, h) > 2048:
            scale = 2048.0 / max(w, h)
            pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
            w, h = pil_img.size

        buffer = io.BytesIO()
        pil_img.save(buffer, format="JPEG", quality=90)
        b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return b64_str, w, h

    def _calculate_confidence(self, name: str, price: Optional[float], desc: Optional[str], section: Optional[str]) -> float:
        """Calibrates item extraction confidence based on completeness and semantic coherence."""
        score = 0.85
        if name and len(name) >= 3:
            score += 0.08
        if desc and len(desc) > 5:
            score += 0.04
        if section and section.lower() not in ("general", "other", "unknown"):
            score += 0.03
        return min(0.99, max(0.60, score))

    def extract_menu(self, image_input: Union[str, np.ndarray, Image.Image, io.BytesIO, Path]) -> RecognizedMenu:
        """
        Processes a restaurant or college mess menu image with Gemini Flash and returns a structured RecognizedMenu object.
        """
        b64_img, img_w, img_h = self._prepare_base64_image(image_input)

        prompt = """
You are an expert culinary AI specializing in restaurant and university mess menu digitization.
Analyze this menu image and extract ALL individual food and beverage items with complete accuracy.

CRITICAL EXTRACTION & TABLE GRID RULES:
1. IF THIS IS A TABLE / TIMETABLE GRID (e.g. Days across columns, Meal slots across rows):
   - Treat EVERY CELL independently.
   - NEVER combine text horizontally across multiple columns into one item.
   - Extract dishes individually cell by cell across all days and meal slots.
2. DISH TOKENIZATION & SPLITTING:
   - If a cell or line contains multiple items separated by commas, slashes (/), 'and', or newlines (e.g. 'Dosa, Sambhar, Chutney' or 'Veg Biryani/Egg Biryani'), EXTRACT EACH DISH AS A SEPARATE INDIVIDUAL ITEM IN THE JSON.
3. EXCLUDE TABLE HEADERS & NOISE:
   - Exclude column/row headers (e.g., 'Monday', 'Tuesday', 'Breakfast', 'Lunch', 'Snacks', 'Dinner', time ranges like '7:30 AM - 9:15 AM', '10:00 AM - 11:00 PM').
   - Exclude document headers, notices, template placeholders, footer notes (e.g., 'SRM UNIVERSITY', 'NOTE:', 'THIS MENU WILL BE...', 'INSERT YOUR LOCATION HERE', 'NAME', 'RESTAURANT NAME', 'ORDER NOW').
4. SPELLING FIXES:
   - Fix OCR spelling errors (e.g. fix 'Tdly' to 'Idli', 'Pillka' to 'Phulka', 'Rajama' to 'Rajma', 'Wkk' to 'Milk', 'Hasala' to 'Masala', 'Panner' to 'Paneer').

Return ONLY valid JSON matching this exact structure:
{
  "restaurant_name": "Restaurant / Mess Name if visible",
  "sections": [
    {
      "category": "Section or Meal Name (e.g. Breakfast, Lunch, Snacks, Dinner, Appetizers, Mains, Desserts)",
      "items": [
        {
          "name": "Single Individual Food Item Name",
          "price": null,
          "raw_price": null,
          "currency": null,
          "description": "",
          "dietary_tags": []
        }
      ]
    }
  ]
}
"""
        response_json = self.gemini_client.generate_json(
            prompt=prompt,
            image_b64=b64_img,
            image_mime_type="image/jpeg",
            temperature=0.1,
        )

        if not isinstance(response_json, dict):
            raise GeminiAPIError("Invalid response structure from Gemini menu extraction.")

        # Build RecognizedMenu object
        sections: List[MenuSection] = []
        seen_items = set()

        raw_sections = response_json.get("sections") or []
        for sec_data in raw_sections:
            cat_title = str(sec_data.get("category") or sec_data.get("title") or "General").strip()
            sec_items: List[MenuItem] = []

            for it_data in sec_data.get("items", []):
                raw_name = str(it_data.get("name", "")).strip()
                if not raw_name:
                    continue

                # Tokenize and split any compound items returned in raw_name
                individual_names = tokenize_food_item(raw_name)

                for name in individual_names:
                    item_key = name.lower()
                    if item_key in seen_items:
                        continue
                    seen_items.add(item_key)

                    price_val = it_data.get("price")
                    if price_val is not None:
                        try:
                            price_val = float(price_val)
                        except (ValueError, TypeError):
                            price_val = None

                    raw_price = it_data.get("raw_price")
                    currency = it_data.get("currency")
                    desc = it_data.get("description", "")
                    dietary = it_data.get("dietary_tags", []) or []

                    conf = self._calculate_confidence(name, price_val, desc, cat_title)

                    menu_item = MenuItem(
                        name=name,
                        price=price_val,
                        raw_price=str(raw_price) if raw_price else None,
                        currency=currency,
                        description=desc,
                        section=cat_title,
                        dietary_tags=dietary,
                        confidence=conf,
                    )
                    sec_items.append(menu_item)

            if sec_items:
                sections.append(MenuSection(title=cat_title, items=sec_items))

        # Handle flat food_items if returned
        if not sections and response_json.get("food_items"):
            flat_items: List[MenuItem] = []
            for fi in response_json["food_items"]:
                raw_name = str(fi.get("name", "")).strip()
                for name in tokenize_food_item(raw_name):
                    if name.lower() in seen_items:
                        continue
                    seen_items.add(name.lower())
                    flat_items.append(
                        MenuItem(
                            name=name,
                            price=float(fi["price"]) if fi.get("price") is not None else None,
                            section=fi.get("section", "General"),
                            confidence=0.90,
                        )
                    )
            if flat_items:
                sections.append(MenuSection(title="Menu Items", items=flat_items))

        image_path_str = str(image_input) if isinstance(image_input, (str, Path)) else "in_memory_image"
        return RecognizedMenu(
            image_path=image_path_str,
            image_width=img_w,
            image_height=img_h,
            num_columns=1,
            sections=sections,
            unclassified_items=[],
            raw_blocks=[],
            metadata={"extractor": "Gemini-Flash", "model": self.gemini_client.model_name},
        )


VisionMenuExtractor = GeminiMenuExtractor

__all__ = [
    "GeminiMenuExtractor",
    "VisionMenuExtractor",
    "tokenize_food_item",
]
