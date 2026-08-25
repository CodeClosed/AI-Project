"""
Streamlit Web Application for NutriMenu AI.
Features a modern 3-Step Guided Wizard:
- Step 1: 📷 Upload & Scan Restaurant Menu (Deep OCR)
- Step 2: 👤 User Health Profile & Live Nutritional Matrix Studio
- Step 3: 🍽️ Beautified 3-Tier Food Matchmaker Dashboard
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

import streamlit as st

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.matrix_generator import AIMatrixGenerator, UserNutritionalMatrix
from src.pipeline import MenuRecognitionPipeline
from src.recommendation_engine import (
    TieredFoodRecommender,
    TieredRecommendationResult,
)
from src.config import DEFAULT_GOOD_THRESHOLD, DEFAULT_BAD_THRESHOLD
from src.ui_components import (
    get_custom_css,
    render_stepper,
    render_step1_menu_upload,
    render_step2_health_matrix,
    render_step3_recommendations,
    render_medical_disclaimer,
)


# --- Page Configuration ---
st.set_page_config(
    page_title="NutriMenu AI | Personalized Food Recommender",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Apply Ultra-Modern Design System CSS
st.markdown(get_custom_css(), unsafe_allow_html=True)


# --- Cached Engine Singletons ---
@st.cache_resource
def get_matrix_generator():
    return AIMatrixGenerator()


@st.cache_resource
def get_ocr_pipeline():
    return MenuRecognitionPipeline()


# --- Session State Initialization ---
if "wizard_step" not in st.session_state:
    st.session_state["wizard_step"] = 1

if "dishes_to_evaluate" not in st.session_state:
    st.session_state["dishes_to_evaluate"] = []

if "user_matrix" not in st.session_state:
    st.session_state["user_matrix"] = None

if "eval_result" not in st.session_state:
    st.session_state["eval_result"] = None


# --- Navigation Stepper Bar ---
current_step = st.session_state["wizard_step"]
render_stepper(current_step)


# =========================================================================
# STEP 1: Upload & Scan Menu
# =========================================================================
if current_step == 1:
    dishes, source_id, can_proceed = render_step1_menu_upload(get_ocr_pipeline)
    
    if dishes:
        st.session_state["dishes_to_evaluate"] = dishes

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button(
            "➡️ Next: Configure Health Matrix & Biometrics",
            type="primary",
            use_container_width=True,
            disabled=not (bool(st.session_state["dishes_to_evaluate"])),
            key="btn_next_to_step2",
        ):
            st.session_state["wizard_step"] = 2
            st.rerun()


# =========================================================================
# STEP 2: Health Profile & Nutritional Matrix Studio
# =========================================================================
elif current_step == 2:
    user_matrix, can_proceed_matrix = render_step2_health_matrix(get_matrix_generator)
    st.session_state["user_matrix"] = user_matrix

    st.markdown("<br>", unsafe_allow_html=True)
    nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 2])
    with nav_col1:
        if st.button("⬅️ Back to Menu", use_container_width=True, key="btn_back_to_step1"):
            st.session_state["wizard_step"] = 1
            st.rerun()

    with nav_col3:
        if st.button(
            "🚀 Run 3-Tier Matchmaker & Generate Recommendations ➔",
            type="primary",
            use_container_width=True,
            key="btn_run_step3_eval",
        ):
            with st.spinner("Analyzing menu items against metabolic targets and clinical guardrails..."):
                recommender = TieredFoodRecommender(
                    user_matrix=user_matrix,
                    good_threshold=DEFAULT_GOOD_THRESHOLD,
                    bad_threshold=DEFAULT_BAD_THRESHOLD,
                )
                eval_result = recommender.recommend_menu(st.session_state["dishes_to_evaluate"])
                st.session_state["eval_result"] = eval_result
                st.session_state["wizard_step"] = 3
                st.rerun()


# =========================================================================
# STEP 3: 3-Tier Recommendations Dashboard
# =========================================================================
elif current_step == 3:
    eval_result: Optional[TieredRecommendationResult] = st.session_state.get("eval_result")
    
    if eval_result:
        render_step3_recommendations(eval_result)
    else:
        st.warning("No recommendation results available. Please run evaluation from Step 2.")

    st.markdown("<br>", unsafe_allow_html=True)
    c_back1, c_back2, c_spacer = st.columns([1, 1, 2])
    with c_back1:
        if st.button("⬅️ Edit Health Matrix", use_container_width=True, key="btn_back_step2_from_step3"):
            st.session_state["wizard_step"] = 2
            st.rerun()
    with c_back2:
        if st.button("🔄 Scan Another Menu", use_container_width=True, key="btn_restart_wizard"):
            st.session_state["wizard_step"] = 1
            st.session_state["dishes_to_evaluate"] = []
            st.session_state["eval_result"] = None
            st.rerun()


# --- Global Medical Notice Footer ---
st.markdown("---")
render_medical_disclaimer()
