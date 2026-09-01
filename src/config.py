"""
Centralized Configuration Module for NutriMenu AI.
Handles environment variables, Streamlit secrets, Gemini 3.7 Flash model definitions, and system defaults.
"""

import os
from pathlib import Path
from typing import Optional, List

# --- Project Paths ---
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent

# --- Gemini 3.7 Flash Defaults ---
DEFAULT_GEMINI_MODEL = "gemini-3.7-flash"
FALLBACK_GEMINI_MODELS = [
    "gemini-3.7-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-flash-latest",
]

# --- OpenRouter Defaults ---
DEFAULT_OPENROUTER_MODEL = "meta-llama/llama-3.2-11b-vision-instruct:free"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

FALLBACK_OPENROUTER_MODELS = [
    "meta-llama/llama-3.2-11b-vision-instruct:free",
    "mistralai/pixtral-12b:free",
    "qwen/qwen-2.5-vl-72b-instruct:free",
    "deepseek/deepseek-chat",
]

DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_TEMPERATURE = 0.15

# --- Recommendation Defaults ---
DEFAULT_GOOD_THRESHOLD = 75
DEFAULT_BAD_THRESHOLD = 45

# --- OCR & Validator Defaults ---
DEFAULT_OCR_LANGUAGES = ["en"]
DEFAULT_MIN_OCR_CONFIDENCE = 0.20
DEFAULT_VALIDATOR_ACCEPT_THRESHOLD = 80.0
DEFAULT_VALIDATOR_FLAG_THRESHOLD = 50.0
DEFAULT_ENABLE_SECOND_PASS_VERIFICATION = False
DEFAULT_MAX_SECOND_PASS_ITEMS = 5


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
    for key_name in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "AI_API_KEY"]:
        api_key = os.environ.get(key_name, "").strip()
        if api_key and not api_key.startswith("mock_") and len(api_key) >= 10:
            return api_key

    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            for key_name in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "AI_API_KEY"]:
                if key_name in st.secrets:
                    secret_key = str(st.secrets[key_name]).strip()
                    if secret_key and not secret_key.startswith("mock_") and len(secret_key) >= 10:
                        return secret_key
    except Exception:
        pass

    return None


def get_gemini_model_name() -> str:
    """Retrieves the configured Gemini model name or default (gemini-3.7-flash)."""
    for model_var in ["GEMINI_MODEL", "GOOGLE_MODEL"]:
        model = os.environ.get(model_var, "").strip()
        if model:
            return model

    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            for model_var in ["GEMINI_MODEL", "GOOGLE_MODEL"]:
                if model_var in st.secrets:
                    secret_model = str(st.secrets[model_var]).strip()
                    if secret_model:
                        return secret_model
    except Exception:
        pass

    return DEFAULT_GEMINI_MODEL


def is_gemini_available() -> bool:
    """Returns True if a valid Gemini API key is configured."""
    key = get_gemini_api_key()
    return bool(key and len(key.strip()) >= 10)


def get_openrouter_api_key() -> Optional[str]:
    """Retrieves OpenRouter API key if present."""
    for key_name in ["OPENROUTER_API_KEY", "OPENAI_API_KEY"]:
        api_key = os.environ.get(key_name, "").strip()
        if api_key and not api_key.startswith("mock_") and len(api_key) >= 10:
            return api_key

    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            for key_name in ["OPENROUTER_API_KEY", "OPENAI_API_KEY"]:
                if key_name in st.secrets:
                    secret_key = str(st.secrets[key_name]).strip()
                    if secret_key and not secret_key.startswith("mock_") and len(secret_key) >= 10:
                        return secret_key
    except Exception:
        pass

    return None


def get_openrouter_model_name() -> str:
    """Retrieves configured OpenRouter model name."""
    model = os.environ.get("OPENROUTER_MODEL", "").strip()
    if model:
        return model
    return DEFAULT_OPENROUTER_MODEL


def is_openrouter_available() -> bool:
    key = get_openrouter_api_key()
    return bool(key and len(key.strip()) >= 10)


def get_active_ai_provider() -> str:
    """Determines active AI provider: Gemini -> OpenRouter -> Local."""
    if is_gemini_available():
        return "gemini"
    if is_openrouter_available():
        return "openrouter"
    return "local"


def get_candidate_models(configured_model: Optional[str] = None) -> List[str]:
    """Returns ordered candidate models for Gemini API requests."""
    primary = configured_model or get_gemini_model_name()
    models = [primary]
    for m in FALLBACK_GEMINI_MODELS:
        if m not in models:
            models.append(m)
    return models
