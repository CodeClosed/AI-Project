"""
Groq Vision Menu Extractor for NutriMenu AI.

Provides modular vision-language menu digitization using Groq's high-speed LPU infrastructure
with multimodal vision models (e.g., llama-3.2-11b-vision-preview).
Strictly filters out non-food noise and returns a fully typed RecognizedMenu object.
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
    get_groq_api_key,
    get_groq_model_name,
    DEFAULT_GROQ_VISION_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
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
from .models import RecognizedMenu, MenuSection, MenuItem
from .noise_filter import is_valid_food_item, AdvancedNoiseFilter
from .gemini_extractor import tokenize_food_item

logger = logging.getLogger(__name__)


class GroqMenuExtractor:
    """Extracts structured food dishes from menu images using Groq Vision models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        allow_beverages: bool = False,
        session: Optional[requests.Session] = None,
    ):
        self.api_key = api_key if api_key is not None else get_groq_api_key()
        self.model_name = model_name or DEFAULT_GROQ_VISION_MODEL
        self.timeout = timeout
        self.allow_beverages = allow_beverages
        self.session = session or requests.Session()
        self.noise_filter = AdvancedNoiseFilter()
        self.client = GroqClient(
            api_key=self.api_key,
            model_name=self.model_name,
            vision_model=self.model_name,
            timeout=timeout,
            session=self.session,
        )

    def is_available(self) -> bool:
        """Returns True if a valid non-mock Groq API key is configured."""
        return self.client.is_available()

    def _prepare_base64_image(self, image_input: Union[str, Path, np.ndarray, Image.Image, io.BytesIO, bytes]) -> Tuple[str, int, int]:
        """Converts image input formats into a base64 JPEG string and returns (b64_str, width, height)."""
        if isinstance(image_input, Image.Image):
            pil_img = image_input.convert("RGB")
        elif isinstance(image_input, io.BytesIO):
            image_input.seek(0)
            pil_img = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, (str, Path)):
            pil_img = Image.open(str(image_input)).convert("RGB")
        elif isinstance(image_input, np.ndarray):
            if len(image_input.shape) == 2:
                pil_img = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_GRAY2RGB))
            elif image_input.shape[2] == 4:
                pil_img = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGRA2RGB))
            else:
                pil_img = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB))
        elif isinstance(image_input, bytes):
            pil_img = Image.open(io.BytesIO(image_input)).convert("RGB")
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        w, h = pil_img.size
        # Resize if exceeding 2000px max dimension for network efficiency
        if max(w, h) > 2000:
            scale = 2000.0 / max(w, h)
            pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
            w, h = pil_img.size

        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=85)
        b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
        return b64_str, w, h

    def extract(self, image_input: Union[str, Path, np.ndarray, Image.Image, io.BytesIO, bytes]) -> RecognizedMenu:
        """Sends menu image to Groq Vision API and returns parsed RecognizedMenu."""
        if not self.is_available():
            raise GroqAuthError("Groq API key is not configured. Set GROQ_API_KEY in your environment.")

        b64_img, width, height = self._prepare_base64_image(image_input)

        prompt = (
            "You are an expert culinary AI specializing in restaurant and university mess menu digitization.\n"
            "Analyze this menu image and extract ALL individual food and beverage items with complete accuracy.\n\n"
            "CRITICAL EXTRACTION RULES:\n"
            "1. IF THIS IS A TABLE / TIMETABLE GRID (e.g. Days across columns, Meal slots across rows):\n"
            "   - Treat EVERY CELL independently.\n"
            "   - Extract dishes individually cell by cell across all days and meal slots.\n"
            "2. DISH TOKENIZATION & SPLITTING:\n"
            "   - If a cell or line contains multiple items separated by commas, slashes (/), 'and', or newlines (e.g. 'Dosa, Sambhar, Chutney'), EXTRACT EACH DISH AS A SEPARATE INDIVIDUAL ITEM.\n"
            "3. EXCLUDE TABLE HEADERS & NOISE:\n"
            "   - Exclude column/row headers (e.g., 'Monday', 'Tuesday', 'Breakfast', 'Lunch', 'Snacks', 'Dinner', time ranges).\n"
            "   - Exclude document headers, notices, template placeholders, footer notes.\n"
            "4. Return strictly valid JSON matching this schema:\n"
            "{\n"
            "  \"sections\": [\n"
            "    {\n"
            "      \"category\": \"Category or Section Name\",\n"
            "      \"items\": [\"Dish 1\", \"Dish 2\"]\n"
            "    }\n"
            "  ]\n"
            "}\n"
        )

        data = self.client.generate_json(
            prompt=prompt,
            image_b64=b64_img,
            image_mime_type="image/jpeg",
        )

        sections: List[MenuSection] = []
        seen_items = set()

        raw_sections = data.get("sections", [])
        if not raw_sections and "items" in data:
            raw_sections = [{"category": "General", "items": data["items"]}]

        for sec_data in raw_sections:
            cat_name = sec_data.get("category", "General") or "General"
            sec = MenuSection(title=cat_name)
            raw_items = sec_data.get("items", [])

            for item in raw_items:
                raw_name = item.get("name", "") if isinstance(item, dict) else str(item)
                raw_desc = item.get("description", "") if isinstance(item, dict) else ""
                raw_price = str(item.get("price", "")) if isinstance(item, dict) else ""

                for sub_dish in tokenize_food_item(raw_name):
                    clean_dish = sub_dish.strip()
                    if not clean_dish or clean_dish.lower() in seen_items:
                        continue

                    # Filter day of week and meal slot combinations (e.g. Monday Breakfast, Sunday Dinner)
                    dish_words = set(clean_dish.lower().split())
                    calendar_headers = {
                        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
                        "breakfast", "lunch", "snacks", "dinner", "mess", "menu", "timing", "timings"
                    }
                    if dish_words and dish_words.issubset(calendar_headers):
                        continue

                    is_food, _ = is_valid_food_item(clean_dish, allow_beverages=self.allow_beverages)
                    if is_food:
                        seen_items.add(clean_dish.lower())
                        sec.items.append(
                            MenuItem(
                                name=clean_dish,
                                description=raw_desc,
                                raw_price=raw_price,
                                section=cat_name,
                            )
                        )

            if sec.items:
                sections.append(sec)

        return RecognizedMenu(
            image_path=str(image_input) if isinstance(image_input, (str, Path)) else "",
            image_width=width,
            image_height=height,
            num_columns=1,
            sections=sections,
            metadata={"extractor": "Groq", "model": self.model_name},
        )
