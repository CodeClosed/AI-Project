"""
Modular UI & Visual Presentation Components for NutriMenu AI.
Provides multi-step wizard navigation, glassmorphic card styling,
dynamic nutritional matrix visualizations, and modern 3-tier recommendation cards.
"""

from typing import Dict, Any, List, Tuple, Optional
import io
import json
from PIL import Image
import streamlit as st

from .models import RecognizedMenu
from .matrix_generator import UserNutritionalMatrix, AIMatrixGenerator
from .recommendation_engine import (
    TieredRecommendationResult,
    TieredFoodRecommendation,
    FoodTier,
)


def get_custom_css() -> str:
    """Returns ultra-modern glassmorphic design system CSS."""
    return """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Glassmorphism Container */
    .glass-card {
        background: rgba(255, 255, 255, 0.04);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.15);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .glass-card:hover {
        border-color: rgba(255, 255, 255, 0.22);
    }

    /* Hero Header */
    .hero-container {
        text-align: center;
        padding: 20px 0 30px 0;
    }
    .hero-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #10B981 0%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
    }
    .hero-subtitle {
        font-size: 1.1rem;
        opacity: 0.85;
        max-width: 650px;
        margin: 0 auto;
    }

    /* Stepper Navigation */
    .stepper-wrapper {
        display: flex;
        justify-content: center;
        gap: 16px;
        margin-bottom: 28px;
    }
    .step-badge {
        padding: 10px 20px;
        border-radius: 30px;
        font-weight: 600;
        font-size: 0.95rem;
        display: flex;
        align-items: center;
        gap: 8px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        background: rgba(255, 255, 255, 0.03);
        opacity: 0.6;
    }
    .step-active {
        opacity: 1.0;
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(59, 130, 246, 0.2) 100%);
        border: 1.5px solid #10B981;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.3);
    }

    /* Modern 3-Tier Food Cards */
    .card-good {
        background: linear-gradient(145deg, rgba(22, 163, 74, 0.08) 0%, rgba(16, 185, 129, 0.03) 100%);
        border: 1.5px solid #22C55E;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(34, 197, 94, 0.08);
    }
    .card-medium {
        background: linear-gradient(145deg, rgba(234, 179, 8, 0.08) 0%, rgba(202, 138, 4, 0.03) 100%);
        border: 1.5px solid #EAB308;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(234, 179, 8, 0.08);
    }
    .card-bad {
        background: linear-gradient(145deg, rgba(239, 68, 68, 0.08) 0%, rgba(220, 38, 38, 0.03) 100%);
        border: 1.5px solid #EF4444;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(239, 68, 68, 0.08);
    }

    /* Score Badges */
    .badge-score-good {
        background: #16A34A;
        color: white;
        font-weight: 700;
        font-size: 0.85rem;
        padding: 4px 12px;
        border-radius: 20px;
        float: right;
    }
    .badge-score-medium {
        background: #CA8A04;
        color: white;
        font-weight: 700;
        font-size: 0.85rem;
        padding: 4px 12px;
        border-radius: 20px;
        float: right;
    }
    .badge-score-bad {
        background: #DC2626;
        color: white;
        font-weight: 700;
        font-size: 0.85rem;
        padding: 4px 12px;
        border-radius: 20px;
        float: right;
    }

    /* Feature Chips */
    .chip-green {
        display: inline-block;
        background: rgba(34, 197, 94, 0.15);
        color: #4ADE80;
        border: 1px solid rgba(34, 197, 94, 0.3);
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.82rem;
        font-weight: 500;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .chip-red {
        display: inline-block;
        background: rgba(239, 68, 68, 0.15);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.82rem;
        font-weight: 500;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .chip-allergy {
        display: inline-block;
        background: #DC2626;
        color: white;
        padding: 4px 12px;
        border-radius: 14px;
        font-size: 0.85rem;
        font-weight: 700;
        margin-bottom: 8px;
        letter-spacing: 0.3px;
    }

    /* Tip callout */
    .tip-box {
        background: rgba(255, 255, 255, 0.05);
        border-left: 3px solid #10B981;
        padding: 8px 14px;
        border-radius: 0 8px 8px 0;
        font-size: 0.88rem;
        margin-top: 10px;
    }

    /* KPI Highlights */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 24px;
    }
    .kpi-box {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 16px;
        text-align: center;
    }
    .kpi-val {
        font-size: 1.8rem;
        font-weight: 800;
        margin-bottom: 4px;
    }
</style>
"""


