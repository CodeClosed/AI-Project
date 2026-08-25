"""
Unified Menu Recognition Pipeline and CLI entry point.
Orchestrates preprocessing, local deep OCR, layout analysis, semantic parsing, and visualization.
Supports in-memory PIL/bytes image inputs without leaving temporary files on disk.
"""

from typing import Optional, Union, Dict, Any, List
import argparse
import os
import sys
import time
import io
import cv2
import numpy as np
from PIL import Image

from .models import RecognizedMenu
from .preprocessing import Preprocessor
from .ocr_engine import LocalOCREngine
from .layout_analyzer import LayoutAnalyzer
from .menu_parser import MenuParser
from .gemini_extractor import GeminiMenuExtractor
from .visualizer import MenuVisualizer
from .config import DEFAULT_MIN_OCR_CONFIDENCE, get_gemini_api_key


class MenuRecognitionPipeline:
    """End-to-end pipeline for converting menu images into structured menu data."""

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
        self.gemini_extractor = GeminiMenuExtractor(api_key=api_key)
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
        image_input: Union[str, np.ndarray, Image.Image, io.BytesIO],
        visualize_path: Optional[str] = None,
        use_gemini: Optional[bool] = None,
    ) -> RecognizedMenu:
        """
        Runs the complete recognition pipeline on a menu image path, numpy array, PIL Image, or BytesIO.
        Uses Gemini Vision if configured and preferred, otherwise falls back to local PyTorch OCR engine.
        """
        should_use_gemini = (use_gemini if use_gemini is not None else self.prefer_gemini) and self.gemini_extractor.is_available()

        if should_use_gemini:
            try:
                recognized_menu = self.gemini_extractor.extract_menu(image_input)
                if visualize_path:
                    preprocessed_img, _ = self.preprocessor.process(image_input)
                    self.visualizer.save_visualization(preprocessed_img, recognized_menu, visualize_path)
                return recognized_menu
            except Exception as e:
                print(f"Warning: Gemini API extraction failed ({e}). Falling back to local OCR engine...", file=sys.stderr)

        start_time = time.time()

        # Step 1: Preprocessing & Image Validation
        preprocessed_img, prep_meta = self.preprocessor.process(image_input)
        h, w = preprocessed_img.shape[:2]

        # Step 2: Deep OCR Text Detection and Transcription
        raw_blocks = self.ocr_engine.detect_and_recognize(preprocessed_img)

        # Step 3: Spatial & Multi-column Layout Analysis
        structured_blocks, num_cols = self.layout_analyzer.analyze(raw_blocks, image_width=w, image_height=h)

        # Step 4: Semantic Menu Parsing (Items, Prices, Descriptions, Categories)
        img_name = image_input if isinstance(image_input, str) else "in_memory_image"
        recognized_menu = self.menu_parser.parse(
            blocks=structured_blocks,
            image_path=img_name,
            image_width=w,
            image_height=h,
            num_columns=num_cols,
        )
        recognized_menu.metadata["processing_time_sec"] = round(time.time() - start_time, 2)
        recognized_menu.metadata["active_ocr_device"] = self.ocr_engine.active_device

        # Step 5: Optional Visualization
        if visualize_path:
            self.visualizer.save_visualization(preprocessed_img, recognized_menu, visualize_path)

        return recognized_menu

    def extract_menu_items(
        self,
        image_input: Union[str, np.ndarray, Image.Image, io.BytesIO],
        use_gemini: Optional[bool] = None,
    ) -> List[str]:
        """
        Convenience method that scans a menu image and returns only the clean list of food item names.
        Example: ["Chicken Butter Masala", "Chips", "Mango", ...]
        """
        menu = self.process_image(image_input, use_gemini=use_gemini)
        return menu.get_item_names()


def main():
    parser = argparse.ArgumentParser(description="Menu Item Recognition & Layout Parsing CLI")
    parser.add_argument("--image", "-i", type=str, required=True, help="Path to input menu image file")
    parser.add_argument("--items-only", action="store_true", help="Print only the list of recognized food items")
    parser.add_argument("--gemini", action="store_true", help="Force use Gemini Flash Vision AI")
    parser.add_argument("--offline", action="store_true", help="Force use local offline PyTorch OCR engine")
    parser.add_argument("--api-key", type=str, default=None, help="Google Gemini API key")
    parser.add_argument("--output", "-o", type=str, default=None, help="Path to save output JSON")
    parser.add_argument("--visualize", "-v", type=str, default=None, help="Path to save annotated visual image")
    parser.add_argument("--markdown", "-m", type=str, default=None, help="Path to save Markdown summary")
    parser.add_argument("--cpu", action="store_true", help="Force CPU mode for OCR")
    parser.add_argument("--no-deskew", action="store_true", help="Disable auto-deskewing")

    args = parser.parse_args()

    if not os.path.exists(args.image):
        print(f"Error: Input image '{args.image}' not found.", file=sys.stderr)
        sys.exit(1)

    use_gemini = False if args.offline else (True if args.gemini else None)

    pipeline = MenuRecognitionPipeline(
        gpu=False if args.cpu else None,
        enable_deskew=not args.no_deskew,
        api_key=args.api_key,
        prefer_gemini=not args.offline,
    )

    if args.items_only:
        items = pipeline.extract_menu_items(args.image, use_gemini=use_gemini)
        for item in items:
            print(item)
        if args.output:
            import json
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
        return

    print(f"Processing menu image: {args.image} ...")
    menu = pipeline.process_image(args.image, visualize_path=args.visualize, use_gemini=use_gemini)

    print("\n" + "=" * 50)
    print(f"RECOGNITION COMPLETE: Found {menu.total_items} items in {len(menu.sections)} sections")
    print(f"Engine: {menu.metadata.get('extractor', 'Local-OCR')} | Model: {menu.metadata.get('model', 'CRAFT+CRNN')} | Device: {menu.metadata.get('active_ocr_device', 'cpu')}")
    print("=" * 50 + "\n")

    print("RECOGNIZED FOOD ITEMS:")
    for idx, name in enumerate(menu.get_item_names(), 1):
        print(f"  {idx}. {name}")

    print("\n" + "-" * 50 + "\n")
    print(menu.to_markdown())

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(menu.to_json())
        print(f"\n[+] Saved structured JSON to: {args.output}")

    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(menu.to_markdown())
        print(f"[+] Saved Markdown summary to: {args.markdown}")

    if args.visualize:
        print(f"[+] Saved annotated visualization to: {args.visualize}")


if __name__ == "__main__":
    main()
