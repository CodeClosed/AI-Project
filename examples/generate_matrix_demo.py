"""
Standalone Matrix Generation Demonstration.
Takes raw user inputs (structured and free-form text) and outputs a
standardized, multidimensional Nutritional & Health Matrix ready for external systems.
"""

import sys
from pathlib import Path

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.matrix_generator import AIMatrixGenerator


def main():
    print("=" * 80)
    print(" 📊 STANDALONE USER NUTRITIONAL MATRIX GENERATOR")
    print("=" * 80)

    generator = AIMatrixGenerator()
    status = "Vision/Language AI (Online)" if generator.is_available() else "Deterministic Baseline (Offline)"
    print(f"[*] Engine Status: {status}\n")

    # Example 1: Structured User Input
    print("--- [Example 1: Generating Matrix from Structured User Profile] ---")
    user_data = {
        "age": 34,
        "gender": "male",
        "height_cm": 178,
        "weight_kg": 84.0,
        "activity_level": "sedentary",
        "primary_goal": "fat_loss",
        "health_conditions": ["hypertension", "pre_diabetes"],
        "dietary_preferences": ["vegetarian"],
        "allergies": ["peanuts"],
        "lifestyle_notes": "Desk job 9 hours a day, afternoon fatigue, family history of heart disease."
    }

    matrix = generator.generate(user_data, user_id="usr_001")

    # 1. Print Markdown Summary
    print("\n[+] Rendered Matrix Markdown Card:\n")
    print(matrix.to_markdown())

    # 2. Print JSON Schema Export
    print("\n" + "=" * 80)
    print(" 📦 EXPORT FORMAT 1: Standalone JSON Representation (for APIs/Microservices)")
    print("=" * 80)
    print(matrix.to_json(indent=2))

    # 3. Print 1D Numerical Feature Vector
    print("\n" + "=" * 80)
    print(" 🔢 EXPORT FORMAT 2: 1D Numeric Feature Vector (for ML / Cosine Similarity)")
    print("=" * 80)
    feat_vec = matrix.to_feature_vector()
    print(f"Vector Dimensions: {len(feat_vec)}")
    print(f"Values: {feat_vec}")

    # Example 2: Natural Language Input
    print("\n" + "=" * 80)
    print("--- [Example 2: Generating Matrix from Natural Language Text] ---")
    bio_text = (
        "28yo female, 60kg, 165cm, marathon runner in training. "
        "Vegan diet, mild lactose/dairy sensitivity, aiming for high endurance and fast muscle recovery."
    )
    print(f"Input Bio: '{bio_text}'\n")
    bio_matrix = generator.generate(bio_text, user_id="usr_002")
    
    print(f"• Summary: {bio_matrix.user_summary}")
    print(f"• BMR: {bio_matrix.metabolic_targets.bmr_kcal} kcal | TDEE: {bio_matrix.metabolic_targets.tdee_kcal} kcal")
    print(f"• Calorie Target: {bio_matrix.metabolic_targets.target_calories_kcal} kcal ({bio_matrix.metabolic_targets.caloric_adjustment_ratio:+.1%})")
    print(f"• Protein Target: {bio_matrix.metabolic_targets.target_protein_g}g ({bio_matrix.metabolic_targets.target_protein_pct:.1f}%)")
    print(f"• Plant Protein Weight: {bio_matrix.food_group_weights.get('plant_based_proteins_tofu_tempeh')}")
    print(f"• Whole Grains & Millets Weight: {bio_matrix.food_group_weights.get('whole_grains_and_millets')}")
    print(f"• Animal Meat Weight: {bio_matrix.food_group_weights.get('red_meat_and_game')}")
    print(f"• Hard Exclusion Mask: {bio_matrix.exclusion_mask}")

    print("\n" + "=" * 80)
    print(" ✅ Matrix generation demo completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
