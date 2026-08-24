"""
Semantic parser for extracting structured menu items, prices, descriptions, and categories.
Associates items geometrically with prices, descriptions, and dietary tags.
"""

from typing import List, Dict, Tuple, Optional, Any
import re
import difflib
import numpy as np
from .models import BoundingBox, TextBlock, MenuItem, MenuSection, RecognizedMenu



class MenuParser:
    """Extracts structured menu items, categories, prices, and descriptions from analyzed text blocks."""

    # Common restaurant section titles and keywords
    KNOWN_SECTIONS = {
        "appetizers", "starters", "small plates", "shareables", "tapas", "snacks", "snack",
        "mains", "main courses", "entrees", "entrées", "house specials", "chef specials",
        "dinner specials", "lunch specials", "daily specials", "today specials", "specials",
        "salads", "soups", "sides", "side dishes", "accompaniments",
        "burger", "burgers", "sandwich", "sandwiches", "roll", "rolls", "bun", "buns",
        "fries", "fry", "nuggets", "wraps", "pasta", "pizzas", "pizza",
        "steaks", "seafood", "grill", "bbq", "tacos", "noodles", "rice", "momos", "chaat",
        "desserts", "sweets", "ice cream", "beverages", "beverage", "drinks", "shakes",
        "cocktails", "mocktails", "wine", "beer", "hot drinks", "coffee", "tea",
        "breakfast", "brunch", "lunch", "dinner", "kids menu", "combo", "combos",
        "chinese", "continental", "tandoori", "indian", "south indian", "north indian",
        "punjabi", "mughlai", "thai", "mexican", "italian", "breads", "biryani", "rice & noodles"
    }

    # Dietary tags patterns
    DIETARY_PATTERNS = [
        (r"\b(v|vg|veg|vegetarian)\b", "Vegetarian"),
        (r"\b(vegan)\b", "Vegan"),
        (r"\b(gf|gluten[- ]free)\b", "Gluten-Free"),
        (r"\b(df|dairy[- ]free)\b", "Dairy-Free"),
        (r"\b(halal)\b", "Halal"),
        (r"\b(spicy|hot|mild)\b", "Spicy"),
        (r"\b(keto|low[- ]carb)\b", "Keto"),
        (r"\b(nuts|contains nuts|nut[- ]free)\b", "Nuts"),
    ]

    # Non-food metadata lines to filter out (business info, timings, slogans, templates, footer noise)
    NON_FOOD_PATTERNS = [
        r"\b(phone|tel|mobile|call|contact|email|website|www\.|http|\.com|\.in|\.org)\b",
        r"\b(gst|vat|tax|taxes|service charge|fssai|license|lic no|govt)\b",
        r"\b(address|road|street|nagar|colony|opp|near|floor|cross|lane|pin\s*code)\b",
        r"\b(terms & conditions|conditions apply|all rights reserved|thank you|visit again)\b",
        r"\b(opening hours|timings?|available\s+every|available\s+daily|available\s+on|mon|tue|wed|thu|fri|sat|sun|am|pm)\b",
        r"\b(take[- ]?outs?|take[- ]?away|delivery|pick[- ]?up|order\s+online|dine[- ]?in)\b",
        r"\b(company\s+name|company\s+number|your\s+logo|your\s+company|logo|slogan|tagline|refinement|indulge)\b",
        r"\[.*?(company|logo|number|phone|name|address|website|email).*?\]",
        r"^\s*\(.*?(additional|extra|with cheese|add-on|addon|toppings?).*?\)\s*$", # Add-on notes
        r"\badditional\s+(rs|re|ro|\₹|\$)\b",
        r"^\s*(\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\s*$", # Phone number
        r"^\s*[\d:apm -]{5,25}\s*$", # Time string like 6:00 PM - 8:00 PM
        r"^\s*menu\s*$", # Top header 'MENU'
        r"^\s*your\s*$",
        r"^\s*[a-zA-Z]\s*$", # Single stray letter like 'Y'
    ]

    # Currency symbols and common OCR misclassifications (including ₹, Rs, Re, Ro, /-)
    CURRENCY_SYMBOLS = r"[\$\£\€\₹\¥]|USD|EUR|GBP|INR|Rs\.?|Re\.?|Ro\.?|CAD|AUD|[Ss](?=\s*\d)"
    PRICE_PATTERN = re.compile(
        r"(?:(" + CURRENCY_SYMBOLS + r")\s*)?(\d{1,4}(?:[.,]\d{2})?|\d{1,4}(?:\.-|-|\/-))\s*(?:(" + CURRENCY_SYMBOLS + r"|\/-))?",
        re.IGNORECASE
    )
    STANDALONE_PRICE_PATTERN = re.compile(
        r"^(?:(" + CURRENCY_SYMBOLS + r")\s*)?(\d{1,4}(?:[.,]\d{2})?|\d{1,4}(?:\.-|-|\/-))\s*(?:(" + CURRENCY_SYMBOLS + r"|\/-))?$",
        re.IGNORECASE
    )



    def __init__(self, confidence_threshold: float = 0.3):
        self.confidence_threshold = confidence_threshold

    RESTAURANT_TITLE_WORDS = {"restaurant", "trattoria", "bistro", "cafe", "kitchen", "grill", "bar & grill", "pizzeria", "the bistro"}

    # Ingredients / food descriptors that indicate a menu item, NOT a category section
    FOOD_ITEM_PREFIXES = {
        "chicken", "veg", "vegetarian", "vegan", "egg", "paneer", "mutton", "fish", "prawn",
        "cheese", "beef", "pork", "mushroom", "tofu", "garlic", "butter", "spicy", "crispy", "grilled"
    }


    def normalize_ocr_price_string(self, text: str) -> str:
        """Fixes common OCR misrecognitions like '8180', '7120', '<230', 'r90', 'S 12.50' where ₹/$ was misread."""
        # Replace leading 'S ' or 's ' before digits with '$'
        text = re.sub(r"\b[Ss]\s*(\d+[.,]\d{2})\b", r"$\1", text)
        # Fix OCR misreading ₹ as 8, 7, <, {, r, * before 2-3 digit price numbers at end of line (e.g. 8180 -> 180, 7120 -> 120, r90 -> 90)
        text = re.sub(r"[\s<>{*~|]+[87<r{\*](\d{2,3})\b", r" ₹\1", text)
        text = re.sub(r"\b[87<r{\*](\d{2,3})\s*$", r"₹\1", text)
        # Fix 5xx.xx where 5 was '$' (e.g. 532.00 -> $32.00, 58.50 -> $8.50)
        text = re.sub(r"\b5(\d{1,2}[.,]\d{2})\b", r"$\1", text)
        return text

    def extract_price(self, text: str) -> Tuple[Optional[float], Optional[str], Optional[str], str]:
        """
        Extracts price value, formatted price string, currency, and remaining text.
        Returns: (price_float, raw_price_str, currency, text_without_price)
        """
        text = self.normalize_ocr_price_string(text)
        matches = list(self.PRICE_PATTERN.finditer(text))
        if not matches:
            return None, None, None, text

        # Prioritize the rightmost match (standard menu layout)
        match = matches[-1]
        raw_match = match.group(0).strip()
        curr1 = (match.group(1) or "").strip()
        curr2 = (match.group(3) or "").strip()
        
        if curr1.upper() == "S" or curr2.upper() == "S":
            currency = "$"
        elif curr1:
            currency = curr1
        elif curr2 and curr2 != "/-":
            currency = curr2
        elif "₹" in text or "rs" in text.lower():
            currency = "₹"
        elif "£" in text:
            currency = "£"
        elif "€" in text:
            currency = "€"
        else:
            currency = "$"

        num_part = match.group(2).replace(".-", ".00").replace("-", "").replace(",", ".").strip()
        try:
            val = float(num_part)
            if val < 0.20 or val > 9999:
                return None, None, None, text
            
            # Remove price substring and any leader dots/dashes from text
            text_without = text[:match.start()] + text[match.end():]
            text_without = re.sub(r"[\.·\-_]{2,}", "", text_without).strip()
            return val, f"{currency}{val:.2f}", currency, text_without
        except ValueError:
            return None, None, None, text


    def is_standalone_price(self, text: str) -> Tuple[bool, Optional[float], Optional[str], Optional[str]]:
        """Checks if a text block contains strictly a price string."""
        cleaned = text.strip().replace(" ", "")
        m = self.STANDALONE_PRICE_PATTERN.match(cleaned)
        if m:
            curr1 = m.group(1) or ""
            curr2 = m.group(3) or ""
            currency = curr1 or curr2 or "$"
            num_part = m.group(2).replace(".-", ".00").replace("-", "").replace(",", ".").strip()
            try:
                val = float(num_part)
                if 0.20 <= val <= 9999:
                    return True, val, cleaned, currency
            except ValueError:
                pass
        return False, None, None, None

    COMMON_OCR_FOOD_FIXES = [
        (r"\bpanner\b", "Paneer"),
        (r"\bhushroon\b", "Mushroom"),
        (r"\bhushrooms\b", "Mushrooms"),
        (r"\bhasale\b", "Masala"),
        (r"\bhasala\b", "Masala"),
        (r"\bhacala\b", "Masala"),
        (r"\bsniley'?s?\b", "Smiley's"),
        (r"\byuggets\b", "Nuggets"),
        (r"\bnuggcts\b", "Nuggets"),
        (r"\bohicken\b", "Chicken"),
        (r"\bchickon\b", "Chicken"),
        (r"\bhadurai\b", "Madurai"),
        (r"\bkadurai\b", "Madurai"),
        (r"\bmloo\b", "Aloo"),
        (r"\bprench\b", "French"),
        (r"\bperie\b", "Peri peri"),
        (r"\bspicypanner\b", "Spicy Paneer"),
        (r"\bspicy panner\b", "Spicy Paneer"),
        (r"\bvee\b", "veg"),
    ]


    def is_section_header(self, block: TextBlock, median_height: float) -> Tuple[bool, str]:
        """
        Determines whether a text block is a section/category header.
        Ensures specific food items (e.g. 'Chicken Burger Combo') are NOT misclassified as headers.
        """
        raw_text = block.text.strip()
        norm_text = re.sub(r"[^\w\s]", "", raw_text).lower().strip()
        words = norm_text.split()

        if not words:
            return False, ""

        # If it contains specific food prefixes (e.g. "Chicken", "Veg", "Egg", "Paneer"), it is an ITEM, not a section
        if any(w in self.FOOD_ITEM_PREFIXES for w in words):
            return False, ""

        # Reject restaurant main titles
        if any(w in norm_text for w in self.RESTAURANT_TITLE_WORDS) and norm_text not in self.KNOWN_SECTIONS:
            return False, ""

        # Direct exact match (e.g. "Burger", "Roll", "Sandwich", "Bun", "Fries", "Combos", "Chinese")
        if norm_text in self.KNOWN_SECTIONS:
            return True, raw_text.title()

        # Short category titles (max 2 words) matching a known section
        if len(words) <= 2:
            for known in self.KNOWN_SECTIONS:
                if norm_text == known or norm_text == f"{known}s" or f"{norm_text}s" == known:
                    return True, raw_text.title()

        # Single word fuzzy match (handles OCR errors like 'Sanduich' -> 'Sandwich', 'Eries' -> 'Fries')
        if len(words) == 1:
            close = difflib.get_close_matches(norm_text, list(self.KNOWN_SECTIONS), n=1, cutoff=0.75)
            if close:
                return True, close[0].title()

        return False, ""

    def is_non_food_line(self, text: str) -> bool:
        """Filters out non-food noise like addresses, phone numbers, taxes, licensing, etc."""
        lower = text.lower().strip()
        for pattern in self.NON_FOOD_PATTERNS:
            if re.search(pattern, lower):
                return True
        return False

    def clean_food_name(self, name: str) -> str:
        """Cleans and sanitizes food item names, removing leftover price remnants, leader dots, and formatting artifacts."""
        # Normalize Veg: or Non-Veg: to Veg. / Non-Veg.
        name = re.sub(r"\bVeg\s*:\s*", "Veg. ", name, flags=re.IGNORECASE)
        name = re.sub(r"\bNon[- ]?Veg\s*:\s*", "Non-Veg. ", name, flags=re.IGNORECASE)
        # Replace accidental semicolons with commas
        name = name.replace(";", ",")
        # Remove leftover currency symbols, digits, and isolated symbols at start/end
        name = re.sub(r"^[\$\£\€\₹\¥\d\.\-\/\\#<>|~=]+\s*", "", name)
        name = re.sub(r"\s*[\$\£\€\₹\¥\d\.\-\/\\#<>|~=]+$", "", name)
        # Strip trailing leftover currency words (e.g. "Rs", "Re", "Ro", "R")
        name = re.sub(r"\s+\b(rs|re|ro|inr|usd|eur|gbp|r)\b\s*$", "", name, flags=re.IGNORECASE)
        # Remove leader dots/dashes
        name = re.sub(r"[\.·\-_]{2,}", "", name)
        # Strip trailing/leading punctuation and brackets
        name = re.sub(r"^[\s\/\.\-\\,:;<>|~=\[\]\(\)]+", "", name)
        name = re.sub(r"[\s\/\.\-\\,:;<>|~=\[\]\(\)]+$", "", name)
        
        # Apply common OCR corrections for standard menu terms
        for pattern, replacement in self.COMMON_OCR_FOOD_FIXES:
            name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)

        # Clean extra whitespace
        name = re.sub(r"\s+", " ", name).strip()
        return name





    def extract_dietary_tags(self, text: str) -> Tuple[List[str], str]:
        """Finds dietary tags like (V), (GF), Vegan, etc., and strips them from name if isolated."""
        tags = []
        cleaned_text = text

        for pattern, tag_name in self.DIETARY_PATTERNS:
            if re.search(pattern, cleaned_text, re.IGNORECASE):
                if tag_name not in tags:
                    tags.append(tag_name)
                # Remove brackets enclosing only the tag, e.g. "(V)" or "[GF]"
                cleaned_text = re.sub(r"[\(\[\{]\s*" + pattern + r"\s*[\)\]\}]", "", cleaned_text, flags=re.IGNORECASE)

        cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()
        return tags, cleaned_text

    FOOD_NOUNS = {
        "combo", "pizza", "burger", "rice", "friedrice", "noodles", "noodle", "pasta",
        "salad", "steak", "soup", "curry", "paneer", "tikka", "masala", "roti", "naan",
        "biryani", "sandwich", "wrap", "dosa", "idli", "roll", "platter", "thali",
        "chicken", "mutton", "fish", "egg", "veg", "dal"
    }


    def is_food_item_title(self, text: str) -> bool:
        """Determines if a text row looks like a distinct food item title rather than an ingredient list."""
        lower = text.lower().strip()
        words = lower.split()
        if any(noun in lower for noun in self.FOOD_NOUNS):
            return True
        if text.istitle() and len(words) <= 4 and not any(w in lower for w in ["served with", "with", "fresh", "lemon juice", "sauce"]):
            return True
        return False

    def parse(
        self,
        blocks: List[TextBlock],
        image_path: str = "",
        image_width: int = 1000,
        image_height: int = 1000,
        num_columns: int = 1,
    ) -> RecognizedMenu:
        """
        Parses structured text blocks into a hierarchical RecognizedMenu object.
        """
        if not blocks:
            return RecognizedMenu(
                image_path=image_path,
                image_width=image_width,
                image_height=image_height,
                num_columns=num_columns,
                sections=[],
                unclassified_items=[],
                raw_blocks=[],
            )

        # Calculate median text block height for relative scale reference
        heights = [b.bbox.height for b in blocks if b.bbox.height > 5]
        median_height = float(np.median(heights)) if heights else 20.0

        # Mark standalone prices
        for b in blocks:
            is_price, _, _, _ = self.is_standalone_price(b.text)
            b.is_price = is_price

        # Sort blocks in reading order
        sorted_blocks = sorted(blocks, key=lambda b: (b.column_id, b.bbox.y_min, b.bbox.x_min))

        sections: List[MenuSection] = []
        current_section: Optional[MenuSection] = None
        unclassified_items: List[MenuItem] = []
        last_item: Optional[MenuItem] = None

        i = 0
        while i < len(sorted_blocks):
            block = sorted_blocks[i]
            text = block.text.strip()

            # Skip trivial noise or non-food metadata (addresses, phone numbers, tax lines)
            if not text or (len(text) <= 1 and not text.isalnum()) or self.is_non_food_line(text):
                i += 1
                continue

            # Skip restaurant titles / header branding
            norm_text = re.sub(r"[^\w\s]", "", text).lower().strip()
            if any(w in norm_text for w in self.RESTAURANT_TITLE_WORDS) and norm_text not in self.KNOWN_SECTIONS:
                i += 1
                continue

            # Check for Section Header
            is_header, header_title = self.is_section_header(block, median_height)
            if is_header:
                current_section = MenuSection(title=header_title, bbox=block.bbox)
                sections.append(current_section)
                last_item = None
                i += 1
                continue

            # Check if block itself has an embedded price (e.g. "Margherita Pizza $14.00")
            price_val, raw_price, currency, item_name = self.extract_price(text)
            
            # Check if next block on the same line or right adjacent is a standalone price
            price_bbox = None
            if price_val is None and i + 1 < len(sorted_blocks):
                next_block = sorted_blocks[i + 1]
                if next_block.column_id == block.column_id:
                    v_overlap = block.bbox.vertical_overlap(next_block.bbox)
                    y_diff = abs(block.bbox.center[1] - next_block.bbox.center[1])
                    if v_overlap > 0.4 or y_diff <= (block.bbox.height * 0.6):
                        is_price, p_val, r_p, p_curr = self.is_standalone_price(next_block.text)
                        if is_price:
                            price_val = p_val
                            raw_price = r_p
                            currency = p_curr
                            item_name = text
                            price_bbox = next_block.bbox
                            i += 1  # Consume the price block as well

            if price_val is not None and item_name:
                # Clean dietary tags
                dietary_tags, clean_name = self.extract_dietary_tags(item_name)
                clean_name = self.clean_food_name(clean_name)

                # Check if previous item was an unpriced title (e.g. "Chicken Burger Combo")
                # and this line is its description + price (e.g. "Burger, Fries and spl. lemon juice ₹180")
                if last_item is not None and last_item.price is None:
                    v_dist = block.bbox.vertical_distance(last_item.bbox)
                    if v_dist <= (median_height * 3.0):
                        last_item.price = price_val
                        last_item.raw_price = raw_price
                        last_item.currency = currency
                        last_item.price_bbox = price_bbox
                        if clean_name:
                            last_item.description = f"{last_item.description} {clean_name}".strip() if last_item.description else clean_name
                        i += 1
                        continue

                if not clean_name:
                    clean_name = f"Item @ {raw_price}"

                sec_name = current_section.title if current_section else None
                item = MenuItem(
                    name=clean_name,
                    price=price_val,
                    raw_price=raw_price,
                    currency=currency,
                    description=None,
                    section=sec_name,
                    dietary_tags=dietary_tags,
                    confidence=block.confidence,
                    bbox=block.bbox,
                    price_bbox=price_bbox,
                )

                if current_section:
                    current_section.items.append(item)
                else:
                    unclassified_items.append(item)

                last_item = item
                i += 1
                continue

            # If no price found in this block:
            tags, clean_name = self.extract_dietary_tags(text)
            clean_name = self.clean_food_name(clean_name)

            # Check if it is a description of the previous item (and NOT a new food item title)
            if last_item is not None and not self.is_food_item_title(clean_name):
                v_dist = block.bbox.vertical_distance(last_item.bbox)
                if v_dist <= (median_height * 2.8):
                    if tags:
                        for t in tags:
                            if t not in last_item.dietary_tags:
                                last_item.dietary_tags.append(t)
                    if last_item.description:
                        last_item.description += f" {clean_name}"
                    else:
                        last_item.description = clean_name
                    i += 1
                    continue

            # Otherwise, it is a new food item (or unpriced special)
            if len(clean_name) >= 3 and any(c.isalpha() for c in clean_name):
                sec_name = current_section.title if current_section else None
                fallback_item = MenuItem(
                    name=clean_name,
                    price=None,
                    raw_price=None,
                    currency=None,
                    description=None,
                    section=sec_name,
                    dietary_tags=tags,
                    confidence=block.confidence,
                    bbox=block.bbox,
                )
                if current_section:
                    current_section.items.append(fallback_item)
                else:
                    unclassified_items.append(fallback_item)
                last_item = fallback_item

            i += 1

        return RecognizedMenu(

            image_path=image_path,
            image_width=image_width,
            image_height=image_height,
            num_columns=num_columns,
            sections=sections,
            unclassified_items=unclassified_items,
            raw_blocks=blocks,
            metadata={
                "total_text_blocks": len(blocks),
                "median_font_height": round(median_height, 2),
            },
        )
