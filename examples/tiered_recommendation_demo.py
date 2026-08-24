"""
3-Tier Food Recommendation Engine (Part 3 Demo).
Demonstrates end-to-end integration between:
- Model 1: Food & Menu Item Data (Ingredients, Food Groups)
- Model 2: User Health & Nutritional Matrix (Biometrics, Guardrails, Exclusions)
- Model 3: The Middle Recommender classifying dishes into 🟢 GOOD, 🟡 MEDIUM, and 🔴 BAD tiers.
"""

import os
import sys
import json
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.matrix_generator import AIMatrixGenerator
from src.recommendation_engine import TieredFoodRecommender, FoodTier
from src.models import MenuItem, MenuSection, RecognizedMenu


def main():
    print("=" * 80)
    print("🍽️ PART 3: 3-TIER FOOD RECOMMENDATION ENGINE (THE MIDDLE MODEL)")
    print("=" * 80)

    # 1. MODEL 2: Define User Profile & Generate User Nutritional Matrix
    print("\n[Step 1] Loading User Health Profile & Computing Nutritional Matrix...")
    user_data = {
        "age": 45,
        "gender": "male",
        "height_cm": 176,
        "weight_kg": 86,
        "activity_level": "light",
        "primary_goal": "fat_loss",
        "health_conditions": ["hypertension", "type_2_diabetes", "gerd"],
        "allergies": ["peanuts"],
        "dietary_preferences": ["vegetarian"],
    }

    matrix_gen = AIMatrixGenerator()
    user_matrix = matrix_gen.generate(user_data, user_id="user_45_diabetic_veg")

    print(f"✅ User Matrix Ready: {user_matrix.user_summary}")
    print(f"   - Target Calories : {user_matrix.metabolic_targets.target_calories_kcal:.0f} kcal")
    print(f"   - Target Protein  : {user_matrix.metabolic_targets.target_protein_g:.0f} g")
    print(f"   - Sodium Guardrail: < {user_matrix.nutritional_guardrails.sodium_ceiling_mg} mg/day")
    print(f"   - Glycemic Sens.  : {user_matrix.clinical_risk_weights.glycemic_sensitivity:.2f} (Strict Low GI)")
    print(f"   - Strict Filters  : {', '.join(user_matrix.exclusion_mask)}")

    # 2. MODEL 1: Load Sample Restaurant Menu
    print("\n[Step 2] Loading Scanned Restaurant Dishes (Model 1)...")
    menu_items = [
        MenuItem(
            name="Palak Paneer with Multigrain Roti",
            description="Fresh spinach puree with cottage cheese and whole grain flatbread",
            raw_price="$13.50",
            dietary_tags=["vegetarian"]
        ),
        MenuItem(
            name="Steamed Sprouted Moong Salad",
            description="Sprouted green lentils, cucumber, tomatoes, lemon and cold-pressed olive oil",
            raw_price="$8.99",
            dietary_tags=["vegetarian", "vegan", "gluten-free"]
        ),
        MenuItem(
            name="Tandoori Vegetable Medley",
            description="Char-grilled bell peppers, broccoli, zucchini, and mushrooms marinated in yogurt and spices",
            raw_price="$11.99",
            dietary_tags=["vegetarian", "gluten-free"]
        ),
        MenuItem(
            name="Dal Makhani with Butter Naan",
            description="Black lentils slow cooked overnight in rich cream and churned butter, served with refined maida naan",
            raw_price="$14.00",
            dietary_tags=["vegetarian"]
        ),
        MenuItem(
            name="Vegetable Biryani with Cucumber Raita",
            description="Basmati rice cooked with mixed vegetables, saffron, and aromatic spices",
            raw_price="$12.50",
            dietary_tags=["vegetarian"]
        ),
        MenuItem(
            name="Crispy Peanut Pakora Chaat",
            description="Deep-fried gram flour fritters tossed with roasted peanuts, sweet tamarind chutney and sev",
            raw_price="$7.50",
            dietary_tags=["vegetarian"]
        ),
        MenuItem(
            name="Butter Chicken Makhani",
            description="Tender chicken tikka simmered in a silky tomato and cashew butter gravy",
            raw_price="$16.99",
            dietary_tags=["non-vegetarian"]
        ),
        MenuItem(
            name="Gulab Jamun with Rabri",
            description="Fried condensed milk balls soaked in cardamom sugar syrup with condensed milk",
            raw_price="$6.00",
            dietary_tags=["vegetarian", "dessert"]
        ),
    ]

    menu = RecognizedMenu(
        image_path="sample_indian_menu.png",
        image_width=1200,
        image_height=1600,
        num_columns=1,
        sections=[MenuSection(title="Specialties", items=menu_items)]
    )

    print(f"✅ Loaded {menu.total_items} menu dishes across restaurant sections.")

    # 3. MODEL 3: The Middle Recommender Model
    print("\n[Step 3] Running Middle Model (TieredFoodRecommender)...")
    recommender = TieredFoodRecommender(user_matrix=user_matrix)
    result = recommender.recommend_menu(menu)

    # 4. Display Results by Tier
    print("\n" + "=" * 80)
    print(f"📊 3-TIER RECOMMENDATION BREAKDOWN ({result.tier_counts['GOOD']} Good | {result.tier_counts['MEDIUM']} Medium | {result.tier_counts['BAD']} Bad)")
    print("=" * 80)

    print("\n🟢 TIER 1: GOOD (Recommended & Highly Compatible)")
    print("-" * 80)
    for rec in result.good_items:
        print(f"🌟 {rec.dish_name} ({rec.price}) — Fit Score: {rec.fit_score}/100")
        print(f"   Reason: {rec.summary_reason}")
        if rec.green_flags:
            print(f"   Green Flags: {'; '.join(rec.green_flags)}")
        if rec.customization_tips:
            print(f"   Tip: {rec.customization_tips}")
        print()

    print("🟡 TIER 2: MEDIUM (Moderate / Consume with Caution)")
    print("-" * 80)
    for rec in result.medium_items:
        print(f"⚠️  {rec.dish_name} ({rec.price}) — Fit Score: {rec.fit_score}/100")
        print(f"   Reason: {rec.summary_reason}")
        if rec.red_flags:
            print(f"   Caution: {'; '.join(rec.red_flags)}")
        if rec.customization_tips:
            print(f"   How to improve: {rec.customization_tips}")
        print()

    print("🔴 TIER 3: BAD (Avoid / High Risk / Contraindicated)")
    print("-" * 80)
    for rec in result.bad_items:
        print(f"🚫 {rec.dish_name} ({rec.price}) — Fit Score: {rec.fit_score}/100")
        print(f"   Reason: {rec.summary_reason}")
        if rec.allergen_warnings:
            print(f"   ⚠️ ALLERGEN/DIET ALERT: {'; '.join(rec.allergen_warnings)}")
        if rec.red_flags:
            print(f"   Red Flags: {'; '.join(rec.red_flags)}")
        print()

    # 5. Export Markdown & JSON
    out_dir = root_dir / "examples" / "output"
    out_dir.mkdir(exist_ok=True)
    
    md_path = out_dir / "tiered_recommendations.md"
    json_path = out_dir / "tiered_recommendations.json"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(result.to_markdown())

    with open(json_path, "w", encoding="utf-8") as f:
        f.write(result.to_json(indent=2))

    print("=" * 80)
    print(f"📁 Reports exported successfully:")
    print(f"   - Markdown: {md_path}")
    print(f"   - JSON    : {json_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
