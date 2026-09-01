"""
Plate Optimizer & Multi-Dish Synergy Engine for NutriMenu AI.
Calculates cumulative macronutrients, meal glycemic synergy, daily budget burn-down,
and companion dish suggestions using Gemini 3.7 Flash and deterministic clinical equations.
Strictly adheres to user health matrix, dietary exclusions, and allergen guardrails.
"""

from typing import Dict, Any, List, Optional, Tuple, Union
import json
import logging
import re

from .gemini_client import GeminiClient, GeminiAPIError
from .matrix_generator import UserNutritionalMatrix
from .config import get_gemini_api_key, get_gemini_model_name

logger = logging.getLogger(__name__)

# Base culinary nutrient density reference (per standard serving)
BASE_DISH_NUTRIENTS: Dict[str, Dict[str, float]] = {
    "salad": {"calories": 140, "protein": 4, "carbs": 12, "fat": 8, "sodium": 220, "fiber": 5},
    "broccoli": {"calories": 110, "protein": 5, "carbs": 14, "fat": 3, "sodium": 180, "fiber": 6},
    "soup": {"calories": 160, "protein": 6, "carbs": 18, "fat": 6, "sodium": 580, "fiber": 3},
    "paneer": {"calories": 320, "protein": 18, "carbs": 8, "fat": 24, "sodium": 420, "fiber": 2},
    "tofu": {"calories": 180, "protein": 16, "carbs": 4, "fat": 10, "sodium": 120, "fiber": 3},
    "dal": {"calories": 210, "protein": 12, "carbs": 30, "fat": 5, "sodium": 380, "fiber": 7},
    "lentil": {"calories": 200, "protein": 14, "carbs": 28, "fat": 4, "sodium": 340, "fiber": 8},
    "chickpea": {"calories": 240, "protein": 14, "carbs": 38, "fat": 4, "sodium": 310, "fiber": 9},
    "soya": {"calories": 220, "protein": 24, "carbs": 14, "fat": 6, "sodium": 290, "fiber": 6},
    "chicken": {"calories": 290, "protein": 34, "carbs": 2, "fat": 15, "sodium": 390, "fiber": 0},
    "salmon": {"calories": 340, "protein": 32, "carbs": 0, "fat": 22, "sodium": 310, "fiber": 0},
    "fish": {"calories": 260, "protein": 28, "carbs": 2, "fat": 14, "sodium": 350, "fiber": 0},
    "roti": {"calories": 120, "protein": 4, "carbs": 24, "fat": 1.5, "sodium": 90, "fiber": 3},
    "phulka": {"calories": 110, "protein": 3.5, "carbs": 22, "fat": 1.0, "sodium": 80, "fiber": 3},
    "naan": {"calories": 280, "protein": 8, "carbs": 48, "fat": 6, "sodium": 420, "fiber": 2},
    "rice": {"calories": 220, "protein": 4.5, "carbs": 45, "fat": 1.5, "sodium": 15, "fiber": 1},
    "biryani": {"calories": 490, "protein": 18, "carbs": 58, "fat": 20, "sodium": 680, "fiber": 3},
    "pulao": {"calories": 310, "protein": 7, "carbs": 48, "fat": 10, "sodium": 440, "fiber": 3},
    "dosa": {"calories": 240, "protein": 6, "carbs": 38, "fat": 7, "sodium": 340, "fiber": 2},
    "idli": {"calories": 130, "protein": 4, "carbs": 28, "fat": 0.5, "sodium": 180, "fiber": 2},
    "sambar": {"calories": 140, "protein": 5, "carbs": 20, "fat": 4, "sodium": 460, "fiber": 4},
    "chutney": {"calories": 80, "protein": 1.5, "carbs": 4, "fat": 7, "sodium": 190, "fiber": 1.5},
    "egg": {"calories": 160, "protein": 13, "carbs": 1.5, "fat": 11, "sodium": 210, "fiber": 0},
    "pakora": {"calories": 380, "protein": 7, "carbs": 34, "fat": 24, "sodium": 520, "fiber": 3},
    "samosa": {"calories": 310, "protein": 5, "carbs": 32, "fat": 18, "sodium": 410, "fiber": 2},
    "burger": {"calories": 520, "protein": 22, "carbs": 46, "fat": 28, "sodium": 780, "fiber": 3},
    "sandwich": {"calories": 340, "protein": 14, "carbs": 40, "fat": 14, "sodium": 590, "fiber": 3},
    "fries": {"calories": 360, "protein": 4, "carbs": 48, "fat": 17, "sodium": 460, "fiber": 4},
    "tiramisu": {"calories": 390, "protein": 6, "carbs": 44, "fat": 21, "sodium": 140, "fiber": 1},
    "cake": {"calories": 420, "protein": 5, "carbs": 56, "fat": 20, "sodium": 280, "fiber": 1},
    "tea": {"calories": 45, "protein": 1.5, "carbs": 7, "fat": 1.2, "sodium": 30, "fiber": 0},
    "coffee": {"calories": 55, "protein": 2.0, "carbs": 8, "fat": 1.5, "sodium": 35, "fiber": 0},
}

