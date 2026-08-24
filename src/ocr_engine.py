"""
Local deep learning OCR engine using PyTorch and EasyOCR (CRAFT detector + CRNN recognizer).
Operates completely offline without external cloud APIs.
"""

from typing import List, Tuple, Optional
import re
import numpy as np
import torch
import easyocr

from .models import BoundingBox, TextBlock


class LocalOCREngine:
    """Wraps local deep learning OCR models to detect and transcribe text blocks."""

    def __init__(
        self,
        languages: Optional[List[str]] = None,
        gpu: Optional[bool] = None,
        min_confidence: float = 0.20,
    ):
        if languages is None:
            languages = ["en"]
        
        if gpu is None:
            gpu = torch.cuda.is_available()

        self.gpu = gpu
        self.min_confidence = min_confidence
        self.languages = languages
        
        # Initialize EasyOCR reader (downloads model weights to ~/.EasyOCR on first run and caches locally)
        self.reader = easyocr.Reader(
            lang_list=self.languages,
            gpu=self.gpu,
            verbose=False,
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
        # EasyOCR expects RGB or BGR numpy array
        raw_results = self.reader.readtext(
            image,
            paragraph=False,
            detail=1,
            contrast_ths=0.1,
            adjust_contrast=0.5,
            text_threshold=0.6,
            low_text=0.3,
        )

        blocks: List[TextBlock] = []
        for polygon_pts, raw_text, conf in raw_results:
            cleaned = self.clean_text(raw_text)
            if not cleaned or conf < self.min_confidence:
                continue

            # polygon_pts is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            poly = [[float(pt[0]), float(pt[1])] for pt in polygon_pts]
            bbox = BoundingBox.from_polygon(poly)

            # Skip tiny noisy detections (< 3 pixels height or width)
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
