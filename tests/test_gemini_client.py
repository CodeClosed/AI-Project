"""
Unit tests for GeminiClient with mocked HTTP layer (runs completely offline).
Validates HTTP 200, 400, 401, 404, 429, 500, timeout, and malformed JSON scenarios.
"""

import json
import pytest
from unittest.mock import Mock, patch
import requests

from src.gemini_client import (
    GeminiClient,
    GeminiAPIError,
    GeminiAuthError,
    GeminiRateLimitError,
    GeminiModelNotFoundError,
    GeminiTimeoutError,
    GeminiResponseParsingError,
)


@pytest.fixture
def mock_session():
    return Mock(spec=requests.Session)


def test_missing_api_key_raises_auth_error():
    client = GeminiClient(api_key="")
    with pytest.raises(GeminiAuthError, match="Gemini API key is not configured"):
        client.generate_json("Test prompt")


def test_successful_json_generation_200(mock_session):
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": '{"result": "success", "score": 95}'}]
                }
            }
        ]
    }
    mock_session.post.return_value = mock_resp

    client = GeminiClient(api_key="test_valid_key", session=mock_session)
    result = client.generate_json("Generate nutrition test")

    assert isinstance(result, dict)
    assert result["result"] == "success"
    assert result["score"] == 95
    assert mock_session.post.called


def test_auth_error_401(mock_session):
    mock_resp = Mock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized: API key invalid"
    mock_session.post.return_value = mock_resp

    client = GeminiClient(api_key="invalid_key", session=mock_session)
    with pytest.raises(GeminiAuthError, match="Invalid or unauthorized Gemini API key"):
        client.generate_json("Test prompt")


def test_rate_limit_error_429(mock_session):
    mock_resp = Mock()
    mock_resp.status_code = 429
    mock_resp.text = "Quota exceeded"
    mock_session.post.return_value = mock_resp

    client = GeminiClient(api_key="test_key", session=mock_session)
    with pytest.raises(GeminiRateLimitError, match="rate limit or quota exceeded"):
        client.generate_json("Test prompt")


def test_model_not_found_404_fallback(mock_session):
    mock_resp_404 = Mock()
    mock_resp_404.status_code = 404
    mock_resp_404.text = "Model not found"

    mock_resp_200 = Mock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"text": '{"status": "ok_fallback"}'}]}}
        ]
    }

    # First call returns 404 for primary model, next fallback model returns 200
    mock_session.post.side_effect = [mock_resp_404, mock_resp_200]

    client = GeminiClient(api_key="test_key", model_name="non_existent_model", session=mock_session)
    result = client.generate_json("Test prompt")

    assert result["status"] == "ok_fallback"
    assert mock_session.post.call_count == 2


def test_server_error_500(mock_session):
    mock_resp = Mock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    mock_session.post.return_value = mock_resp

    client = GeminiClient(api_key="test_key", session=mock_session)
    with pytest.raises(GeminiAPIError, match="Gemini server error"):
        client.generate_json("Test prompt")


def test_timeout_error(mock_session):
    mock_session.post.side_effect = requests.exceptions.Timeout("Connection timed out")

    client = GeminiClient(api_key="test_key", timeout=5, session=mock_session)
    with pytest.raises(GeminiTimeoutError, match="timed out"):
        client.generate_json("Test prompt")


def test_malformed_json_response(mock_session):
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": 'Not a JSON text string at all'}]
                }
            }
        ]
    }
    mock_session.post.return_value = mock_resp

    client = GeminiClient(api_key="test_key", session=mock_session)
    with pytest.raises(GeminiResponseParsingError, match="Failed to parse JSON"):
        client.generate_json("Test prompt")


def test_empty_candidates_response(mock_session):
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"candidates": []}
    mock_session.post.return_value = mock_resp

    client = GeminiClient(api_key="test_key", session=mock_session)
    with pytest.raises(GeminiResponseParsingError, match="empty response candidates"):
        client.generate_json("Test prompt")
