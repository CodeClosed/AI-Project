import os
import io
import json
import time
import logging
from typing import List, Optional, Union, Dict, Any
from pathlib import Path
import numpy as np
from PIL import Image
import cv2
import re
from dotenv import load_dotenv

from .config import get_gemini_api_key, DEFAULT_MIN_OCR_CONFIDENCE
from .models import RecognizedMenu, MenuItem, MenuSection, BoundingBox, TextBlock
from .preprocessing import Preprocessor
from .noise_filter import AdvancedNoiseFilter
from .layout_analyzer import LayoutAnalyzer
from .menu_parser import MenuParser
from .visualizer import MenuVisualizer

# Ensure environment variables (.env) are explicitly loaded
load_dotenv(override=True)

logger = logging.getLogger(__name__)

# Global singleton OCR reader to avoid repeated model loading
_GLOBAL_EASYOCR_READER = None


def get_cached_easyocr_reader():
    """Lazily loads and caches the EasyOCR reader singleton for maximum speed."""
    global _GLOBAL_EASYOCR_READER
    if _GLOBAL_EASYOCR_READER is None:
        try:
            import easyocr
            import torch
            has_gpu = torch.cuda.is_available()
            _GLOBAL_EASYOCR_READER = easyocr.Reader(['en'], gpu=has_gpu, verbose=False)
            logger.info("Cached EasyOCR Reader initialized (GPU=%s).", has_gpu)
        except Exception as e:
            logger.warning("Failed to initialize EasyOCR (%s).", e)
            _GLOBAL_EASYOCR_READER = False
    return _GLOBAL_EASYOCR_READER if _GLOBAL_EASYOCR_READER is not False else None


class FastLocalOCRExtractor:
    """Fast local OCR engine that achieves fast extraction on CPU."""

    def __init__(self, min_confidence: float = 0.3):
        self.min_confidence = min_confidence
        self.noise_filter = AdvancedNoiseFilter()
        self.layout_analyzer = LayoutAnalyzer()
        self.menu_parser = MenuParser()

    def extract(self, image_input: Union[str, np.ndarray, Image.Image, Path]) -> RecognizedMenu:
        reader = get_cached_easyocr_reader()
        if isinstance(image_input, (str, Path)):
            img = cv2.imread(str(image_input))
        elif isinstance(image_input, Image.Image):
            img = cv2.cvtColor(np.array(image_input.convert("RGB")), cv2.COLOR_RGB2BGR)
        elif isinstance(image_input, np.ndarray):
            img = image_input
        else:
            img = None

        if reader is None or img is None or img.size == 0:
            return RecognizedMenu(
                image_path=str(image_input) if isinstance(image_input, (str, Path)) else "",
                image_width=img.shape[1] if img is not None else 0,
                image_height=img.shape[0] if img is not None else 0,
                num_columns=1,
                sections=[],
                metadata={"extractor": "offline_fallback"},
            )

        h, w = img.shape[:2]
        try:
            results = reader.readtext(img)
            text_blocks = []
            for poly, text, conf in results:
                if conf >= 0.15 and text.strip():
                    bbox = BoundingBox.from_polygon(poly)
                    text_blocks.append(TextBlock(text=text.strip(), bbox=bbox, confidence=float(conf)))

            analyzed_blocks, num_cols = self.layout_analyzer.analyze(text_blocks, w, h)
            recognized_menu = self.menu_parser.parse(
                analyzed_blocks,
                image_path=str(image_input) if isinstance(image_input, (str, Path)) else "",
                image_width=w,
                image_height=h,
                num_columns=num_cols,
            )
            recognized_menu.metadata["extractor"] = "FastLocalOCR"
            return recognized_menu
        except Exception as e:
            logger.error("Local layout extraction failed: %s", e)
            return RecognizedMenu(
                image_path=str(image_input) if isinstance(image_input, (str, Path)) else "",
                image_width=w,
                image_height=h,
                num_columns=1,
                sections=[],
                metadata={"extractor": "FastLocalOCR", "error": str(e)},
            )


