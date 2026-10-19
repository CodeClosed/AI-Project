"""
Unit tests for GroqClient, GroqMenuExtractor, and unified AIClient Groq integration.
"""

import json
import pytest
import requests
from unittest.mock import MagicMock
from PIL import Image

from src.groq_client import (
    GroqClient,
    GroqAPIError,
    GroqAuthError,
    GroqRateLimitError,
    GroqModelNotFoundError,
    GroqTimeoutError,
    GroqResponseParsingError,
)
from src.groq_extractor import GroqMenuExtractor
from src.ai_client import AIClient
from src.models import RecognizedMenu


@pytest.fixture
def mock_session():
    return MagicMock(spec=requests.Session)


@pytest.fixture
def sample_image():
    return Image.new("RGB", (200, 200), color=(255, 255, 255))


def test_groq_client_availability():
    client_valid = GroqClient(api_key="gsk_1234567890abcdef1234567890")
    assert client_valid.is_available() is True

    client_mock = GroqClient(api_key="mock_groq_key")
    assert client_mock.is_available() is False

    client_none = GroqClient(api_key="")
    assert client_none.is_available() is False


def test_groq_missing_api_key_raises_auth_error():
    client = GroqClient(api_key="")
    with pytest.raises(GroqAuthError, match="Groq API key is not configured"):
        client.generate_json(prompt="Hello")


def test_groq_successful_json_generation_200(mock_session):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"status": "optimal", "score": 95})
                }
            }
        ]
    }
    mock_session.post.return_value = mock_resp

    client = GroqClient(api_key="gsk_1234567890abcdef1234567890", session=mock_session)
    res = client.generate_json(prompt="Evaluate dish", temperature=0.2)

    assert isinstance(res, dict)
    assert res["status"] == "optimal"
    assert res["score"] == 95

    # Verify payload format
    call_args = mock_session.post.call_args
    assert "https://api.groq.com/openai/v1/chat/completions" in call_args[0][0]
    payload = call_args[1]["json"]
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["model"] == "llama-3.3-70b-versatile"


def test_groq_strips_markdown_code_fences(mock_session):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "```json\n{\"tier\": \"GOOD\", \"items\": [\"Quinoa Salad\"]}\n```"
                }
            }
        ]
    }
    mock_session.post.return_value = mock_resp

    client = GroqClient(api_key="gsk_1234567890abcdef1234567890", session=mock_session)
    res = client.generate_json(prompt="Analyze")

    assert res["tier"] == "GOOD"
    assert res["items"] == ["Quinoa Salad"]


def test_groq_auth_error_401_or_403(mock_session):
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Invalid API Key"
    mock_session.post.return_value = mock_resp

    client = GroqClient(api_key="gsk_invalid_key_123456", session=mock_session)
    with pytest.raises(GroqAuthError):
        client.generate_json(prompt="Evaluate")


def test_groq_rate_limit_error_429(mock_session):
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Rate limit reached for TPM"
    mock_session.post.return_value = mock_resp

    client = GroqClient(api_key="gsk_1234567890abcdef1234567890", session=mock_session)
    with pytest.raises(GroqRateLimitError):
        client.generate_json(prompt="Evaluate")


def test_groq_model_fallback_404(mock_session):
    # First model returns 404, fallback model returns 200
    resp_404 = MagicMock()
    resp_404.status_code = 404
    resp_404.text = "Model not found"

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"fallback_success": True})}}]
    }

    mock_session.post.side_effect = [resp_404, resp_200]

    client = GroqClient(api_key="gsk_1234567890abcdef1234567890", session=mock_session)
    res = client.generate_json(prompt="Evaluate")
    assert res["fallback_success"] is True
    assert mock_session.post.call_count == 2


def test_groq_timeout_error(mock_session):
    mock_session.post.side_effect = requests.Timeout("Connection timed out")
    client = GroqClient(api_key="gsk_1234567890abcdef1234567890", session=mock_session)
    with pytest.raises(GroqTimeoutError):
        client.generate_json(prompt="Evaluate")


def test_groq_malformed_json_response(mock_session):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "This is raw unformatted text without JSON"}}]
    }
    mock_session.post.return_value = mock_resp

    client = GroqClient(api_key="gsk_1234567890abcdef1234567890", session=mock_session)
    with pytest.raises(GroqResponseParsingError):
        client.generate_json(prompt="Evaluate")


def test_groq_empty_choices(mock_session):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"choices": []}
    mock_session.post.return_value = mock_resp

    client = GroqClient(api_key="gsk_1234567890abcdef1234567890", session=mock_session)
    with pytest.raises(GroqResponseParsingError, match="empty choices list"):
        client.generate_json(prompt="Evaluate")


def test_groq_vision_image_payload(mock_session):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"extracted": True})}}]
    }
    mock_session.post.return_value = mock_resp

    client = GroqClient(api_key="gsk_1234567890abcdef1234567890", session=mock_session)
    client.generate_json(prompt="OCR this menu", image_b64="fakebase64string==")

    call_args = mock_session.post.call_args
    payload = call_args[1]["json"]
    assert payload["model"] == "llama-3.2-11b-vision-preview"
    user_msg = payload["messages"][0]["content"]
    assert isinstance(user_msg, list)
    assert user_msg[1]["type"] == "image_url"
    assert "data:image/jpeg;base64,fakebase64string==" in user_msg[1]["image_url"]["url"]


def test_groq_menu_extractor(mock_session, sample_image):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "sections": [
                            {
                                "category": "Mains",
                                "items": [
                                    {"name": "Paneer Tikka Masala", "price": "$14.99"},
                                    {"name": "Garlic Naan Bread", "price": "$3.50"},
                                    {"name": "Monday Breakfast", "price": ""} # should be rejected as non-food header
                                ]
                            }
                        ]
                    })
                }
            }
        ]
    }
    mock_session.post.return_value = mock_resp

    extractor = GroqMenuExtractor(api_key="gsk_1234567890abcdef1234567890", session=mock_session)
    menu = extractor.extract(sample_image)

    assert isinstance(menu, RecognizedMenu)
    assert menu.metadata["extractor"] == "Groq"
    item_names = menu.get_item_names()
    assert "Paneer Tikka Masala" in item_names
    assert "Garlic Naan Bread" in item_names
    assert "Monday Breakfast" not in item_names


def test_ai_client_dispatches_to_groq_when_provider_is_groq(monkeypatch, mock_session):
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_1234567890abcdef1234567890")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"provider": "groq"})}}]
    }
    mock_session.post.return_value = mock_resp

    ai = AIClient(session=mock_session)
    res = ai.generate_json(prompt="Test dispatch")

    assert res["provider"] == "groq"
    call_args = mock_session.post.call_args
    assert "api.groq.com" in call_args[0][0]
