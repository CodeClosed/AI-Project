"""
3-Tier Food Recommendation Engine (The Middle Model).
Bridges Food & Menu Item Data (Food Groups, Ingredients, Macros) with User Health Matrices
(Biometrics, Metabolic Targets, Clinical Guardrails, Allergens) to classify dishes into
three distinct tiers: 🟢 GOOD, 🟡 MEDIUM, and 🔴 BAD.

Architecture:
1. Hard Safety Exclusions (Allergies & Strict Diets) -> Instant BAD (Fit Score = 0). AI CANNOT override.
2. Clinical & Nutritional Scoring -> Deterministic explainable scoring based on metabolic targets & guardrails.
3. 3-Tier Classification -> Thresholding into GOOD / MEDIUM / BAD.
4. AI Enrichment (Optional) -> Natural language explanations and culinary tips without safety authority.
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import re
import logging
from pathlib import Path

from .config import DEFAULT_GOOD_THRESHOLD, DEFAULT_BAD_THRESHOLD
from .gemini_client import GeminiClient, GeminiAPIError
from .models import MenuItem, RecognizedMenu
from .user_models import NutritionalMatrixProfile, DishEvaluationResult
from .matrix_generator import UserNutritionalMatrix

logger = logging.getLogger(__name__)


class FoodTier(str, Enum):
    """3-Tier Recommendation Classification."""
    GOOD = "GOOD"        # 🟢 Optimal metabolic fit, safe, high health score
    MEDIUM = "MEDIUM"    # 🟡 Acceptable with portion care, neutral, customizable
    BAD = "BAD"          # 🔴 Violates allergies/diets, high clinical risk, ultra-processed


@dataclass
class TieredFoodRecommendation:
    """Individual food/dish recommendation categorized into Good, Medium, or Bad."""
    dish_name: str
    tier: FoodTier
    fit_score: int                               # 0 to 100
    summary_reason: str                          # High-level concise explanation
    matched_food_groups: List[str] = field(default_factory=list)
    green_flags: List[str] = field(default_factory=list)
    red_flags: List[str] = field(default_factory=list)
    allergen_warnings: List[str] = field(default_factory=list)
    customization_tips: Optional[str] = None
    estimated_calories: Optional[int] = None
    estimated_protein_g: Optional[int] = None
    estimated_carbs_g: Optional[int] = None
    estimated_fat_g: Optional[int] = None
    price: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def tier_badge(self) -> str:
        if self.tier == FoodTier.GOOD:
            return "🟢 GOOD"
        elif self.tier == FoodTier.MEDIUM:
            return "🟡 MEDIUM"
        else:
            return "🔴 BAD"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["tier"] = self.tier.value if isinstance(self.tier, FoodTier) else str(self.tier)
        return data


@dataclass
class TieredRecommendationResult:
    """Consolidated 3-Tier recommendation report for a set of dishes or full menu."""
    user_summary: str
    total_items_evaluated: int
    good_items: List[TieredFoodRecommendation] = field(default_factory=list)
    medium_items: List[TieredFoodRecommendation] = field(default_factory=list)
    bad_items: List[TieredFoodRecommendation] = field(default_factory=list)
    all_recommendations: List[TieredFoodRecommendation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def tier_counts(self) -> Dict[str, int]:
        return {
            "GOOD": len(self.good_items),
            "MEDIUM": len(self.medium_items),
            "BAD": len(self.bad_items),
        }

    @property
    def top_pick(self) -> Optional[TieredFoodRecommendation]:
        return self.good_items[0] if self.good_items else (self.medium_items[0] if self.medium_items else None)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_summary": self.user_summary,
            "total_items_evaluated": self.total_items_evaluated,
            "tier_counts": self.tier_counts,
            "good_items": [i.to_dict() for i in self.good_items],
            "medium_items": [i.to_dict() for i in self.medium_items],
            "bad_items": [i.to_dict() for i in self.bad_items],
            "all_recommendations": [i.to_dict() for i in self.all_recommendations],
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Generates a structured 3-Tier Markdown report."""
        counts = self.tier_counts
        lines = [
            "# 🍽️ Personalized 3-Tier Food & Menu Recommendations",
            f"**User Health Context**: {self.user_summary}\n",
            f"**Evaluation Summary**: Evaluated **{self.total_items_evaluated}** items | "
            f"🟢 **{counts['GOOD']} Good** | 🟡 **{counts['MEDIUM']} Medium** | 🔴 **{counts['BAD']} Bad**\n",
            "---",
            "\n## 🟢 Tier 1: GOOD (Recommended & Optimal Fit)",
        ]

        if self.good_items:
            for item in self.good_items:
                lines.append(f"### 🥗 {item.dish_name} (Fit Score: `{item.fit_score}/100`)")
                if item.price:
                    lines.append(f"- **Price**: {item.price}")
                lines.append(f"- **Why it's Good**: {item.summary_reason}")
                if item.matched_food_groups:
                    lines.append(f"- **Food Groups**: {', '.join(item.matched_food_groups)}")
                if item.green_flags:
                    lines.append(f"- **Green Flags**: {'; '.join(item.green_flags)}")
                if item.customization_tips:
                    lines.append(f"- **Customization Tip**: *{item.customization_tips}*")
                lines.append("")
        else:
            lines.append("_No items qualified for Tier 1 based on current thresholds._\n")

        lines.append("## 🟡 Tier 2: MEDIUM (Moderate / Consume with Caution)")
        if self.medium_items:
            for item in self.medium_items:
                lines.append(f"### 🍲 {item.dish_name} (Fit Score: `{item.fit_score}/100`)")
                if item.price:
                    lines.append(f"- **Price**: {item.price}")
                lines.append(f"- **Evaluation**: {item.summary_reason}")
                if item.red_flags:
                    lines.append(f"- **Caution Areas**: {'; '.join(item.red_flags)}")
                if item.customization_tips:
                    lines.append(f"- **How to Make it Better**: *{item.customization_tips}*")
                lines.append("")
        else:
            lines.append("_No items in Tier 2._\n")

        lines.append("## 🔴 Tier 3: BAD (Avoid / High Risk)")
        if self.bad_items:
            for item in self.bad_items:
                lines.append(f"### 🚫 {item.dish_name} (Fit Score: `{item.fit_score}/100`)")
                lines.append(f"- **Why to Avoid**: {item.summary_reason}")
                if item.allergen_warnings:
                    lines.append(f"- **Allergen / Diet Conflict**: ⚠️ **{'; '.join(item.allergen_warnings)}**")
                if item.red_flags:
                    lines.append(f"- **Red Flags**: {'; '.join(item.red_flags)}")
                lines.append("")
        else:
            lines.append("_No items in Tier 3._\n")

        return "\n".join(lines)