class GeminiMenuExtractor:
    """Extracts clean food and beverage dishes using Google Gemini Multimodal Vision API."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or get_gemini_api_key() or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or os.getenv("GEMINI_MODEL_NAME") or "gemini-3.5-flash"

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) >= 10)

    def extract(self, image_input: Union[str, np.ndarray, Image.Image, Path, io.BytesIO]) -> RecognizedMenu:
        from google import genai
        client = genai.Client(api_key=self.api_key)

        from src.gemini_extractor import tokenize_food_item

        prompt = (
            "You are an expert culinary AI specializing in menu digitization for restaurants and university mess menus.\n"
            "Analyze this menu image and extract ALL individual food and beverage items with complete accuracy.\n\n"
            "CRITICAL EXTRACTION & TABLE GRID RULES:\n"
            "1. IF THIS IS A TABLE / TIMETABLE GRID (e.g. Days across columns, Meal slots across rows):\n"
            "   - Treat EVERY CELL independently.\n"
            "   - NEVER combine text horizontally across multiple columns into one item.\n"
            "   - Extract dishes individually cell by cell across all days and meal slots.\n"
            "2. DISH TOKENIZATION & SPLITTING:\n"
            "   - If a cell or line contains multiple items separated by commas, slashes (/), 'and', or newlines (e.g. 'Dosa, Sambhar, Chutney' or 'Veg Biryani/Egg Biryani'), EXTRACT EACH DISH AS A SEPARATE INDIVIDUAL ITEM.\n"
            "3. EXCLUDE TABLE HEADERS & NOISE:\n"
            "   - Exclude column/row headers (e.g., 'Monday', 'Tuesday', 'Breakfast', 'Lunch', 'Snacks', 'Dinner', time ranges like '7:30 AM - 9:15 AM').\n"
            "   - Exclude document headers, notices, template placeholders, footer notes.\n"
            "4. SPELLING FIXES:\n"
            "   - Fix OCR spelling errors (e.g. fix 'Tdly' to 'Idli', 'Pillka' to 'Phulka', 'Rajama' to 'Rajma', 'Wkk' to 'Milk').\n\n"
            "Return strictly valid JSON matching this structure:\n"
            "{\n"
            "  \"sections\": [\n"
            "    {\n"
            "      \"category\": \"Section or Meal Name (e.g. Appetizers, Main Courses, Desserts, Breakfast, Lunch, Snacks, Dinner, or General)\",\n"
            "      \"items\": [\"Single Individual Food Item 1\", \"Single Individual Food Item 2\"]\n"
            "    }\n"
            "  ]\n"
            "}\n"
        )

        if isinstance(image_input, (str, Path)):
            img = Image.open(str(image_input))
        elif isinstance(image_input, np.ndarray):
            if len(image_input.shape) == 2:
                img = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_GRAY2RGB))
            elif image_input.shape[2] == 4:
                img = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGRA2RGB))
            else:
                img = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB))
        elif isinstance(image_input, io.BytesIO):
            image_input.seek(0)
            img = Image.open(image_input)
        elif isinstance(image_input, Image.Image):
            img = image_input
        else:
            img = image_input

        # Convert to RGB and scale if exceedingly large to optimize network speed
        if isinstance(img, Image.Image):
            if img.mode != "RGB":
                img = img.convert("RGB")
            w, h = img.size
            if max(w, h) > 2000:
                scale = 2000.0 / max(w, h)
                img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

        candidate_models = [
            self.model_name,
            "gemini-3-flash-preview",
            "gemini-flash-latest",
            "gemini-3.1-flash-lite",
            "gemini-3.7-flash",
            "gemini-3.5-flash",
        ]
        seen_models = set()
        ordered_candidates = []
        for m in candidate_models:
            if m and m not in seen_models:
                seen_models.add(m)
                ordered_candidates.append(m)

        last_err = None
        for model in ordered_candidates:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=[prompt, img]
                )
                raw_text = response.text.strip() if response.text else ""

                sections: List[MenuSection] = []
                all_clean_items: List[str] = []
                seen_items = set()

                parsed_json = None
                # Strip markdown fences
                clean_text = raw_text.strip()
                if clean_text.startswith("```"):
                    first_nl = clean_text.find("\n")
                    if first_nl != -1:
                        clean_text = clean_text[first_nl + 1:]
                if clean_text.endswith("```"):
                    last_fence = clean_text.rfind("```")
                    if last_fence != -1:
                        clean_text = clean_text[:last_fence]
                clean_text = clean_text.strip()

                try:
                    parsed_json = json.loads(clean_text)
                except Exception:
                    json_match = re.search(r'\{[\s\S]*\}', raw_text)
                    if json_match:
                        try:
                            parsed_json = json.loads(json_match.group(0))
                        except Exception:
                            pass

                if parsed_json and isinstance(parsed_json, dict) and "sections" in parsed_json:
                    for sec in parsed_json.get("sections", []):
                        cat_title = str(sec.get("category", "Menu Items")).strip()
                        raw_sec_items = sec.get("items", [])
                        sec_menu_items: List[MenuItem] = []
                        for it in raw_sec_items:
                            raw_name = it.get("name", "") if isinstance(it, dict) else str(it)
                            for name in tokenize_food_item(raw_name):
                                if name.lower() not in seen_items:
                                    seen_items.add(name.lower())
                                    all_clean_items.append(name)
                                    sec_menu_items.append(
                                        MenuItem(name=name, section=cat_title, confidence=0.95)
                                    )
                        if sec_menu_items:
                            sections.append(MenuSection(title=cat_title, items=sec_menu_items))

                # Fallback to comma/newline split if sections were empty
                if not sections:
                    raw_items = [it.strip() for it in re.split(r'[,;\n]', raw_text) if it.strip()]
                    flat_menu_items = []
                    for item in raw_items:
                        for clean in tokenize_food_item(item):
                            if clean.lower() not in seen_items:
                                seen_items.add(clean.lower())
                                all_clean_items.append(clean)
                                flat_menu_items.append(
                                    MenuItem(name=clean, section="Menu Items", confidence=0.95)
                                )
                    if flat_menu_items:
                        sections.append(MenuSection(title="Menu Items", items=flat_menu_items))

                if all_clean_items:
                    img_w, img_h = img.size if isinstance(img, Image.Image) else (0, 0)
                    return RecognizedMenu(
                        image_path=str(image_input) if isinstance(image_input, (str, Path)) else "",
                        image_width=img_w,
                        image_height=img_h,
                        num_columns=len(sections) if len(sections) > 1 else 1,
                        sections=sections,
                        dishes=all_clean_items,
                        metadata={"extractor": "gemini-vision", "model": model}
                    )
            except Exception as e:
                logger.warning("Gemini model '%s' failed: %s", model, e)
                last_err = e

        if last_err:
            raise last_err
        raise RuntimeError("Gemini Vision extraction returned empty items.")

    def extract_menu(self, image_input: Any) -> RecognizedMenu:
        """Alias for extract."""
        return self.extract(image_input)


class MenuRecognitionPipeline:
    """End-to-end pipeline for converting menu images into structured dish lists."""

    def __init__(
        self,
        languages: Optional[List[str]] = None,
        gpu: Optional[bool] = None,
        enable_deskew: bool = True,
        enable_illumination_norm: bool = True,
        min_ocr_confidence: float = DEFAULT_MIN_OCR_CONFIDENCE,
        api_key: Optional[str] = None,
        prefer_ai: bool = True,
        prefer_gemini: Optional[bool] = None,
    ):
        self.prefer_gemini = prefer_ai if prefer_gemini is None else prefer_gemini
        effective_gemini_key = api_key or get_gemini_api_key() or os.getenv("GEMINI_API_KEY")

        self.gemini_extractor = GeminiMenuExtractor(api_key=effective_gemini_key)
        self.local_extractor = FastLocalOCRExtractor(min_confidence=min_ocr_confidence)
        self.visualizer = MenuVisualizer()

    def process_image(
        self,
        image_input: Union[str, np.ndarray, Image.Image, Path],
        visualize_path: Optional[str] = None,
    ) -> RecognizedMenu:
        orig_img = None
        if visualize_path:
            if isinstance(image_input, (str, Path)):
                orig_img = cv2.imread(str(image_input))
            elif isinstance(image_input, Image.Image):
                orig_img = cv2.cvtColor(np.array(image_input.convert("RGB")), cv2.COLOR_RGB2BGR)
            elif isinstance(image_input, np.ndarray):
                orig_img = image_input

        if self.prefer_gemini and self.gemini_extractor.is_available():
            try:
                rec_menu = self.gemini_extractor.extract(image_input)
                if visualize_path and orig_img is not None and orig_img.size > 0:
                    try:
                        self.visualizer.save_visualization(orig_img, rec_menu, output_path=visualize_path)
                    except Exception as e:
                        logger.warning("Visualizer error: %s", e)
                return rec_menu
            except Exception as e:
                logger.warning("[MenuRecognitionPipeline] Gemini Vision API failed (%s), running local OCR.", e)

        rec_menu = self.local_extractor.extract(image_input)
        if visualize_path and orig_img is not None and orig_img.size > 0:
            try:
                self.visualizer.save_visualization(orig_img, rec_menu, output_path=visualize_path)
            except Exception as e:
                logger.warning("Visualizer error: %s", e)
        return rec_menu

    def extract_menu_items(
        self,
        image_input: Union[str, np.ndarray, Image.Image, Path],
    ) -> List[str]:
        menu = self.process_image(image_input)
        return menu.get_item_names()

