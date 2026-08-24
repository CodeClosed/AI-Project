"""
Streamlit Web UI for the AI Menu Item Recognition & 3-Tier Nutrition Recommendation System.
Integrates:
- Model 1: Menu Image OCR & Food Item Extraction
- Model 2: Personalized User Health & Nutritional Matrix Generator
- Model 3: 3-Tier Food Recommendation Engine (🟢 GOOD, 🟡 MEDIUM, 🔴 BAD)
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional

import streamlit as st
import numpy as np
import cv2
from PIL import Image

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.models import MenuItem, MenuSection, RecognizedMenu
from src.matrix_generator import AIMatrixGenerator, UserNutritionalMatrix
from src.pipeline import MenuRecognitionPipeline
from src.recommendation_engine import (
    TieredFoodRecommender,
    TieredRecommendationResult,
    TieredFoodRecommendation,
    FoodTier,
)


# --- Page Configuration ---
st.set_page_config(
    page_title="NutriMenu AI | 3-Tier Food Recommender",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .tier-card-good {
        background: #F0FDF4;
        border: 1.5px solid #86EFAC;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 14px;
    }
    .tier-card-medium {
        background: #FEFCE8;
        border: 1.5px solid #FDE047;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 14px;
    }
    .tier-card-bad {
        background: #FEF2F2;
        border: 1.5px solid #FCA5A5;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 14px;
    }
    .kpi-good {
        font-size: 1.6rem;
        font-weight: bold;
        color: #16A34A;
    }
    .kpi-medium {
        font-size: 1.6rem;
        font-weight: bold;
        color: #CA8A04;
    }
    .kpi-bad {
        font-size: 1.6rem;
        font-weight: bold;
        color: #DC2626;
    }
    .badge-pill {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.82rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# --- Helper Functions ---
@st.cache_resource
def get_matrix_generator():
    return AIMatrixGenerator()


@st.cache_resource
def get_ocr_pipeline():
    return MenuRecognitionPipeline()


# --- Sample Menus Pre-population ---
SAMPLE_MENUS = {
    "Indian Specialties Menu": [
        {"name": "Palak Paneer with Multigrain Roti", "description": "Fresh spinach puree with cottage cheese and whole wheat flatbread", "price": "$13.50", "tags": ["vegetarian"]},
        {"name": "Steamed Sprouted Moong Salad", "description": "Sprouted green lentils, cucumber, tomatoes, lemon and olive oil", "price": "$8.99", "tags": ["vegetarian", "vegan"]},
        {"name": "Tandoori Vegetable Medley", "description": "Char-grilled bell peppers, broccoli, zucchini, and mushrooms", "price": "$11.99", "tags": ["vegetarian"]},
        {"name": "Dal Makhani with Butter Naan", "description": "Black lentils slow cooked in butter and cream with refined maida naan", "price": "$14.00", "tags": ["vegetarian"]},
        {"name": "Vegetable Biryani with Cucumber Raita", "description": "Basmati rice cooked with mixed vegetables and spices with curd dip", "price": "$12.50", "tags": ["vegetarian"]},
        {"name": "Crispy Peanut Pakora Chaat", "description": "Deep-fried gram flour fritters tossed with roasted peanuts and tamarind sauce", "price": "$7.50", "tags": ["vegetarian"]},
        {"name": "Butter Chicken Makhani", "description": "Tender chicken tikka simmered in rich cashew and butter gravy", "price": "$16.99", "tags": ["non-vegetarian"]},
        {"name": "Gulab Jamun with Rabri", "description": "Fried condensed milk balls soaked in sugar syrup with thickened sweet milk", "price": "$6.00", "tags": ["dessert", "vegetarian"]},
    ],
    "Mediterranean & Cafe Menu": [
        {"name": "Grilled Salmon with Steamed Asparagus", "description": "Wild-caught salmon filet with lemon herb drizzle and asparagus", "price": "$18.50", "tags": ["pescatarian", "gluten-free"]},
        {"name": "Greek Quinoa Salad Bowl", "description": "Quinoa, kalamata olives, cucumber, cherry tomatoes, and light feta", "price": "$12.00", "tags": ["vegetarian", "gluten-free"]},
        {"name": "Crispy Deep-Fried Calamari", "description": "Battered squid rings fried golden with garlic mayo dip", "price": "$11.50", "tags": ["pescatarian"]},
        {"name": "Hummus & Tabbouleh Platter", "description": "Chickpea dip with parsley bulgur salad and whole wheat pita", "price": "$10.50", "tags": ["vegan"]},
        {"name": "Loaded Bacon Cheeseburger with Fries", "description": "Beef patty topped with cheddar, smoked bacon, mayo and french fries", "price": "$15.99", "tags": ["non-vegetarian"]},
        {"name": "Chocolate Lava Cake", "description": "Molten dark chocolate cake with vanilla ice cream", "price": "$7.50", "tags": ["dessert"]},
    ]
}


# --- SIDEBAR: User Health Matrix (Model 2) ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/salad.png", width=64)
    st.markdown("## 👤 User Health Profile (Model 2)")
    st.caption("Configures biometrics, metabolic targets, and medical guardrails.")

    with st.expander("📝 Quick Bio / Natural Language Intake", expanded=False):
        bio_text = st.text_area(
            "Natural Language Bio",
            placeholder="e.g. 45yo male, 176cm, 86kg, sedentary, looking for fat loss. Has hypertension, diabetes, and peanut allergy. Strictly vegetarian.",
            height=90,
        )

    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Age", min_value=12, max_value=100, value=45, step=1)
        height_cm = st.number_input("Height (cm)", min_value=100, max_value=230, value=176, step=1)
    with col2:
        gender = st.selectbox("Gender", options=["male", "female", "other"], index=0)
        weight_kg = st.number_input("Weight (kg)", min_value=30.0, max_value=200.0, value=86.0, step=0.5)

    activity = st.selectbox(
        "Activity Level",
        options=["sedentary", "light", "moderate", "heavy", "athlete"],
        index=1,
        help="Sedentary (desk job) to Athlete (intense daily training)",
    )

    primary_goal = st.selectbox(
        "Primary Goal",
        options=["fat_loss", "muscle_gain", "maintenance", "endurance", "healthy_aging"],
        index=0,
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
    )

    dietary_prefs = st.multiselect(
        "Dietary Preferences",
        options=["vegetarian", "vegan", "pescatarian", "halal", "kosher", "keto", "low_carb"],
        default=["vegetarian"],
    )

    allergies = st.multiselect(
        "Strict Allergies",
        options=["peanuts", "tree_nuts", "dairy", "gluten", "shellfish", "eggs", "soy", "sesame"],
        default=["peanuts"],
    )

    gen_matrix_btn = st.button("🔄 Generate / Update Health Matrix", type="primary", use_container_width=True)

# Generate or retrieve user matrix in session state
if "user_matrix" not in st.session_state or gen_matrix_btn:
    user_payload = {
        "age": age,
        "gender": gender,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "activity_level": activity,
        "primary_goal": primary_goal,
        "health_conditions": health_conditions,
        "allergies": allergies,
        "dietary_preferences": dietary_prefs,
    }
    if bio_text and bio_text.strip():
        user_payload["raw_bio_text"] = bio_text.strip()

    with st.spinner("Calculating metabolic matrix & clinical guardrails..."):
        generator = get_matrix_generator()
        st.session_state["user_matrix"] = generator.generate(user_payload, user_id="active_user")


# Display User Matrix Summary Card
user_matrix: UserNutritionalMatrix = st.session_state["user_matrix"]

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


# --- MAIN CONTENT AREA ---
st.markdown('<div class="main-header">🥗 NutriMenu AI: 3-Tier Recommendation Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Bridges restaurant menu items with personalized clinical health matrices to classify dishes into 🟢 <b>Good</b>, 🟡 <b>Medium</b>, and 🔴 <b>Bad</b> tiers.</div>', unsafe_allow_html=True)

# Step 1: Input Food / Menu (Model 1)
st.markdown("### 1. Select or Upload Menu (Model 1)")

tab_sample, tab_upload, tab_manual = st.tabs(["📋 Preset Restaurant Menus", "📷 Upload Menu Image (OCR)", "✍️ Manual Dish Input"])

dishes_to_evaluate: List[Dict[str, Any]] = []

with tab_sample:
    selected_preset = st.selectbox("Choose a sample restaurant menu:", list(SAMPLE_MENUS.keys()))
    preset_dishes = SAMPLE_MENUS[selected_preset]
    st.write(f"Loaded **{len(preset_dishes)}** items from *{selected_preset}*:")
    
    # Display preview table
    preview_data = [{"Dish Name": d["name"], "Price": d.get("price", ""), "Description": d.get("description", "")} for d in preset_dishes]
    st.dataframe(preview_data, use_container_width=True, hide_index=True)
    dishes_to_evaluate = preset_dishes

with tab_upload:
    uploaded_file = st.file_uploader("Upload a menu photo or scan (PNG, JPG, JPEG):", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        col_img, col_ocr = st.columns([1, 1])
        with col_img:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Menu Image", use_container_width=True)

        with col_ocr:
            if st.button("🔍 Extract Dishes via Deep OCR Pipeline", use_container_width=True):
                with st.spinner("Extracting text and menu structure..."):
                    # Save to temp file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                        image.save(tmp.name)
                        tmp_path = tmp.name

                    pipeline = get_ocr_pipeline()
                    recognized_menu = pipeline.process_image(tmp_path)
                    
                    extracted_items = []
                    for itm in recognized_menu.to_flat_items():
                        extracted_items.append({
                            "name": itm.name,
                            "description": itm.description or "",
                            "price": itm.raw_price or (str(itm.price) if itm.price else ""),
                            "tags": itm.dietary_tags or [],
                        })
                    st.session_state["ocr_dishes"] = extracted_items
                    st.success(f"Successfully extracted {len(extracted_items)} dishes from image!")

        if "ocr_dishes" in st.session_state and st.session_state["ocr_dishes"]:
            st.dataframe(st.session_state["ocr_dishes"], use_container_width=True)
            dishes_to_evaluate = st.session_state["ocr_dishes"]

with tab_manual:
    manual_text = st.text_area(
        "Enter dishes (one per line, format: Dish Name | Description | Price):",
        value="Steamed Edamame | Fresh steamed soybeans with sea salt | $5.99\nCrispy Deep Fried Mozzarella Sticks | Breaded cheese sticks fried with marinara | $7.99\nGrilled Lemon Chicken | Grilled herb chicken breast with roasted broccoli | $14.50",
        height=120,
    )
    if manual_text:
        manual_dishes = []
        for line in manual_text.strip().split("\n"):
            parts = [p.strip() for p in line.split("|")]
            if parts and parts[0]:
                d = {"name": parts[0], "description": parts[1] if len(parts) > 1 else "", "price": parts[2] if len(parts) > 2 else ""}
                manual_dishes.append(d)
        if st.checkbox("Use manual input for evaluation"):
            dishes_to_evaluate = manual_dishes


# Step 2: Middle Model Evaluation
st.markdown("---")
st.markdown("### 2. Run 3-Tier Matchmaker (The Middle Model)")

eval_col1, eval_col2 = st.columns([2, 1])
with eval_col1:
    good_threshold = st.slider("Tier 1 (GOOD) Fit Score Threshold", min_value=60, max_value=90, value=75, step=5)
with eval_col2:
    bad_threshold = st.slider("Tier 3 (BAD) Fit Score Ceiling", min_value=30, max_value=60, value=45, step=5)

run_eval_btn = st.button("🚀 Evaluate Menu & Classify 3 Tiers", type="primary", use_container_width=True)

if run_eval_btn or "last_recommendation_result" in st.session_state:
    if run_eval_btn:
        if not dishes_to_evaluate:
            st.warning("Please select or upload dishes to evaluate.")
        else:
            with st.spinner("Analyzing food groups against health matrix..."):
                recommender = TieredFoodRecommender(
                    user_matrix=user_matrix,
                    good_threshold=good_threshold,
                    bad_threshold=bad_threshold,
                )
                eval_result = recommender.recommend_menu(dishes_to_evaluate)
                st.session_state["last_recommendation_result"] = eval_result

    result: Optional[TieredRecommendationResult] = st.session_state.get("last_recommendation_result")

    if result:
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
                        <p style="color:#334155; margin-bottom:8px;">{price_display} <i>{item.summary_reason}</i></p>
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
                        <p style="color:#334155; margin-bottom:8px;">{price_display} <i>{item.summary_reason}</i></p>
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
                        <p style="color:#334155; margin-bottom:8px;">{price_display} <i>{item.summary_reason}</i></p>
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
            )
        with exp_col2:
            st.download_button(
                label="📥 Download Structured JSON (.json)",
                data=result.to_json(indent=2),
                file_name="nutrimenu_recommendations.json",
                mime="application/json",
                use_container_width=True,
            )
