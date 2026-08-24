"""
Strongly typed data models for User Profile, Health/Metabolic Matrices,
Food Group Recommendations, and Dish Evaluation.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
import json


@dataclass
class UserProfile:
    """Represents raw or structured user biometrics, lifestyle, and clinical context."""
    age: Optional[int] = None
    gender: Optional[str] = None  # "male", "female", "other"
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    activity_level: Optional[str] = "sedentary"  # sedentary, light, moderate, heavy, athlete
    primary_goal: Optional[str] = "maintenance"   # fat_loss, muscle_gain, maintenance, endurance, healthy_aging
    health_conditions: List[str] = field(default_factory=list)  # e.g. ["hypertension", "type_2_diabetes", "gerd", "pcos"]
    allergies: List[str] = field(default_factory=list)          # e.g. ["peanuts", "shellfish", "dairy", "gluten"]
    dietary_preferences: List[str] = field(default_factory=list) # e.g. ["vegetarian", "vegan", "halal", "keto"]
    raw_bio_text: Optional[str] = None                          # Natural language bio if provided
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MacroSplit:
    """Target macronutrient distribution."""
    protein_g: float
    protein_pct: float
    carbs_g: float
    carbs_pct: float
    fats_g: float
    fats_pct: float
    rationale: str = ""


@dataclass
class MetabolicEnergyMatrix:
    """Metabolic rates and target caloric numbers."""
    bmr_kcal: float
    tdee_kcal: float
    target_calories_kcal: float
    caloric_adjustment_pct: float  # e.g. -15.0 for 15% deficit, +10.0 for surplus
    macro_split: MacroSplit
    metabolic_tier: str = "Standard"  # e.g. "Insulin Sensitive", "Hyperbolic Deficit", "Endurance Fueling"


@dataclass
class ClinicalGuardrailMatrix:
    """Clinical safety limits and biomarker guidance."""
    glycemic_sensitivity_index: float  # 0.0 (low concern) to 1.0 (strict low-GI required)
    sodium_limit_mg: int               # e.g. 1500mg (hypertension) or 2300mg (standard)
    saturated_fat_max_pct: float       # e.g. 0.06 (6% of calories) or 0.10
    fiber_minimum_g: float             # e.g. 35.0g (high soluble)
    digestive_triggers_to_avoid: List[str] = field(default_factory=list) # e.g. ["excess_acid", "deep_fry", "lactose"]
    bioactive_priorities: List[str] = field(default_factory=list)       # e.g. ["potassium", "omega_3", "magnesium"]
    clinical_notes: str = ""


@dataclass
class FoodGroupAffinity:
    """Scored food category with status, priority, and clinical justification."""
    food_group: str                # e.g. "Cruciferous Vegetables", "Lean Plant Protein", "Refined Carbohydrates"
    score: int                     # Range: -10 (strictly avoid) to +10 (essential/highest priority)
    status: str                    # "Essential", "Recommended", "Moderate", "Limit", "Strictly Avoid"
    daily_servings_guide: str      # e.g. "3-5 servings/day", "Unlimited", "Zero / Eliminate"
    key_benefits_or_risks: str     # Clinical rationale
    examples: List[str] = field(default_factory=list)  # e.g. ["Broccoli", "Kale", "Cauliflower"]


@dataclass
class NutritionalMatrixProfile:
    """The master health and nutrition profile generated for a user."""
    user_summary: str
    metabolic_matrix: MetabolicEnergyMatrix
    clinical_guardrails: ClinicalGuardrailMatrix
    food_group_affinities: List[FoodGroupAffinity] = field(default_factory=list)
    excluded_allergens_and_restrictions: List[str] = field(default_factory=list)
    top_recommended_food_groups: List[str] = field(default_factory=list)
    food_groups_to_limit: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Generates a human-friendly markdown health & nutrition card."""
        m = self.metabolic_matrix
        g = self.clinical_guardrails
        
        md = []
        md.append(f"# 🥗 Personalized Nutritional & Health Matrix Profile\n")
        md.append(f"**Profile Summary**: {self.user_summary}\n")
        md.append(f"## ⚡ 1. Metabolic & Caloric Targets")
        md.append(f"- **Basal Metabolic Rate (BMR)**: `{m.bmr_kcal:.0f} kcal`")
        md.append(f"- **Total Daily Energy Expenditure (TDEE)**: `{m.tdee_kcal:.0f} kcal`")
        md.append(f"- **Target Daily Caloric Intake**: `{m.target_calories_kcal:.0f} kcal` ({m.caloric_adjustment_pct:+.1f}%)")
        md.append(f"- **Macro Allocation**:")
        md.append(f"  - **Protein**: `{m.macro_split.protein_g:.0f}g` ({m.macro_split.protein_pct:.0f}%)")
        md.append(f"  - **Carbs**: `{m.macro_split.carbs_g:.0f}g` ({m.macro_split.carbs_pct:.0f}%)")
        md.append(f"  - **Fats**: `{m.macro_split.fats_g:.0f}g` ({m.macro_split.fats_pct:.0f}%)")
        if m.macro_split.rationale:
            md.append(f"  - *Strategy*: {m.macro_split.rationale}")
        
        md.append(f"\n## 🛡️ 2. Clinical Biomarkers & Guardrails")
        md.append(f"- **Glycemic Sensitivity Index**: `{g.glycemic_sensitivity_index:.2f}` / 1.00")
        md.append(f"- **Daily Sodium Guardrail**: `{g.sodium_limit_mg} mg/day`")
        md.append(f"- **Saturated Fat Ceiling**: `< {g.saturated_fat_max_pct * 100:.0f}%` of total calories")
        md.append(f"- **Fiber Minimum Target**: `{g.fiber_minimum_g:.0f}g / day`")
        if g.digestive_triggers_to_avoid:
            md.append(f"- **Digestive / Sensitivities to Avoid**: {', '.join(g.digestive_triggers_to_avoid)}")
        if g.bioactive_priorities:
            md.append(f"- **Micronutrient & Bioactive Focus**: {', '.join(g.bioactive_priorities)}")
        if g.clinical_notes:
            md.append(f"- *Clinical Advisory*: {g.clinical_notes}")

        md.append(f"\n## 🍽️ 3. Scored Food Group Recommendations")
        md.append(f"| Food Group | Score (-10 to +10) | Status | Daily Guide | Clinical Rationale |")
        md.append(f"| :--- | :---: | :--- | :--- | :--- |")
        for fg in self.food_group_affinities:
            icon = "🌟" if fg.score >= 8 else ("✅" if fg.score >= 4 else ("⚠️" if fg.score >= -3 else "🚫"))
            md.append(f"| {icon} **{fg.food_group}** | `{fg.score:+d}` | {fg.status} | {fg.daily_servings_guide} | {fg.key_benefits_or_risks} |")

        if self.excluded_allergens_and_restrictions:
            md.append(f"\n> [!WARNING]\n> **Strict Exclusions & Allergies**: {', '.join(self.excluded_allergens_and_restrictions)}")

        return "\n".join(md)


@dataclass
class DishEvaluationResult:
    """Evaluation of a specific menu dish against a user's nutritional matrix."""
    dish_name: str
    fit_score: int                   # 0 to 100
    verdict: str                     # "Top Recommendation", "Healthy Choice", "Moderate / Consume with Care", "Not Recommended", "Violates Diet/Allergy"
    matched_food_groups: List[str] = field(default_factory=list)
    green_flags: List[str] = field(default_factory=list)
    red_flags: List[str] = field(default_factory=list)
    estimated_calories: Optional[int] = None
    estimated_protein_g: Optional[int] = None
    customization_tips: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
