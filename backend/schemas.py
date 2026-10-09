from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


# --- Auth Schemas ---

TRIVIAL_PASSWORDS = {"password", "12345678", "qwerty123", "nutrimenu", "admin123", "password123"}


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters long")
    profile: Optional[Dict[str, Any]] = None

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if v.lower() in TRIVIAL_PASSWORDS:
            raise ValueError("Password is too common or easily guessable. Please choose a stronger password.")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v



class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str
    is_active: bool
    has_custom_api_key: bool = False
    two_factor_enabled: bool = False
    two_factor_method: Optional[str] = "authenticator"
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional[UserOut] = None
    mfa_required: bool = False
    temp_token: Optional[str] = None
    two_factor_method: Optional[str] = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if v.lower() in TRIVIAL_PASSWORDS:
            raise ValueError("Password is too common. Please choose a stronger password.")
        return v


class AccountDelete(BaseModel):
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8)

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if v.lower() in TRIVIAL_PASSWORDS:
            raise ValueError("Password is too common. Please choose a stronger password.")
        return v


class MfaVerifyRequest(BaseModel):
    temp_token: str
    code: str = Field(..., min_length=6, max_length=12)


class MfaSetupResponse(BaseModel):
    secret_key: str
    otpauth_url: str
    backup_codes: List[str]
    secret: Optional[str] = None
    otpauth_uri: Optional[str] = None


class MfaEnableRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class MfaDisableRequest(BaseModel):
    password: str



# --- Profile Schemas ---

class UserProfileUpdate(BaseModel):
    age: Optional[int] = 35
    gender: Optional[str] = "male"
    height_cm: Optional[float] = 175.0
    weight_kg: Optional[float] = 75.0
    activity_level: Optional[str] = "moderate"
    primary_goal: Optional[str] = "maintenance"
    health_conditions: Optional[List[str]] = Field(default_factory=list)
    allergies: Optional[List[str]] = Field(default_factory=list)
    dietary_preferences: Optional[List[str]] = Field(default_factory=list)
    raw_bio_text: Optional[str] = ""
    cached_matrix: Optional[Dict[str, Any]] = None


class UserProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    age: int
    gender: str
    height_cm: float
    weight_kg: float
    activity_level: str
    primary_goal: str
    health_conditions: List[str]
    allergies: List[str]
    dietary_preferences: List[str]
    raw_bio_text: Optional[str] = ""
    cached_matrix: Optional[Dict[str, Any]] = None
    updated_at: datetime


# --- Logged Meal Schemas ---

class LoggedMealCreate(BaseModel):
    id: Optional[str] = None
    name: str = "Meal Plate"
    meal_type: str = "Lunch"
    date: str  # YYYY-MM-DD
    timestamp: Optional[datetime] = None
    dishes: List[Dict[str, Any]] = Field(default_factory=list)
    total_calories: float = 0.0
    total_protein: float = 0.0
    total_carbs: float = 0.0
    total_fats: float = 0.0
    total_sodium: float = 0.0


class LoggedMealOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: int
    name: str
    meal_type: str
    date: str
    timestamp: datetime
    dishes: List[Dict[str, Any]]
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fats: float
    total_sodium: float


# --- API Key Schema ---

class ApiKeyUpdate(BaseModel):
    api_key: Optional[str] = Field(None, description="Personal Gemini/OpenRouter API key to be stored encrypted")


# --- Saved Menu Schemas ---

class SavedMenuCreate(BaseModel):
    id: Optional[str] = None
    title: str = "Uploaded Menu"
    dishes: List[Any] = Field(default_factory=list)
    image_url: Optional[str] = None
    filename: Optional[str] = None


class SavedMenuOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: int
    title: str
    dishes: List[Any]
    image_url: Optional[str] = None
    filename: Optional[str] = None
    created_at: datetime
