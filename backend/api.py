import os
import re
import shutil
import tempfile
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.pipeline import MenuRecognitionPipeline, RecognizedMenu

# Load environment variables explicitly
load_dotenv(override=True)

app = FastAPI(
    title="NutriMenu AI API",
    description="Backend service for OCR menu extraction, metabolic matrix synthesis, and 3-tier food recommendations.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MatrixRequest(BaseModel):
    items: Optional[List[Any]] = []
    user_profile: Optional[Dict[str, Any]] = None


class RecommendRequest(BaseModel):
    items: Optional[List[Any]] = []
    user_profile: Optional[Dict[str, Any]] = None


@app.get("/")
def read_root():
    return {"status": "ok", "message": "NutriMenu AI Backend Service Running"}


@app.post("/api/ocr/extract")
async def extract_menu_from_image(
    file: UploadFile = File(...), 
    api_key: Optional[str] = Form(None)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    effective_api_key = api_key or os.getenv("GEMINI_API_KEY")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
        shutil.copyfileobj(file.file, tmp_file)
        tmp_path = tmp_file.name

    try:
        pipeline = MenuRecognitionPipeline(api_key=effective_api_key)
        recognized_menu: RecognizedMenu = pipeline.process_image(tmp_path)
        flat_items = recognized_menu.to_flat_items()

        flattened_dishes = []
        for item in flat_items:
            parts = re.split(r'[,/\n]', str(item))
            for part in parts:
                clean_name = part.strip()
                clean_name = re.sub(
                    r'^(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Breakfast|Lunch|Snacks|Dinner)\s*', 
                    '', 
                    clean_name, 
                    flags=re.IGNORECASE
                ).strip()
                
                if clean_name and len(clean_name) > 1 and not clean_name.isdigit():
                    flattened_dishes.append(clean_name.title())

        dishes = flattened_dishes

        # Format items for object-based and string-based frontend rendering
        formatted_dishes = [
            {"id": idx + 1, "name": item} if isinstance(item, str) else item 
            for idx, item in enumerate(dishes)
        ]

        return {
            "success": True,
            "filename": file.filename,
            "total_extracted": len(dishes),
            "dishes": formatted_dishes,
            "items": dishes,
            "metadata": recognized_menu.metadata,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR extraction failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/api/matrix/generate")
async def generate_matrix(req: MatrixRequest):
    raw_items = req.items or []
    items = [item["name"] if isinstance(item, dict) and "name" in item else str(item) for item in raw_items]
    
    matrix_data = {}
    for item in items:
        matrix_data[item] = {
            "glycemic_index": 55,
            "inflammatory_score": 2,
            "gut_irritation": 1,
            "allergic_trigger": False
        }
    return {"success": True, "matrix": matrix_data}

@app.post("/api/recommend/evaluate")
async def evaluate_recommendations(req: Dict[str, Any]):
    raw_items = req.get("items") or req.get("dishes") or []
    target_day = str(req.get("day") or "").strip().lower()
    target_meal = str(req.get("meal_type") or "").strip().lower()

    # Slot specific food rules
    meal_allowed_keywords = {
        "breakfast": ["dosa", "idly", "upma", "poha", "puri", "chapathi", "paratha", "pongal", "bread", "butter", "jam", "tea", "coffee", "milk", "chutney", "sambar", "aloo besan", "boiled egg", "omelette", "muffin", "vada", "halwa"],
        "lunch": ["rice", "pulao", "biryani", "roti", "phulka", "chapathi", "dal", "sambar", "rasam", "curry", "subzi", "paneer", "chicken", "curd", "raita", "salad", "pappu", "fry", "khorma", "makhani"],
        "snacks": ["pakoda", "samosa", "bajji", "vada", "tea", "coffee", "cake", "halwa", "biscuits", "corn", "punugu", "gottalu"],
        "dinner": ["roti", "phulka", "chapathi", "rice", "dal", "curry", "paneer", "chicken", "milk", "curd", "dosa", "idly", "kichidi"]
    }

    clean_items = []
    for item in raw_items:
        item_name = ""
        item_day = ""
        item_meal = ""

        if isinstance(item, dict):
          item_name = item.get("name") or item.get("label") or ""
          item_day = str(item.get("day", "")).strip().lower()
          item_meal = str(item.get("meal_type", "")).strip().lower()
        else:
          item_name = str(item)

        item_name_clean = item_name.strip()
        if not item_name_clean:
          continue

        # Day filtering if metadata exists
        if target_day and item_day and target_day not in item_day:
          continue

        # Meal slot filtering if metadata exists
        if target_meal and item_meal and target_meal not in item_meal:
          continue

        # Category sanity check for flat OCR lists (prevents Biryani in Breakfast)
        allowed_kw = meal_allowed_keywords.get(target_meal, [])
        if allowed_kw and not item_meal:
          if not any(kw in item_name_clean.lower() for kw in allowed_kw):
            continue

        clean_items.append(item_name_clean)

    if not clean_items:
        empty_payload = {
            "tier_counts": {"GOOD": 0, "MEDIUM": 0, "BAD": 0},
            "all_recommendations": [],
            "total_items_evaluated": 0,
            "top_pick": None
        }
        return {"success": True, "result": empty_payload, "recommendations": empty_payload}

    # Group valid items for combo creation
    bases = [i for i in clean_items if any(k in i.lower() for k in ["dosa", "idly", "chapathi", "roti", "phulka", "pulao", "rice", "pongal", "paratha", "puri", "bread", "kichidi"])]
    mains = [i for i in clean_items if any(k in i.lower() for k in ["dal", "curry", "masala", "subzi", "paneer", "sambar", "channa", "rajma", "chicken", "pappu", "khorma", "makhani"])]
    sides = [i for i in clean_items if any(k in i.lower() for k in ["chutney", "curd", "raita", "rasam", "salad", "buttermilk", "pickle"])]

    if not bases:
        bases = clean_items[:2]
    if not mains:
        mains = clean_items[2:4] if len(clean_items) >= 4 else clean_items

    combos = []
    seen = set()

    for base in bases:
        for main in mains:
            side = sides[0] if sides else "Chutney"
            combo_name = f"{base} + {main} + {side}" if base != main else base

            if combo_name in seen:
                continue
            seen.add(combo_name)

            combos.append({
                "tier": "GOOD",
                "fit_score": 88,
                "dish_name": combo_name,
                "price": "",
                "summary_reason": f"Slot-specific meal for {target_day.capitalize()} {target_meal.capitalize()}.",
                "green_flags": ["Matched Schedule"],
                "red_flags": [],
                "allergen_warnings": [],
                "customization_tips": "Sustained energy."
            })

    combos.sort(key=lambda x: x["fit_score"], reverse=True)

    result_data = {
        "tier_counts": {"GOOD": len(combos), "MEDIUM": 0, "BAD": 0},
        "all_recommendations": combos,
        "total_items_evaluated": len(combos),
        "top_pick": combos[0] if combos else None,
    }

    return {"success": True, "result": result_data, "recommendations": result_data}
