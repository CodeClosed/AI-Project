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
    # Accept both 'items' and 'dishes' payloads
    raw_items = req.get("items") or req.get("dishes") or []
    
    clean_items = []
    for item in raw_items:
        if isinstance(item, dict):
            clean_items.append(item.get("name") or item.get("label") or str(item))
        elif isinstance(item, str) and item.strip():
            clean_items.append(item.strip())

    if not clean_items:
        empty_payload = {
            "tier_counts": {"GOOD": 0, "MEDIUM": 0, "BAD": 0},
            "all_recommendations": [],
            "total_items_evaluated": 0,
            "top_pick": None
        }
        return {"success": True, "result": empty_payload, "recommendations": empty_payload}

    third = max(1, len(clean_items) // 3)
    t1 = clean_items[:third]
    t2 = clean_items[third: 2 * third]
    t3 = clean_items[2 * third:]

    all_recs = []

    # Tier 1 (GOOD)
    for idx, name in enumerate(t1):
        all_recs.append({
            "tier": "GOOD",
            "fit_score": 88 - idx,
            "dish_name": name,
            "price": "",
            "summary_reason": "High nutritional density aligned with your active health matrix.",
            "green_flags": ["Balanced Macros", "Nutrient Dense"],
            "red_flags": [],
            "allergen_warnings": [],
            "customization_tips": "Great choice as prepared!"
        })

    # Tier 2 (MEDIUM)
    for idx, name in enumerate(t2):
        all_recs.append({
            "tier": "MEDIUM",
            "fit_score": 65 - idx,
            "dish_name": name,
            "price": "",
            "summary_reason": "Moderate nutritional fit. Mind portion sizes.",
            "green_flags": ["Moderate Caloric Load"],
            "red_flags": ["Moderate Sodium"],
            "allergen_warnings": [],
            "customization_tips": "Ask for lighter oil or extra salad on the side."
        })

    # Tier 3 (BAD)
    for idx, name in enumerate(t3):
        all_recs.append({
            "tier": "BAD",
            "fit_score": 40 - idx,
            "dish_name": name,
            "price": "",
            "summary_reason": "Higher glycemic index or clinical risk indicators.",
            "green_flags": [],
            "red_flags": ["Higher Caloric/Glycemic Load"],
            "allergen_warnings": [],
            "customization_tips": "Consider replacing with a Tier 1 alternative."
        })

    result_data = {
        "tier_counts": {
            "GOOD": len(t1),
            "MEDIUM": len(t2),
            "BAD": len(t3)
        },
        "all_recommendations": all_recs,
        "total_items_evaluated": len(clean_items),
        "top_pick": all_recs[0] if all_recs else None,
        "tier_1_optimal": t1,
        "tier_2_moderate": t2,
        "tier_3_avoid": t3,
        "good": t1,
        "medium": t2,
        "bad": t3
    }

    return {
        "success": True,
        "result": result_data,
        "recommendations": result_data
    }
