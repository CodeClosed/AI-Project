"""
AI-Powered Nutrition & Health Matrix Profiler using Google Gemini.
Synthesizes user biometrics, medical context, lifestyle, and dietary habits
into a comprehensive metabolic matrix, clinical guardrails, and scored food group affinities.
"""

from typing import List, Dict, Any, Optional, Union
import os
import re
import json
from pathlib import Path
import requests

from .user_models import (
    UserProfile,
    MacroSplit,
    MetabolicEnergyMatrix,
    ClinicalGuardrailMatrix,
    FoodGroupAffinity,
    NutritionalMatrixProfile,
)


class AINutritionProfiler:
    """Intelligent clinical & nutritional matrix generator powered by Gemini AI."""

    CANDIDATE_MODELS = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-3.7-flash",
    ]

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or self._load_api_key()
        self.model_name = model_name or "gemini-3.6-flash"

    def _load_api_key(self) -> Optional[str]:
        """Loads API key from environment variable or .env file."""
        if "GEMINI_API_KEY" in os.environ and os.environ["GEMINI_API_KEY"].strip():
            return os.environ["GEMINI_API_KEY"].strip()

        current = Path.cwd()
        for path in [current / ".env", current.parent / ".env", Path(__file__).resolve().parent.parent / ".env"]:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("GEMINI_API_KEY=") and not line.startswith("#"):
                                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                                if key:
                                    os.environ["GEMINI_API_KEY"] = key
                                    return key
                except Exception:
                    pass
        return None

    def is_available(self) -> bool:
        """Returns True if a valid Gemini API key is configured."""
        return bool(self.api_key and self.api_key.strip())

    def generate_matrix(self, user_input: Union[UserProfile, str, Dict[str, Any]]) -> NutritionalMatrixProfile:
        """
        Generates a complete NutritionalMatrixProfile from a UserProfile, dictionary, or natural language bio text.
        If Gemini API is unavailable or fails, falls back to a deterministic scientific calculator.
        """
        if isinstance(user_input, str):
            profile = UserProfile(raw_bio_text=user_input)
        elif isinstance(user_input, dict):
            profile = UserProfile(**user_input)
        elif isinstance(user_input, UserProfile):
            profile = user_input
        else:
            raise TypeError(f"Unsupported user_input type: {type(user_input)}")

        if self.is_available():
            try:
                return self._generate_ai_matrix(profile)
            except Exception as e:
                print(f"[AINutritionProfiler] Gemini AI call failed ({e}), falling back to deterministic baseline calculator.")
                return self._compute_deterministic_baseline(profile)
        else:
            return self._compute_deterministic_baseline(profile)

    def _generate_ai_matrix(self, profile: UserProfile) -> NutritionalMatrixProfile:
        """Calls Gemini Flash with structured JSON schema to generate deep nutritional matrix."""
        prompt = f"""
You are a world-class clinical dietitian, sports nutritionist, and metabolic health specialist.
Analyze this user's profile and generate a rigorous, evidence-based personalized Nutritional & Health Matrix.

USER PROFILE:
- Age: {profile.age or "Unspecified"}
- Biological Gender: {profile.gender or "Unspecified"}
- Height: {f'{profile.height_cm} cm' if profile.height_cm else "Unspecified"}
- Weight: {f'{profile.weight_kg} kg' if profile.weight_kg else "Unspecified"}
- Activity Level: {profile.activity_level or "sedentary"}
- Primary Goal: {profile.primary_goal or "maintenance"}
- Known Health / Medical Conditions: {', '.join(profile.health_conditions) if profile.health_conditions else "None declared"}
- Allergies: {', '.join(profile.allergies) if profile.allergies else "None declared"}
- Dietary Preferences / Restrictions: {', '.join(profile.dietary_preferences) if profile.dietary_preferences else "Omnivore / None"}
- Free-form Lifestyle / Habit Notes: {profile.raw_bio_text or "None"}

INSTRUCTIONS:
1. Infer exact metabolic targets:
   - Calculate scientific BMR and TDEE (using Mifflin-St Jeor / WHO standards).
   - Determine target caloric intake and safe deficit/surplus percentage for their primary goal.
   - Prescribe a tailored Macronutrient split (Protein, Carbs, Fats in grams and percentages) with medical rationale.
2. Formulate Clinical Biomarker Guardrails:
   - Glycemic Sensitivity Index (0.00 to 1.00: where 1.00 = strict low-GI required due to diabetes/insulin resistance).
   - Sodium limit (mg/day, e.g. 1500mg for hypertension vs 2300mg standard).
   - Saturated Fat maximum percentage of total calories (e.g. 0.06 for high cholesterol/CVD risk vs 0.10 standard).
   - Minimum soluble/insoluble dietary fiber target (g/day).
   - Digestive triggers to avoid (e.g. acidic foods, deep fried, lactose, high-FODMAP).
   - Bioactive & micronutrient priorities (e.g. potassium, magnesium, omega-3, iron).
3. Score Major Food Groups (-10 to +10):
   - +10 = Essential/Highest Priority
   - +5 to +9 = Highly Recommended
   - 0 to +4 = Neutral / Moderate
   - -1 to -7 = Restrict / Avoid
   - -8 to -10 = Strictly Forbidden (Allergens, Strict Ethical Diets, or Acute Medical Contraindications)
   - Include major categories: Cruciferous & Leafy Vegetables, Lean Plant Proteins, Fatty Fish & Marine Omega-3, Lean Poultry, Whole Grains & Millets, Refined Carbohydrates, Deep-Fried & Trans Fats, High-Sugar Desserts, Fermented Probiotic Foods, Nuts & Seeds, Dairy/Alternatives.
   - For every food group, give a concrete serving recommendation and the exact clinical rationale for this user.

Return ONLY valid JSON matching this exact structure:
{{
  "user_summary": "1-2 sentence clinical summary of this user's nutritional profile and primary metabolic strategy",
  "metabolic_matrix": {{
    "bmr_kcal": 1650.0,
    "tdee_kcal": 2200.0,
    "target_calories_kcal": 1850.0,
    "caloric_adjustment_pct": -15.9,
    "metabolic_tier": "Insulin-Optimized Moderate Deficit",
    "macro_split": {{
      "protein_g": 140.0,
      "protein_pct": 30.0,
      "carbs_g": 160.0,
      "carbs_pct": 35.0,
      "fats_g": 72.0,
      "fats_pct": 35.0,
      "rationale": "High protein preserves lean mass in deficit; moderate low-GI carbs stabilize blood glucose."
    }}
  }},
  "clinical_guardrails": {{
    "glycemic_sensitivity_index": 0.85,
    "sodium_limit_mg": 1500,
    "saturated_fat_max_pct": 0.06,
    "fiber_minimum_g": 35.0,
    "digestive_triggers_to_avoid": ["Deep fried oil", "Excess spicy acids"],
    "bioactive_priorities": ["Potassium", "Soluble Beta-Glucan Fiber", "Omega-3"],
    "clinical_notes": "Prioritize high-potassium greens and soluble fiber to support endothelial health and blood sugar clearance."
  }},
  "food_group_affinities": [
    {{
      "food_group": "Cruciferous & Dark Leafy Greens",
      "score": 10,
      "status": "Essential",
      "daily_servings_guide": "3-5 servings/day",
      "key_benefits_or_risks": "Potassium-rich, virtually zero glycemic load, high micronutrient density.",
      "examples": ["Spinach", "Broccoli", "Kale", "Methi", "Bok Choy"]
    }},
    {{
      "food_group": "Refined Carbohydrates & Sugary Items",
      "score": -9,
      "status": "Strictly Avoid",
      "daily_servings_guide": "0 servings / strictly eliminate",
      "key_benefits_or_risks": "Triggers rapid insulin spikes and exacerbates metabolic dysfunction.",
      "examples": ["White bread", "Maida", "Sugary syrups", "Soda"]
    }}
  ],
  "excluded_allergens_and_restrictions": ["Peanuts", "Non-Vegetarian"],
  "top_recommended_food_groups": ["Cruciferous & Dark Leafy Greens", "Legumes & Plant Proteins", "Whole Grains (Millets/Oats)"],
  "food_groups_to_limit": ["Refined Carbohydrates", "Deep-Fried Foods", "High-Sodium Sauces"]
}}
"""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2
            }
        }

        headers = {"Content-Type": "application/json"}
        models_to_try = [self.model_name] if self.model_name else self.CANDIDATE_MODELS
        
        last_error = None
        response_json = None

        for model in models_to_try:
            if not model:
                continue
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=25)
                if resp.status_code == 200:
                    result = resp.json()
                    candidates = result.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {}).get("parts", [])
                        if content and "text" in content[0]:
                            response_json = json.loads(content[0]["text"])
                            break
                elif resp.status_code == 404:
                    last_error = f"Model '{model}' not found on endpoint."
                    continue
                else:
                    last_error = f"API Error {resp.status_code}: {resp.text}"
            except Exception as e:
                last_error = str(e)
                continue

        if response_json is None:
            raise RuntimeError(f"Gemini AI matrix generation failed: {last_error}")

        return self._parse_matrix_json(response_json, model_name=model)

    def _parse_matrix_json(self, data: Dict[str, Any], model_name: str = "Gemini-Flash") -> NutritionalMatrixProfile:
        """Converts raw JSON dictionary into strongly-typed NutritionalMatrixProfile."""
        meta = data.get("metabolic_matrix", {})
        macro = meta.get("macro_split", {})
        macro_obj = MacroSplit(
            protein_g=float(macro.get("protein_g", 120.0)),
            protein_pct=float(macro.get("protein_pct", 25.0)),
            carbs_g=float(macro.get("carbs_g", 200.0)),
            carbs_pct=float(macro.get("carbs_pct", 45.0)),
            fats_g=float(macro.get("fats_g", 65.0)),
            fats_pct=float(macro.get("fats_pct", 30.0)),
            rationale=macro.get("rationale", "")
        )

        metabolic_obj = MetabolicEnergyMatrix(
            bmr_kcal=float(meta.get("bmr_kcal", 1600.0)),
            tdee_kcal=float(meta.get("tdee_kcal", 2100.0)),
            target_calories_kcal=float(meta.get("target_calories_kcal", 1800.0)),
            caloric_adjustment_pct=float(meta.get("caloric_adjustment_pct", -14.0)),
            macro_split=macro_obj,
            metabolic_tier=meta.get("metabolic_tier", "Standard")
        )

        cg = data.get("clinical_guardrails", {})
        guardrails_obj = ClinicalGuardrailMatrix(
            glycemic_sensitivity_index=float(cg.get("glycemic_sensitivity_index", 0.5)),
            sodium_limit_mg=int(cg.get("sodium_limit_mg", 2300)),
            saturated_fat_max_pct=float(cg.get("saturated_fat_max_pct", 0.08)),
            fiber_minimum_g=float(cg.get("fiber_minimum_g", 30.0)),
            digestive_triggers_to_avoid=cg.get("digestive_triggers_to_avoid", []),
            bioactive_priorities=cg.get("bioactive_priorities", []),
            clinical_notes=cg.get("clinical_notes", "")
        )

        affinities: List[FoodGroupAffinity] = []
        for fg_data in data.get("food_group_affinities", []):
            affinities.append(
                FoodGroupAffinity(
                    food_group=fg_data.get("food_group", "General"),
                    score=int(fg_data.get("score", 0)),
                    status=fg_data.get("status", "Moderate"),
                    daily_servings_guide=fg_data.get("daily_servings_guide", "1-2 servings"),
                    key_benefits_or_risks=fg_data.get("key_benefits_or_risks", ""),
                    examples=fg_data.get("examples", [])
                )
            )

        # Sort affinities by score descending
        affinities.sort(key=lambda x: x.score, reverse=True)

        return NutritionalMatrixProfile(
            user_summary=data.get("user_summary", "Personalized nutrition profile"),
            metabolic_matrix=metabolic_obj,
            clinical_guardrails=guardrails_obj,
            food_group_affinities=affinities,
            excluded_allergens_and_restrictions=data.get("excluded_allergens_and_restrictions", []),
            top_recommended_food_groups=data.get("top_recommended_food_groups", [fg.food_group for fg in affinities if fg.score >= 6]),
            food_groups_to_limit=data.get("food_groups_to_limit", [fg.food_group for fg in affinities if fg.score <= -4]),
            metadata={"engine": "Google-Gemini", "model": model_name}
        )

    def _compute_deterministic_baseline(self, profile: UserProfile) -> NutritionalMatrixProfile:
        """
        Scientific fallback: Computes Mifflin-St Jeor equations and rule-based
        clinical guardrails when offline or if AI is unconfigured.
        """
        # Default biometrics if missing
        weight = profile.weight_kg or 70.0
        height = profile.height_cm or 170.0
        age = profile.age or 30
        gender = (profile.gender or "male").lower()

        # 1. Mifflin-St Jeor BMR
        s = 5 if gender == "male" else -161
        bmr = (10.0 * weight) + (6.25 * height) - (5.0 * age) + s

        # 2. Activity Multiplier
        act_map = {
            "sedentary": 1.2,
            "light": 1.375,
            "moderate": 1.55,
            "heavy": 1.725,
            "athlete": 1.9
        }
        pal = act_map.get((profile.activity_level or "sedentary").lower(), 1.2)
        tdee = bmr * pal

        # 3. Caloric target by goal
        goal = (profile.primary_goal or "maintenance").lower()
        if "fat_loss" in goal or "weight_loss" in goal or "deficit" in goal:
            adj_pct = -20.0
        elif "muscle" in goal or "hypertrophy" in goal or "surplus" in goal:
            adj_pct = +10.0
        else:
            adj_pct = 0.0
        
        target_calories = tdee * (1.0 + adj_pct / 100.0)

        # 4. Macros
        # Protein: 1.8g/kg for deficit/muscle, 1.2g/kg maintenance
        protein_per_kg = 1.8 if adj_pct != 0 else 1.2
        protein_g = weight * protein_per_kg
        protein_kcal = protein_g * 4.0
        protein_pct = min(40.0, (protein_kcal / target_calories) * 100.0)

        # Fat: 25% of calories
        fat_pct = 25.0
        fat_kcal = target_calories * (fat_pct / 100.0)
        fat_g = fat_kcal / 9.0

        # Carbs: Remaining
        carbs_kcal = target_calories - protein_kcal - fat_kcal
        carbs_g = max(50.0, carbs_kcal / 4.0)
        carbs_pct = (carbs_kcal / target_calories) * 100.0

        macro_obj = MacroSplit(
            protein_g=round(protein_g, 1),
            protein_pct=round(protein_pct, 1),
            carbs_g=round(carbs_g, 1),
            carbs_pct=round(carbs_pct, 1),
            fats_g=round(fat_g, 1),
            fats_pct=round(fat_pct, 1),
            rationale="Scientific baseline calculated via Mifflin-St Jeor equation and body-weight protein targets."
        )

        metabolic_obj = MetabolicEnergyMatrix(
            bmr_kcal=round(bmr, 1),
            tdee_kcal=round(tdee, 1),
            target_calories_kcal=round(target_calories, 1),
            caloric_adjustment_pct=adj_pct,
            macro_split=macro_obj,
            metabolic_tier="Deterministic Clinical Baseline"
        )

        # Health conditions checking
        conds = [c.lower() for c in profile.health_conditions]
        diets = [d.lower() for d in profile.dietary_preferences]
        allergies = [a.lower() for a in profile.allergies]

        glycemic_idx = 0.85 if any(c in conds for c in ["diabetes", "type_2_diabetes", "pcos", "insulin_resistance"]) else 0.4
        sodium_limit = 1500 if any(c in conds for c in ["hypertension", "high_bp", "heart_disease"]) else 2300
        sat_fat_pct = 0.06 if any(c in conds for c in ["cholesterol", "hyperlipidemia", "heart_disease"]) else 0.09
        fiber_min = 35.0 if glycemic_idx > 0.6 else 28.0

        guardrails_obj = ClinicalGuardrailMatrix(
            glycemic_sensitivity_index=glycemic_idx,
            sodium_limit_mg=sodium_limit,
            saturated_fat_max_pct=sat_fat_pct,
            fiber_minimum_g=fiber_min,
            digestive_triggers_to_avoid=["Deep fried oils", "Ultra-processed sugars"],
            bioactive_priorities=["Soluble Fiber", "Potassium", "Antioxidants"],
            clinical_notes="Baseline physiological parameters tailored to cardiovascular and glycemic health."
        )

        # Food group affinities
        affinities = [
            FoodGroupAffinity("Cruciferous & Leafy Vegetables", 10, "Essential", "3-5 servings/day", "High micronutrient density, low calorie, excellent fiber.", ["Spinach", "Broccoli", "Kale"]),
            FoodGroupAffinity("Legumes, Pulses & Plant Proteins", 8, "Recommended", "2-3 servings/day", "High fiber, lean protein, supports glycemic stability.", ["Lentils", "Chickpeas", "Tofu"]),
            FoodGroupAffinity("Whole Grains & Ancient Millets", 7, "Recommended", "2-3 servings/day", "Complex sustained carbohydrates and minerals.", ["Oats", "Quinoa", "Brown Rice", "Ragi"]),
            FoodGroupAffinity("Nuts, Seeds & Healthy Unsaturated Oils", 6, "Moderate", "1-2 servings/day", "Essential fatty acids and vitamin E.", ["Almonds", "Walnuts", "Chia seeds", "Olive oil"]),
            FoodGroupAffinity("Low-GI Fresh Fruits", 6, "Moderate", "1-2 servings/day", "Polyphenols, hydration, natural vitamins.", ["Berries", "Apples", "Pears"]),
            FoodGroupAffinity("Refined Grains & Added Sugars", -8, "Limit Strongly", "0-1 servings/day", "Elevates blood sugar spikes and caloric density without satiety.", ["White flour", "Pastries", "Sodas"]),
            FoodGroupAffinity("Deep-Fried & Trans Fat Foods", -9, "Strictly Avoid", "Zero / Eliminate", "Cardiovascular strain and inflammatory lipid oxidation.", ["Deep fried snacks", "Shortening", "Commercial fast food"]),
        ]

        # Filter ethical diets (e.g. Vegetarian/Vegan)
        if any("veg" in d for d in diets):
            affinities.append(FoodGroupAffinity("Poultry, Seafood & Red Meat", -10, "Strictly Avoid", "Zero (Dietary Restriction)", "Excluded by vegetarian/vegan preference.", ["Chicken", "Fish", "Beef", "Pork"]))
        else:
            affinities.append(FoodGroupAffinity("Lean Poultry & Wild Seafood", 8, "Recommended", "1-2 servings/day", "High bioavailability protein and omega-3s.", ["Grilled Chicken Breast", "Salmon", "Tuna"]))

        affinities.sort(key=lambda x: x.score, reverse=True)

        return NutritionalMatrixProfile(
            user_summary=f"Metabolic profile for {age}yo {gender}, goal: {profile.primary_goal or 'maintenance'}.",
            metabolic_matrix=metabolic_obj,
            clinical_guardrails=guardrails_obj,
            food_group_affinities=affinities,
            excluded_allergens_and_restrictions=profile.allergies + profile.dietary_preferences,
            top_recommended_food_groups=[fg.food_group for fg in affinities if fg.score >= 7],
            food_groups_to_limit=[fg.food_group for fg in affinities if fg.score <= -5],
            metadata={"engine": "Deterministic-Baseline-Calculator"}
        )
