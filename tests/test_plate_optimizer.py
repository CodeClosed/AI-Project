"""
Unit tests for PlateOptimizer & Multi-Dish Synergy Engine.
"""

import pytest
from src.plate_optimizer import PlateOptimizer
from src.matrix_generator import AIMatrixGenerator, UserNutritionalMatrix


@pytest.fixture
def sample_matrix() -> UserNutritionalMatrix:
    gen = AIMatrixGenerator()
    user_dict = {
        "age": 35,
        "gender": "male",
        "height_cm": 178,
        "weight_kg": 80,
        "activity_level": "sedentary",
        "primary_goal": "fat_loss",
        "health_conditions": ["hypertension"],
        "allergies": [],
        "dietary_preferences": ["vegetarian"],
    }
    return gen._generate_deterministic(user_dict, user_id="test_user_plate")


def test_estimate_dish_nutrients():
    opt = PlateOptimizer()
    
    # 1. Standard single serving
    salad = opt.estimate_dish_nutrients("Steamed Broccoli Salad", portion=1.0)
    assert salad["calories"] > 0
    assert salad["fiber"] >= 5.0

    # 2. Portion multiplier
    paneer_2x = opt.estimate_dish_nutrients("Palak Paneer", portion=2.0)
    paneer_1x = opt.estimate_dish_nutrients("Palak Paneer", portion=1.0)
    assert paneer_2x["calories"] == pytest.approx(paneer_1x["calories"] * 2.0)
    assert paneer_2x["protein"] == pytest.approx(paneer_1x["protein"] * 2.0)


def test_evaluate_plate_burn_down(sample_matrix):
    opt = PlateOptimizer(user_matrix=sample_matrix)
    
    plate_items = [
        {"name": "Palak Paneer", "portion": 1.0},
        {"name": "Whole Wheat Tandoori Roti", "portion": 2.0},
        {"name": "Cucumber Salad", "portion": 1.0},
    ]

    result = opt.evaluate_plate(plate_items, user_matrix=sample_matrix)
    assert "total_nutrients" in result
    assert "remaining_budget" in result
    assert "budget_percentages" in result
    assert "synergy_score" in result

    # Total calories must sum all dishes
    cals = result["total_nutrients"]["calories"]
    assert cals > 400
    assert result["remaining_budget"]["calories"] == pytest.approx(
        result["daily_targets"]["calories"] - cals, abs=1.0
    )
    assert 0 <= result["synergy_score"] <= 100


def test_suggest_plate_companions(sample_matrix):
    opt = PlateOptimizer(user_matrix=sample_matrix)

    # Plate has only carbs (Roti) -> should suggest protein or fiber companions
    plate_items = [{"name": "Tandoori Roti", "portion": 2.0}]
    menu_candidates = [
        "Tandoori Roti",
        "Steamed Broccoli Salad",
        "Dal Tadka",
        "Deep Fried Pakora",
        "Gulab Jamun",
    ]

    suggestions = opt.suggest_plate_companions(plate_items, menu_candidates, user_matrix=sample_matrix)
    assert len(suggestions) > 0
    sug_names = [s["dish_name"] for s in suggestions]
    assert "Tandoori Roti" not in sug_names  # Excludes already selected dish
    assert any("Salad" in s or "Dal" in s for s in sug_names)


def test_vegetarian_companion_safety(sample_matrix):
    opt = PlateOptimizer(user_matrix=sample_matrix)
    plate_items = [{"name": "Fruit Salad", "portion": 1.0}]
    menu_candidates = [
        "Fruit Salad",
        "Chicken Burger",
        "Butter Chicken",
        "Steamed Edamame",
        "Paneer Tikka",
    ]

    suggestions = opt.suggest_plate_companions(plate_items, menu_candidates, user_matrix=sample_matrix)
    assert len(suggestions) > 0
    sug_names = [s["dish_name"].lower() for s in suggestions]
    # Chicken Burger and Butter Chicken MUST be excluded
    assert "chicken burger" not in sug_names
    assert "butter chicken" not in sug_names
    assert any("edamame" in s or "paneer" in s for s in sug_names)

