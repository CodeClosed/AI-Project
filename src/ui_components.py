"""
Modular UI Components for NutriMenu AI Streamlit Web App.
Renders sidebar profile controls, nutritional matrix cards, menu selectors,
3-tier recommendation dashboard, and medical disclaimers.
"""

from typing import Dict, Any, List, Tuple, Optional
import io
import json
from PIL import Image
import streamlit as st

from .models import RecognizedMenu
from .matrix_generator import UserNutritionalMatrix
from .recommendation_engine import (
    TieredRecommendationResult,
    TieredFoodRecommendation,
    FoodTier,
)


def render_medical_disclaimer():
    """Renders non-alarmist, professional nutritional guidance disclaimer."""
    st.caption(
        "ℹ️ **Nutritional Guidance Notice**: Recommendations are personalized computational estimates based on your entered dietary parameters and published nutritional literature. This tool does not provide medical diagnoses or healthcare prescriptions. Consult a qualified medical practitioner or registered dietitian for clinical dietary plans."
    )


def render_sidebar_profile() -> Tuple[Dict[str, Any], bool]:
    """
    Renders user health profile form in sidebar.
    Returns:
        user_payload: Dict of validated profile attributes.
        generate_clicked: bool indicating if user clicked the update button.
    """
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/salad.png", width=64)
        st.markdown("## 👤 User Health Profile (Model 2)")
        st.caption("Configures biometrics, metabolic targets, and medical guardrails.")

        with st.expander("📝 Quick Bio / Natural Language Intake", expanded=False):
            bio_text = st.text_area(
                "Natural Language Bio",
                placeholder="e.g. 45yo male, 176cm, 86kg, sedentary, looking for fat loss. Has hypertension, diabetes, and peanut allergy. Strictly vegetarian.",
                height=90,
                key="input_bio_text",
            )

        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age", min_value=10, max_value=120, value=45, step=1, key="input_age")
            height_cm = st.number_input("Height (cm)", min_value=80, max_value=250, value=176, step=1, key="input_height")
        with col2:
            gender = st.selectbox("Gender", options=["male", "female", "other"], index=0, key="input_gender")
            weight_kg = st.number_input("Weight (kg)", min_value=25.0, max_value=300.0, value=86.0, step=0.5, key="input_weight")

        activity = st.selectbox(
            "Activity Level",
            options=["sedentary", "light", "moderate", "heavy", "athlete"],
            index=1,
            help="Sedentary (desk job) to Athlete (intense daily training)",
            key="input_activity",
        )

        primary_goal = st.selectbox(
            "Primary Goal",
            options=["fat_loss", "muscle_gain", "maintenance", "endurance", "healthy_aging"],
            index=0,
            key="input_goal",
        )

        health_conditions = st.multiselect(
            "Medical Conditions",
            options=[
                "hypertension",
                "type_2_diabetes",
                "pre_diabetes",
                "gerd",
                "hyperlipidemia",
                "pcos",
                "fatty_liver",
                "kidney_disease",
            ],
            default=["hypertension", "type_2_diabetes", "gerd"],
            key="input_conditions",
        )

        dietary_prefs = st.multiselect(
            "Dietary Preferences",
            options=["vegetarian", "vegan", "pescatarian", "halal", "kosher", "keto", "low_carb"],
            default=["vegetarian"],
            key="input_diets",
        )

        allergies = st.multiselect(
            "Strict Allergies",
            options=["peanuts", "tree_nuts", "dairy", "gluten", "shellfish", "eggs", "soy", "sesame"],
            default=["peanuts"],
            key="input_allergies",
        )

        gen_matrix_btn = st.button("🔄 Generate / Update Health Matrix", type="primary", use_container_width=True)

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

        return user_payload, gen_matrix_btn


