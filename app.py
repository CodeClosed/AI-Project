"""
Streamlit Web UI for the NutriMenu AI — 3-Tier Nutrition Recommendation System.
Integrates:
- Model 1: Menu Image OCR & Food Item Extraction
- Model 2: Personalized User Health & Nutritional Matrix Generator
- Model 3: 3-Tier Food Recommendation Engine (🟢 GOOD, 🟡 MEDIUM, 🔴 BAD)
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

import streamlit as st

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
from src.config import DEFAULT_GOOD_THRESHOLD, DEFAULT_BAD_THRESHOLD
from src.ui_components import (
    render_sidebar_profile,
    render_user_matrix_card,
    render_menu_input_section,
    render_recommendation_dashboard,
    render_medical_disclaimer,
)


# --- Page Configuration ---
st.set_page_config(
    page_title="NutriMenu AI | 3-Tier Food Recommender",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (adaptive for both Light and Dark Streamlit themes)
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        opacity: 0.85;
        margin-bottom: 1.5rem;
    }
    .tier-card-good {
        background: rgba(22, 163, 74, 0.08);
        border: 1.5px solid #16A34A;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 14px;
    }
    .tier-card-medium {
        background: rgba(202, 138, 4, 0.08);
        border: 1.5px solid #CA8A04;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 14px;
    }
    .tier-card-bad {
        background: rgba(220, 38, 38, 0.08);
        border: 1.5px solid #DC2626;
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
</style>
""", unsafe_allow_html=True)


# --- Cached Singletons ---
@st.cache_resource
def get_matrix_generator():
    return AIMatrixGenerator()


@st.cache_resource
def get_ocr_pipeline():
    return MenuRecognitionPipeline()


# --- SIDEBAR: User Health Matrix (Model 2) ---
user_payload, gen_matrix_btn = render_sidebar_profile()

# Profile state tracking: compute or refresh matrix when profile changes
profile_signature = str(user_payload)
if "last_profile_signature" not in st.session_state or st.session_state["last_profile_signature"] != profile_signature or gen_matrix_btn:
    st.session_state["last_profile_signature"] = profile_signature
    with st.spinner("Calculating metabolic matrix & clinical guardrails..."):
        try:
            generator = get_matrix_generator()
            st.session_state["user_matrix"] = generator.generate(user_payload, user_id="active_user")
            # Invalidate old recommendations on profile change
            if "last_recommendation_result" in st.session_state:
                del st.session_state["last_recommendation_result"]
        except Exception as e:
            st.error(f"Failed to generate user nutritional matrix: {e}")

user_matrix: Optional[UserNutritionalMatrix] = st.session_state.get("user_matrix")

# Display User Matrix Summary Card
if user_matrix:
    render_user_matrix_card(user_matrix)

# --- MAIN CONTENT AREA ---
st.markdown('<div class="main-header">🥗 NutriMenu AI: 3-Tier Recommendation Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Bridges restaurant menu items with personalized clinical health matrices to classify dishes into 🟢 <b>Good</b>, 🟡 <b>Medium</b>, and 🔴 <b>Bad</b> tiers.</div>', unsafe_allow_html=True)

# Step 1: Input Food / Menu (Model 1) - Defaults to Upload Tab
dishes_to_evaluate, current_source_id = render_menu_input_section(get_ocr_pipeline)

# Invalidate stale recommendation if menu source changed
if "last_menu_source_id" not in st.session_state:
    st.session_state["last_menu_source_id"] = current_source_id
elif st.session_state["last_menu_source_id"] != current_source_id:
    st.session_state["last_menu_source_id"] = current_source_id
    if "last_recommendation_result" in st.session_state:
        del st.session_state["last_recommendation_result"]

# Step 2: Middle Model Evaluation
st.markdown("---")
st.markdown("### 2. Configure Recommendation Thresholds & Run Matchmaker")

eval_col1, eval_col2 = st.columns([2, 1])
with eval_col1:
    good_threshold = st.slider(
        "Tier 1 (GOOD) Fit Score Threshold",
        min_value=50,
        max_value=95,
        value=DEFAULT_GOOD_THRESHOLD,
        step=5,
        key="slider_good_threshold"
    )
with eval_col2:
    bad_ceiling = min(good_threshold - 5, 70)
    bad_threshold = st.slider(
        "Tier 3 (BAD) Fit Score Ceiling",
        min_value=20,
        max_value=bad_ceiling,
        value=min(DEFAULT_BAD_THRESHOLD, bad_ceiling),
        step=5,
        key="slider_bad_threshold"
    )

run_eval_btn = st.button("🚀 Evaluate Menu & Classify 3 Tiers", type="primary", use_container_width=True, key="btn_run_eval")

if run_eval_btn:
    if not dishes_to_evaluate:
        st.warning("Please upload a menu image or enter dishes above before running evaluation.")
    elif not user_matrix:
        st.error("User Health Matrix is missing. Please configure your profile in the sidebar.")
    else:
        with st.spinner("Analyzing food groups and safety guardrails against health matrix..."):
            try:
                recommender = TieredFoodRecommender(
                    user_matrix=user_matrix,
                    good_threshold=good_threshold,
                    bad_threshold=bad_threshold,
                )
                eval_result = recommender.recommend_menu(dishes_to_evaluate)
                st.session_state["last_recommendation_result"] = eval_result
            except Exception as e:
                st.error(f"Error during recommendation evaluation: {e}")

result: Optional[TieredRecommendationResult] = st.session_state.get("last_recommendation_result")

if result:
    render_recommendation_dashboard(result)

st.markdown("---")
render_medical_disclaimer()
