"""
Unit tests for configuration and AI provider resolution (Gemini 3.7 Flash & OpenRouter).
"""

import os
import pytest
from src.config import (
    get_gemini_api_key,
    get_gemini_model_name,
    is_gemini_available,
    get_openrouter_api_key,
    get_openrouter_model_name,
    is_openrouter_available,
    get_active_ai_provider,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OPENROUTER_MODEL,
)


def test_gemini_config_loading(monkeypatch):
    """Verify GEMINI_API_KEY is loaded securely from environment."""
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyD-1234567890abcdef1234567890")
    assert get_gemini_api_key() == "AIzaSyD-1234567890abcdef1234567890"
    assert is_gemini_available() is True


def test_gemini_mock_and_empty_filtering(monkeypatch):
    """Verify mock or empty Gemini keys are ignored safely."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock_key_123")
    assert get_gemini_api_key() is None
    assert is_gemini_available() is False

    monkeypatch.setenv("GEMINI_API_KEY", "   ")
    assert get_gemini_api_key() is None
    assert is_gemini_available() is False


def test_gemini_model_defaults_to_3_7_flash(monkeypatch):
    """Verify default Gemini model is gemini-3.7-flash."""
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GOOGLE_MODEL", raising=False)
    assert get_gemini_model_name() == "gemini-3.7-flash"

    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.7-flash")
    assert get_gemini_model_name() == "gemini-3.7-flash"


def test_ai_provider_priority(monkeypatch):
    """Verify active AI provider resolution (Gemini -> OpenRouter -> Local)."""
    # 1. Gemini configured -> Gemini active
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyD-1234567890abcdef1234567890")
    assert get_active_ai_provider() == "gemini"

    # 2. Gemini not configured, OpenRouter configured -> OpenRouter active
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-abcdef1234567890abcdef")
    assert get_active_ai_provider() == "openrouter"

    # 3. None configured -> Local fallback
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert get_active_ai_provider() == "local"
