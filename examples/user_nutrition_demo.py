"""
Demonstration Script: AI-Powered User Health Matrix & Menu Dish Recommender.
Synthesizes a user profile into a multidimensional clinical matrix,
scores food group affinities, and ranks restaurant menu items for optimal health fit.
"""

import os
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

from src.user_models import UserProfile
from src.nutrition_ai import AINutritionProfiler
from src.dish_evaluator import MenuDishEvaluator



def main():
    print("=" * 80)
    print(" 🥗 AI NUTRITION & HEALTH MATRIX ENGINE - LIVE DEMO")
    print("=" * 80)

    # 1. Initialize Profiler
    profiler = AINutritionProfiler()
    engine_status = "Vision/Language AI (Online)" if profiler.is_available() else "Deterministic Baseline (Offline)"
    print(f"[*] Profiler Engine Status: {engine_status}\n")

    # 2. Define Sample User Profile
    user = UserProfile(
        age=34,
        gender="male",
        height_cm=178,
        weight_kg=83.5,
        activity_level="sedentary",
        primary_goal="fat_loss",
        health_conditions=["hypertension", "pre_diabetes"],
        allergies=["peanuts"],
        dietary_preferences=["vegetarian"],
        raw_bio_text="Software engineer sitting 8+ hours a day. Experiencing afternoon energy slumps and high blood pressure."
    )

    print(f"[+] Generating Health Matrix for User:")
    print(f"    - Age: {user.age}, Sex: {user.gender}, Height: {user.height_cm}cm, Weight: {user.weight_kg}kg")
    print(f"    - Activity: {user.activity_level}, Goal: {user.primary_goal}")
    print(f"    - Conditions: {', '.join(user.health_conditions)}")
    print(f"    - Diet: {', '.join(user.dietary_preferences)}, Allergies: {', '.join(user.allergies)}\n")

    # 3. Generate the Nutritional & Metabolic Matrix Profile
    matrix = profiler.generate_matrix(user)

    print("-" * 80)
    print(matrix.to_markdown())
    print("-" * 80)

    # 4. Bridge with Menu Dishes (Evaluating Restaurant Dishes against User's Matrix)
    sample_menu_dishes = [
        "Palak Paneer with Roti",
        "Deep Fried Samosa (2 pcs)",
        "Dal Tadka with Steamed Brown Rice",
        "Butter Chicken with Garlic Naan",
        "Paneer Tikka with Mint Chutney & Garden Salad",
        "Gulab Jamun with Sugar Syrup",
        "Sprouted Moong Salad with Lemon & Cucumber",
        "Crispy French Fries with Cheese Dip",
    ]

    print(f"\n[+] Evaluating Restaurant Menu Dishes against User's Personalized Matrix:")
    evaluator = MenuDishEvaluator(user_matrix=matrix)
    ranked_results = evaluator.evaluate_menu(sample_menu_dishes)

    print("\n" + "=" * 80)
    print(" 🏆 PERSONALIZED MENU RECOMMENDATIONS & FIT LEADERBOARD")
    print("=" * 80)

    for rank, dish in enumerate(ranked_results, 1):
        if dish.fit_score >= 85:
            badge = "🟢 [EXCELLENT CHOICE]"
        elif dish.fit_score >= 70:
            badge = "🟡 [HEALTHY CHOICE]"
        elif dish.fit_score >= 40:
            badge = "🟠 [MODERATE / CAUTION]"
        elif dish.fit_score > 0:
            badge = "🔴 [NOT RECOMMENDED]"
        else:
            badge = "⛔ [DIETARY VIOLATION]"

        print(f"\n{rank}. {dish.dish_name} — Score: {dish.fit_score}/100 {badge}")
        print(f"   • Verdict: {dish.verdict}")
        print(f"   • Matched Food Groups: {', '.join(dish.matched_food_groups)}")
        if dish.green_flags:
            print(f"   • Green Flags: {', '.join(dish.green_flags)}")
        if dish.red_flags:
            print(f"   • Red Flags: {', '.join(dish.red_flags)}")
        if dish.customization_tips:
            print(f"   • 💡 Tip: {dish.customization_tips}")

    print("\n" + "=" * 80)
    print(" Demo complete! Personalized nutrition matrix & dish scoring verified.")
    print("=" * 80)


if __name__ == "__main__":
    main()
