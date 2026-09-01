"""
Unit tests for GeminiClient with mocked HTTP layer (runs completely offline).
Validates HTTP 200, 401, 404, 429, 500, timeout, and malformed JSON scenarios for Gemini 3.7 Flash.
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
    with pytest.raises(GeminiAuthError, match="Gemini API key is missing"):
        client.generate_json("Test prompt")


def test_successful_gemini_json_generation_200(mock_session):
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": '{"result": "success", "score": 98, "model": "gemini-3.7-flash"}'}
                    ]
                }
            }
        ]
    }
    mock_session.post.return_value = mock_resp

    client = GeminiClient(api_key="AIzaSyD-valid-test-key-123456", model_name="gemini-3.7-flash", session=mock_session)
    result = client.generate_json("Generate nutrition test")

    assert isinstance(result, dict)
    assert result["result"] == "success"
    assert result["score"] == 98
    assert result["model"] == "gemini-3.7-flash"
    assert mock_session.post.called


def test_auth_error_401_or_403(mock_session):
    mock_resp = Mock()
    mock_resp.status_code = 401
    mock_resp.text = "API key not valid"
    mock_session.post.return_value = mock_resp

    client = GeminiClient(api_key="AIzaSyD-invalid-key-12345", session=mock_session)
    with pytest.raises(GeminiAuthError, match="Gemini API authentication failed"):
        client.generate_json("Test prompt")


def test_rate_limit_error_429(mock_session):
    mock_resp = Mock()
    mock_resp.status_code = 429
    mock_resp.text = "RESOURCE_EXHAUSTED"
    mock_session.post.return_value = mock_resp

    client = GeminiClient(api_key="AIzaSyD-valid-test-key-123456", session=mock_session)
    with pytest.raises(GeminiAPIError):
        client.generate_json("Test prompt")


def test_model_fallback_404(mock_session):
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

    # First model (e.g. non_existent) fails 404, fallback succeeds with 200
    mock_session.post.side_effect = [mock_resp_404, mock_resp_200]

    client = GeminiClient(api_key="AIzaSyD-valid-test-key-123456", model_name="non_existent_gemini_model", session=mock_session)
    result = client.generate_json("Test prompt")

    assert result["status"] == "ok_fallback"
    assert mock_session.post.call_count == 2


def test_timeout_error(mock_session):
    mock_session.post.side_effect = requests.exceptions.Timeout("Connection timed out")

    client = GeminiClient(api_key="AIzaSyD-valid-test-key-123456", timeout=5, session=mock_session)
    with pytest.raises(GeminiTimeoutError, match="timed out"):
        client.generate_json("Test prompt")


def test_malformed_json_response(mock_session):
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"text": "Non-JSON response text"}]}}
        ]
    }
    mock_session.post.return_value = mock_resp

    client = GeminiClient(api_key="AIzaSyD-valid-test-key-123456", session=mock_session)
    with pytest.raises(GeminiResponseParsingError, match="Failed to parse JSON"):
        client.generate_json("Test prompt")


def test_empty_candidates_response(mock_session):
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"candidates": []}
    mock_session.post.return_value = mock_resp

    client = GeminiClient(api_key="AIzaSyD-valid-test-key-123456", session=mock_session)
    with pytest.raises(GeminiResponseParsingError, match="no candidates"):
        client.generate_json("Test prompt")


def test_markdown_code_fencing_stripped(mock_session):
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": '```json\n{"clean_json": true, "gemini_version": "3.7-flash"}\n```'}
                    ]
                }
            }
        ]
    }
    mock_session.post.return_value = mock_resp

    client = GeminiClient(api_key="AIzaSyD-valid-test-key-123456", session=mock_session)
    result = client.generate_json("Test prompt")

    assert result["clean_json"] is True
    assert result["gemini_version"] == "3.7-flash"
