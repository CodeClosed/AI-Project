"""
Demo testing Indian menu item recognition (with Rupees, INR, Rs., and clean item output).
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PIL import Image, ImageDraw, ImageFont
from src.pipeline import MenuRecognitionPipeline


def generate_indian_menu(output_path: str):
    w, h = 900, 1000
    img = Image.new("RGB", (w, h), color=(255, 253, 248))
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("arial.ttf", 32)
        sec_font = ImageFont.truetype("arial.ttf", 24)
        item_font = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        title_font = ImageFont.load_default()
        sec_font = ImageFont.load_default()
        item_font = ImageFont.load_default()

    # Restaurant Title
    draw.text((300, 30), "SPICE KITCHEN", fill=(180, 50, 20), font=title_font)
    draw.line([(200, 75), (700, 75)], fill=(200, 150, 50), width=2)

    # Section 1: Starters & Snacks
    draw.text((80, 110), "STARTERS & SNACKS", fill=(160, 40, 20), font=sec_font)
    
    draw.text((80, 160), "Chips", fill=(20, 20, 20), font=item_font)
    draw.text((700, 160), "Rs. 50", fill=(20, 20, 20), font=item_font)

    draw.text((80, 210), "Mango Salad", fill=(20, 20, 20), font=item_font)
    draw.text((700, 210), "Rs. 20", fill=(20, 20, 20), font=item_font)

    draw.text((80, 260), "Paneer Tikka (V)", fill=(20, 20, 20), font=item_font)
    draw.text((700, 260), "120/-", fill=(20, 20, 20), font=item_font)

    # Section 2: Main Course
    draw.text((80, 340), "MAIN COURSE", fill=(160, 40, 20), font=sec_font)

    draw.text((80, 390), "Chicken Butter Masala", fill=(20, 20, 20), font=item_font)
    draw.text((700, 390), "Rs. 50", fill=(20, 20, 20), font=item_font)

    draw.text((80, 440), "Paneer Butter Masala (V)", fill=(20, 20, 20), font=item_font)
    draw.text((700, 440), "180/-", fill=(20, 20, 20), font=item_font)

    draw.text((80, 490), "Dal Makhani (V)", fill=(20, 20, 20), font=item_font)
    draw.text((700, 490), "Rs. 140", fill=(20, 20, 20), font=item_font)

    draw.text((80, 540), "Garlic Naan", fill=(20, 20, 20), font=item_font)
    draw.text((700, 540), "40/-", fill=(20, 20, 20), font=item_font)

    # Section 3: Desserts & Beverages
    draw.text((80, 620), "DESSERTS & DRINKS", fill=(160, 40, 20), font=sec_font)

    draw.text((80, 670), "Mango Lassi", fill=(20, 20, 20), font=item_font)
    draw.text((700, 670), "Rs. 60", fill=(20, 20, 20), font=item_font)

    draw.text((80, 720), "Gulab Jamun (2 pcs)", fill=(20, 20, 20), font=item_font)
    draw.text((700, 720), "50/-", fill=(20, 20, 20), font=item_font)

    img.save(output_path)
    print(f"Generated Indian menu at: {output_path}")


if __name__ == "__main__":
    os.makedirs("examples/output", exist_ok=True)
    img_path = "examples/indian_menu.png"
    generate_indian_menu(img_path)

    pipeline = MenuRecognitionPipeline()
    items = pipeline.extract_menu_items(img_path)

    print("\n" + "=" * 40)
    print("EXTRACTED FOOD ITEMS ONLY:")
    print("=" * 40)
    for idx, item in enumerate(items, 1):
        print(f"{idx}. {item}")
