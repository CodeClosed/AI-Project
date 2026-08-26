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
async def evaluate_recommendations(req: RecommendRequest):
    raw_items = req.items or []
    items = [item["name"] if isinstance(item, dict) and "name" in item else str(item) for item in raw_items]
    
    recommendations = {
        "tier_1_optimal": items[:len(items)//3] if items else [],
        "tier_2_moderate": items[len(items)//3: 2*len(items)//3] if items else [],
        "tier_3_avoid": items[2*len(items)//3:] if items else []
    }
    return {"success": True, "recommendations": recommendations}
