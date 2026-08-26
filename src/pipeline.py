import os
from typing import List, Optional, Union, Dict, Any
import numpy as np
from PIL import Image
from dotenv import load_dotenv

# Ensure environment variables (.env) are explicitly loaded
load_dotenv(override=True)

DEFAULT_MIN_OCR_CONFIDENCE = 0.5


class RecognizedMenu:
    def __init__(self, dishes: List[str] = None, metadata: Dict[str, Any] = None):
        self.dishes = dishes or []
        self.metadata = metadata or {}

    def to_flat_items(self) -> List[str]:
        return self.dishes


class Preprocessor:
    def __init__(self, enable_deskew: bool = True, enable_illumination_norm: bool = True):
        pass

    def process(self, image_input: Any) -> Any:
        return image_input


class LocalOCREngine:
    def __init__(self, languages: Optional[List[str]] = None, gpu: Optional[bool] = None, min_confidence: float = 0.5):
        pass

    def recognize(self, image_input: Any) -> List[str]:
        return []


class LayoutAnalyzer:
    def analyze(self, ocr_results: Any) -> Any:
        return ocr_results


class MenuParser:
    def __init__(self, confidence_threshold: float = 0.5):
        pass

    def parse(self, layout_data: Any) -> RecognizedMenu:
        return RecognizedMenu(dishes=layout_data if isinstance(layout_data, list) else [])


class MenuVisualizer:
    pass


class GeminiMenuExtractor:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-3.6-flash")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def extract(self, image_input: Any) -> RecognizedMenu:
        from google import genai
        client = genai.Client(api_key=self.api_key)
        
        prompt = (
            "Extract all individual food items from this menu image. "
            "Return them strictly as a clean comma-separated list of items."
        )
        
        if isinstance(image_input, str):
            img = Image.open(image_input)
        elif isinstance(image_input, np.ndarray):
            img = Image.fromarray(image_input)
        else:
            img = image_input

        response = client.models.generate_content(
            model=self.model_name,
            contents=[prompt, img]
        )
        
        raw_text = response.text.strip() if response.text else ""
        items = [item.strip() for item in raw_text.split(",") if item.strip()]
        return RecognizedMenu(dishes=items, metadata={"extractor": "gemini-vision"})


class MenuRecognitionPipeline:
    """End-to-end pipeline for converting menu images into structured data."""

    def __init__(
        self,
        languages: Optional[List[str]] = None,
        gpu: Optional[bool] = None,
        enable_deskew: bool = True,
        enable_illumination_norm: bool = True,
        min_ocr_confidence: float = DEFAULT_MIN_OCR_CONFIDENCE,
        api_key: Optional[str] = None,
        prefer_gemini: bool = True,
    ):
        self.prefer_gemini = prefer_gemini
        effective_api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        self.gemini_extractor = GeminiMenuExtractor(api_key=effective_api_key)
        self.preprocessor = Preprocessor(
            enable_deskew=enable_deskew,
            enable_illumination_norm=enable_illumination_norm,
        )
        self.ocr_engine = LocalOCREngine(
            languages=languages,
            gpu=gpu,
            min_confidence=min_ocr_confidence,
        )
        self.layout_analyzer = LayoutAnalyzer()
        self.menu_parser = MenuParser(confidence_threshold=min_ocr_confidence)
        self.visualizer = MenuVisualizer()

    def process_image(
        self,
        image_input: Union[str, np.ndarray, Image.Image],
    ) -> RecognizedMenu:
        if self.prefer_gemini and self.gemini_extractor.is_available():
            try:
                return self.gemini_extractor.extract(image_input)
            except Exception as e:
                print(f"Warning: Gemini API extraction failed ({e}). Falling back to local OCR engine...")

        processed_image = self.preprocessor.process(image_input)
        ocr_results = self.ocr_engine.recognize(processed_image)
        layout_data = self.layout_analyzer.analyze(ocr_results)
        recognized_menu = self.menu_parser.parse(layout_data)
        
        return recognized_menu
