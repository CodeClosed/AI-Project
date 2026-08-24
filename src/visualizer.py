"""
Visualizer and diagnostic tool for menu item recognition.
Overlays bounding boxes, category tags, price links, and column dividers on menu images.
"""

from typing import Optional
import os
import numpy as np
import cv2
from .models import RecognizedMenu, BoundingBox



class MenuVisualizer:
    """Renders visual diagnostic overlays on menu images."""

    COLOR_HEADER = (180, 50, 220)       # Purple
    COLOR_ITEM = (230, 100, 30)         # Blue
    COLOR_PRICE = (30, 200, 40)         # Green
    COLOR_DESC = (0, 165, 255)          # Orange
    COLOR_COLUMN = (150, 150, 150)      # Gray
    COLOR_LINK = (255, 255, 0)          # Cyan

    def draw_bbox(
        self,
        image: np.ndarray,
        bbox: BoundingBox,
        color: tuple,
        label: Optional[str] = None,
        thickness: int = 2,
    ) -> None:
        """Draws a labeled rectangle on the image."""
        x1, y1 = int(bbox.x_min), int(bbox.y_min)
        x2, y2 = int(bbox.x_max), int(bbox.y_max)

        cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)

        if label:
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.45
            font_thickness = 1
            (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
            
            # Draw solid background for label readability
            lbl_y1 = max(0, y1 - text_h - 6)
            lbl_y2 = y1
            cv2.rectangle(image, (x1, lbl_y1), (x1 + text_w + 6, lbl_y2), color, -1)
            cv2.putText(
                image,
                label,
                (x1 + 3, lbl_y2 - 3),
                font,
                font_scale,
                (255, 255, 255),
                font_thickness,
                cv2.LINE_AA,
            )

    def draw_connection_line(
        self,
        image: np.ndarray,
        bbox1: BoundingBox,
        bbox2: BoundingBox,
        color: tuple,
    ) -> None:
        """Draws an arrowed line connecting an item and its associated price."""
        pt1 = (int(bbox1.x_max), int((bbox1.y_min + bbox1.y_max) / 2))
        pt2 = (int(bbox2.x_min), int((bbox2.y_min + bbox2.y_max) / 2))
        cv2.arrowedLine(image, pt1, pt2, color, 1, tipLength=0.2)

    def visualize(self, image: np.ndarray, menu: RecognizedMenu) -> np.ndarray:
        """
        Creates an annotated visual copy of the image highlighting recognized entities.
        """
        annotated = image.copy()

        # Draw Section Headers
        for section in menu.sections:
            if section.bbox:
                self.draw_bbox(annotated, section.bbox, self.COLOR_HEADER, f"SECTION: {section.title}", thickness=2)

            for item in section.items:
                if item.bbox:
                    label = f"ITEM: {item.name[:20]}"
                    if item.dietary_tags:
                        label += f" [{' '.join(item.dietary_tags)}]"
                    self.draw_bbox(annotated, item.bbox, self.COLOR_ITEM, label, thickness=2)

                if item.price_bbox:
                    self.draw_bbox(annotated, item.price_bbox, self.COLOR_PRICE, f"${item.price:.2f}" if item.price else "PRICE", thickness=2)
                    if item.bbox:
                        self.draw_connection_line(annotated, item.bbox, item.price_bbox, self.COLOR_LINK)

        # Draw unclassified items
        for item in menu.unclassified_items:
            if item.bbox:
                self.draw_bbox(annotated, item.bbox, self.COLOR_ITEM, f"ITEM: {item.name[:20]}", thickness=1)
            if item.price_bbox:
                self.draw_bbox(annotated, item.price_bbox, self.COLOR_PRICE, f"PRICE: {item.raw_price}", thickness=1)

        return annotated

    def save_visualization(self, image: np.ndarray, menu: RecognizedMenu, output_path: str) -> None:
        """Renders and saves the diagnostic visualization image to disk."""
        annotated = self.visualize(image, menu)
        ext = os.path.splitext(output_path)[1] or ".jpg"
        success, encoded_img = cv2.imencode(ext, annotated)
        if success:
            with open(output_path, "wb") as f:
                f.write(encoded_img.tobytes())
        else:
            cv2.imwrite(output_path, annotated)