class TieredFoodRecommender:
    """
    The Middle Model that bridges Food Group Recognition with User Health Profiles.
    Ranks and classifies food items into Good, Medium, and Bad tiers based on
    clinical guardrails, metabolic targets, food group affinity scores, and strict exclusions.
    """

    NON_VEG_KEYWORDS = [
        "chicken", "mutton", "beef", "pork", "fish", "prawn", "prawns", "seafood", "meat",
        "bacon", "lamb", "egg", "eggs", "shrimp", "shrimps", "squid", "duck", "poultry", "turkey",
        "crab", "crabs", "lobster", "veal", "ham", "prosciutto", "salmon", "tuna", "steak",
        "calamari", "anchovy", "pepperoni", "salami"
    ]

    VEGAN_EXCLUSIONS = [
        "cheese", "paneer", "butter", "cream", "milk", "curd", "yogurt", "ghee",
        "whey", "honey", "dairy", "mayo", "mayonnaise", "egg", "eggs", "omelette"
    ]

    def __init__(
        self,
        user_matrix: Union[UserNutritionalMatrix, NutritionalMatrixProfile, Dict[str, Any]],
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        gemini_client: Optional[GeminiClient] = None,
        good_threshold: int = DEFAULT_GOOD_THRESHOLD,
        bad_threshold: int = DEFAULT_BAD_THRESHOLD,
    ):
        self.user_matrix = user_matrix
        self.gemini_client = gemini_client or GeminiClient(api_key=api_key, model_name=model_name)
        
        # Enforce threshold validity (0 <= bad < good <= 100)
        self.bad_threshold = max(0, min(95, int(bad_threshold)))
        self.good_threshold = max(self.bad_threshold + 5, min(100, int(good_threshold)))

        self._normalize_user_context()

    def is_available(self) -> bool:
        return self.gemini_client.is_available()

    def _normalize_user_context(self):
        """Extracts standard user context fields whether input is UserNutritionalMatrix or NutritionalMatrixProfile."""
        u = self.user_matrix
        if isinstance(u, UserNutritionalMatrix):
            self.user_summary = u.user_summary
            self.target_calories = u.metabolic_targets.target_calories_kcal
            self.target_protein_g = u.metabolic_targets.target_protein_g
            self.glycemic_sensitivity = u.clinical_risk_weights.glycemic_sensitivity
            self.sodium_ceiling = u.nutritional_guardrails.sodium_ceiling_mg
            self.sat_fat_max_pct = u.nutritional_guardrails.saturated_fat_max_pct
            self.fiber_min_g = u.nutritional_guardrails.dietary_fiber_min_g
            self.digestive_triggers = u.nutritional_guardrails.digestive_triggers_to_avoid
            self.exclusions = [str(e).lower().strip() for e in u.exclusion_mask]
            self.food_group_weights = u.food_group_weights
        elif isinstance(u, NutritionalMatrixProfile):
            self.user_summary = u.user_summary
            self.target_calories = u.metabolic_matrix.target_calories_kcal
            self.target_protein_g = u.metabolic_matrix.macro_split.protein_g
            self.glycemic_sensitivity = u.clinical_guardrails.glycemic_sensitivity_index
            self.sodium_ceiling = u.clinical_guardrails.sodium_limit_mg
            self.sat_fat_max_pct = u.clinical_guardrails.saturated_fat_max_pct
            self.fiber_min_g = u.clinical_guardrails.fiber_minimum_g
            self.digestive_triggers = u.clinical_guardrails.digestive_triggers_to_avoid
            self.exclusions = [str(e).lower().strip() for e in u.excluded_allergens_and_restrictions]
            self.food_group_weights = {fg.food_group.lower().replace(" ", "_"): float(fg.score) for fg in u.food_group_affinities}
        elif isinstance(u, dict):
            self.user_summary = u.get("user_summary", "Custom User Profile")
            self.target_calories = float(u.get("target_calories_kcal", 2000))
            self.target_protein_g = float(u.get("target_protein_g", 120))
            self.glycemic_sensitivity = float(u.get("glycemic_sensitivity", 0.3))
            self.sodium_ceiling = int(u.get("sodium_ceiling_mg", 2300))
            self.sat_fat_max_pct = float(u.get("saturated_fat_max_pct", 0.08))
            self.fiber_min_g = float(u.get("dietary_fiber_min_g", 30))
            self.digestive_triggers = u.get("digestive_triggers_to_avoid", [])
            self.exclusions = [str(e).lower().strip() for e in u.get("exclusion_mask", u.get("allergies", []))]
            self.food_group_weights = u.get("food_group_weights", {})
        else:
            self.user_summary = "Standard Nutritional Profile"
            self.target_calories = 2000.0
            self.target_protein_g = 120.0
            self.glycemic_sensitivity = 0.3
            self.sodium_ceiling = 2300
            self.sat_fat_max_pct = 0.08
            self.fiber_min_g = 30.0
            self.digestive_triggers = []
            self.exclusions = []
            self.food_group_weights = {}

    def check_hard_exclusions(self, dish_text: str) -> Optional[Dict[str, Any]]:
        """
        Evaluates deterministic hard safety exclusions (allergens and strict dietary rules).
        Returns a violation dict if violated, or None if safe.
        """
        lower_text = dish_text.lower()

        # 1. Meat / Poultry / Fish exclusion check (Vegetarian / Vegan / Explicit Meat Exclusions)
        has_meat_exclusion = any(
            ex in ("vegetarian", "vegan", "pescatarian", "meat", "poultry", "fish", "seafood", "beef", "pork", "chicken", "mutton")
            or ("veg" in ex and ex not in ("non-veg", "non_veg", "non-vegetarian"))
            for ex in self.exclusions
        )

        if has_meat_exclusion:
            matched_non_veg = [kw for kw in self.NON_VEG_KEYWORDS if re.search(r"\b" + re.escape(kw) + r"\b", lower_text)]
            if matched_non_veg:
                return {
                    "tier": FoodTier.BAD,
                    "fit_score": 0,
                    "summary_reason": f"Violates dietary restriction (contains non-vegetarian item: {', '.join(matched_non_veg)}).",
                    "matched_food_groups": ["Animal Meat"],
                    "green_flags": [],
                    "red_flags": [f"Contains non-vegetarian animal meat/seafood: {', '.join(matched_non_veg)}"],
                    "allergen_warnings": [f"Strict Dietary Violation: Non-vegetarian ({matched_non_veg[0]})"],
                    "customization_tips": "Select a plant-based or dairy protein alternative.",
                }

        # 2. Vegan / Dairy / Egg exclusion check
        has_vegan_exclusion = any(ex in ("vegan", "dairy", "eggs", "egg", "milk", "cheese", "paneer", "butter") for ex in self.exclusions)
        if has_vegan_exclusion:
            matched_dairy_egg = [kw for kw in self.VEGAN_EXCLUSIONS if re.search(r"\b" + re.escape(kw) + r"\b", lower_text)]
            if matched_dairy_egg:
                return {
                    "tier": FoodTier.BAD,
                    "fit_score": 0,
                    "summary_reason": f"Violates vegan/dairy restriction (contains animal byproduct: {', '.join(matched_dairy_egg)}).",
                    "matched_food_groups": ["Dairy / Egg"],
                    "green_flags": [],
                    "red_flags": [f"Contains dairy/egg byproduct: {', '.join(matched_dairy_egg)}"],
                    "allergen_warnings": [f"Strict Dietary Violation: Dairy/Egg ({matched_dairy_egg[0]})"],
                    "customization_tips": "Ask for dairy-free or plant-based preparation.",
                }

        # 3. Strict Allergens Matching
        diet_keywords = {"vegetarian", "vegan", "pescatarian", "halal", "kosher", "omnivore", "non-veg", "non-vegetarian", "meat", "poultry", "fish", "seafood", "dairy", "eggs", "egg", "milk", "cheese", "paneer"}
        for allergy in self.exclusions:
            if allergy in diet_keywords:
                continue

            allergy_words = [allergy]
            if allergy.endswith("s"):
                allergy_words.append(allergy[:-1])
            else:
                allergy_words.append(f"{allergy}s")

            if allergy in ("peanut", "peanuts"):
                allergy_words.extend(["peanut butter", "groundnut", "groundnuts", "arachis"])
            elif allergy in ("gluten", "wheat"):
                allergy_words.extend(["wheat", "maida", "naan", "roti", "bread", "pasta", "gluten"])
            elif allergy in ("tree_nuts", "tree_nut", "nuts"):
                allergy_words.extend(["walnut", "walnuts", "almond", "almonds", "cashew", "cashews", "pistachio", "pistachios", "hazelnut", "hazelnuts"])
            elif allergy in ("shellfish", "crustacean"):
                allergy_words.extend(["prawn", "prawns", "shrimp", "shrimps", "crab", "crabs", "lobster", "lobsters"])

            for target in allergy_words:
                if re.search(r"\b" + re.escape(target) + r"\b", lower_text):
                    return {
                        "tier": FoodTier.BAD,
                        "fit_score": 0,
                        "summary_reason": f"Strictly forbidden: contains declared allergen '{allergy}' ({target}).",
                        "matched_food_groups": [f"Allergen: {allergy}"],
                        "green_flags": [],
                        "red_flags": [f"Critical allergen detected: {allergy}"],
                        "allergen_warnings": [f"Contains allergen: {allergy}"],
                        "customization_tips": "Request completely separate allergen-free preparation or select a different dish.",
                    }

        return None

    def recommend_dish(self, dish: Union[MenuItem, Dict[str, Any], str]) -> TieredFoodRecommendation:
        """
        Classifies and recommends a single dish into GOOD, MEDIUM, or BAD.
        """
        dish_dict = self._to_dish_dict(dish)

        # 1. Hard exclusions check (Immediate BAD)
        full_text = f"{dish_dict.get('name', '')} {dish_dict.get('description', '')} {' '.join(dish_dict.get('tags', []))}"
        hard_violation = self.check_hard_exclusions(full_text)
        if hard_violation:
            return TieredFoodRecommendation(
                dish_name=dish_dict.get("name", "Unknown Item"),
                tier=hard_violation["tier"],
                fit_score=hard_violation["fit_score"],
                summary_reason=hard_violation["summary_reason"],
                matched_food_groups=hard_violation["matched_food_groups"],
                green_flags=hard_violation["green_flags"],
                red_flags=hard_violation["red_flags"],
                allergen_warnings=hard_violation["allergen_warnings"],
                customization_tips=hard_violation["customization_tips"],
                price=dish_dict.get("price", ""),
            )

        # 2. AI evaluation if available
        if self.is_available():
            try:
                results = self._recommend_batch_ai([dish_dict])
                if results:
                    return results[0]
            except Exception as e:
                logger.warning("[TieredFoodRecommender] AI evaluation failed (%s), falling back to deterministic engine.", e)

        # 3. Deterministic scoring
        return self._recommend_dish_deterministic(dish_dict)

    def recommend_menu(
        self,
        menu_input: Union[RecognizedMenu, List[Union[MenuItem, Dict[str, Any], str]]],
    ) -> TieredRecommendationResult:
        """
        Evaluates a complete menu or list of dishes, returning a structured 3-Tier Recommendation Result.
        """
        dishes: List[Dict[str, Any]] = []

        if isinstance(menu_input, RecognizedMenu):
            for item in menu_input.get_all_items():
                dishes.append({
                    "name": item.name,
                    "description": item.description or "",
                    "price": item.raw_price or (str(item.price) if item.price is not None else ""),
                    "tags": item.dietary_tags or [],
                    "section": item.section or "",
                })
        elif isinstance(menu_input, list):
            for item in menu_input:
                dishes.append(self._to_dish_dict(item))

        if not dishes:
            return TieredRecommendationResult(
                user_summary=self.user_summary,
                total_items_evaluated=0,
                good_items=[],
                medium_items=[],
                bad_items=[],
                all_recommendations=[],
            )

        recommendations: List[TieredFoodRecommendation] = []

        if self.is_available():
            try:
                recommendations = self._recommend_batch_ai(dishes)
            except Exception as e:
                logger.warning("[TieredFoodRecommender] Batch AI failed (%s), using deterministic engine.", e)
                recommendations = [self._recommend_dish_deterministic(d) for d in dishes]
        else:
            recommendations = [self._recommend_dish_deterministic(d) for d in dishes]

        # Post-check: Double ensure hard safety constraints across ALL recommendations
        validated_recs: List[TieredFoodRecommendation] = []
        for rec in recommendations:
            full_text = f"{rec.dish_name} {' '.join(rec.matched_food_groups)}"
            violation = self.check_hard_exclusions(full_text)
            if violation:
                rec.tier = FoodTier.BAD
                rec.fit_score = 0
                rec.summary_reason = violation["summary_reason"]
                rec.allergen_warnings = list(set(rec.allergen_warnings + violation["allergen_warnings"]))
                rec.red_flags = list(set(rec.red_flags + violation["red_flags"]))
            validated_recs.append(rec)

        # Sort all recommendations by fit_score descending
        validated_recs.sort(key=lambda x: x.fit_score, reverse=True)

        good_items = [r for r in validated_recs if r.tier == FoodTier.GOOD]
        medium_items = [r for r in validated_recs if r.tier == FoodTier.MEDIUM]
        bad_items = [r for r in validated_recs if r.tier == FoodTier.BAD]

        return TieredRecommendationResult(
            user_summary=self.user_summary,
            total_items_evaluated=len(validated_recs),
            good_items=good_items,
            medium_items=medium_items,
            bad_items=bad_items,
            all_recommendations=validated_recs,
        )

    def _to_dish_dict(self, dish: Union[MenuItem, Dict[str, Any], str]) -> Dict[str, Any]:
        if isinstance(dish, MenuItem):
            return {
                "name": dish.name,
                "description": dish.description or "",
                "price": dish.raw_price or (str(dish.price) if dish.price is not None else ""),
                "tags": dish.dietary_tags or [],
                "section": dish.section or "",
            }
        elif isinstance(dish, dict):
            return {
                "name": dish.get("name", "Unknown Item"),
                "description": dish.get("description", ""),
                "price": str(dish.get("price", "")),
                "tags": dish.get("tags", []),
                "section": dish.get("section", ""),
            }
        else:
            return {
                "name": str(dish),
                "description": "",
                "price": "",
                "tags": [],
                "section": "",
            }

    def _recommend_batch_ai(self, dishes: List[Dict[str, Any]]) -> List[TieredFoodRecommendation]:
        """Classifies dishes into 3 tiers using Gemini Flash."""
        prompt = f"""
You are an expert clinical nutrition matchmaking AI (The Middle Model).
Your task is to classify food dishes into EXACTLY 3 TIERS for the specified user:
- 🟢 "GOOD" (Tier 1: High nutritional fit, aligns with goals, safe, health-promoting)
- 🟡 "MEDIUM" (Tier 2: Moderate choice, neutral food groups, needs portion control or simple customization)
- 🔴 "BAD" (Tier 3: Strictly avoid, contains allergens/diet violations, high glycemic spikes, extreme sodium, or deep-fried)

USER PROFILE & METRICS:
- Summary: {self.user_summary}
- Target Daily Calories: {self.target_calories:.0f} kcal
- Target Protein: {self.target_protein_g:.0f} g
- Glycemic Sensitivity (0 to 1): {self.glycemic_sensitivity:.2f}
- Sodium Limit: {self.sodium_ceiling} mg/day
- Saturated Fat Ceiling: {self.sat_fat_max_pct * 100:.0f}%
- Digestive Triggers to Avoid: {', '.join(self.digestive_triggers) if self.digestive_triggers else 'None'}
- Strict Exclusions & Allergies: {', '.join(self.exclusions) if self.exclusions else 'None'}
- Food Group Compatibility Weights: {json.dumps(self.food_group_weights, indent=1) if self.food_group_weights else 'Standard'}

DISHES TO EVALUATE:
{json.dumps(dishes, indent=2)}

SCORING & TIER ASSIGNMENT RULES:
1. 'tier': MUST be one of ["GOOD", "MEDIUM", "BAD"].
   - GOOD: fit_score >= {self.good_threshold}
   - MEDIUM: {self.bad_threshold} <= fit_score < {self.good_threshold}
   - BAD: fit_score < {self.bad_threshold} OR violates any allergen/dietary restriction.
2. If any dish violates strict exclusions/allergies (e.g. peanuts for peanut allergy, meat for vegetarian), it MUST be Tier "BAD", fit_score 0, with 'allergen_warnings' populated.
3. Provide:
   - 'dish_name': exact dish name
   - 'tier': "GOOD" | "MEDIUM" | "BAD"
   - 'fit_score': integer (0 to 100)
   - 'summary_reason': crisp explanation of tier classification
   - 'matched_food_groups': list of identified food groups in the dish
   - 'green_flags': list of positive metabolic aspects
   - 'red_flags': list of negative metabolic or clinical aspects
   - 'allergen_warnings': list of strict violations if any
   - 'customization_tips': practical request to make dish healthier
   - 'estimated_calories': estimated integer kcal
   - 'estimated_protein_g': estimated integer protein grams

Return ONLY a valid JSON array of objects matching this schema:
[
  {{
    "dish_name": "Tandoori Paneer Tikka",
    "tier": "GOOD",
    "fit_score": 88,
    "summary_reason": "High protein, grilled preparation with low glycemic impact.",
    "matched_food_groups": ["Plant & Dairy Protein", "Grilled Vegetables", "Spices"],
    "green_flags": ["High protein", "Minimal oil preparation", "Rich in calcium"],
    "red_flags": ["Moderate saturated fat"],
    "allergen_warnings": [],
    "customization_tips": "Pair with a fresh green cucumber salad and mint chutney.",
    "estimated_calories": 320,
    "estimated_protein_g": 18
  }}
]
"""
        response_json = self.gemini_client.generate_json(prompt, temperature=0.1)

        if isinstance(response_json, dict) and "recommendations" in response_json:
            response_json = response_json["recommendations"]
        elif isinstance(response_json, dict) and "dishes" in response_json:
            response_json = response_json["dishes"]
        elif not isinstance(response_json, list):
            raise GeminiAPIError("Expected JSON array of recommendations.")

        dish_price_map = {d.get("name", "").lower(): d.get("price", "") for d in dishes}

        results: List[TieredFoodRecommendation] = []
        for d in response_json:
            name = d.get("dish_name", "Unknown Dish")
            raw_tier = str(d.get("tier", "MEDIUM")).upper()
            score = int(d.get("fit_score", 50))

            # Safety enforcement
            full_dish_text = f"{name} {json.dumps(d.get('matched_food_groups', []))}"
            violation = self.check_hard_exclusions(full_dish_text)

            if violation:
                tier = FoodTier.BAD
                score = 0
                summary = violation["summary_reason"]
                warnings = violation["allergen_warnings"]
                reds = violation["red_flags"]
            else:
                if score >= self.good_threshold:
                    tier = FoodTier.GOOD
                elif score >= self.bad_threshold:
                    tier = FoodTier.MEDIUM
                else:
                    tier = FoodTier.BAD
                summary = d.get("summary_reason", "Classified based on nutritional matrix.")
                warnings = d.get("allergen_warnings", [])
                reds = d.get("red_flags", [])

            results.append(
                TieredFoodRecommendation(
                    dish_name=name,
                    tier=tier,
                    fit_score=score,
                    summary_reason=summary,
                    matched_food_groups=d.get("matched_food_groups", []),
                    green_flags=d.get("green_flags", []),
                    red_flags=reds,
                    allergen_warnings=warnings,
                    customization_tips=d.get("customization_tips"),
                    estimated_calories=d.get("estimated_calories"),
                    estimated_protein_g=d.get("estimated_protein_g"),
                    price=dish_price_map.get(name.lower(), ""),
                )
            )

        return results

    def _recommend_dish_deterministic(self, dish: Dict[str, Any]) -> TieredFoodRecommendation:
        """
        High-precision deterministic rule-based matchmaking algorithm.
        Evaluates food against user's exclusions, clinical risk weights, and food group affinities.
        """
        name = dish.get("name", "Unknown Item")
        desc = dish.get("description", "")
        price = dish.get("price", "")
        tags = dish.get("tags", [])

        full_text = f"{name} {desc} {' '.join(tags)}".lower()

        # 1. HARD EXCLUSION & ALLERGY AUDIT (Instant BAD Tier)
        violation = self.check_hard_exclusions(full_text)
        if violation:
            return TieredFoodRecommendation(
                dish_name=name,
                tier=violation["tier"],
                fit_score=violation["fit_score"],
                summary_reason=violation["summary_reason"],
                matched_food_groups=violation["matched_food_groups"],
                green_flags=violation["green_flags"],
                red_flags=violation["red_flags"],
                allergen_warnings=violation["allergen_warnings"],
                customization_tips=violation["customization_tips"],
                price=price,
            )

        score = 65  # Baseline neutral score
        greens: List[str] = []
        reds: List[str] = []
        allergen_alerts: List[str] = []
        matched_groups: List[str] = []

        # Check digestive triggers
        for trigger in self.digestive_triggers:
            if trigger.lower() in full_text:
                score -= 25
                reds.append(f"Contains sensitivity trigger: {trigger}")

        # 2. FOOD GROUP SCORING & HEALTH ENHANCERS
        # Leafy greens / cruciferous / fresh veg
        if any(w in full_text for w in ["salad", "spinach", "palak", "broccoli", "greens", "cucumber", "methi", "saag", "cabbage", "kale", "lettuce", "veggie", "vegetable", "asparagus"]):
            score += 15
            greens.append("High in dietary fiber, micronutrients, and antioxidants")
            matched_groups.append("Cruciferous & Leafy Vegetables")

        # Lean / Healthy Protein
        if any(w in full_text for w in ["dal", "lentil", "chana", "tofu", "beans", "chickpea", "paneer", "sprouts", "edamame", "grilled chicken", "fish tikka", "salmon"]):
            score += 12
            greens.append("High protein density supporting metabolic targets")
            matched_groups.append("Plant / Lean Protein")

        # Healthy cooking method
        if any(w in full_text for w in ["grilled", "tandoori", "steamed", "roasted", "baked", "boiled", "poached"]):
            score += 10
            greens.append("Optimal low-fat cooking preparation (grilled/steamed)")

        # Probiotics & Fermented
        if any(w in full_text for w in ["curd", "yogurt", "raita", "dahi", "kombucha", "kimchi", "fermented"]):
            score += 8
            greens.append("Gut-friendly probiotics and bioavailable minerals")
            matched_groups.append("Fermented & Probiotic Foods")

        # Whole grains / Millets
        if any(w in full_text for w in ["quinoa", "millet", "brown rice", "ragi", "jowar", "bajra", "oats", "whole wheat", "roti"]):
            score += 8
            greens.append("Complex carbohydrates with sustained glucose release")
            matched_groups.append("Whole Grains & Millets")

        # 3. CLINICAL RISK PENALTIES
        # Deep fried / high oxidation
        if any(w in full_text for w in ["fried", "crispy", "fry", "pakora", "samosa", "poori", "bhatura", "fritters", "tempura", "deep fry", "calamari"]):
            score -= 25
            reds.append("Deep-fried; high oxidized lipids and caloric density")
            matched_groups.append("Deep Fried Foods")

        # Saturated fat / Cream / Butter
        if any(w in full_text for w in ["makhani", "butter", "cream", "creamy", "malai", "cheesy", "mayo", "loaded cheese", "ghee loaded", "bacon"]):
            penalty = 20 if self.sat_fat_max_pct < 0.08 else 12
            score -= penalty
            reds.append("High saturated fat load exceeding cardiovascular guardrails")
            matched_groups.append("Saturated & Trans Fats")

        # Refined carbohydrates / High Glycemic
        if any(w in full_text for w in ["naan", "kulcha", "maida", "white bread", "refined flour", "white rice", "bhature", "fries", "french fries"]):
            penalty = 20 if self.glycemic_sensitivity > 0.6 else 10
            score -= penalty
            reds.append("High glycemic refined carbohydrates with rapid glucose spike risk")
            matched_groups.append("Refined Carbohydrates")

        # Added sugar / desserts / syrups
        if any(w in full_text for w in ["gulab jamun", "halwa", "syrup", "kheer", "sweet", "sugar", "caramel", "soda", "pastry", "ice cream", "lava cake", "chocolate cake"]):
            penalty = 30 if self.glycemic_sensitivity > 0.5 else 18
            score -= penalty
            reds.append("Concentrated simple sugars conflicting with metabolic targets")
            matched_groups.append("Added Sugars & Confectionery")

        # High sodium keywords
        if any(w in full_text for w in ["pickle", "achar", "papad", "salted", "soy sauce", "msg", "processed cheese"]):
            if self.sodium_ceiling <= 1800:
                score -= 15
                reds.append("High sodium content exceeding strict hypertension ceiling")

        # Bound score between 5 and 98
        score = max(5, min(98, score))

        # 4. TIER CLASSIFICATION
        if score >= self.good_threshold:
            tier = FoodTier.GOOD
            summary = "Excellent nutritional alignment with low clinical risk."
            customization = "Pair with a fresh salad or green chutney for extra micronutrients."
        elif score >= self.bad_threshold:
            tier = FoodTier.MEDIUM
            summary = "Moderate fit. Recommended in controlled portions or with minor customization."
            customization = "Ask for light oil/butter, and pair with steamed vegetables or whole grain flatbread."
        else:
            tier = FoodTier.BAD
            summary = "Not recommended due to high refined carbs, saturated fat, or sodium load."
            customization = "Consider substituting with grilled, tandoori, or whole food alternatives."

        return TieredFoodRecommendation(
            dish_name=name,
            tier=tier,
            fit_score=score,
            summary_reason=summary,
            matched_food_groups=matched_groups or ["General Cuisine"],
            green_flags=greens or ["Standard meal option"],
            red_flags=reds,
            allergen_warnings=allergen_alerts,
            customization_tips=customization,
            price=price,
        )
