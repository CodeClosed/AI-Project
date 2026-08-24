"""
Comprehensive unit and integration test suite for the Menu Recognition System.
Generates synthetic menu images to validate the entire CV/OCR and parsing pipeline end-to-end.
"""

import os
import tempfile
import pytest
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from src.models import BoundingBox, TextBlock, MenuItem, MenuSection, RecognizedMenu
from src.preprocessing import Preprocessor
from src.layout_analyzer import LayoutAnalyzer
from src.menu_parser import MenuParser
from src.pipeline import MenuRecognitionPipeline


def test_bounding_box_math():
    """Test bounding box coordinate math, area, union, and overlap methods."""
    b1 = BoundingBox(10, 10, 50, 50)
    b2 = BoundingBox(30, 30, 70, 70)
    
    assert b1.width == 40
    assert b1.height == 40
    assert b1.area == 1600
    assert b1.center == (30.0, 30.0)

    u = b1.union(b2)
    assert u.x_min == 10 and u.y_min == 10
    assert u.x_max == 70 and u.y_max == 70

    v_overlap = b1.vertical_overlap(b2)
    assert v_overlap == 0.5  # overlap from y=30 to y=50 (20px / 40px)


def test_menu_parser_price_extraction():
    """Test multi-currency and formatting price extraction."""
    parser = MenuParser()

    # Test standard dollar
    val, raw, curr, name = parser.extract_price("Classic Cheeseburger $14.99")
    assert val == 14.99
    assert raw == "$14.99"
    assert name == "Classic Cheeseburger"

    # Test Indian Rupee format and user example items
    val, raw, curr, name = parser.extract_price("Chicken Butter Masala ₹50")
    assert val == 50.0
    assert parser.clean_food_name(name) == "Chicken Butter Masala"

    val, raw, curr, name = parser.extract_price("Chips ₹50")
    assert val == 50.0
    assert parser.clean_food_name(name) == "Chips"

    val, raw, curr, name = parser.extract_price("Mango ₹20")
    assert val == 20.0
    assert parser.clean_food_name(name) == "Mango"

    val, raw, curr, name = parser.extract_price("Paneer Tikka 120/-")
    assert val == 120.0
    assert parser.clean_food_name(name) == "Paneer Tikka"



    # Test leader dots
    val, raw, curr, name = parser.extract_price("Prime Ribeye Steak .......... 32.00")
    assert val == 32.00
    assert name.strip() == "Prime Ribeye Steak"

    # Test pound format
    val, raw, curr, name = parser.extract_price("Fish and Chips £12.50")
    assert val == 12.50
    assert curr == "£"


def test_dietary_tag_extraction():
    """Test dietary tags (V, VG, GF, etc.) extraction."""
    parser = MenuParser()

    tags, clean_name = parser.extract_dietary_tags("Garden Veggie Burger (V) (GF)")
    assert "Vegetarian" in tags
    assert "Gluten-Free" in tags
    assert clean_name == "Garden Veggie Burger"


def create_synthetic_menu_image(output_path: str):
    """
    Creates a clean high-resolution synthetic restaurant menu image for testing OCR.
    """
    w, h = 900, 1100
    img = Image.new("RGB", (w, h), color=(250, 248, 245))
    draw = ImageDraw.Draw(img)

    # Use default font or basic PIL bitmap font
    try:
        title_font = ImageFont.truetype("arial.ttf", 36)
        header_font = ImageFont.truetype("arial.ttf", 26)
        body_font = ImageFont.truetype("arial.ttf", 20)
        desc_font = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        desc_font = ImageFont.load_default()

    # Menu Title
    draw.text((320, 40), "THE BISTRO", fill=(30, 30, 30), font=title_font)
    draw.line([(250, 90), (650, 90)], fill=(120, 100, 80), width=2)

    # Section 1: Appetizers
    draw.text((80, 130), "APPETIZERS", fill=(160, 40, 40), font=header_font)
    
    draw.text((80, 180), "Crispy Calamari", fill=(20, 20, 20), font=body_font)
    draw.text((720, 180), "$13.50", fill=(20, 20, 20), font=body_font)
    draw.text((80, 210), "Served with garlic aioli and lemon", fill=(100, 100, 100), font=desc_font)

    draw.text((80, 250), "Bruschetta (V)", fill=(20, 20, 20), font=body_font)
    draw.text((720, 250), "$9.00", fill=(20, 20, 20), font=body_font)
    draw.text((80, 280), "Toasted ciabatta with heirloom tomatoes and basil", fill=(100, 100, 100), font=desc_font)

    # Section 2: Main Courses
    draw.text((80, 350), "MAIN COURSES", fill=(160, 40, 40), font=header_font)

    draw.text((80, 400), "Grilled Salmon (GF)", fill=(20, 20, 20), font=body_font)
    draw.text((720, 400), "$26.00", fill=(20, 20, 20), font=body_font)
    draw.text((80, 430), "Atlantic salmon with asparagus and lemon butter", fill=(100, 100, 100), font=desc_font)

    draw.text((80, 470), "Truffle Mushroom Risotto (V)", fill=(20, 20, 20), font=body_font)
    draw.text((720, 470), "$22.50", fill=(20, 20, 20), font=body_font)
    draw.text((80, 500), "Arborio rice with wild mushrooms and parmesan", fill=(100, 100, 100), font=desc_font)

    draw.text((80, 540), "Ribeye Steak 10oz", fill=(20, 20, 20), font=body_font)
    draw.text((720, 540), "$34.00", fill=(20, 20, 20), font=body_font)
    draw.text((80, 570), "Prime beef served with rosemary roasted potatoes", fill=(100, 100, 100), font=desc_font)

    # Section 3: Desserts
    draw.text((80, 640), "DESSERTS", fill=(160, 40, 40), font=header_font)

    draw.text((80, 690), "Tiramisu", fill=(20, 20, 20), font=body_font)
    draw.text((720, 690), "$8.50", fill=(20, 20, 20), font=body_font)

    draw.text((80, 740), "Molten Chocolate Cake", fill=(20, 20, 20), font=body_font)
    draw.text((720, 740), "$9.50", fill=(20, 20, 20), font=body_font)

    img.save(output_path)


def test_end_to_end_recognition():
    """Tests full pipeline on synthetic menu image and verifies extraction accuracy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        image_path = os.path.join(tmpdir, "test_menu.png")
        vis_path = os.path.join(tmpdir, "annotated.jpg")
        
        # Generate menu image
        create_synthetic_menu_image(image_path)
        assert os.path.exists(image_path)

        # Run pipeline
        pipeline = MenuRecognitionPipeline()
        menu = pipeline.process_image(image_path, visualize_path=vis_path)

        # Assertions
        assert menu.total_items >= 5, f"Expected at least 5 items, found {menu.total_items}"
        assert len(menu.sections) >= 2, f"Expected at least 2 sections, found {len(menu.sections)}"
        assert os.path.exists(vis_path), "Visual debug overlay was not saved"

        # Check section names
        sec_titles = [s.title.upper() for s in menu.sections]
        assert any("APPETIZER" in t for t in sec_titles) or any("MAIN" in t for t in sec_titles)

        # Check price and item extraction
        all_items = menu.to_flat_items()
        item_names = " ".join(item.name.lower() for item in all_items)
        assert "calamari" in item_names or "salmon" in item_names or "steak" in item_names or "tiramisu" in item_names

        # Verify JSON serializability
        json_str = menu.to_json()
        assert len(json_str) > 100
