"""
AI-Powered Nutritional & Health Metric Matrix Generator.
Transforms raw user input (biometrics, health conditions, lifestyle, goals)
into a standardized multi-dimensional mathematical and clinical matrix
ready for consumption by external recommendation systems, optimizers, or databases.
"""

from typing import List, Dict, Any, Optional, Union
import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
import requests


@dataclass
class MetabolicTargets:
    """Metabolic and energy targets."""
    bmr_kcal: float
    tdee_kcal: float
    target_calories_kcal: float
    caloric_adjustment_ratio: float  # e.g. -0.20 for 20% deficit, +0.10 for surplus
    target_protein_g: float
    target_protein_pct: float
    target_carbs_g: float
    target_carbs_pct: float
    target_fats_g: float
    target_fats_pct: float
    protein_g_per_kg: float
    target_water_liters: float
    strategy_summary: str = ""


@dataclass
class ClinicalRiskWeights:
    """Normalized risk and sensitivity weights (0.0 to 1.0) for recommendation scoring."""
    glycemic_sensitivity: float        # 0.0 = standard, 1.0 = strict insulin resistance / diabetic control
    cardiovascular_risk_weight: float  # 0.0 = low, 1.0 = hypertension / arterial stiffness focus
    lipid_optimization_weight: float   # 0.0 = low, 1.0 = high LDL / saturated fat restriction
    inflammation_index_weight: float   # 0.0 = low, 1.0 = systemic inflammation / anti-inflammatory focus
    digestive_sensitivity_weight: float# 0.0 = resilient, 1.0 = GERD / IBS / GI sensitivity
    satiety_demand_weight: float       # 0.0 = low, 1.0 = high appetite / volume eating need


@dataclass
class NutritionalGuardrails:
    """Daily quantitative boundaries and nutrient thresholds."""
    sodium_ceiling_mg: int
    saturated_fat_max_pct: float
    added_sugar_max_g: float
    dietary_fiber_min_g: float
    potassium_target_mg: int
    omega3_min_g: float
    digestive_triggers_to_avoid: List[str] = field(default_factory=list)
    key_micronutrient_priorities: List[str] = field(default_factory=list)


