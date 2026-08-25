"""
3-Tier Food Recommendation Engine (The Middle Model).
Bridges Food & Menu Item Data (Food Groups, Ingredients, Macros) with User Health Matrices
(Biometrics, Metabolic Targets, Clinical Guardrails, Allergens) to classify dishes into
three distinct tiers: 🟢 GOOD, 🟡 MEDIUM, and 🔴 BAD.

Architecture:
1. Hard Safety Exclusions (Allergies & Strict Diets) -> Instant BAD (Fit Score = 0). AI CANNOT override.
2. Clinical & Nutritional Scoring -> Explainable scoring based on metabolic targets & guardrails.
3. 3-Tier Classification -> Thresholding into GOOD / MEDIUM / BAD.
4. AI Enrichment -> Deep biochemical clinical explanations, tailored flags, and bespoke chef advice via Gemini.
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
                lines.append(f"- **Clinical Rationale**: {item.summary_reason}")
                if item.matched_food_groups:
                    lines.append(f"- **Food Groups**: {', '.join(item.matched_food_groups)}")
                if item.green_flags:
                    lines.append(f"- **Green Flags**: {'; '.join(item.green_flags)}")
                if item.customization_tips:
                    lines.append(f"- **Chef's Advice**: *{item.customization_tips}*")
                lines.append("")
        else:
            lines.append("_No items qualified for Tier 1 based on current thresholds._\n")

        lines.append("## 🟡 Tier 2: MEDIUM (Moderate / Consume with Caution)")
        if self.medium_items:
            for item in self.medium_items:
                lines.append(f"### 🍲 {item.dish_name} (Fit Score: `{item.fit_score}/100`)")
                if item.price:
                    lines.append(f"- **Price**: {item.price}")
                lines.append(f"- **Clinical Evaluation**: {item.summary_reason}")
                if item.red_flags:
                    lines.append(f"- **Caution Areas**: {'; '.join(item.red_flags)}")
                if item.customization_tips:
                    lines.append(f"- **Chef's Advice**: *{item.customization_tips}*")
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
        "chicken", "mutton", "muttan", "mutan", "beef", "pork", "fish", "prawn", "prawns", "seafood", "meat",
        "bacon", "lamb", "egg", "eggs", "exe", "egs", "shrimp", "shrimps", "squid", "duck", "poultry", "turkey",
        "crab", "crabs", "lobster", "veal", "ham", "prosciutto", "salmon", "tuna", "steak",
        "calamari", "anchovy", "pepperoni", "salami", "chioken", "chiken", "chikken", "gosht", "keema", "kheema"
    ]

    VEGAN_EXCLUSIONS = [
        "cheese", "paneer", "butter", "cream", "milk", "curd", "yogurt", "ghee",
        "whey", "honey", "dairy", "mayo", "mayonnaise", "egg", "eggs", "exe", "omelette"
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
        Evaluates deterministic hard safety exclusions (allergens and strict dietary rules)
        with dish-specific customized culinary substitution tips.
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
                meat = matched_non_veg[0].title()
                
                # Dish-Specific bespoke reason and substitution
                is_biryani = any(b in lower_text for b in ["biryani", "birvani", "blryani", "briyani", "biryany"])
                if is_biryani:
                    if "family" in lower_text or "pack" in lower_text or "handi" in lower_text:
                        reason = f"Large sharing platter containing multiple portions of spiced {meat.lower()} and ghee-infused basmati rice, conflicting with vegetarian diet."
                        tip = "Substitute with a Family Soya Dum Biryani Feast or Paneer Tikka Biryani Handi with cooling cucumber raita."
                    elif "special" in lower_text or "supreme" in lower_text:
                        reason = f"Chef specialty biryani prepared with layered {meat.lower()} chunks, animal broth essence, and egg byproducts."
                        tip = "Request the Special Royal Subz Awadhi Biryani prepared with saffron, grilled paneer, and toasted cashews."
                    else:
                        reason = f"Fragrant spiced basmati rice prepared with slow-cooked {meat.lower()} pieces and animal fats, violating vegetarian diet."
                        tip = "Swap with Soya Chaap Biryani, Dum Jackfruit (Kathal) Biryani, or Mixed Vegetable Dum Biryani."
                elif "burger" in lower_text or "sandwich" in lower_text:
                    reason = f"Contains animal meat patty/filling derived from {meat.lower()}, conflicting with vegetarian lifestyle."
                    tip = "Request a Crispy Spiced Chickpea-Beetroot Patty, Grilled Portobello, or Tandoori Paneer Steak Burger."
                elif "kebab" in lower_text or "tikka" in lower_text or "roast" in lower_text:
                    reason = f"Charcoal-roasted animal protein ({meat.lower()}) marinated in animal-seasoned spices."
                    tip = "Order Tandoori Paneer Tikka, Malai Soya Chaap, or Roasted Stuffed Button Mushrooms."
                elif "curry" in lower_text or "gravy" in lower_text or "makhani" in lower_text or "masala" in lower_text:
                    reason = f"Slow-simmered curry base containing {meat.lower()} protein and rendered animal lipids."
                    tip = "Order Paneer Butter Masala, Soya Chaap Rogan Josh, or Mushroom Do Pyaza with identical rich spices."
                elif "soup" in lower_text or "broth" in lower_text:
                    reason = f"Contains animal-derived {meat.lower()} broth and bone essence."
                    tip = "Ask for Clear Vegetable Wonton Soup or Sweet Corn Asparagus Soup with tofu."
                else:
                    reason = f"Contains {meat.lower()} animal meat protein, conflicting with your vegetarian lifestyle."
                    tip = f"Request a plant-based protein alternative such as grilled paneer, soya chaap, or seasoned tofu."

                return {
                    "tier": FoodTier.BAD,
                    "fit_score": 0,
                    "summary_reason": reason,
                    "matched_food_groups": [f"{meat} Poultry / Meat"],
                    "green_flags": [],
                    "red_flags": [f"Contains non-vegetarian animal ingredient: {meat.lower()}"],
                    "allergen_warnings": [f"Strict Dietary Violation: Non-vegetarian ({meat.lower()})"],
                    "customization_tips": tip,
                }

        # 2. Vegan / Dairy / Egg exclusion check
        has_vegan_exclusion = any(ex in ("vegan", "dairy", "eggs", "egg", "milk", "cheese", "paneer", "butter") for ex in self.exclusions)
        if has_vegan_exclusion:
            matched_dairy_egg = [kw for kw in self.VEGAN_EXCLUSIONS if re.search(r"\b" + re.escape(kw) + r"\b", lower_text)]
            if matched_dairy_egg:
                item_name = matched_dairy_egg[0].title()
                return {
                    "tier": FoodTier.BAD,
                    "fit_score": 0,
                    "summary_reason": f"Contains animal-derived dairy or egg ingredient ({item_name.lower()}), conflicting with vegan/dairy-free protocol.",
                    "matched_food_groups": ["Dairy / Egg Byproduct"],
                    "green_flags": [],
                    "red_flags": [f"Contains animal byproduct: {item_name.lower()}"],
                    "allergen_warnings": [f"Strict Dietary Violation: Dairy/Egg ({item_name.lower()})"],
                    "customization_tips": f"Ask the kitchen for dairy-free coconut milk/cashew cream preparation or tofu substitution.",
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
                        "summary_reason": f"Critical Allergen Alert: Recipe incorporates declared allergen '{allergy}' ({target}).",
                        "matched_food_groups": [f"Allergen: {allergy.title()}"],
                        "green_flags": [],
                        "red_flags": [f"Zero-tolerance allergen detected: {allergy}"],
                        "allergen_warnings": [f"Contains Declared Allergen: {allergy}"],
                        "customization_tips": f"Requires complete kitchen cross-contact isolation or choose a guaranteed {allergy}-free dish.",
                    }

        return None

    def recommend_dish(self, dish: Union[MenuItem, Dict[str, Any], str]) -> TieredFoodRecommendation:
        """Classifies and recommends a single dish into GOOD, MEDIUM, or BAD."""
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
        """Evaluates a complete menu or list of dishes, returning a structured 3-Tier Recommendation Result."""
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

        # Post-check: Enforce hard safety constraints across ALL recommendations
        validated_recs: List[TieredFoodRecommendation] = []
        for rec in recommendations:
            full_text = f"{rec.dish_name} {' '.join(rec.matched_food_groups)}"
            violation = self.check_hard_exclusions(full_text)
            if violation:
                rec.tier = FoodTier.BAD
                rec.fit_score = 0
                # Preserve Gemini summary if detailed, else use dish-specific violation
                if not rec.summary_reason or len(rec.summary_reason) < 20 or "Classified based" in rec.summary_reason:
                    rec.summary_reason = violation["summary_reason"]
                if not rec.customization_tips or "pair with" in rec.customization_tips.lower():
                    rec.customization_tips = violation["customization_tips"]
                rec.allergen_warnings = list(dict.fromkeys(rec.allergen_warnings + violation["allergen_warnings"]))
                rec.red_flags = list(dict.fromkeys(rec.red_flags + violation["red_flags"]))
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
        """Classifies dishes into 3 tiers using Gemini Flash with deep item-specific clinical reasoning."""
        prompt = f"""
