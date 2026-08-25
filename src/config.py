"""
Centralized Configuration Module for NutriMenu AI.
Handles environment variables, Streamlit secrets, model definitions, and system defaults.
"""

import os
from pathlib import Path
from typing import Optional, List

# --- Project Paths ---
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent

# --- Model & API Defaults ---
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-flash-latest",
]

DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_TEMPERATURE = 0.15

# --- Recommendation Defaults ---
DEFAULT_GOOD_THRESHOLD = 75
DEFAULT_BAD_THRESHOLD = 45

# --- OCR Defaults ---
DEFAULT_OCR_LANGUAGES = ["en"]
DEFAULT_MIN_OCR_CONFIDENCE = 0.20


def load_env_file():
    """Loads environment variables from .env if present without external dependencies."""
    for candidate_dir in [PROJECT_ROOT, Path.cwd(), PROJECT_ROOT.parent]:
        env_path = candidate_dir / ".env"
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip('"').strip("'")
                            if key and key not in os.environ:
                                os.environ[key] = val
            except Exception:
                pass


# Preload on import
load_env_file()


def get_gemini_api_key() -> Optional[str]:
    """
    Safely retrieves the Gemini API key from environment or Streamlit secrets.
    Never returns mock or empty keys.
    """
    # 1. Environment variable
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if api_key and not api_key.startswith("mock_"):
        return api_key

    # 2. Streamlit secrets (if running in Streamlit runtime)
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            secret_key = str(st.secrets["GEMINI_API_KEY"]).strip()
            if secret_key and not secret_key.startswith("mock_"):
                return secret_key
    except Exception:
        pass

    return None


def get_gemini_model_name() -> str:
    """Retrieves the configured Gemini model name or default."""
    model = os.environ.get("GEMINI_MODEL", "").strip()
    if model:
        return model

    try:
        import streamlit as st
        if hasattr(st, "secrets") and "GEMINI_MODEL" in st.secrets:
            secret_model = str(st.secrets["GEMINI_MODEL"]).strip()
            if secret_model:
                return secret_model
    except Exception:
        pass

    return DEFAULT_GEMINI_MODEL


def get_candidate_models(configured_model: Optional[str] = None) -> List[str]:
    """Returns the ordered list of model candidates to try during API calls."""
    primary = configured_model or get_gemini_model_name()
    models = [primary]
    for m in FALLBACK_MODELS:
        if m not in models:
            models.append(m)
    return models
