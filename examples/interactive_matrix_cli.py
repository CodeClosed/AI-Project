"""
Interactive User Nutritional & Recommendation Metric Matrix CLI.
Prompts the user directly in the terminal for their details and generates
a personalized multi-dimensional health and food recommendation matrix.
"""

import sys
import os
import json
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


def prompt_guided_profile():
    """Interactively prompts the user for structured biometric and clinical information."""
    print("\n--- [Guided Profile Intake] ---\n")
    
    # 1. Age
    while True:
        age_str = input("• Enter your Age (years, e.g. 30): ").strip()
        if age_str.isdigit() and 1 <= int(age_str) <= 120:
            age = int(age_str)
            break
        print("  Invalid age. Please enter a valid number between 1 and 120.")

    # 2. Gender
    while True:
        gender = input("• Enter your Biological Gender [male / female]: ").strip().lower()
        if gender in ["male", "female", "m", "f"]:
            gender = "male" if gender in ["male", "m"] else "female"
            break
        print("  Please enter 'male' or 'female'.")

    # 3. Height
    while True:
        h_str = input("• Enter your Height in cm (e.g. 175): ").strip()
        try:
            height_cm = float(h_str)
            if 50 <= height_cm <= 250:
                break
        except ValueError:
            pass
        print("  Please enter a valid height in cm (e.g. 175).")

    # 4. Weight
    while True:
        w_str = input("• Enter your Weight in kg (e.g. 78.5): ").strip()
        try:
            weight_kg = float(w_str)
            if 20 <= weight_kg <= 300:
                break
        except ValueError:
            pass
        print("  Please enter a valid weight in kg (e.g. 78.5).")

    # 5. Activity Level
    print("\nSelect your Activity Level:")
    print("  [1] Sedentary (desk job, little to no exercise)")
    print("  [2] Lightly Active (light exercise 1-3 days/week)")
    print("  [3] Moderately Active (moderate exercise 3-5 days/week)")
    print("  [4] Very Active (hard exercise 6-7 days/week)")
    print("  [5] Extra Active / Athlete (physical job or 2x/day training)")
    act_choice = input("Enter choice [1-5] (default: 1): ").strip() or "1"
    act_map = {
        "1": "sedentary",
        "2": "light",
        "3": "moderate",
        "4": "heavy",
        "5": "athlete"
    }
    activity_level = act_map.get(act_choice, "sedentary")

    # 6. Primary Goal
    print("\nSelect your Primary Goal:")
    print("  [1] Fat Loss / Deficit")
    print("  [2] Muscle Gain / Lean Bulking")
    print("  [3] Maintenance & Longevity")
    print("  [4] Athletic Endurance")
    goal_choice = input("Enter choice [1-4] (default: 1): ").strip() or "1"
    goal_map = {
        "1": "fat_loss",
        "2": "muscle_gain",
        "3": "maintenance",
        "4": "endurance"
    }
    primary_goal = goal_map.get(goal_choice, "fat_loss")

    # 7. Health / Medical Conditions
    print("\nHealth / Medical Conditions (comma-separated, e.g. hypertension, type_2_diabetes, gerd, pcos, high_cholesterol):")
    cond_input = input("Enter conditions (leave blank if none): ").strip()
    health_conditions = [c.strip() for c in cond_input.split(",") if c.strip()] if cond_input else []

    # 8. Dietary Preferences
    print("\nDietary Preferences (comma-separated, e.g. vegetarian, vegan, halal, keto, low_carb):")
    diet_input = input("Enter dietary preferences (leave blank if omnivore/none): ").strip()
    dietary_preferences = [d.strip() for d in diet_input.split(",") if d.strip()] if diet_input else []

    # 9. Allergies / Intolerances
    print("\nAllergies & Intolerances (comma-separated, e.g. peanuts, dairy, gluten, shellfish):")
    allergy_input = input("Enter allergies (leave blank if none): ").strip()
    allergies = [a.strip() for a in allergy_input.split(",") if a.strip()] if allergy_input else []

    # 10. Lifestyle / Habit Notes
    print("\nAny other lifestyle habits or details? (e.g. 'work night shifts', 'feel bloated after dairy'):")
    lifestyle_notes = input("Enter notes (optional): ").strip()

    return {
        "age": age,
        "gender": gender,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "activity_level": activity_level,
        "primary_goal": primary_goal,
        "health_conditions": health_conditions,
        "dietary_preferences": dietary_preferences,
        "allergies": allergies,
        "lifestyle_notes": lifestyle_notes
    }


def main():
    print("=" * 80)
    print(" 🥗 INTERACTIVE AI NUTRITIONAL & RECOMMENDATION MATRIX GENERATOR")
    print("=" * 80)

    generator = AIMatrixGenerator()
    status = "Google Gemini AI (Online)" if generator.is_available() else "Deterministic Baseline (Offline)"
    print(f"[*] Engine Status: {status}\n")

    print("Choose input mode:")
    print("  [1] Guided Step-by-Step Questionnaire (Recommended)")
    print("  [2] Quick Natural Language Description (Free-form text)")
    
    choice = input("\nEnter choice [1 or 2] (default: 1): ").strip() or "1"

    if choice == "2":
        print("\nType a natural language description of yourself:")
        print("Example: '32yo male, 82kg, 178cm, desk job, pre-diabetic and hypertension, want to lose 5kg without feeling tired.'\n")
        bio_text = input("Your Bio: ").strip()
        if not bio_text:
            print("No input provided. Exiting.")
            return
        user_input = bio_text
    else:
        user_input = prompt_guided_profile()

    print("\n" + "=" * 80)
    print(" ⏳ Generating your personalized Nutritional & Recommendation Matrix...")
    print("=" * 80)

    matrix = generator.generate(user_input)

    print("\n" + matrix.to_markdown())

    # Optional export prompt
    print("\n" + "=" * 80)
    save_choice = input("Would you like to save this matrix as a JSON file for your other systems? [y/N]: ").strip().lower()
    if save_choice in ["y", "yes"]:
        filename = input("Enter filename (default: user_matrix.json): ").strip() or "user_matrix.json"
        if not filename.endswith(".json"):
            filename += ".json"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(matrix.to_json(indent=2))
        print(f"✅ Successfully saved matrix to '{filename}'!")

    print("\nDone! You can use this matrix vector or JSON in your recommendation system.")


if __name__ == "__main__":
    main()
