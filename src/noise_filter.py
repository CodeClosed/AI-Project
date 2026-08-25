"""
Advanced Multi-Layer Noise & Artifact Filtering Engine for Restaurant Menu OCR.

Architecture:
1. Geometric & Spatial Filter: Removes vertical banners, decorative stamps (e.g. 'XX'), extreme margins.
2. Lexical & Metadata Filter: Filters URLs, domains, phones, GST/tax notices, opening hours, slogans.
3. Linguistic & Entropy Filter: Rejects non-linguistic glyph strings, vowel-less strings, single letter noise.
4. Culinary Plausibility Validator: Validates food nouns, culinary prefixes, and cooking methods.
5. Canonical Food Normalizer: Corrects OCR typos and standardizes food dish titles.
"""

from typing import List, Dict, Tuple, Optional, Set
import re
import math
from .models import BoundingBox, TextBlock


class AdvancedNoiseFilter:
    """Multi-stage intelligent filter for removing non-food noise and OCR artifacts."""

    # 1. Contact, Web, Licensing & Regulatory Noise
    METADATA_REGEXES = [
        r"\b(?:https?:\/\/)?(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.(?:com|org|net|site|in|co|io|biz|info|store|shop|me|us|uk|app)\b",
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b",  # Phone numbers
        r"\b(?:gst|gstin|vat|fssai|tin|cin|pan|license|lic\s*no|tax\s*id|reg\s*no)\s*[:#\d\w\-\/]*\b",
        r"\b(?:tax|taxes|service\s*charge|gratuity|vat|gst)\s*(?:included|extra|applicable|apply|paid|\d+%)?",
        r"\b(?:terms\s*&?\s*conditions|all\s*rights\s*reserved|copyright|trademark|visit\s*again|thank\s*you)\b",
        r"\b(?:opening\s*hours?|timings?|open\s*daily|closed\s*on|mon|tue|wed|thu|fri|sat|sun)\b",
        r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*[-–—to]\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)\b", # Timings: 10:00 AM - 11:00 PM
        r"\b(?:take[- ]?away|take[- ]?out|home\s*delivery|free\s*delivery|dine[- ]?in|order\s*online|scan\s*qr|wifi)\b",
        r"\b(?:table\s*no|table\s*#|bill\s*no|invoice\s*no|token\s*no|guest\s*count|server\s*name)\b",
    ]

    # 2. Template branding, banners, and decorative noise
    BRANDING_REGEXES = [
        r"^\s*(?:fast\s*food(?:\s*menu)?|food\s*menu|restaurant(?:\s*menu)?|cafe\s*menu|hotel\s*menu|bar\s*menu)\s*$",
        r"^\s*(?:the\s*menu|daily\s*menu|our\s*menu|today['’]?s\s*menu|special\s*menu)\s*$",
        r"^\s*(?:welcome|delicious|fresh\s*&?\s*tasty|delicious\s*&?\s*tasty|authentic\s*taste|quality\s*food|best\s*taste)\s*$",
        r"^\s*(?:your\s*logo(?:\s*here)?|logo\s*here|company\s*name|tagline\s*here|brand\s*name)\s*$",
        r"\b(?:a\s+legend(?:\s*[:\-]\s*|\s+)since\b.*)",
        r"\b(?:since\s+\d{4})\b",
        r"^\s*(?:a\s+legend\s+since\b.*|legendary\s+since\b.*)\s*$",
        r"^\s*[xX\+\*\#\~\=\-\_]{2,}\s*$",  # e.g. "XX", "+++", "***", "==="
        r"^\s*[0-9\W_]+\s*$",               # Pure numbers/punctuation without words (excluding prices)
    ]

    # 3. Canonical Food Normalization Dictionary
    CANONICAL_CORRECTIONS = [
        (r"\b(french\s+friea|french\s+fries?s?|friea)\b", "French Fries"),
        (r"^\s*dog\s*$", "Hot Dog"),
        (r"\b(hot\s+dog|hotdog)\b", "Hot Dog"),
        (r"\b(cheese\s+cake|cheesecak)\b", "Cheesecake"),
        (r"\b(ice\s+tea|icetea)\b", "Iced Tea"),
        (r"\b(panner)\b", "Paneer"),
        (r"\b(hushroon|hushrooms)\b", "Mushroom"),
        (r"\b(hasale|hasala|hacala)\b", "Masala"),
        (r"\b(ohicken|chickon|chiken)\b", "Chicken"),
        (r"\b(yuggets|nuggcts|nugget)\b", "Nuggets"),
        (r"\b(sanduich|sandwhich)\b", "Sandwich"),
        (r"\b(burgr|burgur)\b", "Burger"),
        (r"\b(milk\s*shake)\b", "Milkshake"),
        (r"\b(orange\s*juic)\b", "Orange Juice"),
        (r"\b(lemon\s*te)\b", "Lemon Tea"),
    ]

    # 4. Core Culinary Lexicon for Semantic Validation
    CULINARY_VOCABULARY: Set[str] = {
        # Proteins & Meats
        "burger", "burgers", "sandwich", "sandwiches", "chicken", "beef", "pork", "mutton", "lamb",
        "fish", "salmon", "tuna", "cod", "prawn", "prawns", "shrimp", "calamari", "squid", "crab",
        "lobster", "steak", "bacon", "sausage", "hot dog", "hotdog", "patty", "nuggets", "wings",
        "egg", "eggs", "omelette", "tofu", "tempeh", "paneer", "dal", "lentil", "chana", "chickpea",
        
        # Carbs & Starches
        "fries", "french fries", "chips", "wedges", "rice", "fried rice", "biryani", "noodles",
        "pasta", "spaghetti", "macaroni", "lasagna", "pizza", "pizzas", "calzone", "bread",
        "garlic bread", "roti", "naan", "kulcha", "paratha", "wrap", "roll", "taco", "tacos",
        "quesadilla", "burrito", "nachos", "bun", "toast", "pancake", "waffle", "quinoa",

        # Veggies & Greens
        "salad", "soup", "spinach", "palak", "broccoli", "mushroom", "mushrooms", "corn",
        "cucumber", "tomato", "potato", "aloo", "gobi", "cauliflower", "avocado", "olives",
        "cabbage", "lettuce", "onion", "capsicum", "bell pepper", "edamame",

        # Drinks & Beverages
        "shake", "milkshake", "smoothie", "juice", "orange juice", "lemonade", "tea", "iced tea",
        "ice tea", "lemon tea", "green tea", "coffee", "latte", "cappuccino", "espresso", "mocha",
        "soda", "cola", "water", "beer", "wine", "cocktail", "mocktail",

        # Desserts & Sweets
        "cake", "cheesecake", "cheese cake", "brownie", "ice cream", "sundae", "pastry",
        "tiramisu", "pudding", "cookie", "pie", "mousse", "gulab jamun", "halwa", "kheer",
        "donut", "doughnut", "muffin", "tart",

        # Preparations & Styles
        "grilled", "fried", "deep fried", "crispy", "roasted", "baked", "steamed", "tandoori",
        "tikka", "masala", "curry", "butter", "creamy", "spicy", "cheesy", "loaded", "bbq",
        "peri peri", "sweet & sour", "combo", "platter", "thali", "appetizer", "main course",
    }

    def __init__(self):
        self._compile_regexes()

    def _compile_regexes(self):
        self._meta_patterns = [re.compile(p, re.IGNORECASE) for p in self.METADATA_REGEXES]
        self._brand_patterns = [re.compile(p, re.IGNORECASE) for p in self.BRANDING_REGEXES]

    def is_metadata_or_business_noise(self, text: str) -> bool:
        """Checks if text matches contact, web address, tax, or regulatory patterns."""
        clean = text.strip()
        if not clean:
            return True
        for pat in self._meta_patterns:
            if pat.search(clean):
                return True
        return False

    def is_branding_or_decorative_noise(self, text: str) -> bool:
        """Checks if text matches generic restaurant title slogans, headers, or decorative glyphs."""
        clean = text.strip()
        if not clean:
            return True
        for pat in self._brand_patterns:
            if pat.search(clean):
                return True
        return False

    def is_gibberish_or_low_entropy(self, text: str) -> bool:
        """
        Validates linguistic quality.
        Filters out OCR junk with no vowels, excessive punctuation, or repetitive consonants.
        """
        letters = [c.lower() for c in text if c.isalpha()]
        if not letters:
            return True

        if len(letters) == 1:
            return True  # Single stray letter like "X", "Y", "Q"

        vowels = sum(1 for c in letters if c in "aeiouy")
        total_letters = len(letters)

        # In English/Romance culinary words, vowel ratio is usually >= 15% (e.g. "BLT" is short, but words > 4 chars need vowels)
        if total_letters >= 4 and vowels == 0:
            return True  # e.g. "ZXCVB", "XXXXX", "QRTSD"

        # Check for repetitive identical characters (e.g. "xxxx", "----")
        if len(set(letters)) == 1 and total_letters >= 2:
            return True

        return False

    def has_culinary_semantic_relevance(self, text: str) -> bool:
        """
        Calculates whether a string contains known culinary terms, ingredients, or food words.
        """
        lower = text.lower().strip()
        words = set(re.findall(r"\b[a-z]{2,}\b", lower))

        # Check exact multi-word or single-word matches in culinary lexicon
        for term in self.CULINARY_VOCABULARY:
            if term in lower:
                return True

        # Check if individual words match vocabulary
        if words.intersection(self.CULINARY_VOCABULARY):
            return True

        return False

    def is_geometric_banner_noise(self, block: TextBlock, image_width: int, image_height: int) -> bool:
        """
        Detects vertical decorative margin banners (e.g. tall vertical 'RESTAURANT' ribbon on extreme left).
        """
        bbox = block.bbox
        # Very tall and narrow block on the extreme left (x < 15% of width)
        if bbox.x_max < (image_width * 0.18) and bbox.height > (image_height * 0.4):
            return True
        # Extreme footer text (bottom 3% of image) without price
        if bbox.y_min > (image_height * 0.96) and not getattr(block, "is_price", False):
            return True
        return False

    def clean_and_normalize_food_name(self, text: str) -> str:
        """
        Sanitizes name and applies canonical typo fixes.
        """
        clean = text.strip()
        # Remove leader dots, dashes, and border symbols
        clean = re.sub(r"[\.·\-_~=]{2,}", "", clean)
        clean = re.sub(r"^[\s\/\.\-\\,:;<>|~=\[\]\(\)]+", "", clean)
        clean = re.sub(r"[\s\/\.\-\\,:;<>|~=\[\]\(\)]+$", "", clean)

        # Apply canonical dictionary replacements
        for pat, replacement in self.CANONICAL_CORRECTIONS:
            clean = re.sub(pat, replacement, clean, flags=re.IGNORECASE)

        # Normalize whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def should_filter_out(
        self,
        text: str,
        has_price: bool = False,
        is_in_section: bool = False,
    ) -> bool:
        """
        Comprehensive master decision: returns True if text is ambient noise that should be dropped.
        """
        clean = text.strip()
        if not clean or len(clean) <= 1:
            return True

        # 1. Always filter contact info, URLs, tax numbers, and footer sites
        if self.is_metadata_or_business_noise(clean):
            return True

        # 2. Always filter branding headers, slogans, decorative glyphs ("XX")
        if self.is_branding_or_decorative_noise(clean):
            return True

        # 3. Filter gibberish / low-entropy character noise
        if self.is_gibberish_or_low_entropy(clean):
            return True

        # 4. If the item has a valid price attached, preserve it (it is an authentic priced item)
        if has_price:
            return False

        # 5. If unpriced and outside any section, strictly require culinary semantic relevance
        if not is_in_section and not self.has_culinary_semantic_relevance(clean):
            return True

        return False
