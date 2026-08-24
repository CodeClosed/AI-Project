"""
Sample script demonstrating the menu recognition pipeline on a realistic sample restaurant menu.
"""

import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PIL import Image, ImageDraw, ImageFont
from src.pipeline import MenuRecognitionPipeline



def generate_sample_menu(output_image_path: str):
    """Generates a realistic 2-column menu image."""
    w, h = 1200, 900
    img = Image.new("RGB", (w, h), color=(253, 251, 247))
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("arial.ttf", 34)
        sec_font = ImageFont.truetype("arial.ttf", 24)
        item_font = ImageFont.truetype("arial.ttf", 18)
        desc_font = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        title_font = ImageFont.load_default()
        sec_font = ImageFont.load_default()
        item_font = ImageFont.load_default()
        desc_font = ImageFont.load_default()

    # Header
    draw.text((450, 30), "TRATTORIA ROMANA", fill=(40, 20, 10), font=title_font)
    draw.line([(350, 75), (850, 75)], fill=(180, 140, 80), width=2)

    # Column 1 (Left): Starters & Pasta
    c1_x = 80
    c1_price_x = 480

    # Starters
    draw.text((c1_x, 110), "STARTERS", fill=(170, 40, 30), font=sec_font)
    
    draw.text((c1_x, 160), "Garlic Herb Focaccia (V)", fill=(20, 20, 20), font=item_font)
    draw.text((c1_price_x, 160), "$7.50", fill=(20, 20, 20), font=item_font)
    draw.text((c1_x, 185), "Freshly baked with rosemary & extra virgin olive oil", fill=(100, 100, 100), font=desc_font)

    draw.text((c1_x, 225), "Caprese Salad (V) (GF)", fill=(20, 20, 20), font=item_font)
    draw.text((c1_price_x, 225), "$11.00", fill=(20, 20, 20), font=item_font)
    draw.text((c1_x, 250), "Buffalo mozzarella, ripe tomatoes, fresh basil & pesto", fill=(100, 100, 100), font=desc_font)

    draw.text((c1_x, 290), "Beef Carpaccio", fill=(20, 20, 20), font=item_font)
    draw.text((c1_price_x, 290), "$14.50", fill=(20, 20, 20), font=item_font)
    draw.text((c1_x, 315), "Thinly sliced beef tenderloin with shaved parmesan", fill=(100, 100, 100), font=desc_font)

    # Pasta
    draw.text((c1_x, 380), "PASTA", fill=(170, 40, 30), font=sec_font)

    draw.text((c1_x, 430), "Spaghetti Carbonara", fill=(20, 20, 20), font=item_font)
    draw.text((c1_price_x, 430), "$17.00", fill=(20, 20, 20), font=item_font)
    draw.text((c1_x, 455), "Crispy guanciale, pecorino romano, farm fresh egg yolk", fill=(100, 100, 100), font=desc_font)

    draw.text((c1_x, 495), "Penne all'Arrabbiata (V)", fill=(20, 20, 20), font=item_font)
    draw.text((c1_price_x, 495), "$15.50", fill=(20, 20, 20), font=item_font)
    draw.text((c1_x, 520), "Spicy San Marzano tomato sauce with garlic and chili", fill=(100, 100, 100), font=desc_font)

    # Column 2 (Right): Mains & Desserts
    c2_x = 650
    c2_price_x = 1050

    # Mains
    draw.text((c2_x, 110), "MAIN COURSES", fill=(170, 40, 30), font=sec_font)

    draw.text((c2_x, 160), "Osso Buco alla Milanese", fill=(20, 20, 20), font=item_font)
    draw.text((c2_price_x, 160), "$32.00", fill=(20, 20, 20), font=item_font)
    draw.text((c2_x, 185), "Braised veal shanks served with saffron risotto", fill=(100, 100, 100), font=desc_font)

    draw.text((c2_x, 225), "Pan-Seared Sea Bass", fill=(20, 20, 20), font=item_font)
    draw.text((c2_price_x, 225), "$28.00", fill=(20, 20, 20), font=item_font)
    draw.text((c2_x, 250), "Mediterranean sea bass with sautéed broccolini and lemon caper butter", fill=(100, 100, 100), font=desc_font)

    draw.text((c2_x, 290), "Chicken Parmigiana", fill=(20, 20, 20), font=item_font)
    draw.text((c2_price_x, 290), "$22.00", fill=(20, 20, 20), font=item_font)
    draw.text((c2_x, 315), "Breaded chicken breast baked with marinara and melted mozzarella", fill=(100, 100, 100), font=desc_font)

    # Desserts
    draw.text((c2_x, 380), "DESSERTS", fill=(170, 40, 30), font=sec_font)

    draw.text((c2_x, 430), "Classic Tiramisu", fill=(20, 20, 20), font=item_font)
    draw.text((c2_price_x, 430), "$9.00", fill=(20, 20, 20), font=item_font)
    draw.text((c2_x, 455), "Espresso soaked ladyfingers with mascarpone cream", fill=(100, 100, 100), font=desc_font)

    draw.text((c2_x, 495), "Sicilian Cannoli (2pcs)", fill=(20, 20, 20), font=item_font)
    draw.text((c2_price_x, 495), "$8.50", fill=(20, 20, 20), font=item_font)
    draw.text((c2_x, 520), "Crispy pastry shells filled with sweet ricotta and chocolate chips", fill=(100, 100, 100), font=desc_font)

    img.save(output_image_path)
    print(f"Generated sample menu image at: {output_image_path}")


if __name__ == "__main__":
    os.makedirs("examples/output", exist_ok=True)
    img_path = "examples/sample_menu.png"
    generate_sample_menu(img_path)

    pipeline = MenuRecognitionPipeline()
    menu = pipeline.process_image(
        image_input=img_path,
        visualize_path="examples/output/sample_annotated.jpg",
    )

    with open("examples/output/sample_menu.json", "w", encoding="utf-8") as f:
        f.write(menu.to_json())

    with open("examples/output/sample_menu.md", "w", encoding="utf-8") as f:
        f.write(menu.to_markdown())

    print("\n--- EXTRACTED MENU ---")
    print(menu.to_markdown())
    print("\nGenerated artifacts in examples/output/")
