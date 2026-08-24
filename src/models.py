"""
Data models for the Menu Item Recognition System.
Defines strongly-typed representations for bounding boxes, text blocks, menu items, sections, and full menus.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple, Dict, Any
import json


@dataclass
class BoundingBox:
    """Represents a 2D bounding box with coordinate math and geometry utilities."""
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    polygon: Optional[List[List[float]]] = None

    @classmethod
    def from_polygon(cls, polygon: List[List[float]]) -> BoundingBox:
        xs = [pt[0] for pt in polygon]
        ys = [pt[1] for pt in polygon]
        return cls(
            x_min=float(min(xs)),
            y_min=float(min(ys)),
            x_max=float(max(xs)),
            y_max=float(max(ys)),
            polygon=polygon,
        )

    @classmethod
    def from_xywh(cls, x: float, y: float, w: float, h: float) -> BoundingBox:
        return cls(
            x_min=float(x),
            y_min=float(y),
            x_max=float(x + w),
            y_max=float(y + h),
            polygon=[[x, y], [x + w, y], [x + w, y + h], [x, y + h]],
        )

    @property
    def width(self) -> float:
        return max(0.0, self.x_max - self.x_min)

    @property
    def height(self) -> float:
        return max(0.0, self.y_max - self.y_min)

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x_min + self.x_max) / 2.0, (self.y_min + self.y_max) / 2.0)

    @property
    def area(self) -> float:
        return self.width * self.height

    def union(self, other: BoundingBox) -> BoundingBox:
        """Returns the bounding box enclosing both self and other."""
        return BoundingBox(
            x_min=min(self.x_min, other.x_min),
            y_min=min(self.y_min, other.y_min),
            x_max=max(self.x_max, other.x_max),
            y_max=max(self.y_max, other.y_max),
        )

    def vertical_overlap(self, other: BoundingBox) -> float:
        """Calculates vertical intersection over the minimum height."""
        overlap = max(0.0, min(self.y_max, other.y_max) - max(self.y_min, other.y_min))
        min_h = min(self.height, other.height)
        return overlap / min_h if min_h > 0 else 0.0

    def horizontal_distance(self, other: BoundingBox) -> float:
        """Horizontal gap between boxes (0 if overlapping horizontally)."""
        if self.x_max < other.x_min:
            return other.x_min - self.x_max
        elif other.x_max < self.x_min:
            return self.x_min - other.x_max
        return 0.0

    def vertical_distance(self, other: BoundingBox) -> float:
        """Vertical gap between boxes (0 if overlapping vertically)."""
        if self.y_max < other.y_min:
            return other.y_min - self.y_max
        elif other.y_max < self.y_min:
            return self.y_min - other.y_max
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x_min": round(self.x_min, 2),
            "y_min": round(self.y_min, 2),
            "x_max": round(self.x_max, 2),
            "y_max": round(self.y_max, 2),
            "width": round(self.width, 2),
            "height": round(self.height, 2),
        }


@dataclass
class TextBlock:
    """Represents a recognized text segment from OCR with spatial coordinates."""
    text: str
    bbox: BoundingBox
    confidence: float
    column_id: int = 0
    line_id: int = 0
    is_price: bool = False
    is_header_candidate: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": round(self.confidence, 4),
            "bbox": self.bbox.to_dict(),
            "column_id": self.column_id,
            "line_id": self.line_id,
            "is_price": self.is_price,
            "is_header_candidate": self.is_header_candidate,
        }


@dataclass
class MenuItem:
    """Represents a structured restaurant menu item with name, price, description, and tags."""
    name: str
    price: Optional[float] = None
    raw_price: Optional[str] = None
    currency: Optional[str] = None
    description: Optional[str] = None
    section: Optional[str] = None
    dietary_tags: List[str] = field(default_factory=list)
    confidence: float = 1.0
    bbox: Optional[BoundingBox] = None
    price_bbox: Optional[BoundingBox] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "price": self.price,
            "raw_price": self.raw_price,
            "currency": self.currency,
            "description": self.description,
            "section": self.section,
            "dietary_tags": self.dietary_tags,
            "confidence": round(self.confidence, 4),
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "price_bbox": self.price_bbox.to_dict() if self.price_bbox else None,
        }


@dataclass
class MenuSection:
    """Represents a categorized menu section containing a title and associated items."""
    title: str
    items: List[MenuItem] = field(default_factory=list)
    bbox: Optional[BoundingBox] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "item_count": len(self.items),
            "items": [item.to_dict() for item in self.items],
            "bbox": self.bbox.to_dict() if self.bbox else None,
        }


@dataclass
class RecognizedMenu:
    """The root output model representing the entire structured recognized menu."""
    image_path: str
    image_width: int
    image_height: int
    num_columns: int
    sections: List[MenuSection] = field(default_factory=list)
    unclassified_items: List[MenuItem] = field(default_factory=list)
    raw_blocks: List[TextBlock] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_items(self) -> int:
        return sum(len(s.items) for s in self.sections) + len(self.unclassified_items)

    def to_flat_items(self) -> List[MenuItem]:
        all_items = []
        for s in self.sections:
            all_items.extend(s.items)
        all_items.extend(self.unclassified_items)
        return all_items

    def get_all_items(self) -> List[MenuItem]:
        """Alias for to_flat_items."""
        return self.to_flat_items()

    NON_DISH_WORDS = {
        "menu", "your logo", "logo", "your company name", "your company number",
        "for take-outs", "for takeouts", "for take-out", "for takeout",
        "available every", "take-outs", "takeouts", "dine-in", "delivery",
        "timings", "opening hours", "contact us", "y", "x"
    }

    def get_item_names(self) -> List[str]:
        """Returns a clean list of recognized food item names only."""
        names = []
        seen = set()
        for item in self.to_flat_items():
            name = item.name.strip()
            lower = name.lower()
            # Filter noise, single chars, bracket placeholders, and non-food lines
            if len(name) <= 1:
                continue
            if lower in self.NON_DISH_WORDS:
                continue
            if "[" in name and "]" in name and any(k in lower for k in ["company", "number", "name", "logo", "address", "phone", "email"]):
                continue
            if any(k in lower for k in ["available every", "for take-out", "for take away", "for delivery", "indulge in refinement"]):
                continue
            if lower not in seen:
                seen.add(lower)
                names.append(name)
        return names


    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_path": self.image_path,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "num_columns": self.num_columns,
            "total_items": self.total_items,
            "item_names_only": self.get_item_names(),
            "sections": [sec.to_dict() for sec in self.sections],
            "unclassified_items": [item.to_dict() for item in self.unclassified_items],
            "metadata": self.metadata,
        }


    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        lines = [f"# Recognized Menu ({self.total_items} items)", ""]
        for section in self.sections:
            lines.append(f"## {section.title}")
            for item in section.items:
                price_str = f" - {item.raw_price}" if item.raw_price else ""
                tags_str = f" `[{', '.join(item.dietary_tags)}]`" if item.dietary_tags else ""
                lines.append(f"- **{item.name}**{price_str}{tags_str}")
                if item.description:
                    lines.append(f"  *_{item.description}_*")
            lines.append("")
        if self.unclassified_items:
            lines.append("## Other Items")
            for item in self.unclassified_items:
                price_str = f" - {item.raw_price}" if item.raw_price else ""
                tags_str = f" `[{', '.join(item.dietary_tags)}]`" if item.dietary_tags else ""
                lines.append(f"- **{item.name}**{price_str}{tags_str}")
                if item.description:
                    lines.append(f"  *_{item.description}_*")
            lines.append("")
        return "\n".join(lines)
