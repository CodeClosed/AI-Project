import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, JSON
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

    # OTP Verification & Password Reset fields
    otp_code = Column(String(6), nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    otp_purpose = Column(String(30), nullable=True)  # 'email_verification', 'password_reset'
    otp_attempts = Column(Integer, default=0, nullable=False)

    # 2FA / MFA Configuration
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_method = Column(String(20), default="authenticator", nullable=False)  # 'authenticator' or 'email'
    totp_secret = Column(Text, nullable=True)  # Fernet encrypted base32 secret
    backup_codes = Column(JSON, default=list)  # Hashed single-use recovery codes

    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    logged_meals = relationship("LoggedMeal", back_populates="user", cascade="all, delete-orphan")
    saved_menus = relationship("SavedMenu", back_populates="user", cascade="all, delete-orphan")


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
