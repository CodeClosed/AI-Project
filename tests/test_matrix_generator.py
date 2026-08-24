"""
Unit Tests for Standalone UserNutritionalMatrix and AIMatrixGenerator.
"""

import pytest
import json
from src.matrix_generator import (
    AIMatrixGenerator,
    UserNutritionalMatrix,
    MetabolicTargets,
    ClinicalRiskWeights,
    NutritionalGuardrails,
)


def test_deterministic_matrix_generation_hypertension_diabetes():
    """Verify matrix calculation for user with hypertension and diabetes."""
    generator = AIMatrixGenerator(api_key="mock_disabled_key")
    
    user_data = {
        "age": 35,
        "gender": "male",
        "height_cm": 180.0,
        "weight_kg": 85.0,
        "activity_level": "sedentary",
        "primary_goal": "fat_loss",
        "health_conditions": ["hypertension", "type_2_diabetes"],
        "dietary_preferences": ["vegetarian"],
        "allergies": ["peanuts"]
    }
    
    matrix = generator.generate(user_data, user_id="test_user_01")
    
    assert isinstance(matrix, UserNutritionalMatrix)
    assert matrix.user_id == "test_user_01"
    
    # 1. Metabolic targets
    m = matrix.metabolic_targets
    assert m.bmr_kcal > 1700
    assert m.tdee_kcal > m.bmr_kcal
    assert m.target_calories_kcal < m.tdee_kcal  # Deficit for fat loss
    assert m.caloric_adjustment_ratio < 0
    assert m.target_protein_g > 100
    assert m.target_water_liters > 2.0
    
    # 2. Risk weights
    w = matrix.clinical_risk_weights
    assert w.glycemic_sensitivity >= 0.80  # High due to diabetes
    assert w.cardiovascular_risk_weight >= 0.80  # High due to hypertension
    assert 0.0 <= w.satiety_demand_weight <= 1.0
    
    # 3. Guardrails
    g = matrix.nutritional_guardrails
    assert g.sodium_ceiling_mg <= 1500  # DASH limit
    assert g.dietary_fiber_min_g >= 35.0
    assert g.saturated_fat_max_pct <= 0.10
    
    # 4. Food group weights
    fg = matrix.food_group_weights
    assert fg["cruciferous_vegetables"] >= 9.0
    assert fg["dark_leafy_greens"] >= 9.0
    assert fg["refined_carbohydrates"] <= -8.0
    assert fg["deep_fried_and_ultra_processed"] <= -8.0
    # Vegetarian should penalize meat
    assert fg["red_meat_and_game"] == -10.0
    assert fg["lean_poultry"] == -10.0
    
    # 5. Exclusion mask
    assert "peanuts" in matrix.exclusion_mask
    assert any("meat" in ex or "poultry" in ex for ex in matrix.exclusion_mask)


def test_matrix_serialization_and_feature_vector():
    """Verify JSON, dict, and flat numeric feature vector outputs."""
    generator = AIMatrixGenerator(api_key="mock_disabled_key")
    
    user_data = {
        "age": 28,
        "gender": "female",
        "height_cm": 165.0,
        "weight_kg": 60.0,
        "activity_level": "moderate",
        "primary_goal": "maintenance"
    }
    matrix = generator.generate(user_data)
    
    # Dict serialization
    d = matrix.to_dict()
    assert "metabolic_targets" in d
    assert "clinical_risk_weights" in d
    assert "food_group_weights" in d
    
    # JSON serialization
    js = matrix.to_json()
    loaded = json.loads(js)
    assert loaded["metabolic_targets"]["target_calories_kcal"] > 0
    
    # 1D Feature vector
    vec = matrix.to_feature_vector()
    assert isinstance(vec, list)
    assert len(vec) == 20
    assert all(isinstance(x, (int, float)) for x in vec)
    
    # Markdown rendering
    md = matrix.to_markdown()
    assert "# 📊 User Nutritional & Recommendation Metric Matrix" in md
    assert "Clinical Risk Weights" in md
    assert "Food Group Compatibility Weights" in md


def test_natural_language_bio_generation():
    """Verify generation from a natural language string."""
    generator = AIMatrixGenerator(api_key="mock_disabled_key")
    bio = "40yo male, 90kg, 182cm, desk job, wants to lose weight and has high cholesterol."
    
    matrix = generator.generate(bio)
    assert matrix.metabolic_targets.target_calories_kcal > 0
    assert len(matrix.food_group_weights) > 10
    assert len(matrix.to_feature_vector()) == 20
