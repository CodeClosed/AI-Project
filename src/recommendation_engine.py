"""
3-Tier Food Recommendation Engine (The Middle Model).
Bridges Food & Menu Item Data (Food Groups, Ingredients, Macros) with User Health Matrices
(Biometrics, Metabolic Targets, Clinical Guardrails, Allergens) to classify dishes into
three distinct tiers: 🟢 GOOD, 🟡 MEDIUM, and 🔴 BAD.
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import os
import json
from pathlib import Path
import requests

from .models import MenuItem, RecognizedMenu
from .user_models import NutritionalMatrixProfile, DishEvaluationResult
from .matrix_generator import UserNutritionalMatrix


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
            lines.append("_No items qualified for Tier 1._\n")

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

    CANDIDATE_MODELS = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-3.7-flash",
    ]

    def __init__(
        self,
        user_matrix: Union[UserNutritionalMatrix, NutritionalMatrixProfile, Dict[str, Any]],
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        good_threshold: int = 75,
        bad_threshold: int = 45,
    ):
        """
        Initialize the Recommender with a User Matrix.
        
        Args:
            user_matrix: The user's nutritional matrix profile or UserNutritionalMatrix.
            api_key: Optional Gemini API key.
            model_name: Gemini model name.
            good_threshold: Minimum fit score (out of 100) to classify as GOOD (default: 75).
            bad_threshold: Score below which an item is classified as BAD (default: 45).
        """
        self.user_matrix = user_matrix
        self.api_key = api_key or self._load_api_key()
        self.model_name = model_name or "gemini-3.6-flash"
        self.good_threshold = good_threshold
        self.bad_threshold = bad_threshold
        self._normalize_user_context()

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
            self.exclusions = u.exclusion_mask
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
            self.exclusions = u.excluded_allergens_and_restrictions
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
            self.exclusions = u.get("exclusion_mask", u.get("allergies", []))
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

    def recommend_dish(self, dish: Union[MenuItem, Dict[str, Any], str]) -> TieredFoodRecommendation:
        """
        Classifies and recommends a single dish into GOOD, MEDIUM, or BAD.
        """
        dish_dict = self._to_dish_dict(dish)

        if self.is_available():
            try:
                results = self._recommend_batch_ai([dish_dict])
                if results:
                    return results[0]
            except Exception as e:
                print(f"[TieredFoodRecommender] AI evaluation failed ({e}), falling back to deterministic tier engine.")

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
                print(f"[TieredFoodRecommender] Batch AI failed ({e}), using deterministic tier engine.")
                recommendations = [self._recommend_dish_deterministic(d) for d in dishes]
        else:
            recommendations = [self._recommend_dish_deterministic(d) for d in dishes]

        # Sort all recommendations by fit_score descending
        recommendations.sort(key=lambda x: x.fit_score, reverse=True)

        good_items = [r for r in recommendations if r.tier == FoodTier.GOOD]
        medium_items = [r for r in recommendations if r.tier == FoodTier.MEDIUM]
        bad_items = [r for r in recommendations if r.tier == FoodTier.BAD]

        return TieredRecommendationResult(
            user_summary=self.user_summary,
            total_items_evaluated=len(recommendations),
            good_items=good_items,
            medium_items=medium_items,
            bad_items=bad_items,
            all_recommendations=recommendations,
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

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
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
            raise RuntimeError(f"Gemini tier recommendation failed: {last_error}")

        if isinstance(response_json, dict) and "recommendations" in response_json:
            response_json = response_json["recommendations"]
        elif isinstance(response_json, dict) and "dishes" in response_json:
            response_json = response_json["dishes"]

        # Map to original dishes for prices
        dish_price_map = {d.get("name", "").lower(): d.get("price", "") for d in dishes}

        results: List[TieredFoodRecommendation] = []
        for d in response_json:
            name = d.get("dish_name", "Unknown Dish")
            raw_tier = str(d.get("tier", "MEDIUM")).upper()
            tier = FoodTier.GOOD if "GOOD" in raw_tier else (FoodTier.BAD if "BAD" in raw_tier else FoodTier.MEDIUM)
            score = int(d.get("fit_score", 50))

            # Guardrail consistency
            if tier == FoodTier.BAD and score >= self.good_threshold:
                tier = FoodTier.GOOD
            elif tier == FoodTier.GOOD and score < self.bad_threshold:
                tier = FoodTier.BAD

            results.append(
                TieredFoodRecommendation(
                    dish_name=name,
                    tier=tier,
                    fit_score=score,
                    summary_reason=d.get("summary_reason", "Classified based on nutritional profile."),
                    matched_food_groups=d.get("matched_food_groups", []),
                    green_flags=d.get("green_flags", []),
                    red_flags=d.get("red_flags", []),
                    allergen_warnings=d.get("allergen_warnings", []),
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

        score = 65  # Baseline neutral score
        greens: List[str] = []
        reds: List[str] = []
        allergen_alerts: List[str] = []
        matched_groups: List[str] = []

        # 1. HARD EXCLUSION & ALLERGY AUDIT (Instant BAD Tier)
        exclusions = [ex.lower() for ex in self.exclusions]
        
        # Check meat / poultry / fish / seafood exclusions & vegetarian/vegan diets
        non_veg_keywords = ["chicken", "mutton", "beef", "pork", "fish", "prawn", "seafood", "meat", "bacon", "lamb", "egg", "shrimp", "squid", "duck", "poultry", "turkey", "crab", "lobster", "veal"]
        meat_exclusions = {"meat", "poultry", "fish", "seafood", "pork", "beef", "non-veg", "non_veg", "vegetarian", "vegan"}
        
        if any(ex in meat_exclusions or "veg" in ex for ex in exclusions):
            matched_meat = [k for k in non_veg_keywords if k in full_text]
            if matched_meat:
                return TieredFoodRecommendation(
                    dish_name=name,
                    tier=FoodTier.BAD,
                    fit_score=0,
                    summary_reason=f"Violates dietary restriction (contains non-vegetarian meat/poultry: {', '.join(matched_meat)}).",
                    matched_food_groups=["Animal Meat"],
                    green_flags=[],
                    red_flags=[f"Contains non-vegetarian animal meat: {', '.join(matched_meat)}"],
                    allergen_warnings=[f"Strict Dietary Violation: Non-vegetarian ({matched_meat[0]})"],
                    customization_tips="Select a plant-based or dairy protein alternative.",
                    price=price,
                )

        # Check explicit allergens & specific ingredients
        for allergy in exclusions:
            if allergy in meat_exclusions or "veg" in allergy:
                continue
            # Also handle single vs plural (e.g. peanut vs peanuts)
            allergy_root = allergy.rstrip("s")
            if allergy in full_text or (len(allergy_root) > 3 and allergy_root in full_text):
                return TieredFoodRecommendation(
                    dish_name=name,
                    tier=FoodTier.BAD,
                    fit_score=0,
                    summary_reason=f"Strictly forbidden: contains declared allergen '{allergy}'.",
                    matched_food_groups=[f"Allergen: {allergy}"],
                    green_flags=[],
                    red_flags=[f"Critical allergen detected: {allergy}"],
                    allergen_warnings=[f"Contains allergen: {allergy}"],
                    customization_tips="Request completely separate allergen-free preparation or select a different dish.",
                    price=price,
                )

        # Check digestive triggers
        for trigger in self.digestive_triggers:
            if trigger.lower() in full_text:
                score -= 25
                reds.append(f"Contains sensitivity trigger: {trigger}")

        # 2. FOOD GROUP SCORING & HEALTH ENHANCERS
        # Leafy greens / cruciferous / fresh veg
        if any(w in full_text for w in ["salad", "spinach", "palak", "broccoli", "greens", "cucumber", "methi", "saag", "cabbage", "kale", "lettuce", "veggie", "vegetable"]):
            score += 15
            greens.append("High in dietary fiber, micronutrients, and antioxidants")
            matched_groups.append("Cruciferous & Leafy Vegetables")

        # Lean / Healthy Protein
        if any(w in full_text for w in ["dal", "lentil", "chana", "tofu", "beans", "chickpea", "paneer", "sprouts", "edamame", "grilled chicken", "fish tikka"]):
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
        if any(w in full_text for w in ["fried", "crispy", "fry", "pakora", "samosa", "poori", "bhatura", "fritters", "tempura", "deep fry"]):
            score -= 25
            reds.append("Deep-fried; high oxidized lipids and caloric density")
            matched_groups.append("Deep Fried Foods")

        # Saturated fat / Cream / Butter
        if any(w in full_text for w in ["makhani", "butter", "cream", "creamy", "malai", "cheesy", "mayo", "loaded cheese", "ghee loaded"]):
            penalty = 20 if self.sat_fat_max_pct < 0.08 else 12
            score -= penalty
            reds.append("High saturated fat load exceeding cardiovascular guardrails")
            matched_groups.append("Saturated & Trans Fats")

        # Refined carbohydrates / High Glycemic
        if any(w in full_text for w in ["naan", "kulcha", "maida", "white bread", "refined flour", "white rice", "bhature"]):
            penalty = 20 if self.glycemic_sensitivity > 0.6 else 10
            score -= penalty
            reds.append("High glycemic refined flour with rapid glucose spike risk")
            matched_groups.append("Refined Carbohydrates")

        # Added sugar / desserts / syrups
        if any(w in full_text for w in ["gulab jamun", "halwa", "syrup", "kheer", "sweet", "sugar", "caramel", "soda", "pastry", "ice cream"]):
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
            customization = "Ask for light oil/butter, and pair with steamed vegetables or whole grain roti."
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
