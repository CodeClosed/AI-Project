"""
Spatial and geometric layout analyzer for restaurant menus.
Handles column partitioning, reading order reconstruction, horizontal line merging, and visual structure analysis.
"""

from typing import List, Tuple, Dict, Any, Optional
import re
import numpy as np
from .models import BoundingBox, TextBlock



class LayoutAnalyzer:
    """Analyzes spatial layout of text blocks on menus (multi-column, reading order, lines)."""

    def __init__(
        self,
        vertical_overlap_threshold: float = 0.45,
        line_merge_max_gap_multiplier: float = 2.5,
        column_gutter_min_width: float = 40.0,
    ):
        self.vertical_overlap_threshold = vertical_overlap_threshold
        self.line_merge_max_gap_multiplier = line_merge_max_gap_multiplier
        self.column_gutter_min_width = column_gutter_min_width

    def detect_columns(
        self, blocks: List[TextBlock], image_width: int
    ) -> Tuple[List[TextBlock], int]:
        """
        Partitions text blocks into columns based on horizontal positions and gutters.
        Assigns `column_id` to each TextBlock.
        """
        if not blocks:
            return blocks, 1

        # Calculate horizontal centers and spans
        x_centers = [b.bbox.center[0] for b in blocks]
        x_mins = [b.bbox.x_min for b in blocks]
        x_maxs = [b.bbox.x_max for b in blocks]

        # Look for multi-column split if we have enough blocks and wide enough image
        if len(blocks) < 6:
            for b in blocks:
                b.column_id = 0
            return blocks, 1

        # Check if there is a strong 2-column or 3-column split
        # We construct a horizontal coverage histogram
        hist = np.zeros(image_width, dtype=np.int32)
        for b in blocks:
            start = max(0, int(b.bbox.x_min))
            end = min(image_width, int(b.bbox.x_max))
            if end > start:
                hist[start:end] += 1

        min_x = int(image_width * 0.15)
        max_x = int(image_width * 0.85)
        
        # Smoothed histogram
        window = 35
        smoothed = np.convolve(hist, np.ones(window) / window, mode="same")
        mid_smoothed = smoothed[min_x:max_x]

        split_points = []
        if len(mid_smoothed) > 0:
            avg_density = np.mean(smoothed)
            threshold = max(1.0, avg_density * 0.20)
            
            # Find contiguous valleys below threshold with width >= column_gutter_min_width
            in_valley = False
            valley_start = 0
            for idx, val in enumerate(mid_smoothed):
                actual_x = min_x + idx
                if val < threshold and not in_valley:
                    in_valley = True
                    valley_start = actual_x
                elif val >= threshold and in_valley:
                    in_valley = False
                    valley_width = actual_x - valley_start
                    if valley_width >= self.column_gutter_min_width:
                        split_points.append((valley_start + actual_x) // 2)

        # Assign initial column IDs based on split points
        if not split_points:
            for b in blocks:
                b.column_id = 0
            return blocks, 1

        # Assign column IDs
        for b in blocks:
            c_x = b.bbox.center[0]
            col = 0
            for sp in split_points:
                if c_x >= sp:
                    col += 1
            b.column_id = col

        # Post-process columns: If a column consists predominantly of standalone prices/numbers
        # or short tokens without substantial text, merge it with the column immediately to its left!
        num_cols = len(split_points) + 1
        cols_to_merge = {}
        for c in range(num_cols):
            c_blocks = [b for b in blocks if b.column_id == c]
            if not c_blocks:
                continue
            # Check if this column is merely a price column (short text or price digits)
            is_price_like = sum(1 for b in c_blocks if re.search(r"^[\$£€¥Ss]?\s*\d+[.,]?\d*$", b.text.strip()) or len(b.text.strip()) <= 6)
            price_ratio = is_price_like / len(c_blocks)
            if price_ratio >= 0.65 and c > 0:
                cols_to_merge[c] = c - 1

        if cols_to_merge:
            for b in blocks:
                if b.column_id in cols_to_merge:
                    b.column_id = cols_to_merge[b.column_id]

            # Re-index columns consecutively
            unique_cols = sorted(list(set(b.column_id for b in blocks)))
            col_map = {old_c: new_c for new_c, old_c in enumerate(unique_cols)}
            for b in blocks:
                b.column_id = col_map[b.column_id]
            num_cols = len(unique_cols)

        return blocks, num_cols


    def sort_reading_order(self, blocks: List[TextBlock]) -> List[TextBlock]:
        """
        Sorts text blocks in natural reading order:
        First by column_id (left to right), then vertically (top to bottom).
        """
        return sorted(blocks, key=lambda b: (b.column_id, b.bbox.y_min, b.bbox.x_min))

    def merge_horizontal_lines(self, blocks: List[TextBlock]) -> List[TextBlock]:
        """
        Groups adjacent word fragments on the same line within each column into unified text blocks.
        """
        if not blocks:
            return []

        # Group by column
        columns_dict: Dict[int, List[TextBlock]] = {}
        for b in blocks:
            columns_dict.setdefault(b.column_id, []).append(b)

        merged_blocks: List[TextBlock] = []

        for col_id, col_blocks in sorted(columns_dict.items()):
            # Sort vertically first
            sorted_blocks = sorted(col_blocks, key=lambda b: b.bbox.y_min)
            
            lines: List[List[TextBlock]] = []
            for b in sorted_blocks:
                matched = False
                for line in lines:
                    base_block = line[0]
                    base_y = base_block.bbox.center[1]
                    base_h = base_block.bbox.height
                    
                    # Exact line check against original line anchor (prevents vertical snowballing)
                    y_diff = abs(b.bbox.center[1] - base_y)
                    v_overlap = b.bbox.vertical_overlap(base_block.bbox)

                    if y_diff <= (base_h * 0.45) or v_overlap >= 0.40:
                        line.append(b)
                        matched = True
                        break

                if not matched:
                    lines.append([b])


            # Sort lines vertically
            lines.sort(key=lambda line: min(b.bbox.y_min for b in line))

            # Now, for each line, sort words horizontally and create a unified line block
            line_idx = 0
            for line in lines:
                sorted_line = sorted(line, key=lambda b: b.bbox.x_min)
                merged_line_block = self._create_merged_block(sorted_line, col_id, line_idx)
                merged_blocks.append(merged_line_block)
                line_idx += 1

        return self.sort_reading_order(merged_blocks)


    def _create_merged_block(self, group: List[TextBlock], column_id: int, line_id: int) -> TextBlock:
        if len(group) == 1:
            b = group[0]
            b.column_id = column_id
            b.line_id = line_id
            return b

        merged_text = " ".join(b.text for b in group)
        merged_bbox = group[0].bbox
        for b in group[1:]:
            merged_bbox = merged_bbox.union(b.bbox)

        avg_conf = sum(b.confidence for b in group) / len(group)
        return TextBlock(
            text=merged_text,
            bbox=merged_bbox,
            confidence=avg_conf,
            column_id=column_id,
            line_id=line_id,
        )

    def analyze(self, raw_blocks: List[TextBlock], image_width: int, image_height: int) -> Tuple[List[TextBlock], int]:
        """
        Runs full layout analysis pipeline:
        1. Multi-column partitioning
        2. Horizontal line grouping and merging
        3. Sorting into reading order
        """
        blocks_with_cols, num_cols = self.detect_columns(raw_blocks, image_width)
        merged = self.merge_horizontal_lines(blocks_with_cols)
        return merged, num_cols