def render_user_matrix_card(user_matrix: UserNutritionalMatrix):
    """Renders active user matrix metrics and clinical guardrails summary."""
    with st.expander("📊 View Active User Nutritional Matrix & Clinical Guardrails", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        m = user_matrix.metabolic_targets
        g = user_matrix.nutritional_guardrails
        w = user_matrix.clinical_risk_weights

        c1.metric("Daily Calories", f"{m.target_calories_kcal:.0f} kcal", f"{m.caloric_adjustment_ratio:+.0%}")
        c2.metric("Target Protein", f"{m.target_protein_g:.0f} g", f"{m.target_protein_pct:.0f}% kcal")
        c3.metric("Sodium Ceiling", f"< {g.sodium_ceiling_mg} mg", "Guardrail")
        c4.metric("Glycemic Sensitivity", f"{w.glycemic_sensitivity:.2f} / 1.0", "High Risk" if w.glycemic_sensitivity > 0.6 else "Normal")

        st.markdown(f"**Clinical Summary**: *{user_matrix.user_summary}*")
        st.markdown(f"**Strict Exclusions**: `{', '.join(user_matrix.exclusion_mask) if user_matrix.exclusion_mask else 'None'}`")


def render_menu_input_section(ocr_pipeline_fn) -> Tuple[List[Dict[str, Any]], str]:
    """
    Renders menu input tabs starting with OCR Photo Upload, followed by Manual Dish Text.
    Preset section has been removed so upload is the default landing input.
    Returns:
        dishes_to_evaluate: List of dish dicts.
        menu_source_id: Unique string identifying the active input selection.
    """
    st.markdown("### 1. Upload or Enter Menu (Model 1)")
    tab_upload, tab_manual = st.tabs([
        "📷 Upload Menu Image (OCR)",
        "✍️ Manual Dish Input",
    ])

    dishes_to_evaluate: List[Dict[str, Any]] = []
    source_id = "none"

    with tab_upload:
        st.write("Upload a restaurant menu photo or scan (PNG, JPG, JPEG) to automatically extract dishes:")
        uploaded_file = st.file_uploader(
            "Choose a menu image file:",
            type=["png", "jpg", "jpeg"],
            key="menu_file_uploader",
            label_visibility="collapsed",
        )
        if uploaded_file is not None:
            col_img, col_ocr = st.columns([1, 1])
            try:
                uploaded_bytes = uploaded_file.getvalue()
                image = Image.open(io.BytesIO(uploaded_bytes))
                with col_img:
                    st.image(image, caption="Uploaded Menu Image", use_container_width=True)

                with col_ocr:
                    run_ocr_btn = st.button("🔍 Extract Dishes via Deep OCR Pipeline", type="primary", use_container_width=True, key="btn_run_ocr")
                    
                    # Auto-extract on upload if not already extracted for this file
                    current_file_key = f"{uploaded_file.name}_{uploaded_file.size}"
                    if run_ocr_btn or ("ocr_file_key" in st.session_state and st.session_state["ocr_file_key"] != current_file_key):
                        with st.spinner("Extracting text and menu structure with OCR..."):
                            pipeline = ocr_pipeline_fn()
                            recognized_menu: RecognizedMenu = pipeline.process_image(image)
                            
                            extracted_items = []
                            for itm in recognized_menu.to_flat_items():
                                extracted_items.append({
                                    "name": itm.name,
                                    "description": itm.description or "",
                                    "price": itm.raw_price or (str(itm.price) if itm.price else ""),
                                    "tags": itm.dietary_tags or [],
                                })
                            st.session_state["ocr_file_key"] = current_file_key
                            st.session_state["ocr_dishes"] = extracted_items
                            st.session_state["ocr_menu_obj"] = recognized_menu
                            st.success(f"Successfully extracted {len(extracted_items)} dishes from image!")

                if "ocr_dishes" in st.session_state and st.session_state["ocr_dishes"]:
                    st.markdown(f"**Extracted Dishes ({len(st.session_state['ocr_dishes'])} items):**")
                    st.dataframe(st.session_state["ocr_dishes"], use_container_width=True, hide_index=True)
                    dishes_to_evaluate = st.session_state["ocr_dishes"]
                    source_id = f"ocr_{uploaded_file.name}_{len(dishes_to_evaluate)}"
            except Exception as e:
                st.error(f"Failed to process image: {e}")
        else:
            st.info("👆 Please upload a menu image above to start.")

    with tab_manual:
        st.write("Or type dishes manually (format: `Dish Name | Description | Price`):")
        manual_text = st.text_area(
            "Enter dishes (one per line):",
            value="Steamed Edamame | Fresh steamed soybeans with sea salt | $5.99\nCrispy Deep Fried Mozzarella Sticks | Breaded cheese sticks fried with marinara | $7.99\nGrilled Lemon Chicken | Grilled herb chicken breast with roasted broccoli | $14.50\nPalak Paneer with Multigrain Roti | Fresh spinach puree with cottage cheese | $13.50",
            height=120,
            key="manual_dish_textarea",
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
                    d = {
                        "name": parts[0],
                        "description": parts[1] if len(parts) > 1 else "",
                        "price": parts[2] if len(parts) > 2 else "",
                        "tags": []
                    }
                    manual_dishes.append(d)
            if uploaded_file is None or st.checkbox("Use manual dish input instead of uploaded image", key="use_manual_check"):
                dishes_to_evaluate = manual_dishes
                source_id = f"manual_{len(manual_dishes)}"

    return dishes_to_evaluate, source_id


def render_recommendation_dashboard(result: TieredRecommendationResult):
    """Renders KPI metrics, top pick banner, 3-tier tabs, and download buttons."""
    st.markdown("---")
    st.markdown("### 📊 Recommendation Results")

    # KPI Summary Metrics
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Total Items Evaluated", result.total_items_evaluated)
    kpi2.markdown(f'<div class="kpi-good">🟢 {result.tier_counts["GOOD"]} Good</div><small>Optimal Health Fit</small>', unsafe_allow_html=True)
    kpi3.markdown(f'<div class="kpi-medium">🟡 {result.tier_counts["MEDIUM"]} Medium</div><small>Consume with Care</small>', unsafe_allow_html=True)
    kpi4.markdown(f'<div class="kpi-bad">🔴 {result.tier_counts["BAD"]} Bad</div><small>Avoid / High Risk</small>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Highlight Top Pick
    if result.top_pick and result.top_pick.tier == FoodTier.GOOD:
        st.info(f"🌟 **Top Recommendation**: **{result.top_pick.dish_name}** (Fit Score: `{result.top_pick.fit_score}/100`) — *{result.top_pick.summary_reason}*")

    # 3-Tier Categorized Display
    tier_tab_good, tier_tab_medium, tier_tab_bad, tier_tab_all = st.tabs([
        f"🟢 Tier 1: GOOD ({result.tier_counts['GOOD']})",
        f"🟡 Tier 2: MEDIUM ({result.tier_counts['MEDIUM']})",
        f"🔴 Tier 3: BAD ({result.tier_counts['BAD']})",
        "📋 Full Table View",
    ])

    with tier_tab_good:
        if result.good_items:
            for item in result.good_items:
                price_display = f" • **{item.price}**" if item.price else ""
                st.markdown(f"""
                <div class="tier-card-good">
                    <h4>🥗 {item.dish_name} <span style="float:right; color:#16A34A;">Fit Score: {item.fit_score}/100</span></h4>
                    <p style="margin-bottom:8px;">{price_display} <i>{item.summary_reason}</i></p>
                    {'<p><b>🌿 Green Flags:</b> ' + '; '.join(item.green_flags) + '</p>' if item.green_flags else ''}
                    {'<p><b>💡 Tip:</b> ' + item.customization_tips + '</p>' if item.customization_tips else ''}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No items qualified for Tier 1 based on current thresholds.")

    with tier_tab_medium:
        if result.medium_items:
            for item in result.medium_items:
                price_display = f" • **{item.price}**" if item.price else ""
                st.markdown(f"""
                <div class="tier-card-medium">
                    <h4>🍲 {item.dish_name} <span style="float:right; color:#CA8A04;">Fit Score: {item.fit_score}/100</span></h4>
                    <p style="margin-bottom:8px;">{price_display} <i>{item.summary_reason}</i></p>
                    {'<p><b>⚠️ Caution Areas:</b> ' + '; '.join(item.red_flags) + '</p>' if item.red_flags else ''}
                    {'<p><b>🛠️ How to Customize:</b> ' + item.customization_tips + '</p>' if item.customization_tips else ''}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No items in Tier 2.")

    with tier_tab_bad:
        if result.bad_items:
            for item in result.bad_items:
                price_display = f" • **{item.price}**" if item.price else ""
                warnings_html = ""
                if item.allergen_warnings:
                    warnings_html = f'<p style="color:#DC2626; font-weight:600;">⚠️ ALLERGEN / DIET CONFLICT: {"; ".join(item.allergen_warnings)}</p>'

                st.markdown(f"""
                <div class="tier-card-bad">
                    <h4>🚫 {item.dish_name} <span style="float:right; color:#DC2626;">Fit Score: {item.fit_score}/100</span></h4>
                    <p style="margin-bottom:8px;">{price_display} <i>{item.summary_reason}</i></p>
                    {warnings_html}
                    {'<p><b>⛔ Red Flags:</b> ' + '; '.join(item.red_flags) + '</p>' if item.red_flags else ''}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No items in Tier 3.")

    with tier_tab_all:
        table_rows = []
        for item in result.all_recommendations:
            table_rows.append({
                "Tier": item.tier_badge,
                "Dish Name": item.dish_name,
                "Fit Score": item.fit_score,
                "Price": item.price or "-",
                "Evaluation Summary": item.summary_reason,
                "Warnings / Caution": "; ".join(item.allergen_warnings or item.red_flags),
                "Customization Tip": item.customization_tips or "-",
            })
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

    # Export & Download Section
    st.markdown("---")
    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        st.download_button(
            label="📥 Download Markdown Report (.md)",
            data=result.to_markdown(),
            file_name="nutrimenu_recommendations.md",
            mime="text/markdown",
            use_container_width=True,
            key="btn_download_md",
        )
    with exp_col2:
        st.download_button(
            label="📥 Download Structured JSON (.json)",
            data=result.to_json(indent=2),
            file_name="nutrimenu_recommendations.json",
            mime="application/json",
            use_container_width=True,
            key="btn_download_json",
        )