@dataclass
class UserNutritionalMatrix:
    """
    Master standalone matrix representation of a user's nutritional & health profile.
    Can be directly consumed by recommendation systems, linear programming optimizers,
    vector databases, or machine learning models.
    """
    user_id: Optional[str]
    user_summary: str
    metabolic_targets: MetabolicTargets
    clinical_risk_weights: ClinicalRiskWeights
    nutritional_guardrails: NutritionalGuardrails
    food_group_weights: Dict[str, float] = field(default_factory=dict)
    exclusion_mask: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the entire matrix to a Python dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serializes the matrix to standard JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_feature_vector(self) -> List[float]:
        """
        Returns a flat numerical 1D feature vector for machine learning,
        cosine similarity, or clustering algorithms.
        """
        m = self.metabolic_targets
        w = self.clinical_risk_weights
        g = self.nutritional_guardrails
        return [
            m.target_calories_kcal,
            m.target_protein_g,
            m.target_protein_pct,
            m.target_carbs_g,
            m.target_carbs_pct,
            m.target_fats_g,
            m.target_fats_pct,
            m.protein_g_per_kg,
            w.glycemic_sensitivity,
            w.cardiovascular_risk_weight,
            w.lipid_optimization_weight,
            w.inflammation_index_weight,
            w.digestive_sensitivity_weight,
            w.satiety_demand_weight,
            float(g.sodium_ceiling_mg),
            g.saturated_fat_max_pct,
            g.added_sugar_max_g,
            g.dietary_fiber_min_g,
            float(g.potassium_target_mg),
            g.omega3_min_g,
        ]

    def to_markdown(self) -> str:
        """Renders an inspection markdown view of the matrix."""
        m = self.metabolic_targets
        w = self.clinical_risk_weights
        g = self.nutritional_guardrails

        lines = [
            f"# 📊 User Nutritional & Recommendation Metric Matrix",
            f"**Clinical Summary**: {self.user_summary}\n",
            f"## ⚡ 1. Metabolic & Energy Targets",
            f"- **BMR**: `{m.bmr_kcal:.0f} kcal` | **TDEE**: `{m.tdee_kcal:.0f} kcal`",
            f"- **Target Caloric Intake**: `{m.target_calories_kcal:.0f} kcal` ({m.caloric_adjustment_ratio:+.1%})",
            f"- **Macronutrients**:",
            f"  - **Protein**: `{m.target_protein_g:.0f}g` ({m.target_protein_pct:.0f}%) — `{m.protein_g_per_kg:.1f} g/kg`",
            f"  - **Carbs**: `{m.target_carbs_g:.0f}g` ({m.target_carbs_pct:.0f}%)",
            f"  - **Fats**: `{m.target_fats_g:.0f}g` ({m.target_fats_pct:.0f}%)",
            f"- **Hydration Target**: `{m.target_water_liters:.1f} L/day`",
            f"- *Strategy*: {m.strategy_summary}\n",
            f"## 🎚️ 2. Clinical Risk Weights (0.0 to 1.0)",
            f"| Metric / Vector Dimension | Weight (0.0 - 1.0) | Interpretation |",
            f"| :--- | :---: | :--- |",
            f"| Glycemic Sensitivity | `{w.glycemic_sensitivity:.2f}` | {'High: strict low-GI requirement' if w.glycemic_sensitivity >= 0.7 else 'Moderate/Standard'} |",
            f"| Cardiovascular Risk Weight | `{w.cardiovascular_risk_weight:.2f}` | {'High: strict sodium & endothelial focus' if w.cardiovascular_risk_weight >= 0.7 else 'Normal'} |",
            f"| Lipid Optimization Weight | `{w.lipid_optimization_weight:.2f}` | {'High: strict saturated fat limit' if w.lipid_optimization_weight >= 0.7 else 'Normal'} |",
            f"| Inflammation Index Weight | `{w.inflammation_index_weight:.2f}` | {'High: maximize polyphenols/omega-3' if w.inflammation_index_weight >= 0.7 else 'Normal'} |",
            f"| Digestive Sensitivity Weight | `{w.digestive_sensitivity_weight:.2f}` | {'High: avoid acid/deep fry triggers' if w.digestive_sensitivity_weight >= 0.7 else 'Resilient'} |",
            f"| Satiety Demand Weight | `{w.satiety_demand_weight:.2f}` | {'High: prioritize high-fiber/volume' if w.satiety_demand_weight >= 0.7 else 'Moderate'} |",
            f"\n## 🛡️ 3. Quantitative Nutritional Guardrails",
            f"- **Sodium Ceiling**: `< {g.sodium_ceiling_mg} mg/day`",
            f"- **Saturated Fat Ceiling**: `< {g.saturated_fat_max_pct * 100:.0f}%` of total kcal",
            f"- **Added Sugar Limit**: `< {g.added_sugar_max_g:.0f} g/day`",
            f"- **Minimum Dietary Fiber**: `> {g.dietary_fiber_min_g:.0f} g/day`",
            f"- **Potassium Target**: `{g.potassium_target_mg} mg/day`",
            f"- **Omega-3 Minimum**: `> {g.omega3_min_g:.1f} g/day`",
            f"\n## 🥗 4. Food Group Compatibility Weights (-10.0 to +10.0)",
            f"| Food Category | Weight (-10 to +10) | Recommendation Tier |",
            f"| :--- | :---: | :--- |",
        ]

        for fg, weight in sorted(self.food_group_weights.items(), key=lambda x: x[1], reverse=True):
            tier = "🌟 Top Priority" if weight >= 7 else ("✅ Recommended" if weight >= 3 else ("⚠️ Moderate/Limit" if weight >= -3 else "🚫 Strongly Avoid"))
            lines.append(f"| **{fg.replace('_', ' ').title()}** | `{weight:+.1f}` | {tier} |")

        if self.exclusion_mask:
            lines.append(f"\n> [!WARNING]\n> **Hard Exclusion Mask (Filter Out)**: {', '.join(self.exclusion_mask)}")

        return "\n".join(lines)