def render_stepper(current_step: int):
    """Renders 3-step progress navigation wizard."""
    step1_cls = "step-badge step-active" if current_step == 1 else "step-badge"
    step2_cls = "step-badge step-active" if current_step == 2 else "step-badge"
    step3_cls = "step-badge step-active" if current_step == 3 else "step-badge"

    st.markdown(
        f"""
        <div class="stepper-wrapper">
            <div class="{step1_cls}"><span>1</span> 📷 Upload Menu</div>
            <div class="{step2_cls}"><span>2</span> 👤 Health Profile & Matrix</div>
            <div class="{step3_cls}"><span>3</span> 🍽️ 3-Tier Recommendations</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_medical_disclaimer():
    """Renders non-alarmist, professional nutritional guidance disclaimer."""
    st.caption(
        "ℹ️ **Nutritional Guidance Notice**: Recommendations are personalized computational estimates based on user-entered parameters and clinical nutritional references. This tool does not provide medical diagnoses or medical prescriptions. Consult a licensed dietitian for medical diet plans."
    )


def render_step1_menu_upload(ocr_pipeline_fn) -> Tuple[List[Dict[str, Any]], str, bool]:
    """
    Step 1: Upload Menu Image or Manual Dish Input.
    Returns: (dishes_to_evaluate, source_id, can_proceed)
    """
    st.markdown(
        """
        <div class="hero-container">
            <div class="hero-title">🥗 NutriMenu AI: Visual Menu Scanner</div>
            <div class="hero-subtitle">Upload any restaurant menu photo to extract food items with deep learning OCR, then match them to your personal nutritional matrix.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_upload, tab_manual = st.tabs([
        "📷 Upload Menu Photo (Deep OCR)",
        "✍️ Manual Dish Input",
    ])

    dishes: List[Dict[str, Any]] = []
    source_id = "none"
    can_proceed = False

    with tab_upload:
        uploaded_file = st.file_uploader(
            "Upload a menu photo or scan (PNG, JPG, JPEG):",
            type=["png", "jpg", "jpeg"],
            key="menu_file_uploader",
        )

        if uploaded_file is not None:
            col_img, col_info = st.columns([1, 1])
            uploaded_bytes = uploaded_file.getvalue()
            image = Image.open(io.BytesIO(uploaded_bytes))

            with col_img:
                st.image(image, caption="Uploaded Menu Image", use_container_width=True)

            with col_info:
                st.markdown("#### 🔍 OCR Recognition Pipeline")
                st.write("Extracts dish names, prices, categories, and filters out noise automatically.")
                
                extract_btn = st.button("🚀 Run Deep OCR Extraction", type="primary", use_container_width=True, key="btn_run_step1_ocr")
                
                current_file_key = f"{uploaded_file.name}_{uploaded_file.size}"
                if extract_btn or ("ocr_file_key" not in st.session_state or st.session_state["ocr_file_key"] != current_file_key):
                    with st.spinner("Processing image and filtering noise..."):
                        pipeline = ocr_pipeline_fn()
                        recognized_menu: RecognizedMenu = pipeline.process_image(image)
                        extracted = []
                        for itm in recognized_menu.to_flat_items():
                            extracted.append({
                                "name": itm.name,
                                "description": itm.description or "",
                                "price": itm.raw_price or (f"${itm.price:.2f}" if itm.price else ""),
                                "tags": itm.dietary_tags or [],
                            })
                        st.session_state["ocr_file_key"] = current_file_key
                        st.session_state["ocr_dishes"] = extracted
                        st.session_state["ocr_menu_obj"] = recognized_menu

                if "ocr_dishes" in st.session_state and st.session_state["ocr_dishes"]:
                    st.success(f"✨ Found **{len(st.session_state['ocr_dishes'])}** dishes from your menu:")
                    st.dataframe(st.session_state["ocr_dishes"], use_container_width=True, hide_index=True)
                    dishes = st.session_state["ocr_dishes"]
                    source_id = f"ocr_{uploaded_file.name}_{len(dishes)}"
                    can_proceed = len(dishes) > 0

    with tab_manual:
        st.write("Type or paste dishes manually (format: `Dish Name | Description | Price`):")
        manual_text = st.text_area(
            "Manual Dishes",
            value="Steamed Edamame | Fresh steamed soybeans with sea salt | $5.99\nCrispy Deep Fried Mozzarella Sticks | Breaded cheese sticks fried with marinara | $7.99\nGrilled Lemon Chicken | Grilled herb chicken breast with roasted broccoli | $14.50\nPalak Paneer with Whole Wheat Roti | Fresh spinach puree with cottage cheese | $13.50",
            height=130,
            key="step1_manual_text",
            label_visibility="collapsed",
        )
        if manual_text and manual_text.strip():
            manual_dishes = []
            for line in manual_text.strip().split("\n"):
                line_clean = line.strip()
                if not line_clean:
                    continue
                parts = [p.strip() for p in line_clean.split("|")]
                if parts and parts[0]:
                    manual_dishes.append({
                        "name": parts[0],
                        "description": parts[1] if len(parts) > 1 else "",
                        "price": parts[2] if len(parts) > 2 else "",
                        "tags": []
                    })
            if uploaded_file is None or st.checkbox("Use manual dishes instead of image", key="check_use_manual_step1"):
                dishes = manual_dishes
                source_id = f"manual_{len(manual_dishes)}"
                can_proceed = len(dishes) > 0
                st.dataframe(dishes, use_container_width=True, hide_index=True)

    return dishes, source_id, can_proceed


def render_step2_health_matrix(matrix_generator_fn) -> Tuple[UserNutritionalMatrix, bool]:
    """
    Step 2: Dedicated Health Profile & Live Nutritional Matrix Studio.
    Returns: (user_matrix, can_proceed)
    """
    st.markdown(
        """
        <div class="hero-container">
            <div class="hero-title">👤 User Health Profile & Matrix Studio</div>
            <div class="hero-subtitle">Configure your biometrics, clinical conditions, and strict allergens to synthesize a personalized computational health matrix.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_input, col_matrix = st.columns([1.1, 1.3], gap="large")

    with col_input:
        st.markdown("### 📋 1. Biometrics & Lifestyle")
        
        with st.expander("📝 Optional Natural Language Intake", expanded=False):
            bio_text = st.text_area(
                "Bio Description",
                placeholder="e.g. 45yo male, 176cm, 86kg, sedentary, looking for fat loss. Has hypertension, diabetes, and peanut allergy. Strictly vegetarian.",
                height=80,
                key="step2_bio_text",
            )

        c_age, c_gen = st.columns(2)
        with c_age:
            age = st.number_input("Age", min_value=10, max_value=120, value=45, step=1, key="step2_age")
            height_cm = st.number_input("Height (cm)", min_value=80, max_value=250, value=176, step=1, key="step2_height")
        with c_gen:
            gender = st.selectbox("Gender", options=["male", "female", "other"], index=0, key="step2_gender")
            weight_kg = st.number_input("Weight (kg)", min_value=25.0, max_value=300.0, value=86.0, step=0.5, key="step2_weight")

        activity = st.selectbox(
            "Physical Activity Level",
            options=["sedentary", "light", "moderate", "heavy", "athlete"],
            index=1,
            key="step2_activity",
        )

        primary_goal = st.selectbox(
            "Primary Metabolic Goal",
            options=["fat_loss", "muscle_gain", "maintenance", "endurance", "healthy_aging"],
            index=0,
            key="step2_goal",
        )

        st.markdown("### 🩺 2. Clinical Conditions & Guardrails")
        health_conditions = st.multiselect(
            "Medical Conditions",
            options=["hypertension", "type_2_diabetes", "pre_diabetes", "gerd", "hyperlipidemia", "pcos", "fatty_liver", "kidney_disease"],
            default=["hypertension", "type_2_diabetes", "gerd"],
            key="step2_conditions",
        )

        dietary_prefs = st.multiselect(
            "Dietary Restrictions",
            options=["vegetarian", "vegan", "pescatarian", "halal", "kosher", "keto", "low_carb"],
            default=["vegetarian"],
            key="step2_diets",
        )

        allergies = st.multiselect(
            "Strict Allergies (Zero-Tolerance Hard Exclusions)",
            options=["peanuts", "tree_nuts", "dairy", "gluten", "shellfish", "eggs", "soy", "sesame"],
            default=["peanuts"],
            key="step2_allergies",
        )

        user_payload = {
            "age": int(age),
            "gender": str(gender),
            "height_cm": float(height_cm),
            "weight_kg": float(weight_kg),
            "activity_level": str(activity),
            "primary_goal": str(primary_goal),
            "health_conditions": health_conditions,
            "allergies": allergies,
            "dietary_preferences": dietary_prefs,
        }
        if bio_text and bio_text.strip():
            user_payload["raw_bio_text"] = bio_text.strip()

    # Dynamic Matrix Computation
    generator: AIMatrixGenerator = matrix_generator_fn()
    user_matrix = generator.generate(user_payload, user_id="active_user")

    with col_matrix:
        st.markdown("### 📊 3. Live Nutritional Matrix & Guardrails")
        
        m = user_matrix.metabolic_targets
        w = user_matrix.clinical_risk_weights
        g = user_matrix.nutritional_guardrails

        # Energy & Macros Card
        st.markdown(
            f"""
            <div class="glass-card">
                <h4>⚡ Daily Energy & Macro Split Target</h4>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div>
                        <span style="font-size:1.8rem; font-weight:800; color:#10B981;">{m.target_calories_kcal:.0f}</span>
                        <span style="opacity:0.8;"> kcal/day</span>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-weight:600;">{m.caloric_adjustment_ratio:+.0%} Deficit</span><br>
                        <small style="opacity:0.7;">BMR: {m.bmr_kcal:.0f} | TDEE: {m.tdee_kcal:.0f}</small>
                    </div>
                </div>
                <div style="margin-bottom:8px;">
                    <div style="display:flex; justify-content:space-between; font-size:0.85rem; font-weight:600;">
                        <span>🥩 Protein: {m.target_protein_g:.0f}g ({m.target_protein_pct:.0f}%)</span>
                        <span>🌾 Carbs: {m.target_carbs_g:.0f}g ({m.target_carbs_pct:.0f}%)</span>
                        <span>🥑 Fats: {m.target_fats_g:.0f}g ({m.target_fats_pct:.0f}%)</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Clinical Boundaries Card
        glycemic_label = "High Risk / Low-GI Required" if w.glycemic_sensitivity > 0.6 else "Standard Tolerance"
        sodium_label = f"< {g.sodium_ceiling_mg} mg/day (Strict)" if g.sodium_ceiling_mg <= 1800 else f"< {g.sodium_ceiling_mg} mg/day"

        st.markdown(
            f"""
            <div class="glass-card">
                <h4>🛡️ Clinical Guardrails & Risk Weights</h4>
                <p><b>🩺 Clinical Summary:</b> <i>{user_matrix.user_summary}</i></p>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px;">
                    <div style="background:rgba(255,255,255,0.03); padding:10px; border-radius:10px;">
                        <small style="opacity:0.8;">Sodium Ceiling</small><br>
                        <b style="color:#38BDF8;">{sodium_label}</b>
                    </div>
                    <div style="background:rgba(255,255,255,0.03); padding:10px; border-radius:10px;">
                        <small style="opacity:0.8;">Glycemic Sensitivity</small><br>
                        <b style="color:#FBBF24;">{glycemic_label} ({w.glycemic_sensitivity:.2f})</b>
                    </div>
                    <div style="background:rgba(255,255,255,0.03); padding:10px; border-radius:10px;">
                        <small style="opacity:0.8;">Saturated Fat Max</small><br>
                        <b style="color:#F87171;">&lt; {g.saturated_fat_max_pct*100:.0f}% Total Kcal</b>
                    </div>
                    <div style="background:rgba(255,255,255,0.03); padding:10px; border-radius:10px;">
                        <small style="opacity:0.8;">Min Dietary Fiber</small><br>
                        <b style="color:#4ADE80;">&gt; {g.dietary_fiber_min_g:.0f} g/day</b>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Strict Exclusion Mask
        if user_matrix.exclusion_mask:
            st.markdown(
                f"""
                <div class="glass-card" style="border-left: 4px solid #DC2626;">
                    <h4>⛔ Strict Exclusion Mask (Score = 0 Authority)</h4>
                    <p style="margin-bottom:0;"><code>{', '.join(user_matrix.exclusion_mask)}</code></p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    return user_matrix, True


def render_step3_recommendations(result: TieredRecommendationResult):
    """
    Step 3: Beautified 3-Tier Food Recommendation Dashboard.
    """
    st.markdown(
        """
        <div class="hero-container">
            <div class="hero-title">🍽️ 3-Tier Food Recommendation Dashboard</div>
            <div class="hero-subtitle">Dishes ranked and classified according to your personalized biometric health matrix.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    counts = result.tier_counts

    # KPI Summary Cards
    st.markdown(
        f"""
        <div class="kpi-container">
            <div class="kpi-box">
                <div class="kpi-val" style="color:#94A3B8;">{result.total_items_evaluated}</div>
                <small>Total Evaluated</small>
            </div>
            <div class="kpi-box">
                <div class="kpi-val" style="color:#22C55E;">{counts['GOOD']}</div>
                <small>🟢 Tier 1: GOOD</small>
            </div>
            <div class="kpi-box">
                <div class="kpi-val" style="color:#EAB308;">{counts['MEDIUM']}</div>
                <small>🟡 Tier 2: MEDIUM</small>
            </div>
            <div class="kpi-box">
                <div class="kpi-val" style="color:#EF4444;">{counts['BAD']}</div>
                <small>🔴 Tier 3: BAD</small>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Top Pick Spotlight
    if result.top_pick and result.top_pick.tier == FoodTier.GOOD:
        p = result.top_pick
        price_txt = f" • {p.price}" if p.price else ""
        st.markdown(
            f"""
            <div class="glass-card" style="border: 2px solid #10B981; background: linear-gradient(145deg, rgba(16, 185, 129, 0.12) 0%, rgba(59, 130, 246, 0.05) 100%);">
                <h3 style="margin-top:0; color:#10B981;">🌟 Top Recommendation Pick: {p.dish_name} <span class="badge-score-good">{p.fit_score}/100</span></h3>
                <p style="font-size:1.05rem;">{price_txt} <i>{p.summary_reason}</i></p>
                {'<div>' + ''.join(f'<span class="chip-green">🌿 {g}</span>' for g in p.green_flags) + '</div>' if p.green_flags else ''}
                {f'<div class="tip-box">💡 <b>Chef Customization:</b> {p.customization_tips}</div>' if p.customization_tips else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Interactive Search & Filter
    search_q = st.text_input("🔍 Search evaluated dishes:", placeholder="Filter by dish name or ingredient...", key="search_dishes_q")
    
    tier_tab_all, tier_tab_good, tier_tab_medium, tier_tab_bad, tier_tab_table = st.tabs([
        f"📋 All Items ({result.total_items_evaluated})",
        f"🟢 Tier 1: GOOD ({counts['GOOD']})",
        f"🟡 Tier 2: MEDIUM ({counts['MEDIUM']})",
        f"🔴 Tier 3: BAD ({counts['BAD']})",
        "📊 Detailed Table",
    ])

    def matches_search(rec: TieredFoodRecommendation) -> bool:
        if not search_q or not search_q.strip():
            return True
        q = search_q.lower().strip()
        return q in rec.dish_name.lower() or any(q in g.lower() for g in rec.matched_food_groups) or (rec.summary_reason and q in rec.summary_reason.lower())

    with tier_tab_all:
        for item in result.all_recommendations:
            if not matches_search(item):
                continue
            _render_single_dish_card(item)

    with tier_tab_good:
        good_filtered = [i for i in result.good_items if matches_search(i)]
        if good_filtered:
            for item in good_filtered:
                _render_single_dish_card(item)
        else:
            st.info("No items in Tier 1 matching current filters.")

    with tier_tab_medium:
        med_filtered = [i for i in result.medium_items if matches_search(i)]
        if med_filtered:
            for item in med_filtered:
                _render_single_dish_card(item)
        else:
            st.info("No items in Tier 2 matching current filters.")

    with tier_tab_bad:
        bad_filtered = [i for i in result.bad_items if matches_search(i)]
        if bad_filtered:
            for item in bad_filtered:
                _render_single_dish_card(item)
        else:
            st.info("No items in Tier 3 matching current filters.")

    with tier_tab_table:
        table_rows = []
        for item in result.all_recommendations:
            table_rows.append({
                "Tier": item.tier_badge,
                "Dish Name": item.dish_name,
                "Fit Score": item.fit_score,
                "Price": item.price or "-",
                "Summary": item.summary_reason,
                "Warnings / Flags": "; ".join(item.allergen_warnings or item.red_flags),
                "Customization Tip": item.customization_tips or "-",
            })
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

    # Export Section
    st.markdown("---")
    st.markdown("#### 📥 Export Personalized Recommendation Report")
    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        st.download_button(
            label="📥 Download Markdown Summary (.md)",
            data=result.to_markdown(),
            file_name="nutrimenu_recommendations.md",
            mime="text/markdown",
            use_container_width=True,
            key="btn_download_step3_md",
        )
    with exp_col2:
        st.download_button(
            label="📥 Download Structured JSON Data (.json)",
            data=result.to_json(indent=2),
            file_name="nutrimenu_recommendations.json",
            mime="application/json",
            use_container_width=True,
            key="btn_download_step3_json",
        )


def _render_single_dish_card(item: TieredFoodRecommendation):
    """Renders a modern, visually appealing card for an individual dish recommendation."""
    price_str = f" • <span style='opacity:0.8;'>{item.price}</span>" if item.price else ""
    
    if item.tier == FoodTier.GOOD:
        card_class = "card-good"
        score_badge = f'<span class="badge-score-good">Fit: {item.fit_score}/100</span>'
        icon = "🥗"
    elif item.tier == FoodTier.MEDIUM:
        card_class = "card-medium"
        score_badge = f'<span class="badge-score-medium">Fit: {item.fit_score}/100</span>'
        icon = "🍲"
    else:
        card_class = "card-bad"
        score_badge = f'<span class="badge-score-bad">Fit: {item.fit_score}/100</span>'
        icon = "🚫"

    allergy_html = ""
    if item.allergen_warnings:
        allergy_html = f'<div class="chip-allergy">⛔ ALLERGEN / DIET CONFLICT: {"; ".join(item.allergen_warnings)}</div>'

    greens_html = "".join(f'<span class="chip-green">🌿 {g}</span>' for g in item.green_flags)
    reds_html = "".join(f'<span class="chip-red">⚠️ {r}</span>' for r in item.red_flags)
    tip_html = f'<div class="tip-box">💡 <b>Customization Advice:</b> {item.customization_tips}</div>' if item.customization_tips else ""

    st.markdown(
        f"""
        <div class="{card_class}">
            {score_badge}
            <h4 style="margin:0 0 6px 0;">{icon} {item.dish_name}{price_str}</h4>
            <p style="margin:0 0 10px 0; font-size:0.92rem; opacity:0.9;"><i>{item.summary_reason}</i></p>
            {allergy_html}
            <div>{greens_html}{reds_html}</div>
            {tip_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
