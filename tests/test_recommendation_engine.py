"""
Unit tests for the 3-Tier Food Recommendation Engine (The Middle Model).
"""

import pytest
from src.recommendation_engine import (
    FoodTier,
    TieredFoodRecommendation,
    TieredRecommendationResult,
    TieredFoodRecommender,
)
from src.models import MenuItem, MenuSection, RecognizedMenu
from src.user_models import UserProfile, NutritionalMatrixProfile
from src.matrix_generator import AIMatrixGenerator, UserNutritionalMatrix


@pytest.fixture
def sample_user_matrix() -> UserNutritionalMatrix:
    """Fixture providing a deterministic UserNutritionalMatrix for a hypertensive pre-diabetic vegetarian."""
    gen = AIMatrixGenerator()
    user_dict = {
        "age": 42,
        "gender": "female",
        "height_cm": 165,
        "weight_kg": 72,
        "activity_level": "sedentary",
        "primary_goal": "fat_loss",
        "health_conditions": ["hypertension", "pre_diabetes"],
        "allergies": ["peanuts"],
        "dietary_preferences": ["vegetarian"],
    }
    return gen._generate_deterministic(user_dict, user_id="test_user_01")


@pytest.fixture
def sample_menu() -> RecognizedMenu:
    """Fixture providing a mock recognized menu."""
    menu = RecognizedMenu(image_path="test_menu.jpg", image_width=800, image_height=1000, num_columns=1)
    
    sec1 = MenuSection(title="Salads & Starters")
    sec1.items.append(MenuItem(name="Steamed Broccoli Salad", description="Fresh steamed broccoli, cucumber, and lemon herb dressing", raw_price="$7.99"))
    sec1.items.append(MenuItem(name="Deep Fried Pakoras", description="Crispy gram flour fritters deep fried in oil", raw_price="$5.99"))
    sec1.items.append(MenuItem(name="Crispy Peanut Chaat", description="Spicy roasted peanuts with onions and lime", raw_price="$6.50"))
    
    sec2 = MenuSection(title="Mains")
    sec2.items.append(MenuItem(name="Tandoori Paneer Tikka", description="Grilled cottage cheese with bell peppers and tandoori spices", raw_price="$12.99"))
    sec2.items.append(MenuItem(name="Butter Chicken Curry", description="Rich chicken curry simmered in butter and heavy cream", raw_price="$14.99"))
    sec2.items.append(MenuItem(name="Dal Tadka with Whole Wheat Roti", description="Yellow lentil curry with cumin and whole wheat flatbread", raw_price="$10.99"))
    sec2.items.append(MenuItem(name="Gulab Jamun", description="Deep fried milk solids soaked in sugar syrup", raw_price="$4.50"))

    menu.sections = [sec1, sec2]
    return menu


def test_recommender_initialization(sample_user_matrix):
    recommender = TieredFoodRecommender(user_matrix=sample_user_matrix)
    assert recommender.user_summary is not None
    assert recommender.target_calories > 0
    assert "vegetarian" in [e.lower() for e in recommender.exclusions] or "peanuts" in recommender.exclusions


def test_good_tier_classification(sample_user_matrix):
    recommender = TieredFoodRecommender(user_matrix=sample_user_matrix)
    item = MenuItem(
        name="Steamed Broccoli Salad",
        description="Fresh steamed greens with lemon dressing",
        raw_price="$8.00"
    )
    rec = recommender._recommend_dish_deterministic(recommender._to_dish_dict(item))
    
    assert rec.tier == FoodTier.GOOD
    assert rec.fit_score >= 75
    assert len(rec.green_flags) > 0
    assert "GOOD" in rec.tier_badge


def test_medium_tier_classification(sample_user_matrix):
    recommender = TieredFoodRecommender(user_matrix=sample_user_matrix)
    item = MenuItem(
        name="Mixed Veg Curry with Rice",
        description="Standard spiced vegetables served with white rice",
        raw_price="$11.00"
    )
    rec = recommender._recommend_dish_deterministic(recommender._to_dish_dict(item))
    
    assert rec.tier in [FoodTier.MEDIUM, FoodTier.GOOD]
    assert rec.fit_score >= 45


def test_bad_tier_due_to_unhealthy_profile(sample_user_matrix):
    recommender = TieredFoodRecommender(user_matrix=sample_user_matrix)
    item = MenuItem(
        name="Deep Fried Bhatura & Sweet Halwa",
        description="Crispy deep fried refined flour bread with sugary halwa",
        raw_price="$9.00"
    )
    rec = recommender._recommend_dish_deterministic(recommender._to_dish_dict(item))
    
    assert rec.tier == FoodTier.BAD
    assert rec.fit_score < 50
    assert len(rec.red_flags) > 0


def test_bad_tier_due_to_dietary_violation(sample_user_matrix):
    recommender = TieredFoodRecommender(user_matrix=sample_user_matrix)
    item = MenuItem(
        name="Butter Chicken Makhani",
        description="Chicken curry with heavy butter cream",
        raw_price="$15.00"
    )
    rec = recommender._recommend_dish_deterministic(recommender._to_dish_dict(item))
    
    assert rec.tier == FoodTier.BAD
    assert rec.fit_score == 0
    assert any("vegetarian" in w.lower() or "meat" in w.lower() for w in rec.allergen_warnings + rec.red_flags)


def test_bad_tier_due_to_declared_allergen(sample_user_matrix):
    recommender = TieredFoodRecommender(user_matrix=sample_user_matrix)
    item = MenuItem(
        name="Crispy Peanut Chaat",
        description="Spicy roasted peanuts with lime",
        raw_price="$6.00"
    )
    rec = recommender._recommend_dish_deterministic(recommender._to_dish_dict(item))
    
    assert rec.tier == FoodTier.BAD
    assert rec.fit_score == 0
    assert any("peanut" in w.lower() for w in rec.allergen_warnings)


def test_menu_recommendation_batch(sample_user_matrix, sample_menu):
    recommender = TieredFoodRecommender(user_matrix=sample_user_matrix)
    result = recommender.recommend_menu(sample_menu)
    
    assert isinstance(result, TieredRecommendationResult)
    assert result.total_items_evaluated == len(sample_menu.get_all_items())
    assert len(result.good_items) > 0
    assert len(result.bad_items) > 0
    assert result.tier_counts["GOOD"] == len(result.good_items)
    assert result.tier_counts["BAD"] == len(result.bad_items)
    
    # Top pick should be from GOOD tier
    assert result.top_pick is not None
    assert result.top_pick.tier == FoodTier.GOOD

    # Verify JSON and Markdown serialization
    json_str = result.to_json()
    assert '"GOOD"' in json_str or '"total_items_evaluated"' in json_str
    
    md_report = result.to_markdown()
    assert "Tier 1: GOOD" in md_report
    assert "Tier 2: MEDIUM" in md_report
    assert "Tier 3: BAD" in md_report
