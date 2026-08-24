"""
Menu Item Recognition & Layout Parsing System with Personalized 3-Tier Nutrition Recommendations.
"""

from .models import BoundingBox, TextBlock, MenuItem, MenuSection, RecognizedMenu
from .preprocessing import Preprocessor
from .ocr_engine import LocalOCREngine
from .layout_analyzer import LayoutAnalyzer
from .menu_parser import MenuParser
from .gemini_extractor import GeminiMenuExtractor
from .visualizer import MenuVisualizer
from .pipeline import MenuRecognitionPipeline

from .user_models import (
    UserProfile,
    MacroSplit,
    MetabolicEnergyMatrix,
    ClinicalGuardrailMatrix,
    FoodGroupAffinity,
    NutritionalMatrixProfile,
    DishEvaluationResult,
)
from .nutrition_ai import AINutritionProfiler
from .dish_evaluator import MenuDishEvaluator
from .matrix_generator import (
    UserNutritionalMatrix,
    AIMatrixGenerator,
    MetabolicTargets,
    ClinicalRiskWeights,
    NutritionalGuardrails,
)
from .recommendation_engine import (
    FoodTier,
    TieredFoodRecommendation,
    TieredRecommendationResult,
    TieredFoodRecommender,
)

__all__ = [
    "BoundingBox",
    "TextBlock",
    "MenuItem",
    "MenuSection",
    "RecognizedMenu",
    "Preprocessor",
    "LocalOCREngine",
    "LayoutAnalyzer",
    "MenuParser",
    "GeminiMenuExtractor",
    "MenuVisualizer",
    "MenuRecognitionPipeline",
    "UserProfile",
    "MacroSplit",
    "MetabolicEnergyMatrix",
    "ClinicalGuardrailMatrix",
    "FoodGroupAffinity",
    "NutritionalMatrixProfile",
    "DishEvaluationResult",
    "AINutritionProfiler",
    "MenuDishEvaluator",
    "UserNutritionalMatrix",
    "AIMatrixGenerator",
    "MetabolicTargets",
    "ClinicalRiskWeights",
    "NutritionalGuardrails",
    "FoodTier",
    "TieredFoodRecommendation",
    "TieredRecommendationResult",
    "TieredFoodRecommender",
]
