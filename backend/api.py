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

    # Slot-specific keywords to filter OCR list when items lack strict tags
    meal_allowed_keywords = {
        "breakfast": ["dosa", "idly", "upma", "poha", "puri", "chapathi", "paratha", "pongal", "bread", "butter", "jam", "tea", "coffee", "milk", "chutney", "sambar", "aloo besan", "boiled egg", "omelette", "muffin", "vada", "halwa"],
        "lunch": ["rice", "pulao", "biryani", "roti", "phulka", "chapathi", "dal", "sambar", "rasam", "curry", "subzi", "paneer", "chicken", "curd", "raita", "salad", "pappu", "fry", "khorma", "makhani"],
        "snacks": ["pakoda", "samosa", "bajji", "vada", "tea", "coffee", "cake", "halwa", "biscuits", "corn", "punugu", "gottalu"],
        "dinner": ["roti", "phulka", "chapathi", "rice", "dal", "curry", "paneer", "chicken", "milk", "curd", "dosa", "idly", "kichidi"]
    }

    clean_items = []
    seen = set()

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
        if not item_name_clean or item_name_clean.lower() in seen:
            continue

        # 1. Day filtering if structured metadata exists
        if target_day and item_day and target_day not in item_day:
            continue

        # 2. Meal slot filtering if structured metadata exists
        if target_meal and item_meal and target_meal not in item_meal:
            continue

        # 3. Keyword filtering for flat OCR lists (prevents Biryani in Breakfast)
        allowed_kw = meal_allowed_keywords.get(target_meal, [])
        if allowed_kw and not item_meal:
            if not any(kw in item_name_clean.lower() for kw in allowed_kw):
                continue

        seen.add(item_name_clean.lower())
        clean_items.append(item_name_clean)

    if not clean_items:
        empty_payload = {
            "tier_counts": {"GOOD": 0, "MEDIUM": 0, "BAD": 0},
            "all_recommendations": [],
            "total_items_evaluated": 0,
            "top_pick": None
        }
        return {"success": True, "result": empty_payload, "recommendations": empty_payload}

    # Format each individual dish as a standalone recommendation
    recommendations = []
    for dish in clean_items:
        lower_name = dish.lower()
        score = 88
        tier = "GOOD"
        flags = ["Matched Schedule"]
        tips = "Supports steady energy levels."

        # Assign basic clinical tier scoring rules
        if any(k in lower_name for k in ["fried", "pakoda", "samosa", "halwa", "bajji", "cake"]):
            score = 45
            tier = "BAD"
            flags = ["High Calorie / Fried"]
            tips = "Consume in moderation."
        elif any(k in lower_name for k in ["paneer", "butter", "biryani"]):
            score = 68
            tier = "MEDIUM"
            flags = ["Moderate Saturated Fats"]
            tips = "Pair with fresh salad or fiber."

        recommendations.append({
            "tier": tier,
            "fit_score": score,
            "dish_name": dish,
            "price": "",
            "summary_reason": f"Available for {target_day.capitalize()} {target_meal.capitalize()}.",
            "green_flags": flags if tier == "GOOD" else [],
            "red_flags": flags if tier != "GOOD" else [],
            "allergen_warnings": [],
            "customization_tips": tips
        })

    # Sort high-scoring individual items to the top
    recommendations.sort(key=lambda x: x["fit_score"], reverse=True)

    result_data = {
        "tier_counts": {
            "GOOD": sum(1 for r in recommendations if r["tier"] == "GOOD"),
            "MEDIUM": sum(1 for r in recommendations if r["tier"] == "MEDIUM"),
            "BAD": sum(1 for r in recommendations if r["tier"] == "BAD")
        },
        "all_recommendations": recommendations,
        "total_items_evaluated": len(recommendations),
        "top_pick": recommendations[0] if recommendations else None,
    }

    return {"success": True, "result": result_data, "recommendations": result_data}
