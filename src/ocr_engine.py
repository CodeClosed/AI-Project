"""
Local deep learning OCR engine using PyTorch and EasyOCR (CRAFT detector + CRNN recognizer).
Operates completely offline without external cloud APIs.
Includes automatic GPU-to-CPU fallback, device reporting, and graceful initialization.
"""

from typing import List, Tuple, Optional
import re
import logging
import numpy as np
import torch

from .models import BoundingBox, TextBlock
from .config import DEFAULT_OCR_LANGUAGES, DEFAULT_MIN_OCR_CONFIDENCE

logger = logging.getLogger(__name__)


class LocalOCREngine:
    """Wraps local deep learning OCR models to detect and transcribe text blocks."""

    def __init__(
        self,
        languages: Optional[List[str]] = None,
        gpu: Optional[bool] = None,
        min_confidence: float = DEFAULT_MIN_OCR_CONFIDENCE,
    ):
        self.languages = languages or DEFAULT_OCR_LANGUAGES
        self.min_confidence = min_confidence
        self.active_device = "cpu"
        self.reader = None

        self._initialize_reader(gpu=gpu)

    def _initialize_reader(self, gpu: Optional[bool] = None):
        """Initializes EasyOCR reader with robust GPU-to-CPU fallback."""
        try:
            import easyocr
        except ImportError:
            raise RuntimeError(
                "EasyOCR is not installed. Please install it using 'pip install easyocr'."
            )

        desired_gpu = torch.cuda.is_available() if gpu is None else bool(gpu and torch.cuda.is_available())

        if desired_gpu:
            try:
                self.reader = easyocr.Reader(
                    lang_list=self.languages,
                    gpu=True,
                    verbose=False,
                )
                self.active_device = "cuda"
                logger.info("EasyOCR initialized successfully on GPU (CUDA).")
                return
            except Exception as e:
                logger.warning(
                    "EasyOCR GPU initialization failed (%s). Falling back gracefully to CPU mode.", e
                )

        # CPU Mode
        try:
            self.reader = easyocr.Reader(
                lang_list=self.languages,
                gpu=False,
                verbose=False,
            )
            self.active_device = "cpu"
            logger.info("EasyOCR initialized successfully on CPU.")
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize EasyOCR reader on CPU ({e}). Check your network connection for initial model download or verify torch installation."
            )

    def clean_text(self, text: str) -> str:
        """Cleans and standardizes raw OCR text."""
        # Replace unusual whitespace/control characters
        text = re.sub(r"[\r\n\t]+", " ", text).strip()
        # Clean repetitive dots/dashes used as menu fill lines (leader dots)
        text = re.sub(r"\.{3,}", " ... ", text)
        text = re.sub(r"-{3,}", " --- ", text)
        text = re.sub(r"_{3,}", " ___ ", text)
        # Normalize multiple spaces
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def detect_and_recognize(self, image: np.ndarray) -> List[TextBlock]:
        """
        Runs deep OCR detection and recognition on an image array (BGR or RGB).
        Returns a list of structured TextBlock objects.
        """
        if self.reader is None:
            raise RuntimeError("OCR reader is not initialized.")

        if image is None or not isinstance(image, np.ndarray) or image.size == 0:
            return []

        try:
            raw_results = self.reader.readtext(
                image,
                paragraph=False,
                detail=1,
                contrast_ths=0.1,
                adjust_contrast=0.5,
                text_threshold=0.6,
                low_text=0.3,
            )
        except Exception as e:
            logger.error("EasyOCR inference error: %s", e)
            return []

        blocks: List[TextBlock] = []
        for polygon_pts, raw_text, conf in raw_results:
            cleaned = self.clean_text(raw_text)
            if not cleaned or float(conf) < self.min_confidence:
                continue

            # polygon_pts is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            try:
                poly = [[float(pt[0]), float(pt[1])] for pt in polygon_pts]
                bbox = BoundingBox.from_polygon(poly)
            except Exception:
                continue

            # Skip tiny noisy detections (< 4 pixels height or width)
            if bbox.height < 4 or bbox.width < 4:
                continue

            blocks.append(
                TextBlock(
                    text=cleaned,
                    bbox=bbox,
                    confidence=float(conf),
                )
            )

        return blocks
