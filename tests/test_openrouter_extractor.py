"""
Unit tests for OpenRouterMenuExtractor.
Validates authentication, API payload structure, JSON parsing, error classification,
food filtering, and output schema compatibility with GeminiMenuExtractor.
"""

import io
import json
import pytest
import requests
from unittest.mock import MagicMock
from PIL import Image

from src.openrouter_extractor import (
    OpenRouterMenuExtractor,
    OpenRouterAPIError,
    OpenRouterAuthError,
    OpenRouterRateLimitError,
    OpenRouterModelNotFoundError,
    OpenRouterTimeoutError,
    OpenRouterResponseParsingError,
)
from src.models import RecognizedMenu, MenuItem, MenuSection


@pytest.fixture
def mock_session():
    return MagicMock(spec=requests.Session)


@pytest.fixture
def sample_image():
    return Image.new("RGB", (200, 200), color=(255, 255, 255))


def test_openrouter_availability():
    """Verify is_available accurately checks for a valid non-mock API key."""
    # Valid key
    ext = OpenRouterMenuExtractor(api_key="sk-or-v1-abcdef1234567890abcdef")
    assert ext.is_available() is True

    # Missing / None key
    ext_none = OpenRouterMenuExtractor(api_key="")
    assert ext_none.is_available() is False

    # Mock key
    ext_mock = OpenRouterMenuExtractor(api_key="mock_key_test")
    assert ext_mock.is_available() is False


def test_openrouter_successful_extraction(mock_session, sample_image):
    """Verify successful vision menu extraction and schema output."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "food_items": [
                            {"name": "Cheeseburger"},
                            {"name": "French Fries"},
                            {"name": "Spicy Chicken"},
                        ]
                    })
                }
            }
        ]
    }
    mock_session.post.return_value = mock_resp

    extractor = OpenRouterMenuExtractor(
        api_key="sk-or-v1-validkey12345678",
        model_name="google/gemini-2.5-flash",
        session=mock_session,
    )

    menu: RecognizedMenu = extractor.extract_menu(sample_image)

    assert isinstance(menu, RecognizedMenu)
    assert menu.total_items == 3
    names = menu.get_item_names()
    assert "Cheeseburger" in names
    assert "French Fries" in names
    assert "Spicy Chicken" in names
    assert menu.metadata["extractor"] == "OpenRouter"
    assert menu.metadata["model"] == "google/gemini-2.5-flash"


def test_openrouter_strips_markdown_codeblocks(mock_session, sample_image):
    """Verify parser extracts JSON wrapped in ```json ... ``` markdown."""
    raw_markdown = """```json
{
  "food_items": [
    {"name": "Hot Dog"},
    {"name": "Cheese Sandwich"}
  ]
}
```"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": raw_markdown
                }
            }
        ]
    }
    mock_session.post.return_value = mock_resp

    extractor = OpenRouterMenuExtractor(
        api_key="sk-or-v1-validkey12345678",
        session=mock_session,
    )

    menu = extractor.extract_menu(sample_image)
    assert menu.total_items == 2
    assert "Hot Dog" in menu.get_item_names()


def test_openrouter_deterministic_filter_rejects_headers_and_drinks(mock_session, sample_image):
    """Verify deterministic filter strips headers, templates, and beverages from LLM output."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "food_items": [
                            {"name": "MAIN COURSE"},
                            {"name": "APPETIZERS"},
                            {"name": "INSERT YOUR LOCATION HERE"},
                            {"name": "ORDER NOW"},
                            {"name": "Cheeseburger"},
                            {"name": "French Fries"},
                            {"name": "Iced Tea"},
                            {"name": "Coffee"},
                            {"name": "$34"},
                        ]
                    })
                }
            }
        ]
    }
    mock_session.post.return_value = mock_resp

    extractor = OpenRouterMenuExtractor(
        api_key="sk-or-v1-validkey12345678",
        session=mock_session,
        allow_beverages=False,
    )

    menu = extractor.extract_menu(sample_image)
    names = menu.get_item_names()

    # Food dishes preserved
    assert "Cheeseburger" in names
    assert "French Fries" in names

    # Non-food and drinks excluded
    assert "MAIN COURSE" not in names
    assert "APPETIZERS" not in names
    assert "INSERT YOUR LOCATION HERE" not in names
    assert "ORDER NOW" not in names
    assert "Iced Tea" not in names
    assert "Coffee" not in names
    assert "$34" not in names


def test_openrouter_error_handling(mock_session, sample_image):
    """Verify robust error classification for OpenRouter API failures."""
    extractor = OpenRouterMenuExtractor(api_key="sk-or-v1-validkey12345678", session=mock_session)

    # 1. 401 Unauthorized
    mock_401 = MagicMock(status_code=401, text="Unauthorized")
    mock_session.post.return_value = mock_401
    with pytest.raises(OpenRouterAuthError):
        extractor.extract_menu(sample_image)

    # 2. 429 Rate Limit
    mock_429 = MagicMock(status_code=429, text="Rate limit exceeded")
    mock_session.post.return_value = mock_429
    with pytest.raises(OpenRouterRateLimitError):
        extractor.extract_menu(sample_image)

    # 3. 404 Model Not Found
    mock_404 = MagicMock(status_code=404, text="Model not found")
    mock_session.post.return_value = mock_404
    with pytest.raises(OpenRouterModelNotFoundError):
        extractor.extract_menu(sample_image)

    # 4. Timeout
    mock_session.post.side_effect = requests.exceptions.Timeout("Connection timeout")
    with pytest.raises(OpenRouterTimeoutError):
        extractor.extract_menu(sample_image)


def test_openrouter_missing_key_raises_auth_error(sample_image):
    """Verify extracting without an API key raises OpenRouterAuthError immediately."""
    extractor = OpenRouterMenuExtractor(api_key="")
    with pytest.raises(OpenRouterAuthError):
        extractor.extract_menu(sample_image)