You are an elite Clinical Nutrition Scientist and Master Culinary Dietitian (The Middle Model).
Evaluate each restaurant menu item against the user's specific clinical health profile and classify it into EXACTLY ONE of 3 TIERS:
- 🟢 "GOOD" (Tier 1: High nutritional fit, optimal metabolic alignment, safe, health-promoting)
- 🟡 "MEDIUM" (Tier 2: Moderate choice, acceptable with portion control or minor culinary modification)
- 🔴 "BAD" (Tier 3: Strictly avoid, contains allergens/diet violations, high glycemic spikes, excessive saturated fat/sodium, or deep-fried)

USER CLINICAL HEALTH MATRIX:
- Clinical Summary: {self.user_summary}
- Target Daily Energy: {self.target_calories:.0f} kcal/day
- Target Protein: {self.target_protein_g:.0f} g/day
- Glycemic Sensitivity Index (0.0 to 1.0): {self.glycemic_sensitivity:.2f} (High values require strict low-GI / low glycemic load)
- Sodium Limit: < {self.sodium_ceiling} mg/day (Strict threshold for hypertension)
- Saturated Fat Ceiling: < {self.sat_fat_max_pct * 100:.0f}% of total calories (Strict threshold for hyperlipidemia / heart disease)
- Gastrointestinal / Reflux Triggers: {', '.join(self.digestive_triggers) if self.digestive_triggers else 'None'}
- Strict Exclusions & Allergens: {', '.join(self.exclusions) if self.exclusions else 'None'}

