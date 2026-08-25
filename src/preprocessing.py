"""
Image preprocessing and enhancement module for menu text recognition.
Provides deskewing, illumination normalization, contrast enhancement, and noise reduction.
Supports PIL Image objects, raw byte streams, numpy arrays, and file paths.
"""

from typing import Tuple, Optional, Dict, Any, Union
from pathlib import Path
import io
import numpy as np
import cv2
from PIL import Image


class Preprocessor:
    """Performs image enhancement and normalization on menu photos and scans."""

    def __init__(
        self,
        enable_deskew: bool = True,
        enable_illumination_norm: bool = True,
        enable_clahe: bool = True,
        max_dimension: int = 2400,
        min_dimension: int = 1400,
    ):

        self.enable_deskew = enable_deskew
        self.enable_illumination_norm = enable_illumination_norm
        self.enable_clahe = enable_clahe
        self.max_dimension = max_dimension
        self.min_dimension = min_dimension

    def resize_if_needed(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """Rescales the image to an optimal resolution range for text detection."""
        h, w = image.shape[:2]
        scale = 1.0

        if max(h, w) > self.max_dimension:
            scale = self.max_dimension / float(max(h, w))
        elif max(h, w) < self.min_dimension:
            scale = self.min_dimension / float(max(h, w))

        if scale != 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC)
            return resized, scale
        return image, scale

    def estimate_skew_angle(self, gray: np.ndarray) -> float:
        """Estimates skew angle in degrees using edge detection and Hough line transform."""
        try:
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(
                edges, 1, np.pi / 180, threshold=100, minLineLength=80, maxLineGap=10
            )
            if lines is None:
                return 0.0

            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                # Only consider near-horizontal lines (-30 to +30 deg)
                if -30.0 <= angle <= 30.0:
                    angles.append(angle)

            if not angles:
                return 0.0

            median_angle = float(np.median(angles))
            return median_angle
        except Exception:
            return 0.0

    def rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Rotates an image by a specified angle while expanding boundaries to prevent cropping."""
        h, w = image.shape[:2]
        center = (w // 2, h // 2)

        rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
        cos = np.abs(rot_mat[0, 0])
        sin = np.abs(rot_mat[0, 1])

        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))

        rot_mat[0, 2] += (new_w / 2) - center[0]
        rot_mat[1, 2] += (new_h / 2) - center[1]

        rotated = cv2.warpAffine(
            image,
            rot_mat,
            (new_w, new_h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return rotated

    def normalize_illumination(self, image: np.ndarray) -> np.ndarray:
        """Removes shadows and uneven background lighting using morphological background division."""
        if len(image.shape) == 3:
            planes = cv2.split(image)
            norm_planes = []
            for plane in planes:
                dilated = cv2.dilate(plane, np.ones((7, 7), np.uint8))
                bg = cv2.medianBlur(dilated, 21)
                diff = 255 - cv2.absdiff(plane, bg)
                norm = cv2.normalize(
                    diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U
                )
                norm_planes.append(norm)
            return cv2.merge(norm_planes)
        else:
            dilated = cv2.dilate(image, np.ones((7, 7), np.uint8))
            bg = cv2.medianBlur(dilated, 21)
            diff = 255 - cv2.absdiff(image, bg)
            return cv2.normalize(
                diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U
            )

    def apply_clahe(self, image: np.ndarray) -> np.ndarray:
        """Applies Contrast Limited Adaptive Histogram Equalization to boost faint menu text."""
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l_clahe = clahe.apply(l)
            lab_clahe = cv2.merge((l_clahe, a, b))
            return cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)
        else:
            return clahe.apply(image)

    def sharpen_text(self, image: np.ndarray) -> np.ndarray:
        """Applies unsharp masking to enhance text character edges."""
        gaussian = cv2.GaussianBlur(image, (0, 0), sigmaX=1.5)
        sharpened = cv2.addWeighted(image, 1.4, gaussian, -0.4, 0)
        return sharpened

    def process(
        self,
        image_input: Union[str, Path, np.ndarray, bytes, bytearray, Image.Image, io.BytesIO],
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Runs the full preprocessing pipeline on input image.
        Accepts PIL Image, file paths, numpy arrays, BytesIO, or raw bytes.
        Returns: (preprocessed_bgr_image, metadata_dict)
        """
        if isinstance(image_input, Image.Image):
            pil_rgb = image_input.convert("RGB")
            image = cv2.cvtColor(np.array(pil_rgb), cv2.COLOR_RGB2BGR)
        elif isinstance(image_input, io.BytesIO):
            image_input.seek(0)
            file_bytes = np.frombuffer(image_input.read(), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if image is None:
                pil_rgb = Image.open(image_input).convert("RGB")
                image = cv2.cvtColor(np.array(pil_rgb), cv2.COLOR_RGB2BGR)
        elif isinstance(image_input, (bytes, bytearray)):
            file_bytes = np.frombuffer(image_input, dtype=np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Could not decode image from provided byte buffer.")
        elif isinstance(image_input, (str, Path)):
            image_path_str = str(image_input)
            try:
                pil_img = Image.open(image_path_str).convert("RGB")
                image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            except Exception:
                try:
                    with open(image_path_str, "rb") as f:
                        file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
                        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                except Exception:
                    image = cv2.imread(image_path_str)

            if image is None:
                raise ValueError(f"Could not read image file from path: {image_input}")
        elif isinstance(image_input, np.ndarray):
            if len(image_input.shape) == 2:
                image = cv2.cvtColor(image_input, cv2.COLOR_GRAY2BGR)
            elif image_input.shape[2] == 4:
                image = cv2.cvtColor(image_input, cv2.COLOR_BGRA2BGR)
            else:
                image = image_input.copy()
        else:
            raise TypeError(f"Unsupported image input type: {type(image_input)}")

        orig_h, orig_w = image.shape[:2]
        metadata: Dict[str, Any] = {
            "original_width": orig_w,
            "original_height": orig_h,
            "skew_angle": 0.0,
            "scale_factor": 1.0,
        }

        # Step 1: Scale to optimal working resolution
        resized, scale = self.resize_if_needed(image)
        metadata["scale_factor"] = scale

        # Step 2: Invert if dark background (white text on dark background)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY) if len(resized.shape) == 3 else resized
        if np.mean(gray) < 115:
            resized = cv2.bitwise_not(resized)
            metadata["inverted_dark_background"] = True

        # Step 3: Deskew if enabled
        if self.enable_deskew:
            gray_for_skew = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY) if len(resized.shape) == 3 else resized
            angle = self.estimate_skew_angle(gray_for_skew)
            metadata["skew_angle"] = angle
            if abs(angle) >= 0.5:
                resized = self.rotate_image(resized, angle)

        # Step 4: Illumination leveling if enabled
        if self.enable_illumination_norm:
            try:
                resized = self.normalize_illumination(resized)
            except Exception:
                pass

        # Step 5: CLAHE Contrast enhancement
        if self.enable_clahe:
            resized = self.apply_clahe(resized)

        # Step 6: Text edge sharpening
        resized = self.sharpen_text(resized)

        metadata["processed_width"] = resized.shape[1]
        metadata["processed_height"] = resized.shape[0]

        return resized, metadata
