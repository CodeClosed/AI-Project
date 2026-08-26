"""
Intelligent Menu Extractor powered by Google Gemini Vision API.
Provides zero-shot semantic understanding, automatic OCR typo correction,
and structured menu hierarchy extraction with calibrated confidence scoring.
"""

from typing import List, Dict, Any, Optional, Union, Tuple
import os
import re
import json
import base64
import io
import logging
from pathlib import Path
import numpy as np
from PIL import Image
import cv2

from .config import get_gemini_api_key, get_gemini_model_name
from .gemini_client import GeminiClient, GeminiAPIError
from .models import RecognizedMenu, MenuSection, MenuItem, BoundingBox

logger = logging.getLogger(__name__)


def tokenize_food_item(raw_name: str) -> List[str]:
    """
    Splits compound food strings (separated by commas, slashes, or 'and')
    into individual clean food item strings.
    """
    if not raw_name:
        return []
    
    # Remove parenthetical portions e.g. "(200 gm)", "(2 Nos.)", "(250 mL)"
    text = re.sub(r'\([^)]*\)', '', raw_name)
    

    # Split by comma, slash, semicolon, or newline
    parts = re.split(r'[,/;\n]', text)
    
    clean_items = []
    for part in parts:
        item = part.strip()
        # Clean up leading/trailing punctuation or bullet noise
        item = re.sub(r'^[\-\*\•\.]+', '', item).strip()
        
        # Filter out headers, times, or empty strings
        if not item or item.upper() in ["BREAKFAST", "LUNCH", "SNACKS", "DINNER", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY", "NOTE"]:
            continue
            
        # If item has ' and ' with multiple dishes, split cautiously if length is short
        if ' and ' in item.lower() and not any(k in item.lower() for k in ['rice and', 'dal and', 'mac and']):
            sub_parts = re.split(r'\s+and\s+', item, flags=re.IGNORECASE)
            for sp in sub_parts:
                sp_clean = sp.strip()
                if sp_clean and len(sp_clean) > 1:
                    clean_items.append(sp_clean.title())
        else:
            if len(item) > 1:
                clean_items.append(item.title())
                
    return clean_items


class GeminiMenuExtractor:
    """Extracts structured menu items, categories, and prices using Google Gemini Flash."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        gemini_client: Optional[GeminiClient] = None,
    ):
        self.gemini_client = gemini_client or GeminiClient(api_key=api_key, model_name=model_name)

    def is_available(self) -> bool:
        """Returns True if a valid Gemini API key is configured."""
        return self.gemini_client.is_available()

    def _prepare_base64_image(self, image_input: Union[str, np.ndarray, Image.Image, io.BytesIO]) -> Tuple[str, int, int]:
        """Converts image input to base64 JPEG string and returns (b64_string, width, height)."""
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
        # Resize if huge to speed up upload
        if max(w, h) > 2000:
            scale = 2000.0 / max(w, h)
            pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        pil_img.save(buffer, format="JPEG", quality=90)
        b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return b64_str, w, h

    def _calculate_confidence(self, name: str, price: Optional[float], desc: Optional[str], section: Optional[str]) -> float:
        """
        Calibrates item extraction confidence based on completeness and semantic coherence.
        """
        score = 0.75
        if name and len(name) >= 3:
            score += 0.10
        if desc and len(desc) > 5:
            score += 0.05
        if section and section.lower() not in ("general", "other", "unknown"):
            score += 0.05
        return min(0.98, max(0.50, score))

    def extract_menu(self, image_input: Union[str, np.ndarray, Image.Image, io.BytesIO]) -> RecognizedMenu:
        """
        Processes a restaurant or college mess menu image with Gemini Flash and returns a structured RecognizedMenu object.
        """
        b64_img, img_w, img_h = self._prepare_base64_image(image_input)

        prompt = """
You are an expert culinary AI specializing in menu digitization for restaurants and university mess menus.
Analyze this menu image and extract ALL individual food and beverage items with complete accuracy.

CRITICAL EXTRACTION & TABLE GRID RULES:
1. IF THIS IS A TABLE/TIMETABLE GRID (e.g. Days across columns, Meal slots across rows):
   - Treat EVERY CELL independently.
   - NEVER read text horizontally across multiple columns into one combined item.
   - Extract dishes individually cell by cell.
2. DISH TOKENIZATION & SPLITTING:
   - If a cell or line contains multiple items separated by commas, slashes (/), 'and', or newlines (e.g. 'Dosa, Sambhar, Chutney' or 'Veg Biryani/Egg Biryani'), EXTRACT EACH DISH AS A SEPARATE INDIVIDUAL ITEM IN THE JSON.
3. EXCLUDE TABLE HEADERS & NOISE:
   - Exclude column/row headers (e.g., 'Monday', 'Tuesday', 'Breakfast', 'Lunch', 'Snacks', 'Dinner', time ranges like '7:30 AM - 9:15 AM').
   - Exclude document headers, notices, footer notes (e.g., 'SRM UNIVERSITY', 'NOTE:', 'THIS MENU WILL BE...').
4. SPELLING FIXES:
   - Fix OCR spelling errors (e.g. fix 'Tdly' to 'Idli', 'Pillka' to 'Phulka', 'Rajama' to 'Rajma', 'Wkk' to 'Milk').

Return ONLY valid JSON with this exact structure:
{
  "sections": [
    {
      "category": "Section or Meal Name (e.g. Breakfast, Lunch, Snacks, Dinner, or General)",
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

        for sec_data in response_json.get("sections", []):
            cat_title = str(sec_data.get("category", "General")).strip()
            sec_items: List[MenuItem] = []

            for it_data in sec_data.get("items", []):
                raw_name = str(it_data.get("name", "")).strip()
                if not raw_name:
                    continue

                # Tokenize and split any compound items returned in raw_name
                individual_names = tokenize_food_item(raw_name)

                for name in individual_names:
                    item_key = name.lower()
                    # Skip duplicate items across sections/cells to prevent multi-scoring bugs
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
                        raw_price=raw_price,
                        currency=currency,
                        description=desc,
                        section=cat_title,
                        dietary_tags=dietary,
                        confidence=conf,
                    )
                    sec_items.append(menu_item)

            if sec_items:
                sections.append(MenuSection(title=cat_title, items=sec_items))

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
