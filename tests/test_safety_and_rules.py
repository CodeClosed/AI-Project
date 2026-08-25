"""
Unit tests for deterministic safety rules, hard exclusions, and nutritional scoring.
Ensures allergies, dietary prohibitions, and clinical guardrails cannot be overridden.
"""

import pytest
from src.matrix_generator import AIMatrixGenerator
from src.recommendation_engine import (
    TieredFoodRecommender,
    FoodTier,
    TieredFoodRecommendation,
)


@pytest.fixture
def peanut_allergy_user():
    gen = AIMatrixGenerator(api_key="mock_disabled_key")
    return gen.generate({
        "age": 30,
        "gender": "male",
        "height_cm": 175,
        "weight_kg": 75,
        "primary_goal": "maintenance",
        "allergies": ["peanuts"],
        "dietary_preferences": [],
    })


@pytest.fixture
def vegetarian_user():
    gen = AIMatrixGenerator(api_key="mock_disabled_key")
    return gen.generate({
        "age": 32,
        "gender": "female",
        "height_cm": 165,
        "weight_kg": 60,
        "primary_goal": "fat_loss",
        "allergies": [],
        "dietary_preferences": ["vegetarian"],
    })


@pytest.fixture
def vegan_user():
    gen = AIMatrixGenerator(api_key="mock_disabled_key")
    return gen.generate({
        "age": 29,
        "gender": "female",
        "height_cm": 170,
        "weight_kg": 62,
        "primary_goal": "maintenance",
        "allergies": [],
        "dietary_preferences": ["vegan"],
    })


@pytest.fixture
def diabetic_hypertensive_user():
    gen = AIMatrixGenerator(api_key="mock_disabled_key")
    return gen.generate({
        "age": 55,
        "gender": "male",
        "height_cm": 178,
        "weight_kg": 90,
        "primary_goal": "fat_loss",
        "health_conditions": ["type_2_diabetes", "hypertension"],
        "allergies": [],
        "dietary_preferences": [],
    })


def test_peanut_allergy_hard_exclusion(peanut_allergy_user):
    recommender = TieredFoodRecommender(user_matrix=peanut_allergy_user)
    
    dish = {
        "name": "Peanut Butter Satay Skewers",
        "description": "Grilled skewers with rich peanut sauce and chili",
        "price": "$12.00",
    }
    rec = recommender.recommend_dish(dish)

    assert rec.tier == FoodTier.BAD
    assert rec.fit_score == 0
    assert any("peanut" in w.lower() for w in rec.allergen_warnings)
    assert "Strictly forbidden" in rec.summary_reason or "allergen" in rec.summary_reason.lower()


def test_vegetarian_hard_conflict_meat(vegetarian_user):
    recommender = TieredFoodRecommender(user_matrix=vegetarian_user)
    
    dishes = [
        {"name": "Butter Chicken Curry", "description": "Tender chicken in tomato cream sauce"},
        {"name": "Grilled Beef Cheeseburger", "description": "Beef patty with cheddar on bun"},
        {"name": "Crispy Calamari Rings", "description": "Deep fried squid with garlic mayo"},
    ]

    for dish in dishes:
        rec = recommender.recommend_dish(dish)
        assert rec.tier == FoodTier.BAD
        assert rec.fit_score == 0
        assert any("vegetarian" in w.lower() or "meat" in w.lower() for w in rec.allergen_warnings + rec.red_flags)


def test_vegan_hard_conflict_dairy_and_egg(vegan_user):
    recommender = TieredFoodRecommender(user_matrix=vegan_user)
    
    dishes = [
        {"name": "Paneer Tikka Masala", "description": "Cottage cheese in spiced gravy"},
        {"name": "Egg Fried Rice", "description": "Jasmine rice stir-fried with scrambled eggs"},
    ]

    for dish in dishes:
        rec = recommender.recommend_dish(dish)
        assert rec.tier == FoodTier.BAD
        assert rec.fit_score == 0
        assert any("vegan" in w.lower() or "dairy" in w.lower() or "egg" in w.lower() for w in rec.allergen_warnings + rec.red_flags)


def test_diabetic_glycemic_load_penalty(diabetic_hypertensive_user):
    recommender = TieredFoodRecommender(user_matrix=diabetic_hypertensive_user)
    
    sugary_dish = {
        "name": "Chocolate Lava Cake with Vanilla Ice Cream",
        "description": "Warm chocolate cake with molten center and sweet syrup",
        "price": "$8.00",
    }
    rec = recommender.recommend_dish(sugary_dish)

    assert rec.tier == FoodTier.BAD
    assert rec.fit_score < 45
    assert any("sugar" in r.lower() or "carbohydrate" in r.lower() for r in rec.red_flags)


def test_clearly_compatible_dish_reaches_good_tier(vegetarian_user):
    recommender = TieredFoodRecommender(user_matrix=vegetarian_user)
    
    healthy_dish = {
        "name": "Steamed Sprouted Moong and Spinach Salad",
        "description": "Steamed lentils, fresh baby spinach, cucumber, lemon herb dressing",
        "price": "$9.50",
        "tags": ["vegetarian"],
    }
    rec = recommender.recommend_dish(healthy_dish)

    assert rec.tier == FoodTier.GOOD
    assert rec.fit_score >= 75
    assert len(rec.green_flags) >= 1
    assert len(rec.allergen_warnings) == 0


def test_borderline_dish_reaches_medium_tier(vegetarian_user):
    recommender = TieredFoodRecommender(user_matrix=vegetarian_user)
    
    borderline_dish = {
        "name": "Mixed Vegetable Curry with Steamed Rice",
        "description": "Assorted vegetables in mild spiced gravy with portion of rice",
        "price": "$11.00",
    }
    rec = recommender.recommend_dish(borderline_dish)

    assert rec.tier in (FoodTier.MEDIUM, FoodTier.GOOD)
    assert rec.fit_score >= 45


def test_threshold_safety_enforcement(vegetarian_user):
    # Invalid combinations: good <= bad
    recommender = TieredFoodRecommender(
        user_matrix=vegetarian_user,
        good_threshold=40,
        bad_threshold=50
    )
    # The recommender should automatically normalize good > bad
    assert recommender.good_threshold > recommender.bad_threshold
    assert 0 <= recommender.bad_threshold < recommender.good_threshold <= 100
