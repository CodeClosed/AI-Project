"""
Unit and Integration Tests for AI Nutrition Profiler, Matrix Models, and Dish Evaluator.
"""

import pytest
from src.user_models import (
    UserProfile,
    NutritionalMatrixProfile,
    MetabolicEnergyMatrix,
    ClinicalGuardrailMatrix,
    FoodGroupAffinity,
    MacroSplit,
    DishEvaluationResult,
)
from src.nutrition_ai import AINutritionProfiler
from src.dish_evaluator import MenuDishEvaluator


def test_user_profile_creation():
    """Test UserProfile initialization and dictionary serialization."""
    profile = UserProfile(
        age=30,
        gender="male",
        height_cm=175.0,
        weight_kg=75.0,
        activity_level="moderate",
        primary_goal="fat_loss",
        health_conditions=["hypertension"],
        allergies=["peanuts"],
        dietary_preferences=["vegetarian"]
    )
    d = profile.to_dict()
    assert d["age"] == 30
    assert d["gender"] == "male"
    assert "hypertension" in d["health_conditions"]
    assert "vegetarian" in d["dietary_preferences"]


def test_deterministic_baseline_calculation():
    """Test mathematical BMR/TDEE and guardrail computations."""
    profiler = AINutritionProfiler(api_key="mock_disabled_key")
    
    # 30yo Male, 75kg, 175cm -> Mifflin-St Jeor BMR = (10*75) + (6.25*175) - (5*30) + 5 = 750 + 1093.75 - 150 + 5 = 1698.75
    profile = UserProfile(
        age=30,
        gender="male",
        height_cm=175.0,
        weight_kg=75.0,
        activity_level="sedentary",
        primary_goal="fat_loss",
        health_conditions=["hypertension", "type_2_diabetes"],
        dietary_preferences=["vegetarian"]
    )
    
    matrix = profiler._compute_deterministic_baseline(profile)
    assert isinstance(matrix, NutritionalMatrixProfile)
    assert 1690 <= matrix.metabolic_matrix.bmr_kcal <= 1710
    assert matrix.metabolic_matrix.tdee_kcal > matrix.metabolic_matrix.bmr_kcal
    assert matrix.metabolic_matrix.target_calories_kcal < matrix.metabolic_matrix.tdee_kcal  # Deficit for fat loss
    
    # Clinical guardrails
    assert matrix.clinical_guardrails.glycemic_sensitivity_index >= 0.8  # Due to diabetes
    assert matrix.clinical_guardrails.sodium_limit_mg <= 1500           # Due to hypertension
    assert matrix.clinical_guardrails.saturated_fat_max_pct <= 0.10


def test_markdown_and_json_serialization():
    """Test formatting and serialization of NutritionalMatrixProfile."""
    profiler = AINutritionProfiler(api_key="mock_disabled_key")
    profile = UserProfile(
        age=28,
        gender="female",
        height_cm=165.0,
        weight_kg=60.0,
        activity_level="light",
        primary_goal="maintenance"
    )
    matrix = profiler.generate_matrix(profile)
    
    md = matrix.to_markdown()
    assert "# 🥗 Personalized Nutritional & Health Matrix Profile" in md
    assert "Metabolic & Caloric Targets" in md
    assert "Scored Food Group Recommendations" in md
    
    js = matrix.to_json()
    assert '"target_calories_kcal"' in js


def test_dish_evaluation_heuristic():
    """Test dish evaluation heuristics for health fit and dietary constraints."""
    profiler = AINutritionProfiler(api_key="mock_disabled_key")
    profile = UserProfile(
        age=35,
        gender="male",
        height_cm=180.0,
        weight_kg=85.0,
        activity_level="sedentary",
        primary_goal="fat_loss",
        dietary_preferences=["vegetarian"]
    )
    matrix = profiler.generate_matrix(profile)
    
    evaluator = MenuDishEvaluator(user_matrix=matrix, api_key="mock_disabled_key")
    
    # 1. Healthy vegetarian dish
    healthy_dish = evaluator.evaluate_dish("Steamed Spinach & Lentil Dal with Quinoa")
    assert healthy_dish.fit_score >= 80
    assert healthy_dish.verdict in ["Top Recommendation", "Healthy Choice"]
    
    # 2. Deep fried dish
    fried_dish = evaluator.evaluate_dish("Deep Fried Crispy Pakoras")
    assert fried_dish.fit_score < healthy_dish.fit_score
    assert any("Deep fried" in r for r in fried_dish.red_flags)
    
    # 3. Non-vegetarian dish violation for vegetarian user
    meat_dish = evaluator.evaluate_dish("Butter Chicken Curry")
    assert meat_dish.fit_score == 0
    assert meat_dish.verdict == "Violates Diet/Allergy"


def test_menu_ranking():
    """Test batch menu ranking."""
    profiler = AINutritionProfiler(api_key="mock_disabled_key")
    profile = UserProfile(
        age=40,
        gender="female",
        height_cm=160.0,
        weight_kg=70.0,
        primary_goal="fat_loss",
        dietary_preferences=["vegetarian"]
    )
    matrix = profiler.generate_matrix(profile)
    
    evaluator = MenuDishEvaluator(user_matrix=matrix, api_key="mock_disabled_key")
    dishes = [
        "Crispy Fried Samosa",
        "Palak Paneer with Salad",
        "Roast Chicken Breast",
        "Sprouted Moong Salad"
    ]
    ranked = evaluator.evaluate_menu(dishes)
    
    assert len(ranked) == 4
    # Highest scoring dish should be first, violation (Roast Chicken) should be last
    assert ranked[0].fit_score >= ranked[1].fit_score
    assert ranked[-1].dish_name == "Roast Chicken Breast"
    assert ranked[-1].fit_score == 0
