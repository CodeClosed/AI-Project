import os
import re
from typing import Literal, List, Optional
from pydantic import BaseModel, SecretStr, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = Field(default="sqlite:///nutrimenu.db")
    better_auth_secret: Optional[SecretStr] = None
    auth_secret: Optional[SecretStr] = None
    secret_key: Optional[SecretStr] = None
    encryption_secret_key: Optional[SecretStr] = None

    # Allowed Origins
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8501,http://127.0.0.1:8501,http://localhost:3000,https://codeclosed.github.io"
    better_auth_trusted_origins: Optional[str] = None
    trusted_proxy_count: int = 0

    # Token Lifetimes
    access_token_ttl_minutes: int = 15
    refresh_token_idle_days: int = 7
    refresh_token_absolute_days: int = 30

    # SMTP Configuration
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[SecretStr] = None
    smtp_from: Optional[str] = None
    smtp_tls_mode: Literal["starttls", "ssl", "none"] = "starttls"

    # Frontend URL for link generation in emails
    frontend_url: str = "https://codeclosed.github.io/AI-Project"

    # Account Lifecycle Policies
    deletion_grace_days: int = 14
    audit_retention_days: int = 180
    require_email_verification: bool = Field(default=False)  # Enforced to True in production

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def is_verification_enforced(self) -> bool:
        return self.is_production or self.require_email_verification

    def get_auth_secret(self) -> str:
        """Returns active secret string, checking better_auth_secret, auth_secret, then secret_key."""
        for s in [self.better_auth_secret, self.auth_secret, self.secret_key]:
            if s and s.get_secret_value().strip():
                return s.get_secret_value().strip()
        return "nutrimenu-dev-ephemeral-secret-key-32-chars-minimum"

    def get_encryption_key(self) -> str:
        if self.encryption_secret_key and self.encryption_secret_key.get_secret_value().strip():
            return self.encryption_secret_key.get_secret_value().strip()
        return self.get_auth_secret()

    def get_trusted_origins_list(self) -> List[str]:
        raw = self.better_auth_trusted_origins or self.allowed_origins
        return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]

    def assert_production_ready(self) -> None:
        """Validates security invariants when running in production."""
        if not self.is_production:
            return

        secret = self.get_auth_secret()
        insecure_placeholders = {
            "nutrimenu-ai-jwt-super-secret-key-production-change-this-2026",
            "nutrimenu-dev-ephemeral-secret-key-32-chars-minimum",
            "change-this-secret",
            "secret",
            "supersecret",
            "defaultsecret",
        }
        if secret in insecure_placeholders:
            raise RuntimeError("CRITICAL PRODUCTION SECURITY ERROR: Insecure placeholder AUTH_SECRET detected!")

        if len(secret) < 32:
            raise RuntimeError(f"CRITICAL PRODUCTION SECURITY ERROR: Auth secret is {len(secret)} characters. Must be >= 32 characters (256 bits).")

        db_url = self.database_url.lower()
        if db_url.startswith("sqlite"):
            raise RuntimeError("CRITICAL PRODUCTION SECURITY ERROR: SQLite is not permitted in production. Use PostgreSQL (Neon / Supabase).")

        if not self.smtp_host or not self.smtp_user or not self.smtp_password:
            raise RuntimeError("CRITICAL PRODUCTION SECURITY ERROR: SMTP configuration (SMTP_HOST, SMTP_USER, SMTP_PASSWORD) is required in production for secure account emails.")

        for origin in self.get_trusted_origins_list():
            if "*" in origin:
                raise RuntimeError(f"CRITICAL PRODUCTION SECURITY ERROR: Wildcard origin '{origin}' is forbidden in production.")


settings = AppSettings()