DISHES TO EVALUATE:
{json.dumps(dishes, indent=2)}

CRITICAL INSTRUCTIONS FOR HIGH-CRAFT, BESPOKE ANALYSIS:
1. ZERO-GENERIC POLICY: Do NOT use boilerplate phrases like "Moderate fit", "Good choice", or generic repeats. Every single field MUST be 100% UNIQUE, vivid, and specific to the exact ingredients, cooking technique, and biochemistry of THAT particular dish.
2. DISH-SPECIFIC CLINICAL ASSESSMENT ('summary_reason'):
   - Provide a 2-3 sentence rigorous clinical breakdown directly naming the specific culinary ingredients (e.g. makhani cashew gravy, stone-ground whole wheat atta, refined maida, russet potato starch, aspartame, deep-fry oil, cheese casein, basmati rice amylose).
   - If the dish violates a lifestyle rule (like vegetarianism), explain the specific dish anatomy (e.g. for 'Chicken Biryani': "Layered fragrant basmati rice cooked with spiced bone-in poultry meat and animal lipids, directly violating vegetarian principles").
3. DISTINCT NUTRITIONAL FLAGS:
   - 'green_flags': 2-3 specific biochemical strengths of this exact dish (e.g. "Tandoor dry-heat preparation avoids oxidized cooking fats", "Rich in lycopene from slow-cooked tomatoes", "High biological value complete poultry protein").
   - 'red_flags': 2-3 specific clinical caution areas of this exact dish (e.g. "Heavy dairy cream and butter emulsion elevates saturated fat", "Refined starch causes rapid glycemic surge", "Deep-fryer thermal degradation produces advanced lipid peroxides").
4. BESPOKE CHEF CUSTOMIZATION ADVICE ('customization_tips'):
   - Provide practical, creative culinary hacks tailored specifically to that dish:
     - For Biryanis: suggest specific vegetarian alternatives like "Swap with Dum Soya Chaap Biryani, Paneer Tikka Biryani, or Jackfruit (Kathal) Handi Biryani with cucumber mint raita".
     - For Family Packs: suggest "Order the Family Soya Dum Biryani Feast or Assorted Tandoori Paneer & Subz Platter to share".
     - For Curries: suggest "Ask the kitchen to prepare with half the butter and substitute heavy cream with whisked dahi".
     - For Rotis: suggest "Request unbuttered 100% whole wheat tandoori roti rather than maida-based naan".
     - For Burgers: suggest "Request a spiced chickpea patty or grilled paneer steak on a whole wheat bun".
