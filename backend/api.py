import os
import shutil
import tempfile
import re
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.pipeline import MenuRecognitionPipeline
from src.models import RecognizedMenu
from src.matrix_generator import AIMatrixGenerator, UserNutritionalMatrix
from src.recommendation_engine import TieredFoodRecommender, TieredRecommendationResult
from src.noise_filter import is_valid_food_item
from src.gemini_extractor import tokenize_food_item

# Load environment variables explicitly
load_dotenv(override=True)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="NutriMenu AI API",
    description="Backend service for Gemini 3.7 Flash OCR menu extraction, metabolic matrix synthesis, and personalized 3-tier food recommendations.",
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


@app.get("/api/health")
def health_check():
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    return {
        "status": "ok",
        "gemini_available": bool(gemini_key and len(gemini_key.strip()) >= 10),
        "model": os.getenv("GEMINI_MODEL", "gemini-3.7-flash"),
    }


@app.post("/api/ocr/extract")
async def extract_menu_from_image(
    file: UploadFile = File(...), 
    api_key: Optional[str] = Form(None)
):
    is_image = (
        (file.content_type and file.content_type.startswith("image/"))
        or (file.filename and file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif')))
    )
    if not is_image:
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    effective_api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("OPENROUTER_API_KEY")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
        shutil.copyfileobj(file.file, tmp_file)
        tmp_path = tmp_file.name

    try:
        pipeline = MenuRecognitionPipeline(api_key=effective_api_key)
        recognized_menu = pipeline.process_image(tmp_path)

        raw_dishes = []
        if hasattr(recognized_menu, "get_item_names") and callable(recognized_menu.get_item_names):
            raw_dishes = recognized_menu.get_item_names()
        elif hasattr(recognized_menu, "to_flat_items") and callable(recognized_menu.to_flat_items):
            raw_dishes = [item.name for item in recognized_menu.to_flat_items()]

        # Filter out day names, timetable headers, time strings, and noise
        flattened_dishes = []
        seen = set()

        for dish in raw_dishes:
            tokenized = tokenize_food_item(str(dish))
            for clean_name in tokenized:
                # Strip leading day names or slot names
                clean_name = re.sub(
                    r'^(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Breakfast|Lunch|Snacks|Dinner)\s*[:\-]?\s*', 
                    '', 
                    clean_name, 
                    flags=re.IGNORECASE
                ).strip()

                if not clean_name or len(clean_name) <= 1 or clean_name.isdigit():
                    continue

                valid, _ = is_valid_food_item(clean_name, allow_beverages=True)
                if not valid:
                    continue

                if clean_name.lower() not in seen:
                    seen.add(clean_name.lower())
                    flattened_dishes.append(clean_name.title())

        # Fallback to direct flat items if list is empty
        if not flattened_dishes and hasattr(recognized_menu, "to_flat_items"):
            for item in recognized_menu.to_flat_items():
                name = item.name.strip().title()
                if name.lower() not in seen:
                    seen.add(name.lower())
                    flattened_dishes.append(name)

        formatted_dishes = [
            {"id": idx + 1, "name": item, "section": "Menu Items"}
            for idx, item in enumerate(flattened_dishes)
        ]

        return {
            "success": True,
            "filename": file.filename,
            "total_extracted": len(flattened_dishes),
            "dishes": formatted_dishes,
            "items": flattened_dishes,
            "metadata": recognized_menu.metadata,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("OCR extraction failed: %s", e)
        raise HTTPException(status_code=500, detail=f"OCR extraction failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/api/matrix/generate")
async def generate_matrix(req: Dict[str, Any]):
    user_prof = req.get("profile") or req.get("user_profile") or req
    api_key = req.get("api_key") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("OPENROUTER_API_KEY")

    try:
        generator = AIMatrixGenerator(api_key=api_key)
        matrix = generator.generate(user_prof)
        return {"success": True, "matrix": matrix.to_dict()}
    except Exception as e:
        logger.warning("AI matrix generation fallback: %s", e)
        fallback_gen = AIMatrixGenerator()
        matrix = fallback_gen._generate_deterministic(user_prof)
        return {"success": True, "matrix": matrix.to_dict(), "fallback": True, "error": str(e)}


@app.post("/api/recommend/evaluate")
async def evaluate_recommendations(req: Dict[str, Any]):
    raw_items = req.get("dishes") or req.get("items") or []
    matrix_dict = req.get("matrix")
    user_prof = req.get("profile") or req.get("user_profile") or {}
    api_key = req.get("api_key") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("OPENROUTER_API_KEY")

    # Build or parse UserNutritionalMatrix
    matrix: Optional[UserNutritionalMatrix] = None
    if matrix_dict and isinstance(matrix_dict, dict) and "metabolic_targets" in matrix_dict:
        try:
            matrix = UserNutritionalMatrix.from_dict(matrix_dict)
        except Exception:
            matrix = None

    if matrix is None:
        generator = AIMatrixGenerator(api_key=api_key)
        matrix = generator.generate(user_prof or {
            "age": 35,
            "gender": "male",
            "height_cm": 175,
            "weight_kg": 75,
            "activity_level": "moderate",
            "primary_goal": "maintenance",
            "health_conditions": [],
            "allergies": [],
            "dietary_preferences": [],
        })

    # Prepare dish dictionaries for evaluation
    dishes = []
    seen = set()

    for item in raw_items:
        if isinstance(item, dict):
            name = item.get("name") or item.get("label") or item.get("dish_name") or ""
            price = item.get("price") or item.get("raw_price") or ""
            desc = item.get("description") or ""
            tags = item.get("tags") or item.get("dietary_tags") or []
        else:
            name = str(item)
            price = ""
            desc = ""
            tags = []

        name = name.strip()
        if not name or name.lower() in seen:
            continue

        valid, _ = is_valid_food_item(name, allow_beverages=True)
        if not valid:
            continue

        seen.add(name.lower())
        dishes.append({
            "name": name,
            "price": price,
            "description": desc,
            "tags": tags,
        })

    if not dishes:
        empty_payload = {
            "user_summary": matrix.user_summary,
            "total_items_evaluated": 0,
            "tier_counts": {"GOOD": 0, "MEDIUM": 0, "BAD": 0},
            "good_items": [],
            "medium_items": [],
            "bad_items": [],
            "all_recommendations": [],
            "top_pick": None
        }
        return {"success": True, "result": empty_payload, "recommendations": empty_payload}

    # Run personalized 3-tier recommendation engine powered by Gemini
    recommender = TieredFoodRecommender(user_matrix=matrix, api_key=api_key)
    rec_result: TieredRecommendationResult = recommender.recommend_menu(dishes)
    result_dict = rec_result.to_dict()

    return {
        "success": True,
        "result": result_dict,
        "recommendations": result_dict,
    }


@app.post("/api/plate/evaluate")
async def evaluate_plate_meal(req: Dict[str, Any]):
    """Calculates cumulative plate nutrition, remaining budget, and multi-dish synergy."""
    plate_items = req.get("plate") or req.get("items") or []
    matrix_dict = req.get("matrix")
    user_prof = req.get("profile") or {}
    api_key = req.get("api_key") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("OPENROUTER_API_KEY")

    matrix: Optional[UserNutritionalMatrix] = None
    if matrix_dict and isinstance(matrix_dict, dict) and "metabolic_targets" in matrix_dict:
        try:
            matrix = UserNutritionalMatrix.from_dict(matrix_dict)
        except Exception:
            matrix = None

    if matrix is None:
        generator = AIMatrixGenerator(api_key=api_key)
        matrix = generator.generate(user_prof or {
            "age": 35,
            "gender": "male",
            "height_cm": 175,
            "weight_kg": 75,
        })

    from src.plate_optimizer import PlateOptimizer
    optimizer = PlateOptimizer(user_matrix=matrix, api_key=api_key)
    plate_summary = optimizer.evaluate_plate(plate_items, user_matrix=matrix)

    return {
        "success": True,
        "plate_evaluation": plate_summary,
    }


@app.post("/api/plate/complete")
async def complete_plate_suggestions(req: Dict[str, Any]):
    """Suggests complementary companion dishes from the menu to balance the plate."""
    plate_items = req.get("plate") or []
    candidate_menu = req.get("menu_dishes") or req.get("dishes") or []
    matrix_dict = req.get("matrix")
    api_key = req.get("api_key") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("OPENROUTER_API_KEY")

    matrix: Optional[UserNutritionalMatrix] = None
    if matrix_dict and isinstance(matrix_dict, dict) and "metabolic_targets" in matrix_dict:
        try:
            matrix = UserNutritionalMatrix.from_dict(matrix_dict)
        except Exception:
            matrix = None

    if matrix is None:
        user_prof = req.get("profile") or req.get("user_profile") or {}
        generator = AIMatrixGenerator(api_key=api_key)
        matrix = generator.generate(user_prof or {
            "age": 35,
            "gender": "male",
            "height_cm": 175,
            "weight_kg": 75,
        })

    from src.plate_optimizer import PlateOptimizer
    optimizer = PlateOptimizer(user_matrix=matrix, api_key=api_key)
    clean_candidates = [
        d["name"] if isinstance(d, dict) and "name" in d else str(d)
        for d in candidate_menu
    ]
    suggestions = optimizer.suggest_plate_companions(plate_items, clean_candidates, user_matrix=matrix)

    return {
        "success": True,
        "suggestions": suggestions,
    }