MEAT_KEYWORDS = [
    "chicken", "mutton", "beef", "pork", "fish", "prawn", "prawns", "seafood", "meat",
    "bacon", "lamb", "duck", "poultry", "turkey", "crab", "lobster", "veal", "ham",
    "prosciutto", "salmon", "tuna", "steak", "calamari", "anchovy", "pepperoni", "salami",
    "keema", "kheema", "gosht", "tikka chicken", "butter chicken"
]


class PlateOptimizer:
    """
    Evaluates multi-dish meal combinations, tracks remaining macronutrient budgets,
    and suggests complementary dishes strictly adhering to user health constraints.
    """

    def __init__(
        self,
        user_matrix: Optional[UserNutritionalMatrix] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.user_matrix = user_matrix
        self.api_key = api_key or get_gemini_api_key()
        self.model_name = model_name or get_gemini_model_name()
        self.gemini_client = GeminiClient(api_key=self.api_key, model_name=self.model_name)

    def _is_dish_allowed(self, dish_name: str, matrix: Optional[UserNutritionalMatrix] = None) -> bool:
        """Checks if a dish violates the user's strict dietary preferences and allergens."""
        mat = matrix or self.user_matrix
        if not mat:
            return True

        exclusions = [str(e).lower().strip() for e in getattr(mat, "exclusion_mask", [])]
        lower = dish_name.lower().strip()

        # Check Vegetarian / Vegan restriction
        is_veg = any(
            ex in ("vegetarian", "vegan", "veg") or ("veg" in ex and ex not in ("non-veg", "non_veg", "non-vegetarian"))
            for ex in exclusions
        )
        if is_veg:
            if any(re.search(r"\b" + re.escape(kw) + r"\b", lower) for kw in MEAT_KEYWORDS):
                return False

        # Check Allergens
        for ex in exclusions:
            if ex in ("peanut", "peanuts") and "peanut" in lower:
                return False
            if ex in ("dairy", "milk", "lactose") and any(k in lower for k in ["milk", "cheese", "paneer", "cream", "butter"]):
                return False
            if ex in ("gluten", "wheat") and any(k in lower for k in ["wheat", "roti", "naan", "bread", "pasta", "flour"]):
                return False
            if ex in ("egg", "eggs") and "egg" in lower:
                return False
            if ex in ("seafood", "fish", "shellfish") and any(k in lower for k in ["fish", "prawn", "crab", "salmon", "tuna"]):
                return False

        return True

    def estimate_dish_nutrients(self, dish_name: str, portion: float = 1.0) -> Dict[str, float]:
        """Calculates approximate nutritional values based on dish name and portion multiplier."""
        clean = dish_name.lower().strip()
        matched: Optional[Dict[str, float]] = None

        for kw, vals in BASE_DISH_NUTRIENTS.items():
            if kw in clean:
                matched = vals
                break

        if not matched:
            matched = {"calories": 260, "protein": 10, "carbs": 30, "fat": 10, "sodium": 350, "fiber": 3}

        multiplier = max(0.25, min(4.0, float(portion)))
        return {
            "calories": round(matched["calories"] * multiplier, 1),
            "protein": round(matched["protein"] * multiplier, 1),
            "carbs": round(matched["carbs"] * multiplier, 1),
            "fat": round(matched["fat"] * multiplier, 1),
            "sodium": round(matched["sodium"] * multiplier, 1),
            "fiber": round(matched["fiber"] * multiplier, 1),
        }

    def evaluate_plate(
        self,
        plate_items: List[Dict[str, Any]],
        user_matrix: Optional[UserNutritionalMatrix] = None,
    ) -> Dict[str, Any]:
        """
        Calculates cumulative plate nutrition, remaining daily budget, and AI meal synergy.
        """
        matrix = user_matrix or self.user_matrix
        mt = matrix.metabolic_targets if matrix and hasattr(matrix, "metabolic_targets") else None
        cg = matrix.clinical_guardrails if matrix and hasattr(matrix, "clinical_guardrails") else (matrix.nutritional_guardrails if matrix and hasattr(matrix, "nutritional_guardrails") else None)

        target_cals = float(getattr(mt, "target_calories_kcal", getattr(mt, "target_calories", 2000.0)) if mt else 2000.0)
        target_protein = float(getattr(mt, "target_protein_g", getattr(mt, "protein_g", 120.0)) if mt else 120.0)
        target_carbs = float(getattr(mt, "target_carbs_g", getattr(mt, "carb_g", 225.0)) if mt else 225.0)
        target_fat = float(getattr(mt, "target_fats_g", getattr(mt, "fat_g", 65.0)) if mt else 65.0)
        sodium_ceiling = float(getattr(cg, "sodium_ceiling_mg", getattr(cg, "sodium_mg_ceiling", 2000.0)) if cg else 2000.0)

        # Sum item nutrients
        total_cals = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
        total_sodium = 0.0
        total_fiber = 0.0

        items_breakdown = []
        for item in plate_items:
            name = item.get("name") or str(item)
            portion = float(item.get("portion", 1.0))
            nutrients = self.estimate_dish_nutrients(name, portion)
            total_cals += nutrients["calories"]
            total_protein += nutrients["protein"]
            total_carbs += nutrients["carbs"]
            total_fat += nutrients["fat"]
            total_sodium += nutrients["sodium"]
            total_fiber += nutrients["fiber"]

            items_breakdown.append({
                "name": name,
                "portion": portion,
                "nutrients": nutrients,
            })

        # Calculate remaining budgets
        rem_cals = max(0.0, target_cals - total_cals)
        rem_protein = max(0.0, target_protein - total_protein)
        rem_carbs = max(0.0, target_carbs - total_carbs)
        rem_fat = max(0.0, target_fat - total_fat)
        rem_sodium = max(0.0, sodium_ceiling - total_sodium)

        # Base meal synergy calculations
        has_protein = total_protein >= 20.0
        has_fiber = total_fiber >= 4.0

        synergy_score = 75
        synergy_notes = []

        if has_protein and has_fiber:
            synergy_score += 15
            synergy_notes.append("High satiety synergy: protein and fiber combination stabilizes post-meal glucose.")
        elif has_protein:
            synergy_score += 8
            synergy_notes.append("Good protein density supports muscle retention and satiety.")
        elif has_fiber:
            synergy_score += 6
            synergy_notes.append("Adequate fiber slows gastric emptying and moderates glycemic load.")
        else:
            synergy_score -= 12
            synergy_notes.append("Low in fiber and protein; consider adding a leafy salad or legume starter.")

        if total_sodium > (sodium_ceiling * 0.45):
            synergy_score -= 10
            synergy_notes.append(f"Sodium alert: This meal consumes {(total_sodium/sodium_ceiling)*100:.0f}% of your daily ceiling.")

        synergy_score = max(20, min(99, synergy_score))

        return {
            "total_nutrients": {
                "calories": round(total_cals, 1),
                "protein": round(total_protein, 1),
                "carbs": round(total_carbs, 1),
                "fat": round(total_fat, 1),
                "sodium": round(total_sodium, 1),
                "fiber": round(total_fiber, 1),
            },
            "daily_targets": {
                "calories": round(target_cals, 1),
                "protein": round(target_protein, 1),
                "carbs": round(target_carbs, 1),
                "fat": round(target_fat, 1),
                "sodium_ceiling": round(sodium_ceiling, 1),
            },
            "remaining_budget": {
                "calories": round(rem_cals, 1),
                "protein": round(rem_protein, 1),
                "carbs": round(rem_carbs, 1),
                "fat": round(rem_fat, 1),
                "sodium": round(rem_sodium, 1),
            },
            "budget_percentages": {
                "calories": min(100, round((total_cals / target_cals) * 100, 1)) if target_cals > 0 else 0,
                "protein": min(100, round((total_protein / target_protein) * 100, 1)) if target_protein > 0 else 0,
                "carbs": min(100, round((total_carbs / target_carbs) * 100, 1)) if target_carbs > 0 else 0,
                "fat": min(100, round((total_fat / target_fat) * 100, 1)) if target_fat > 0 else 0,
                "sodium": min(100, round((total_sodium / sodium_ceiling) * 100, 1)) if sodium_ceiling > 0 else 0,
            },
            "synergy_score": synergy_score,
            "synergy_notes": synergy_notes,
            "items": items_breakdown,
        }

    def suggest_plate_companions(
        self,
        plate_items: List[Dict[str, Any]],
        candidate_menu: List[str],
        user_matrix: Optional[UserNutritionalMatrix] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scans remaining menu items and suggests 1-2 complementary companion dishes
        to fill nutritional gaps in the current plate, strictly enforcing dietary and allergen exclusions.
        """
        matrix = user_matrix or self.user_matrix
        plate_names = [item.get("name") if isinstance(item, dict) else str(item) for item in plate_items]
        
        # 1. Filter out dishes already on the plate
        raw_candidates = [d for d in candidate_menu if d.lower() not in [p.lower() for p in plate_names]]

        # 2. Strict Safety Filter: Remove any dish conflicting with user's matrix (vegetarian, vegan, allergies)
        safe_candidates = [d for d in raw_candidates if self._is_dish_allowed(d, matrix)]

        if not safe_candidates:
            return []

        # 3. If Gemini is available, use intelligent AI gap filling with strict clinical safety instructions
        if self.gemini_client.is_available() and len(safe_candidates) >= 1:
            try:
                suggestions = self._suggest_companions_with_gemini(plate_names, safe_candidates[:25], matrix)
                # Double-check safety on AI response
                safe_suggestions = [s for s in suggestions if self._is_dish_allowed(s.get("dish_name", ""), matrix)]
                if safe_suggestions:
                    return safe_suggestions
            except Exception as e:
                logger.warning("Gemini companion suggestion fallback: %s", e)

        # 4. Deterministic companion selection fallback (strictly safe)
        return self._suggest_companions_deterministic(plate_names, safe_candidates, matrix)

    def _suggest_companions_with_gemini(
        self,
        plate_items: List[str],
        candidate_dishes: List[str],
        matrix: Optional[UserNutritionalMatrix] = None,
    ) -> List[Dict[str, Any]]:
        """Invokes Gemini 3.7 Flash to pick complementary dishes from the menu."""
        user_context = matrix.user_summary if matrix else "General Adult"
        exclusions = getattr(matrix, "exclusion_mask", []) if matrix else []
        exclusions_str = ", ".join(exclusions) if exclusions else "None"

        prompt = f"""
You are an expert Clinical Dietitian optimizing a restaurant meal combination.
The user has selected the following dish(es) on their plate:
{', '.join(plate_items)}

User Clinical Context:
{user_context}

STRICT EXCLUSIONS & ALLERGIES:
{exclusions_str}

Available Remaining Menu Options (PRE-FILTERED):
{json.dumps(candidate_dishes)}

CRITICAL SAFETY RULES:
1. NEVER recommend any meat, poultry, or fish dish if the user is VEGETARIAN or VEGAN.
2. NEVER recommend any dish containing the user's declared allergens.
3. Select 1 to 2 best companion dishes from the available options that balance this meal (e.g. adding missing fiber, plant protein, or micronutrients).

Return ONLY valid JSON:
[
  {{
    "dish_name": "Exact Name from available options",
    "why_recommended": "Brief explanation of how this dish balances the current plate (e.g. 'Adds 6g of soluble fiber to blunt carb absorption').",
    "synergy_benefit": "+12% Fiber Balance"
  }}
]
"""
        resp = self.gemini_client.generate_json(prompt, temperature=0.1)
        if isinstance(resp, list):
            return resp
        if isinstance(resp, dict) and "suggestions" in resp:
            return resp["suggestions"]
        return []

    def _suggest_companions_deterministic(
        self,
        plate_items: List[str],
        candidates: List[str],
        matrix: Optional[UserNutritionalMatrix] = None,
    ) -> List[Dict[str, Any]]:
        """Fallback deterministic heuristic companion picker strictly respecting exclusions."""
        suggestions = []
        plate_text = " ".join(plate_items).lower()

        exclusions = [str(e).lower().strip() for e in getattr(matrix, "exclusion_mask", [])] if matrix else []
        is_veg = any(ex in ("vegetarian", "vegan", "veg") for ex in exclusions)

        needs_greens = not any(k in plate_text for k in ["salad", "broccoli", "spinach", "cucumber", "soup"])
        needs_protein = not any(k in plate_text for k in ["paneer", "dal", "lentil", "tofu", "chickpea", "soya"] + ([] if is_veg else ["chicken", "fish", "egg"]))

        allowed_protein_kws = ["paneer", "dal", "lentil", "tofu", "chickpea", "soya", "sprouts", "besan"] if is_veg else ["paneer", "dal", "lentil", "chicken", "fish", "egg"]

        for cand in candidates:
            c_lower = cand.lower()
            if not self._is_dish_allowed(cand, matrix):
                continue

            if needs_greens and any(k in c_lower for k in ["salad", "broccoli", "soup", "cucumber", "green", "subzi", "spinach"]):
                suggestions.append({
                    "dish_name": cand,
                    "why_recommended": "Adds essential dietary fiber and antioxidants to stabilize meal glycemic index.",
                    "synergy_benefit": "+8g Dietary Fiber",
                })
                needs_greens = False
                if len(suggestions) >= 2:
                    break

            if needs_protein and any(k in c_lower for k in allowed_protein_kws):
                suggestions.append({
                    "dish_name": cand,
                    "why_recommended": "Enhances protein density and satiety without spiking blood sugar.",
                    "synergy_benefit": "+18g Plant Protein" if is_veg else "+18g Lean Protein",
                })
                needs_protein = False
                if len(suggestions) >= 2:
                    break

        # Fallback to first 2 safe candidates if none matched keyword heuristics
        if not suggestions:
            for cand in candidates[:2]:
                if self._is_dish_allowed(cand, matrix):
                    suggestions.append({
                        "dish_name": cand,
                        "why_recommended": "Safe nutritional companion matching your health matrix and dietary preferences.",
                        "synergy_benefit": "Dietary Match",
                    })

        return suggestions
