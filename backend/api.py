"""
FastAPI Backend API Server for NutriMenu AI.
Exposes REST endpoints for:
- Menu Image Deep OCR Extraction (/api/ocr/extract)
- Personalized Nutritional Matrix Synthesis (/api/matrix/generate)
- 3-Tier Recommendation Engine (/api/recommend/evaluate)
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import io
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.models import RecognizedMenu, MenuItem
from src.pipeline import MenuRecognitionPipeline
from src.matrix_generator import AIMatrixGenerator, UserNutritionalMatrix
from src.recommendation_engine import (
    TieredFoodRecommender,
    TieredRecommendationResult,
    FoodTier,
)
from src.config import DEFAULT_GOOD_THRESHOLD, DEFAULT_BAD_THRESHOLD


# Initialize FastAPI app
app = FastAPI(
    title="NutriMenu AI API",
    description="Backend service for OCR menu extraction, metabolic matrix synthesis, and 3-tier food recommendations.",
    version="2.0.0",
)

# CORS configuration for local React / Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singleton instances
ocr_pipeline = MenuRecognitionPipeline()
matrix_generator = AIMatrixGenerator()


# --- Pydantic Request / Response Models ---
class UserProfilePayload(BaseModel):
    age: int = Field(default=45, ge=10, le=120)
    gender: str = Field(default="male")
    height_cm: float = Field(default=176.0, ge=80, le=250)
    weight_kg: float = Field(default=86.0, ge=25, le=300)
    activity_level: str = Field(default="sedentary")
    primary_goal: str = Field(default="fat_loss")
    health_conditions: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    dietary_preferences: List[str] = Field(default_factory=list)
    raw_bio_text: Optional[str] = None
    api_key: Optional[str] = None


class DishItem(BaseModel):
    name: str
    description: Optional[str] = ""
    price: Optional[str] = ""
    tags: Optional[List[str]] = Field(default_factory=list)


class RecommendationRequest(BaseModel):
    user_matrix: Dict[str, Any]
    dishes: List[DishItem]
    good_threshold: int = DEFAULT_GOOD_THRESHOLD
    bad_threshold: int = DEFAULT_BAD_THRESHOLD


# --- API Routes ---
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "NutriMenu AI API",
        "gemini_active": matrix_generator.is_available(),
        "ocr_device": getattr(ocr_pipeline.ocr_engine, "active_device", "cpu"),
    }


@app.post("/api/ocr/extract")
async def extract_menu_from_image(file: UploadFile = File(...)):
    """
    Accepts an uploaded menu image, processes it via Preprocessor & EasyOCR / Gemini Vision,
    and returns a structured list of cleaned dishes.
    """
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        try:
            image = Image.open(io.BytesIO(contents))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image format: {e}")

        # Run OCR Pipeline
        recognized_menu: RecognizedMenu = ocr_pipeline.process_image(image)
        flat_items = recognized_menu.to_flat_items()

        dishes = []
        for itm in flat_items:
            dishes.append({
                "name": itm.name,
                "description": itm.description or "",
                "price": itm.raw_price or (f"${itm.price:.2f}" if itm.price else ""),
                "tags": itm.dietary_tags or [],
                "section": itm.section or "Main",
                "confidence": itm.confidence,
            })

        return {
            "success": True,
            "filename": file.filename,
            "total_extracted": len(dishes),
            "dishes": dishes,
            "metadata": recognized_menu.metadata,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR extraction failed: {str(e)}")


@app.post("/api/matrix/generate")
def generate_user_matrix(profile: UserProfilePayload):
    """
    Synthesizes metabolic energy targets, macro distribution, and clinical guardrails via Gemini API.
    """
    try:
        gen = AIMatrixGenerator(api_key=profile.api_key) if profile.api_key else matrix_generator
        matrix: UserNutritionalMatrix = gen.generate(
            profile.model_dump(),
            user_id="active_user",
        )
        return {
            "success": True,
            "matrix": matrix.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Matrix generation failed: {str(e)}")


@app.post("/api/recommend/evaluate")
def evaluate_recommendations(req: RecommendationRequest):
    """
    Evaluates dish items against user nutritional matrix and classifies them into 3 tiers.
    """
    try:
        # Reconstruct UserNutritionalMatrix
        user_matrix = UserNutritionalMatrix.from_dict(req.user_matrix)

        recommender = TieredFoodRecommender(
            user_matrix=user_matrix,
            good_threshold=req.good_threshold,
            bad_threshold=req.bad_threshold,
        )

        dishes_raw = [d.model_dump() for d in req.dishes]
        result: TieredRecommendationResult = recommender.recommend_menu(dishes_raw)

        return {
            "success": True,
            "result": result.to_dict(),
            "markdown_report": result.to_markdown(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation evaluation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