5. HARD SAFETY VIOLATIONS: If a dish violates declared allergens or vegetarian/vegan restrictions, force Tier = "BAD", fit_score = 0, and describe the exact violation in 'allergen_warnings'.

Return ONLY valid JSON matching this schema:
[
  {{
    "dish_name": "Exact Name",
    "tier": "GOOD" | "MEDIUM" | "BAD",
    "fit_score": 85,
    "summary_reason": "Detailed, bespoke clinical evaluation referencing the specific ingredients and biochemical impact.",
    "matched_food_groups": ["Food Group 1", "Food Group 2"],
    "green_flags": ["Specific advantage 1", "Specific advantage 2"],
    "red_flags": ["Specific caution 1"],
    "allergen_warnings": [],
    "customization_tips": "Specific culinary instruction tailored to this exact recipe.",
    "estimated_calories": 350,
    "estimated_protein_g": 22,
    "estimated_carbs_g": 25,
    "estimated_fat_g": 12
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
            score = int(d.get("fit_score", 50))

            # Safety enforcement
            full_dish_text = f"{name} {json.dumps(d.get('matched_food_groups', []))}"
            violation = self.check_hard_exclusions(full_dish_text)

            if violation:
                tier = FoodTier.BAD
                score = 0
                summary = d.get("summary_reason") if d.get("summary_reason") and len(d.get("summary_reason")) > 25 and "Classified based" not in d.get("summary_reason") else violation["summary_reason"]
                tips = d.get("customization_tips") if d.get("customization_tips") and len(d.get("customization_tips")) > 20 else violation["customization_tips"]
                warnings = list(dict.fromkeys(d.get("allergen_warnings", []) + violation["allergen_warnings"]))
                reds = list(dict.fromkeys(d.get("red_flags", []) + violation["red_flags"]))
            else:
                if score >= self.good_threshold:
                    tier = FoodTier.GOOD
                elif score >= self.bad_threshold:
                    tier = FoodTier.MEDIUM
                else:
                    tier = FoodTier.BAD
                summary = d.get("summary_reason", "Classified based on clinical nutritional matrix.")
                tips = d.get("customization_tips")
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
                    customization_tips=tips,
                    estimated_calories=d.get("estimated_calories"),
                    estimated_protein_g=d.get("estimated_protein_g"),
                    estimated_carbs_g=d.get("estimated_carbs_g"),
                    estimated_fat_g=d.get("estimated_fat_g"),
                    price=dish_price_map.get(name.lower(), ""),
                )
            )

        return results

    def _recommend_dish_deterministic(self, dish: Dict[str, Any]) -> TieredFoodRecommendation:
        """
        High-precision deterministic rule-based matchmaking algorithm with rich culinary heuristics.
        Provides distinct, item-specific assessments across popular dishes when offline.
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

        score = 65
        greens: List[str] = []
        reds: List[str] = []
        allergen_alerts: List[str] = []
        matched_groups: List[str] = []
        summary = ""
        customization = ""

        # Specific Dish Heuristics
        is_biryani = any(b in full_text for b in ["biryani", "birvani", "blryani", "briyani", "biryany"])
        is_manchurian = any(m in full_text for m in ["manchurian", "manchurlan", "manchuria"])
        is_family_pack = any(fp in full_text for fp in ["family pack", "supreme pack", "combo pack", "platter", "feast", "jumbo"])

        if "butter chicken" in full_text or "makhani" in full_text:
            score = 42
            matched_groups = ["Poultry Protein", "Dairy Fats & Cream", "Tomato Gravy"]
            greens = ["High biological value intact poultry protein", "Lycopene antioxidants from simmered tomato base"]
            reds = ["High saturated fat load from heavy butter and cashew-cream emulsion", "Elevated sodium in restaurant curry base"]
            summary = "Provides rich protein density from chicken breast, but the heavy dairy butter and cashew gravy carries a significant saturated fat and caloric density penalty."
            customization = "Ask the kitchen for light gravy, substitute half the heavy cream with whisked dahi, or pair with steamed whole wheat roti rather than butter naan."
        elif is_family_pack and is_biryani:
            score = 58
            matched_groups = ["Whole Spices & Herbs", "High-Volume Basmati Rice", "Portion Multiplier"]
            greens = ["Aromatic whole spices (cardamom, clove, cinnamon) provide antioxidant bioflavonoids", "Conforms to vegetarian protocol if plant-based"]
            reds = ["Extremely large portion size carries high risk of caloric and glycemic overshoot", "High cooking fat and ghee infusion"]
            summary = "Multi-serving sharing platter of seasoned basmati rice. While suitable for group dining, individual serving control is critical to manage carbohydrate density."
            customization = "Divide into measured individual portions (~1.5 cups per serving) and pair with generous cucumber raita and raw onion salad."
        elif is_family_pack:
            score = 60
            matched_groups = ["Multi-Serving Platter", "Mixed Cuisine"]
            greens = ["Diverse assortment of meal components for balanced sharing"]
            reds = ["High cumulative caloric and sodium content across full multi-item pack"]
            summary = "Large-format multi-item sharing package. Contains high cumulative sodium and fat density across combined preparations."
            customization = "Share among 3-4 persons, prioritize salad and tandoori components, and request gravies with reduced butter."
        elif is_biryani and any(v in full_text for v in ["veg", "vcg", "subz", "vegetable", "paneer", "soya", "kathal", "jackfruit"]):
            score = 70
            matched_groups = ["Vegetable Fiber", "Basmati Grains", "Aromatic Spices"]
            greens = ["Rich in plant-based micronutrients, carrot beta-carotene, and bean fiber", "Potent polyphenol antioxidant blend from cloves, saffron, and star anise", "Strictly vegetarian-compliant"]
            reds = ["Starch-dense basmati rice carries high glycemic load", "Restaurant preparation typically includes generous ghee or refined oil"]
            summary = "Fragrant vegetarian rice preparation cooked with seasonal vegetables and whole spices. Offers fiber and phytonutrients, though mindful portioning is recommended for blood glucose management."
            customization = "Pair with double cucumber-mint raita to slow gastric emptying, or request preparation with minimal oil."
        elif is_manchurian:
            score = 55
            matched_groups = ["Deep Fried Dumplings", "Soy-Garlic Sauce", "Refined Starch"]
            greens = ["Minced vegetable content (cabbage, carrots, bell peppers)", "Allicin and capsaicin from garlic and chili aromatics"]
            reds = ["Dumplings are deep-fried in thermal cooking oils", "Cornstarch thickener and soy sauce contribute to high sodium and glycemic index"]
            summary = "Indo-Chinese spiced vegetable florets or dumplings deep-fried and tossed in a cornstarch-thickened soy sauce. Elevated sodium and oxidized lipid load warrant moderate consumption."
            customization = "Request gravy prepared with low sodium, ask for stir-fried rather than deep-fried florets, or pair with steamed brown rice."
        elif "tandoori roti" in full_text:
            score = 80
            matched_groups = ["Whole Grains & Millets", "Low-Fat Bread"]
            greens = ["Stone-ground whole wheat atta provides complex dietary fiber", "Clay tandoor baking uses dry radiative heat with zero added frying oil", "Moderate glycemic index supporting steady glucose release"]
            reds = ["Contains gluten", "Portion control needed for low-carb targets"]
            summary = "Excellent whole grain staple baked in a clay tandoor without frying oils. Delivers unrefined complex fiber that buffers postprandial glucose surges."
            customization = "Request plain dry tandoori roti without butter or ghee brushing."
        elif "rumali roti" in full_text or "roomali" in full_text:
            score = 48
            matched_groups = ["Refined Carbohydrates"]
            greens = ["Low in saturated fat", "Easily digestible starch"]
            reds = ["Made primarily with refined maida flour", "Rapid enzymatic starch breakdown accelerates blood glucose spike"]
            summary = "Thinly rolled refined maida flatbread. Lacks bran fiber, resulting in rapid starch absorption and elevated glycemic load."
            customization = "Substitute with stone-ground whole wheat tandoori roti or multi-grain phulka."
        elif any(d in full_text for d in ["double ka meetha", "shahi tukda", "lava cake", "chocolate cake", "ice cream", "sundae", "brownie", "gulab jamun", "jalebi", "cheesecake"]):
            score = 15
            matched_groups = ["Deep Fried Foods", "Added Sugars & Confectionery", "Refined Carbohydrates"]
            greens = ["Aromatic cocoa and spice bioflavonoids"]
            reds = ["High simple sugar content causes severe postprandial glucose spike", "High saturated dairy fat and caloric density"]
            summary = "High-glycemic confectionery and dessert. Contains concentrated sucrose and saturated fats, conflicting with glucose management and caloric targets."
            customization = "Share a single small portion or substitute with fresh fruit and unsweetened probiotic curd."
        elif "diet coke" in full_text or "diet pepsi" in full_text or "zero sugar" in full_text:
            score = 72
            matched_groups = ["Zero Calorie Beverages"]
            greens = ["Zero caloric density and zero glycemic impact", "Does not trigger insulin secretion"]
            reds = ["Contains artificial non-nutritive sweeteners (aspartame/acesulfame-K)", "Phosphoric acid can increase urinary calcium excretion"]
            summary = "Zero-calorie carbonated beverage that satisfies sweetness without adding caloric or glycemic burden, though phosphoric acid and artificial sweeteners warrant moderation."
            customization = "Enjoy chilled with a fresh lemon wedge; balance with ample mineral water."
        elif "paneer tikka" in full_text or "tandoori paneer" in full_text:
            score = 84
            matched_groups = ["Dairy Protein", "Grilled Vegetables", "Capsaicin Spices"]
            greens = ["High biological value dairy protein and calcium", "Tandoor charring uses minimal added fat", "Spices (turmeric, ginger) provide anti-inflammatory curcumin"]
            reds = ["Moderate saturated fat from full-fat cottage cheese"]
            summary = "Nutrient-dense protein dish prepared with marinated cottage cheese cubes roasted in dry tandoor heat. Fosters satiety with low glycemic impact."
            customization = "Pair with a crisp raw onion-cucumber salad and fresh mint-coriander chutney."
        elif "fries" in full_text or "french fries" in full_text:
            score = 30
            matched_groups = ["Deep Fried Foods", "Refined Starch", "High Sodium"]
            greens = ["Contains dietary potassium from potato tissue"]
            reds = ["Deep-fried in thermal oxidized oil generating lipid peroxides", "Rapidly digestible starch combined with high salt crystals", "High caloric density with low satiety per calorie"]
            summary = "Deep-fried russet potato strips with rapid starch bioavailability and high surface salt adherence. Conflicting with lipid and blood pressure guardrails."
            customization = "Request oven-baked potato wedges with skin-on or substitute with steamed edamame."
        else:
            # Fallback general heuristics
            if any(w in full_text for w in ["salad", "spinach", "palak", "broccoli", "greens", "cucumber"]):
                score += 15
                greens.append("High in dietary fiber, polyphenols, and micronutrients")
                matched_groups.append("Leafy & Cruciferous Vegetables")
            if any(w in full_text for w in ["dal", "lentil", "chana", "tofu", "beans", "grilled chicken", "fish tikka", "salmon"]):
                score += 12
                greens.append("High protein density supporting lean mass preservation")
                matched_groups.append("Lean / Plant Protein")
            if any(w in full_text for w in ["fried", "crispy", "fry", "pakora", "samosa"]):
                score -= 25
                reds.append("Deep-fried; high oxidized lipid load and elevated caloric density")
                matched_groups.append("Deep Fried Foods")

            score = max(5, min(98, score))
            if score >= self.good_threshold:
                summary = f"Strong nutritional alignment for '{name}'. Low glycemic impact with quality micronutrient density."
                customization = "Pair with a fresh green salad or steamed whole grain side."
            elif score >= self.bad_threshold:
                summary = f"Moderate metabolic fit for '{name}'. Acceptable in portion-controlled servings with mindful sodium and fat balance."
                customization = "Request light cooking oil or sauce on the side."
            else:
                summary = f"'{name}' is not recommended due to high refined carbohydrate, saturated fat, or sodium density."
                customization = "Consider substituting with grilled, tandoori, or unrefined whole food alternatives."

        tier = FoodTier.GOOD if score >= self.good_threshold else (FoodTier.MEDIUM if score >= self.bad_threshold else FoodTier.BAD)

        return TieredFoodRecommendation(
            dish_name=name,
            tier=tier,
            fit_score=score,
            summary_reason=summary,
            matched_food_groups=matched_groups or ["General Cuisine"],
            green_flags=greens or ["Balanced meal component"],
            red_flags=reds,
            allergen_warnings=allergen_alerts,
            customization_tips=customization,
            price=price,
        )
