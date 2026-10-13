import pytest
from pydantic import SecretStr
from fastapi.testclient import TestClient
from backend.api import app
from backend.settings import AppSettings

client = TestClient(app)


def test_production_validator_rejects_sqlite():
    settings = AppSettings(
        environment="production",
        database_url="sqlite:///nutrimenu.db",
        better_auth_secret=SecretStr("a" * 32),
        smtp_host="smtp.example.com",
        smtp_user="user",
        smtp_password=SecretStr("password"),
        allowed_origins="https://codeclosed.github.io",
    )
    with pytest.raises(RuntimeError, match="SQLite is not permitted in production"):
        settings.assert_production_ready()


def test_production_validator_rejects_short_secret():
    settings = AppSettings(
        environment="production",
        database_url="postgresql+psycopg://user:pass@localhost:5432/db",
        better_auth_secret=SecretStr("tooshort"),
        smtp_host="smtp.example.com",
        smtp_user="user",
        smtp_password=SecretStr("password"),
        allowed_origins="https://codeclosed.github.io",
    )
    with pytest.raises(RuntimeError, match="Must be >= 32 characters"):
        settings.assert_production_ready()


def test_production_validator_rejects_missing_smtp():
    settings = AppSettings(
        environment="production",
        database_url="postgresql+psycopg://user:pass@localhost:5432/db",
        better_auth_secret=SecretStr("a" * 32),
        smtp_host=None,
        allowed_origins="https://codeclosed.github.io",
    )
    with pytest.raises(RuntimeError, match="SMTP configuration.*is required in production"):
        settings.assert_production_ready()


def test_production_validator_rejects_wildcard_origins():
    settings = AppSettings(
        environment="production",
        database_url="postgresql+psycopg://user:pass@localhost:5432/db",
        better_auth_secret=SecretStr("a" * 32),
        smtp_host="smtp.example.com",
        smtp_user="user",
        smtp_password=SecretStr("password"),
        allowed_origins="https://*.example.com",
    )
    with pytest.raises(RuntimeError, match="Wildcard origin.*is forbidden in production"):
        settings.assert_production_ready()


def test_dev_code_never_in_forgot_password_response():
    res = client.post("/api/auth/forgot-password", json={"email": "nonexistent_dev_test@example.com"})
    assert res.status_code == 200
    data = res.json()
    assert "dev_code" not in data
    assert "success" in data
