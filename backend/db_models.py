import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, Float, JSON, BigInteger
)
from sqlalchemy.orm import relationship
from backend.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    encrypted_api_key = Column(Text, nullable=True)  # Fernet encrypted custom Gemini API key
    role = Column(String(32), default="user", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(DateTime, nullable=True)

    # Token Version for Instant Global Invalidation (Password changes, Security resets)
    token_version = Column(Integer, default=0, nullable=False)

    # Brute-force Account Lockout
    failed_login_count = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)

    # GDPR Deletion Grace Period
    deletion_requested_at = Column(DateTime, nullable=True)

    # Legacy OTP fields (preserved for zero downtime)
    otp_code = Column(String(6), nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    otp_purpose = Column(String(30), nullable=True)
    otp_attempts = Column(Integer, default=0, nullable=False)

    # 2FA / MFA Configuration
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_method = Column(String(20), default="authenticator", nullable=False)
    totp_secret = Column(Text, nullable=True)  # Fernet encrypted active secret
    pending_totp_secret = Column(Text, nullable=True)  # Setup secret awaiting initial code verification
    backup_codes = Column(JSON, default=list)

    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    logged_meals = relationship("LoggedMeal", back_populates="user", cascade="all, delete-orphan")
    saved_menus = relationship("SavedMenu", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("AuthSession", back_populates="user", cascade="all, delete-orphan")
    verification_codes = relationship("VerificationCode", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")


class AuthSession(Base):
    """
    Server-side authenticated sessions table.
    Enforces rotating refresh tokens, session revocation, and device tracking.
    """
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))  # Matches JWT sid claim
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    family_id = Column(String(36), index=True, nullable=False)  # Rotation family for token reuse detection
    refresh_token_hash = Column(String(64), unique=True, index=True, nullable=False)  # SHA-256 of opaque refresh token

    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    last_used_at = Column(DateTime, default=get_utc_now, nullable=False)
    idle_expires_at = Column(DateTime, nullable=False)
    absolute_expires_at = Column(DateTime, nullable=False)

    revoked_at = Column(DateTime, nullable=True)
    revoked_reason = Column(String(50), nullable=True)

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    device_label = Column(String(100), nullable=True)

    user = relationship("User", back_populates="sessions")


class VerificationCode(Base):
    """
    Cryptographic verification codes table.
    Stores HMAC-SHA256 hashes of codes for email verification, password reset,
    2FA login, and email changes.
    """
    __tablename__ = "verification_codes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    purpose = Column(String(40), index=True, nullable=False)  # email_verify, password_reset, login_2fa, email_change
    code_hash = Column(String(64), nullable=False)  # HMAC-SHA256
    new_email = Column(String(255), nullable=True)  # Populated when purpose == email_change

    attempts = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    user = relationship("User", back_populates="verification_codes")


class AuditLog(Base):
    """
    Persistent security audit logs table.
    Tracks authentication, permission, and sensitive account mutations.
    """
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    event = Column(String(80), index=True, nullable=False)
    status = Column(String(30), default="success", nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=get_utc_now, index=True, nullable=False)

    user = relationship("User", back_populates="audit_logs")


class RateLimitBucket(Base):
    """
    Persistent sliding/fixed window rate limit counter.
    Survives server restarts and distributes across multi-worker environments.
    """
    __tablename__ = "rate_limit_buckets"

    key = Column(String(200), primary_key=True)
    window_start = Column(Float, nullable=False)
    count = Column(Integer, default=1, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, nullable=False)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    age = Column(Integer, default=35)
    gender = Column(String(20), default="male")
    height_cm = Column(Float, default=175.0)
    weight_kg = Column(Float, default=75.0)
    activity_level = Column(String(30), default="moderate")
    primary_goal = Column(String(50), default="maintenance")

    # JSON collections
    health_conditions = Column(JSON, default=list)
    allergies = Column(JSON, default=list)
    dietary_preferences = Column(JSON, default=list)
    raw_bio_text = Column(Text, default="")
    cached_matrix = Column(JSON, nullable=True)

    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    user = relationship("User", back_populates="profile")


class LoggedMeal(Base):
    __tablename__ = "logged_meals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(100), default="Meal Plate")
    meal_type = Column(String(50), default="Lunch")
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    timestamp = Column(DateTime, default=get_utc_now, nullable=False)

    dishes = Column(JSON, default=list)
    total_calories = Column(Float, default=0.0)
    total_protein = Column(Float, default=0.0)
    total_carbs = Column(Float, default=0.0)
    total_fats = Column(Float, default=0.0)
    total_sodium = Column(Float, default=0.0)

    user = relationship("User", back_populates="logged_meals")


class SavedMenu(Base):
    __tablename__ = "saved_menus"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(150), default="Uploaded Menu")
    dishes = Column(JSON, default=list)
    image_url = Column(String(255), nullable=True)
    filename = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    user = relationship("User", back_populates="saved_menus")