class AIMatrixGenerator:
    """
    AI-powered standalone generator that takes user information and outputs
    a standardized UserNutritionalMatrix.
    """

    CANDIDATE_MODELS = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-3.7-flash",
    ]

    # Standardized 22 Food Group Taxonomies for the Matrix
    STANDARD_FOOD_GROUPS = [
        "cruciferous_vegetables",
        "dark_leafy_greens",
        "allium_and_colorful_vegetables",
        "starchy_tubers",
        "whole_grains_and_millets",
        "refined_carbohydrates",
        "legumes_pulses_and_beans",
        "plant_based_proteins_tofu_tempeh",
        "fatty_coldwater_fish_omega3",
        "lean_white_fish_and_seafood",
        "lean_poultry",
        "eggs_and_egg_whites",
        "red_meat_and_game",
        "processed_and_cured_meats",
        "fermented_probiotic_foods",
        "low_fat_dairy",
        "full_fat_dairy_and_cheese",
        "nuts_and_seeds",
        "healthy_unsaturated_oils_olive_avocado",
        "saturated_and_trans_fats",
        "low_gi_berries_and_fruits",
        "high_sugar_fruits_and_juices",
        "added_sugars_and_confectionery",
        "deep_fried_and_ultra_processed"
    ]

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
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
        return bool(self.api_key and self.api_key.strip() and not self.api_key.startswith("mock_"))

    def generate(self, user_input: Union[Dict[str, Any], str], user_id: Optional[str] = None) -> UserNutritionalMatrix:
        """
        Generates a complete UserNutritionalMatrix from either a dictionary of attributes
        or a natural language text description of the user.
        """
        if self.is_available():
            try:
                return self._generate_ai(user_input, user_id)
            except Exception as e:
                print(f"[AIMatrixGenerator] AI generation failed ({e}), falling back to deterministic baseline calculator.")
                return self._generate_deterministic(user_input, user_id)
        else:
            return self._generate_deterministic(user_input, user_id)

    def _generate_ai(self, user_input: Union[Dict[str, Any], str], user_id: Optional[str] = None) -> UserNutritionalMatrix:
        """Invokes Gemini Flash in JSON mode to synthesize the complete matrix."""
        input_str = json.dumps(user_input, indent=2) if isinstance(user_input, dict) else str(user_input)

        prompt = f"""
You are an expert computational clinical nutritionist and biometric data scientist.
Transform this user profile data into a highly precise, standardized Nutritional & Recommendation Metric Matrix.

USER INPUT:
{input_str}

REQUIRED MATRIX SCHEMA & INSTRUCTIONS:
1. Calculate exact physiological metabolic targets (Mifflin-St Jeor & WHO standards):
   - bmr_kcal, tdee_kcal, target_calories_kcal, caloric_adjustment_ratio (e.g. -0.20 for 20% deficit)
   - target_protein_g, target_protein_pct, target_carbs_g, target_carbs_pct, target_fats_g, target_fats_pct
   - protein_g_per_kg, target_water_liters, strategy_summary
2. Infer normalized clinical risk & sensitivity weights (0.00 to 1.00):
   - glycemic_sensitivity (1.0 = severe insulin resistance / diabetes)
   - cardiovascular_risk_weight (1.0 = hypertension / high arterial resistance)
   - lipid_optimization_weight (1.0 = high LDL / cardiovascular disease risk)
   - inflammation_index_weight (1.0 = chronic systemic inflammation / autoimmune)
   - digestive_sensitivity_weight (1.0 = active GERD / IBS / acid reflux)
   - satiety_demand_weight (1.0 = high appetite during caloric deficit)
3. Set precise quantitative numerical guardrails:
   - sodium_ceiling_mg (e.g. 1500 for hypertension vs 2300 standard)
   - saturated_fat_max_pct (e.g. 0.06 for CVD/high LDL vs 0.10 standard)
   - added_sugar_max_g (e.g. 15.0 to 25.0)
   - dietary_fiber_min_g (e.g. 35.0 to 45.0 for insulin/lipid health)
   - potassium_target_mg (e.g. 3500 to 4700)
   - omega3_min_g (e.g. 2.0 to 3.0)
   - digestive_triggers_to_avoid (array of strings)
   - key_micronutrient_priorities (array of strings)
4. Score ALL 24 standardized food groups from -10.0 (strictly avoid / harmful) to +10.0 (highest therapeutic benefit):
   - cruciferous_vegetables, dark_leafy_greens, allium_and_colorful_vegetables, starchy_tubers,
     whole_grains_and_millets, refined_carbohydrates, legumes_pulses_and_beans, plant_based_proteins_tofu_tempeh,
     fatty_coldwater_fish_omega3, lean_white_fish_and_seafood, lean_poultry, eggs_and_egg_whites,
     red_meat_and_game, processed_and_cured_meats, fermented_probiotic_foods, low_fat_dairy,
     full_fat_dairy_and_cheese, nuts_and_seeds, healthy_unsaturated_oils_olive_avocado,
     saturated_and_trans_fats, low_gi_berries_and_fruits, high_sugar_fruits_and_juices,
     added_sugars_and_confectionery, deep_fried_and_ultra_processed.
   - If user is vegetarian/vegan, set animal meats to -10.0.
   - If user has peanut allergy, score nuts_and_seeds cautiously or flag in exclusion_mask.
5. Create exclusion_mask:
   - List of hard filter strings (e.g. ["peanuts", "meat", "poultry", "fish", "shellfish", "dairy", "gluten"]).

Return ONLY valid JSON matching this exact structure:
{{
  "user_summary": "1-2 sentence clinical summary of this user's nutritional profile and target strategy",
  "metabolic_targets": {{
    "bmr_kcal": 1680.0,
    "tdee_kcal": 2250.0,
    "target_calories_kcal": 1800.0,
    "caloric_adjustment_ratio": -0.20,
    "target_protein_g": 145.0,
    "target_protein_pct": 32.2,
    "target_carbs_g": 160.0,
    "target_carbs_pct": 35.6,
    "target_fats_g": 64.0,
    "target_fats_pct": 32.0,
    "protein_g_per_kg": 1.75,
    "target_water_liters": 3.2,
    "strategy_summary": "Moderate caloric deficit with high protein to protect lean mass and low glycemic carbs to stabilize insulin."
  }},
  "clinical_risk_weights": {{
    "glycemic_sensitivity": 0.85,
    "cardiovascular_risk_weight": 0.90,
    "lipid_optimization_weight": 0.70,
    "inflammation_index_weight": 0.65,
    "digestive_sensitivity_weight": 0.75,
    "satiety_demand_weight": 0.80
  }},
  "nutritional_guardrails": {{
    "sodium_ceiling_mg": 1500,
    "saturated_fat_max_pct": 0.06,
    "added_sugar_max_g": 15.0,
    "dietary_fiber_min_g": 38.0,
    "potassium_target_mg": 4000,
    "omega3_min_g": 2.5,
    "digestive_triggers_to_avoid": ["Deep fried oil", "Excess spicy acids", "Ultra-processed sodium"],
    "key_micronutrient_priorities": ["Potassium", "Magnesium", "Soluble Beta-Glucans", "Omega-3"]
  }},
  "food_group_weights": {{
    "cruciferous_vegetables": 10.0,
    "dark_leafy_greens": 10.0,
    "allium_and_colorful_vegetables": 9.0,
    "starchy_tubers": 4.0,
    "whole_grains_and_millets": 7.5,
    "refined_carbohydrates": -9.0,
    "legumes_pulses_and_beans": 9.0,
    "plant_based_proteins_tofu_tempeh": 8.5,
    "fatty_coldwater_fish_omega3": -10.0,
    "lean_white_fish_and_seafood": -10.0,
    "lean_poultry": -10.0,
    "eggs_and_egg_whites": -10.0,
    "red_meat_and_game": -10.0,
    "processed_and_cured_meats": -10.0,
    "fermented_probiotic_foods": 8.0,
    "low_fat_dairy": 5.0,
    "full_fat_dairy_and_cheese": 1.0,
    "nuts_and_seeds": 7.0,
    "healthy_unsaturated_oils_olive_avocado": 7.5,
    "saturated_and_trans_fats": -9.5,
    "low_gi_berries_and_fruits": 8.0,
    "high_sugar_fruits_and_juices": 2.0,
    "added_sugars_and_confectionery": -10.0,
    "deep_fried_and_ultra_processed": -10.0
  }},
  "exclusion_mask": ["peanuts", "meat", "poultry", "fish", "shellfish"]
}}
"""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.15
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
                    last_error = f"Model '{model}' not found."
                    continue
                else:
                    last_error = f"API Error {resp.status_code}: {resp.text}"
            except Exception as e:
                last_error = str(e)
                continue

        if response_json is None:
            raise RuntimeError(f"Matrix generation failed via Gemini: {last_error}")

        return self._parse_json_matrix(response_json, user_id=user_id, model_name=model)

    def _parse_json_matrix(self, data: Dict[str, Any], user_id: Optional[str] = None, model_name: str = "Gemini-Flash") -> UserNutritionalMatrix:
        """Constructs UserNutritionalMatrix object from validated JSON."""
        mt = data.get("metabolic_targets", {})
        metabolic_obj = MetabolicTargets(
            bmr_kcal=float(mt.get("bmr_kcal", 1600.0)),
            tdee_kcal=float(mt.get("tdee_kcal", 2100.0)),
            target_calories_kcal=float(mt.get("target_calories_kcal", 1800.0)),
            caloric_adjustment_ratio=float(mt.get("caloric_adjustment_ratio", -0.15)),
            target_protein_g=float(mt.get("target_protein_g", 120.0)),
            target_protein_pct=float(mt.get("target_protein_pct", 25.0)),
            target_carbs_g=float(mt.get("target_carbs_g", 200.0)),
            target_carbs_pct=float(mt.get("target_carbs_pct", 45.0)),
            target_fats_g=float(mt.get("target_fats_g", 65.0)),
            target_fats_pct=float(mt.get("target_fats_pct", 30.0)),
            protein_g_per_kg=float(mt.get("protein_g_per_kg", 1.6)),
            target_water_liters=float(mt.get("target_water_liters", 3.0)),
            strategy_summary=mt.get("strategy_summary", "")
        )

        rw = data.get("clinical_risk_weights", {})
        weights_obj = ClinicalRiskWeights(
            glycemic_sensitivity=float(rw.get("glycemic_sensitivity", 0.5)),
            cardiovascular_risk_weight=float(rw.get("cardiovascular_risk_weight", 0.5)),
            lipid_optimization_weight=float(rw.get("lipid_optimization_weight", 0.5)),
            inflammation_index_weight=float(rw.get("inflammation_index_weight", 0.5)),
            digestive_sensitivity_weight=float(rw.get("digestive_sensitivity_weight", 0.5)),
            satiety_demand_weight=float(rw.get("satiety_demand_weight", 0.5))
        )

        ng = data.get("nutritional_guardrails", {})
        guardrails_obj = NutritionalGuardrails(
            sodium_ceiling_mg=int(ng.get("sodium_ceiling_mg", 2300)),
            saturated_fat_max_pct=float(ng.get("saturated_fat_max_pct", 0.08)),
            added_sugar_max_g=float(ng.get("added_sugar_max_g", 25.0)),
            dietary_fiber_min_g=float(ng.get("dietary_fiber_min_g", 30.0)),
            potassium_target_mg=int(ng.get("potassium_target_mg", 3500)),
            omega3_min_g=float(ng.get("omega3_min_g", 2.0)),
            digestive_triggers_to_avoid=ng.get("digestive_triggers_to_avoid", []),
            key_micronutrient_priorities=ng.get("key_micronutrient_priorities", [])
        )

        # Standardize food group weights
        fg_weights: Dict[str, float] = {}
        raw_fg = data.get("food_group_weights", {})
        for fg, val in raw_fg.items():
            try:
                fg_weights[fg] = round(float(val), 1)
            except (ValueError, TypeError):
                fg_weights[fg] = 0.0

        return UserNutritionalMatrix(
            user_id=user_id,
            user_summary=data.get("user_summary", "Custom user nutritional profile"),
            metabolic_targets=metabolic_obj,
            clinical_risk_weights=weights_obj,
            nutritional_guardrails=guardrails_obj,
            food_group_weights=fg_weights,
            exclusion_mask=data.get("exclusion_mask", []),
            metadata={"engine": "Google-Gemini-AI", "model": model_name}
        )

    def _generate_deterministic(self, user_input: Union[Dict[str, Any], str], user_id: Optional[str] = None) -> UserNutritionalMatrix:
        """Deterministic mathematical and clinical baseline calculation for offline fallback."""
        data = user_input if isinstance(user_input, dict) else {}
        
        age = data.get("age", 30)
        gender = str(data.get("gender", "male")).lower()
        height = float(data.get("height_cm", 172.0))
        weight = float(data.get("weight_kg", 72.0))
        activity = str(data.get("activity_level", "sedentary")).lower()
        goal = str(data.get("primary_goal", "maintenance")).lower()
        conditions = [str(c).lower() for c in data.get("health_conditions", [])]
        diets = [str(d).lower() for d in data.get("dietary_preferences", [])]
        allergies = [str(a).lower() for a in data.get("allergies", [])]

        # 1. BMR (Mifflin-St Jeor)
        s = 5.0 if gender == "male" else -161.0
        bmr = (10.0 * weight) + (6.25 * height) - (5.0 * age) + s

        # 2. TDEE
        pal_map = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "heavy": 1.725, "athlete": 1.9}
        pal = pal_map.get(activity, 1.2)
        tdee = bmr * pal

        # 3. Caloric Target
        if "fat_loss" in goal or "deficit" in goal or "weight_loss" in goal:
            adj = -0.20
        elif "muscle" in goal or "surplus" in goal or "gain" in goal:
            adj = +0.10
        else:
            adj = 0.0
        target_kcal = tdee * (1.0 + adj)

        # 4. Macros
        p_per_kg = 1.8 if adj != 0.0 else 1.2
        p_g = weight * p_per_kg
        p_kcal = p_g * 4.0
        p_pct = (p_kcal / target_kcal) * 100.0

        f_pct = 25.0
        f_kcal = target_kcal * (f_pct / 100.0)
        f_g = f_kcal / 9.0

        c_kcal = target_kcal - p_kcal - f_kcal
        c_g = max(50.0, c_kcal / 4.0)
        c_pct = (c_kcal / target_kcal) * 100.0

        water = round(weight * 0.035, 1)

        metabolic_obj = MetabolicTargets(
            bmr_kcal=round(bmr, 1),
            tdee_kcal=round(tdee, 1),
            target_calories_kcal=round(target_kcal, 1),
            caloric_adjustment_ratio=adj,
            target_protein_g=round(p_g, 1),
            target_protein_pct=round(p_pct, 1),
            target_carbs_g=round(c_g, 1),
            target_carbs_pct=round(c_pct, 1),
            target_fats_g=round(f_g, 1),
            target_fats_pct=round(f_pct, 1),
            protein_g_per_kg=round(p_per_kg, 2),
            target_water_liters=water,
            strategy_summary=f"Deterministic metabolic allocation targeting {goal}."
        )

        # Risk weights
        glycemic_w = 0.85 if any(c in conditions for c in ["diabetes", "type_2_diabetes", "pcos", "insulin_resistance"]) else 0.35
        cvd_w = 0.90 if any(c in conditions for c in ["hypertension", "high_bp", "heart_disease"]) else 0.30
        lipid_w = 0.80 if any(c in conditions for c in ["cholesterol", "hyperlipidemia", "ldl"]) else 0.35
        reflux_w = 0.85 if any(c in conditions for c in ["gerd", "acid_reflux", "gastritis"]) else 0.20
        satiety_w = 0.80 if adj < 0.0 else 0.40

        weights_obj = ClinicalRiskWeights(
            glycemic_sensitivity=glycemic_w,
            cardiovascular_risk_weight=cvd_w,
            lipid_optimization_weight=lipid_w,
            inflammation_index_weight=0.5,
            digestive_sensitivity_weight=reflux_w,
            satiety_demand_weight=satiety_w
        )

        guardrails_obj = NutritionalGuardrails(
            sodium_ceiling_mg=1500 if cvd_w > 0.6 else 2300,
            saturated_fat_max_pct=0.06 if lipid_w > 0.6 else 0.09,
            added_sugar_max_g=15.0 if glycemic_w > 0.6 else 25.0,
            dietary_fiber_min_g=35.0 if (glycemic_w > 0.6 or lipid_w > 0.6) else 28.0,
            potassium_target_mg=4000 if cvd_w > 0.6 else 3500,
            omega3_min_g=2.5,
            digestive_triggers_to_avoid=["Deep fried oils", "Ultra-processed items"],
            key_micronutrient_priorities=["Potassium", "Fiber", "Magnesium"]
        )

        # Food group scoring
        is_veg = any("veg" in d for d in diets)
        meat_score = -10.0 if is_veg else 8.0

        fg_weights = {
            "cruciferous_vegetables": 10.0,
            "dark_leafy_greens": 10.0,
            "allium_and_colorful_vegetables": 9.0,
            "starchy_tubers": 4.0 if glycemic_w < 0.6 else 1.0,
            "whole_grains_and_millets": 8.0,
            "refined_carbohydrates": -9.0,
            "legumes_pulses_and_beans": 9.0,
            "plant_based_proteins_tofu_tempeh": 8.5,
            "fatty_coldwater_fish_omega3": -10.0 if is_veg else 9.0,
            "lean_white_fish_and_seafood": -10.0 if is_veg else 8.0,
            "lean_poultry": -10.0 if is_veg else 8.5,
            "eggs_and_egg_whites": -10.0 if any("vegan" in d for d in diets) else 7.5,
            "red_meat_and_game": -10.0 if is_veg else 2.0,
            "processed_and_cured_meats": -10.0,
            "fermented_probiotic_foods": 8.0,
            "low_fat_dairy": -10.0 if any("vegan" in d or "dairy" in allergies for d in diets) else 6.0,
            "full_fat_dairy_and_cheese": 1.0,
            "nuts_and_seeds": 7.5,
            "healthy_unsaturated_oils_olive_avocado": 8.0,
            "saturated_and_trans_fats": -9.5,
            "low_gi_berries_and_fruits": 8.0,
            "high_sugar_fruits_and_juices": 2.0 if glycemic_w < 0.6 else -2.0,
            "added_sugars_and_confectionery": -10.0,
            "deep_fried_and_ultra_processed": -10.0
        }

        exclusions = allergies + (["meat", "poultry", "fish"] if is_veg else [])

        return UserNutritionalMatrix(
            user_id=user_id,
            user_summary=f"Calculated baseline matrix for {age}yo {gender}, goal: {goal}.",
            metabolic_targets=metabolic_obj,
            clinical_risk_weights=weights_obj,
            nutritional_guardrails=guardrails_obj,
            food_group_weights=fg_weights,
            exclusion_mask=exclusions,
            metadata={"engine": "Deterministic-Baseline-Calculator"}
        )


if __name__ == "__main__":
    from examples.interactive_matrix_cli import main
    main()

