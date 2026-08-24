"""
Dish & Menu Item Evaluator.
Evaluates recognized menu items against a user's personalized Nutritional Matrix Profile,
scoring their personal health fit (0-100), tagging constituent food groups,
and highlighting green flags / medical warnings.
"""

from typing import List, Dict, Any, Optional, Union
import json
import os
from pathlib import Path
import requests

from .models import MenuItem, RecognizedMenu
from .user_models import NutritionalMatrixProfile, DishEvaluationResult


class MenuDishEvaluator:
    """Evaluates menu dishes against a user's NutritionalMatrixProfile using AI or heuristic scoring."""

    CANDIDATE_MODELS = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-3.7-flash",
    ]

    def __init__(self, user_matrix: NutritionalMatrixProfile, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.user_matrix = user_matrix
        self.api_key = api_key or self._load_api_key()
        self.model_name = model_name or "gemini-3.6-flash"

    def _load_api_key(self) -> Optional[str]:
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
        return bool(self.api_key and self.api_key.strip())

    def evaluate_dish(self, dish: Union[MenuItem, str]) -> DishEvaluationResult:
        """Evaluates a single dish or MenuItem object."""
        dish_name = dish.name if isinstance(dish, MenuItem) else str(dish)
        dish_desc = dish.description if isinstance(dish, MenuItem) else ""
        dietary_tags = dish.dietary_tags if isinstance(dish, MenuItem) else []

        if self.is_available():
            try:
                results = self._evaluate_batch_ai([{"name": dish_name, "description": dish_desc, "tags": dietary_tags}])
                if results:
                    return results[0]
            except Exception as e:
                print(f"[MenuDishEvaluator] AI evaluation error ({e}), falling back to heuristic.")

        return self._evaluate_dish_heuristic(dish_name, dish_desc, dietary_tags)

    def evaluate_menu(self, menu_input: Union[RecognizedMenu, List[Union[MenuItem, str]]]) -> List[DishEvaluationResult]:
        """
        Evaluates an entire recognized menu or list of dishes, returning results ranked by fit_score descending.
        """
        dishes: List[Dict[str, Any]] = []
        if isinstance(menu_input, RecognizedMenu):
            for item in menu_input.get_all_items():
                dishes.append({
                    "name": item.name,
                    "description": item.description or "",
                    "tags": item.dietary_tags or []
                })
        elif isinstance(menu_input, list):
            for item in menu_input:
                if isinstance(item, MenuItem):
                    dishes.append({
                        "name": item.name,
                        "description": item.description or "",
                        "tags": item.dietary_tags or []
                    })
                else:
                    dishes.append({"name": str(item), "description": "", "tags": []})

        if not dishes:
            return []

        if self.is_available():
            try:
                evaluations = self._evaluate_batch_ai(dishes)
            except Exception as e:
                print(f"[MenuDishEvaluator] Batch AI failed ({e}), using heuristic.")
                evaluations = [self._evaluate_dish_heuristic(d["name"], d["description"], d["tags"]) for d in dishes]
        else:
            evaluations = [self._evaluate_dish_heuristic(d["name"], d["description"], d["tags"]) for d in dishes]

        # Sort ranked by fit score descending
        evaluations.sort(key=lambda x: x.fit_score, reverse=True)
        return evaluations

    def _evaluate_batch_ai(self, dishes: List[Dict[str, Any]]) -> List[DishEvaluationResult]:
        """Batch evaluates dishes with Gemini structured JSON."""
        prompt = f"""
You are a clinical culinary nutritionist. Evaluate these restaurant menu dishes specifically for the given user profile.

USER NUTRITION PROFILE & MATRIX:
- User Summary: {self.user_matrix.user_summary}
- Target Calories: {self.user_matrix.metabolic_matrix.target_calories_kcal:.0f} kcal
- Macro Targets: Protein: {self.user_matrix.metabolic_matrix.macro_split.protein_pct}%, Carbs: {self.user_matrix.metabolic_matrix.macro_split.carbs_pct}%, Fats: {self.user_matrix.metabolic_matrix.macro_split.fats_pct}%
- Glycemic Sensitivity: {self.user_matrix.clinical_guardrails.glycemic_sensitivity_index}
- Sodium Limit: {self.user_matrix.clinical_guardrails.sodium_limit_mg} mg/day
- Excluded Allergens / Diets: {', '.join(self.user_matrix.excluded_allergens_and_restrictions)}
- Top Priority Food Groups: {', '.join(self.user_matrix.top_recommended_food_groups)}
- Food Groups to Avoid: {', '.join(self.user_matrix.food_groups_to_limit)}

DISHES TO EVALUATE:
{json.dumps(dishes, indent=2)}

CRITICAL EVALUATION RULES:
1. Assign a personal 'fit_score' (0 to 100).
   - 90-100: Exceptional alignment with health matrix & food groups.
   - 75-89: Good healthy choice.
   - 50-74: Moderate / contains high refined carbs, sodium, or saturated fat.
   - 20-49: Poor choice / conflicts with user's metabolic goals.
   - 0: Contains user's strict allergens or violates religious/ethical restrictions (e.g. meat for vegetarian).
2. Assign a 'verdict':
   - 'Top Recommendation', 'Healthy Choice', 'Moderate / Consume with Care', 'Not Recommended', 'Violates Diet/Allergy'
3. Identify 'matched_food_groups' found in each dish.
4. List concrete 'green_flags' (health benefits) and 'red_flags' (nutritional risks).
5. Give 'customization_tips' (e.g. "Request dressing on side, substitute white rice for salad or roti").

Return ONLY valid JSON array with this structure:
[
  {{
    "dish_name": "Paneer Tikka",
    "fit_score": 88,
    "verdict": "Healthy Choice",
    "matched_food_groups": ["Dairy & Probiotics", "Grilled Vegetables", "Spices"],
    "green_flags": ["High protein", "Tandoori grilled (minimal oil)", "Low glycemic"],
    "red_flags": ["Moderate saturated fat from paneer"],
    "estimated_calories": 320,
    "estimated_protein_g": 18,
    "customization_tips": "Pair with a fresh green salad or mint chutney without sugar."
  }}
]
"""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1
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
                resp = requests.post(url, json=payload, headers=headers, timeout=30)
                if resp.status_code == 200:
                    result = resp.json()
                    candidates = result.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {}).get("parts", [])
                        if content and "text" in content[0]:
                            response_json = json.loads(content[0]["text"])
                            break
                elif resp.status_code == 404:
                    last_error = f"Model '{model}' not found."
                    continue
                else:
                    last_error = f"API Error {resp.status_code}: {resp.text}"
            except Exception as e:
                last_error = str(e)
                continue

        if response_json is None:
            raise RuntimeError(f"Gemini dish evaluation failed: {last_error}")

        if isinstance(response_json, dict) and "dishes" in response_json:
            response_json = response_json["dishes"]

        results: List[DishEvaluationResult] = []
        for d in response_json:
            results.append(
                DishEvaluationResult(
                    dish_name=d.get("dish_name", "Unknown Dish"),
                    fit_score=int(d.get("fit_score", 50)),
                    verdict=d.get("verdict", "Moderate"),
                    matched_food_groups=d.get("matched_food_groups", []),
                    green_flags=d.get("green_flags", []),
                    red_flags=d.get("red_flags", []),
                    estimated_calories=d.get("estimated_calories"),
                    estimated_protein_g=d.get("estimated_protein_g"),
                    customization_tips=d.get("customization_tips")
                )
            )
        return results

    def _evaluate_dish_heuristic(self, dish_name: str, description: str, dietary_tags: List[str]) -> DishEvaluationResult:
        """Heuristic fallback for offline evaluation."""
        text = f"{dish_name} {description}".lower()
        score = 70
        greens: List[str] = []
        reds: List[str] = []
        matched_groups: List[str] = []

        # Check allergens & strict diets
        exclusions = [ex.lower() for ex in self.user_matrix.excluded_allergens_and_restrictions]
        if any("veg" in ex for ex in exclusions):
            non_veg_keywords = ["chicken", "mutton", "beef", "pork", "fish", "prawn", "meat", "bacon", "lamb", "egg"]
            if any(k in text for k in non_veg_keywords):
                return DishEvaluationResult(
                    dish_name=dish_name,
                    fit_score=0,
                    verdict="Violates Diet/Allergy",
                    matched_food_groups=["Animal Meat"],
                    green_flags=[],
                    red_flags=["Contains meat/poultry, violating vegetarian preference."],
                    customization_tips="Choose a vegetarian alternative like Dal or Paneer."
                )

        for allergy in self.user_matrix.clinical_guardrails.digestive_triggers_to_avoid:
            if allergy.lower() in text:
                score -= 30
                reds.append(f"Contains sensitivity trigger: {allergy}")

        # Positive keywords
        if any(w in text for w in ["salad", "spinach", "broccoli", "greens", "cucumber", "methi", "saag", "vegetable"]):
            score += 15
            greens.append("High vegetable and fiber content")
            matched_groups.append("Leafy & Cruciferous Greens")

        if any(w in text for w in ["grilled", "tandoori", "steamed", "boiled", "baked"]):
            score += 10
            greens.append("Healthy cooking preparation (grilled/steamed)")

        if any(w in text for w in ["dal", "lentil", "chana", "tofu", "beans", "chickpea", "paneer"]):
            score += 10
            greens.append("Good source of protein & soluble fiber")
            matched_groups.append("Plant Protein & Legumes")

        # Negative keywords
        if any(w in text for w in ["fried", "crispy", "fry", "pakora", "samosa", "poori", "bhatura"]):
            score -= 25
            reds.append("Deep fried; high in saturated & oxidized fats")
            matched_groups.append("Deep Fried Foods")

        if any(w in text for w in ["butter", "cream", "creamy", "cheesy", "mayo"]):
            score -= 15
            reds.append("High saturated fat and calorie density")

        if any(w in text for w in ["naan", "kulcha", "white bread", "maida", "syrup", "halwa", "jamun", "sweet"]):
            score -= 15
            reds.append("Refined carbohydrates with high glycemic index")
            matched_groups.append("Refined Carbohydrates")

        score = max(0, min(100, score))
        if score >= 85:
            verdict = "Top Recommendation"
        elif score >= 70:
            verdict = "Healthy Choice"
        elif score >= 50:
            verdict = "Moderate / Consume with Care"
        else:
            verdict = "Not Recommended"

        return DishEvaluationResult(
            dish_name=dish_name,
            fit_score=score,
            verdict=verdict,
            matched_food_groups=matched_groups or ["General Cuisine"],
            green_flags=greens or ["Standard meal option"],
            red_flags=reds,
            customization_tips="Request light oil and pair with steamed vegetables or salad."
        )
