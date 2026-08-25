"""
Integration tests for the complete NutriMenu AI pipeline.
Executes User Profile -> Nutritional Matrix -> Menu Recognition / Input -> Tiered Recommendation
completely offline without launching Streamlit.
"""

import pytest
import json
from src.matrix_generator import AIMatrixGenerator, UserNutritionalMatrix
from src.recommendation_engine import (
    TieredFoodRecommender,
    TieredRecommendationResult,
    FoodTier,
)
from src.models import MenuItem, MenuSection, RecognizedMenu
from src.menu_parser import MenuParser
from src.preprocessing import Preprocessor


def test_full_pipeline_user_to_recommendation():
    """End-to-end test from user profile dictionary to 3-tier menu classification."""
    # 1. User Profile Input
    user_payload = {
        "age": 45,
        "gender": "male",
        "height_cm": 176.0,
        "weight_kg": 86.0,
        "activity_level": "sedentary",
        "primary_goal": "fat_loss",
        "health_conditions": ["hypertension", "type_2_diabetes"],
        "dietary_preferences": ["vegetarian"],
        "allergies": ["peanuts"],
    }

    # 2. Generate Nutritional Matrix
    gen = AIMatrixGenerator(api_key="mock_disabled_key")
    matrix = gen.generate(user_payload, user_id="integration_user_01")

    assert isinstance(matrix, UserNutritionalMatrix)
    assert matrix.clinical_risk_weights.glycemic_sensitivity >= 0.80
    assert matrix.nutritional_guardrails.sodium_ceiling_mg <= 1500
    assert "peanuts" in matrix.exclusion_mask

    # 3. Supply Menu Dishes (Preset or Parsed)
    menu_dishes = [
        {"name": "Steamed Sprouted Moong Salad", "description": "Lentils, cucumber, tomatoes, lemon dressing", "price": "$8.99"},
        {"name": "Palak Paneer with Whole Wheat Roti", "description": "Fresh spinach puree with cottage cheese", "price": "$13.50"},
        {"name": "Crispy Peanut Pakora Chaat", "description": "Deep fried fritters with roasted peanuts", "price": "$7.50"},
        {"name": "Butter Chicken Makhani", "description": "Chicken tikka in heavy butter gravy", "price": "$16.99"},
        {"name": "Gulab Jamun with Rabri", "description": "Deep fried sweet condensed milk in sugar syrup", "price": "$6.00"},
        {"name": "Vegetable Biryani with Cucumber Raita", "description": "Basmati rice with mixed vegetables and yogurt dip", "price": "$12.50"},
    ]

    # 4. Run 3-Tier Matchmaker
    recommender = TieredFoodRecommender(user_matrix=matrix, good_threshold=75, bad_threshold=45)
    result = recommender.recommend_menu(menu_dishes)

    # 5. Verify Results
    assert isinstance(result, TieredRecommendationResult)
    assert result.total_items_evaluated == len(menu_dishes)
    assert result.tier_counts["GOOD"] >= 1
    assert result.tier_counts["BAD"] >= 2  # Peanut pakora (peanut allergy), Butter chicken (non-veg), Gulab jamun (sugar/fried)

    # Verify Peanut Pakora is BAD with peanut alert
    bad_dish_names = [item.dish_name for item in result.bad_items]
    assert "Crispy Peanut Pakora Chaat" in bad_dish_names
    assert "Butter Chicken Makhani" in bad_dish_names

    peanut_item = next(item for item in result.bad_items if item.dish_name == "Crispy Peanut Pakora Chaat")
    assert peanut_item.fit_score == 0
    assert any("peanut" in w.lower() for w in peanut_item.allergen_warnings)

    # Verify JSON and Markdown export
    json_out = result.to_json()
    assert len(json_out) > 100
    assert json.loads(json_out)["total_items_evaluated"] == len(menu_dishes)

    md_out = result.to_markdown()
    assert "Personalized 3-Tier Food & Menu Recommendations" in md_out
    assert "Tier 1: GOOD" in md_out
    assert "Tier 3: BAD" in md_out


def test_empty_and_duplicate_menu_handling():
    """Verify graceful handling for empty and duplicate dish inputs."""
    gen = AIMatrixGenerator(api_key="mock_disabled_key")
    matrix = gen.generate({"age": 30, "gender": "female", "height_cm": 165, "weight_kg": 60})

    recommender = TieredFoodRecommender(user_matrix=matrix)

    # Empty menu
    empty_result = recommender.recommend_menu([])
    assert empty_result.total_items_evaluated == 0
    assert len(empty_result.all_recommendations) == 0

    # Duplicate dishes
    duplicate_dishes = [
        {"name": "Greek Salad", "description": "Cucumber, tomato, feta", "price": "$10"},
        {"name": "Greek Salad", "description": "Cucumber, tomato, feta", "price": "$10"},
    ]
    dup_result = recommender.recommend_menu(duplicate_dishes)
    assert dup_result.total_items_evaluated == 2
    assert dup_result.all_recommendations[0].fit_score == dup_result.all_recommendations[1].fit_score
