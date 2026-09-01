import os
import io
import time
import logging
from typing import List, Optional, Union, Dict, Any
from pathlib import Path
import numpy as np
from PIL import Image
import cv2
from dotenv import load_dotenv

from .config import get_gemini_api_key, get_openrouter_api_key, DEFAULT_MIN_OCR_CONFIDENCE
from .gemini_extractor import GeminiMenuExtractor
from .openrouter_extractor import OpenRouterMenuExtractor
from .models import RecognizedMenu, MenuItem, MenuSection, BoundingBox, TextBlock
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


class MenuRecognitionPipeline:
    """High-performance pipeline for converting menu images into structured dish lists."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        prefer_ai: bool = True,
        prefer_gemini: Optional[bool] = None,
        min_ocr_confidence: float = DEFAULT_MIN_OCR_CONFIDENCE,
    ):
        self.prefer_ai = prefer_ai if prefer_gemini is None else prefer_gemini
        effective_gemini_key = api_key or get_gemini_api_key()

        self.gemini_extractor = GeminiMenuExtractor(api_key=effective_gemini_key)
        self.ai_extractor = self.gemini_extractor
        self.local_extractor = FastLocalOCRExtractor(min_confidence=min_ocr_confidence)
        self.visualizer = MenuVisualizer()

    def process_image(
        self,
        image_input: Union[str, np.ndarray, Image.Image, Path],
        visualize_path: Optional[str] = None,
    ) -> RecognizedMenu:
        # Load image array for visualizer if requested
        orig_img = None
        if isinstance(image_input, (str, Path)):
            orig_img = cv2.imread(str(image_input))
        elif isinstance(image_input, Image.Image):
            orig_img = cv2.cvtColor(np.array(image_input.convert("RGB")), cv2.COLOR_RGB2BGR)
        elif isinstance(image_input, np.ndarray):
            orig_img = image_input

        rec_menu = None
        if self.prefer_ai and self.ai_extractor.is_available():
            try:
                rec_menu = self.ai_extractor.extract_menu(image_input)
            except Exception as e:
                logger.warning("[MenuRecognitionPipeline] Vision AI API failed (%s), running local OCR.", e)

        if not rec_menu or (not rec_menu.sections and not rec_menu.get_all_items()):
            rec_menu = self.local_extractor.extract(image_input)

        if visualize_path and orig_img is not None and orig_img.size > 0:
            try:
                self.visualizer.save_visualization(orig_img, rec_menu, output_path=visualize_path)
            except Exception as e:
                logger.warning("Visualizer error: %s", e)

        return rec_menu
