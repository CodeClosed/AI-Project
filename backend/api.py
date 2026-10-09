import os
import shutil
import tempfile
import re
import logging
import uuid
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv

import json
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.jobs import job_manager, JobStatus

from backend.database import get_db, init_db
from backend.db_models import User, UserProfile, LoggedMeal, SavedMenu
from backend.security import (
    hash_password,
    verify_password,
    verify_dummy_password,
    encrypt_data,
    decrypt_data,
    create_access_token,
    create_temp_2fa_token,
    decode_temp_2fa_token,
    generate_secure_otp,
    generate_totp_secret,
    get_totp_uri,
    verify_totp_code,
    generate_backup_codes,
    get_current_user,
    get_optional_current_user,
    rate_limit_dependency,
    log_audit_event,
    get_client_ip,
)
from backend.schemas import (
    UserRegister,
    UserLogin,
    UserOut,
    Token,
    LoginResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MfaVerifyRequest,
    MfaSetupResponse,
    MfaEnableRequest,
    MfaDisableRequest,
    UserProfileUpdate,
    UserProfileOut,
    LoggedMealCreate,
    LoggedMealOut,
    ApiKeyUpdate,
    SavedMenuCreate,
    SavedMenuOut,
    PasswordChange,
    AccountDelete,
)
from src.pipeline import MenuRecognitionPipeline
from src.models import RecognizedMenu
from src.matrix_generator import AIMatrixGenerator, UserNutritionalMatrix
from src.recommendation_engine import TieredFoodRecommender, TieredRecommendationResult
from src.noise_filter import is_valid_food_item
from src.gemini_extractor import tokenize_food_item

# Load environment variables explicitly
load_dotenv(override=True)

logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error("Database initialization failed: %s", e)
    yield

app = FastAPI(
    title="NutriMenu AI API",
    description="Enterprise Full-Stack Backend for Menu OCR, Clinical Matrix Synthesis, User Authentication, and Encrypted Health Storage.",
    version="2.0.0",
    lifespan=lifespan,
)

# Persistent Local File Storage for Menu Images
UPLOAD_ROOT = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_MENUS_DIR = UPLOAD_ROOT / "menus"
UPLOAD_MENUS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_ROOT)), name="uploads")


# Security Response Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# Hardened CORS & Trusted Origins (Better Auth Specification)
raw_trusted_origins = (
    os.getenv("BETTER_AUTH_TRUSTED_ORIGINS")
    or os.getenv("ALLOWED_ORIGINS")
    or "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8501,http://127.0.0.1:8501,http://localhost:3000"
)
trusted_origins = [origin.strip() for origin in raw_trusted_origins.split(",") if origin.strip()]
trusted_origin_pattern = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$|^https://[a-zA-Z0-9-]+\.github\.io$")


def is_trusted_origin(origin_val: Optional[str]) -> bool:
    if not origin_val:
        return True
    clean = origin_val.strip().rstrip("/")
    if any(clean == t.rstrip("/") for t in trusted_origins):
        return True
    if trusted_origin_pattern.match(clean):
        return True
    return False


# CSRF & Trusted Origin Guard Middleware for Mutative HTTP Methods
@app.middleware("http")
async def csrf_origin_guard(request: Request, call_next):
    if request.method in {"POST", "PUT", "DELETE", "PATCH"}:
        origin = request.headers.get("origin")
        if origin and not is_trusted_origin(origin):
            log_audit_event(
                event_type="auth.csrf_blocked",
                request=request,
                status="blocked",
                details={"reason": "untrusted_origin", "origin": origin},
            )
            from starlette.responses import JSONResponse
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": f"Forbidden: Untrusted Origin '{origin}'."},
            )
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=trusted_origins if trusted_origins else ["*"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$|^https://[a-zA-Z0-9-]+\.github\.io$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================================
# 🔐 AUTHENTICATION & AUTHORIZATION ENDPOINTS (HARDENED)
# =====================================================================

def user_to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        has_custom_api_key=bool(user.encrypted_api_key),
        two_factor_enabled=bool(getattr(user, "two_factor_enabled", False)),
        two_factor_method=getattr(user, "two_factor_method", "authenticator") or "authenticator",
        created_at=user.created_at,
    )


@app.post(
    "/api/auth/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_dependency(max_requests=5, window_seconds=60, endpoint_label="register"))]
)
def register_user(req: UserRegister, request: Request, db: Session = Depends(get_db)):
    """Registers a new user account with hashed password, rate limiting, and default health profile."""
    clean_email = req.email.strip().lower()

    # Check if user already exists
    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        log_audit_event(
            event_type="auth.register_duplicate",
            request=request,
            email=clean_email,
            status="failure",
            details={"reason": "email_already_registered"}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    # Hash password with bcrypt
    hashed = hash_password(req.password)
    user = User(
        email=clean_email,
        hashed_password=hashed,
        role="user",
        is_active=True,
    )
    db.add(user)
    db.flush()  # populate user.id

    # Create associated default profile
    p_data = req.profile or {}
    profile = UserProfile(
        user_id=user.id,
        age=int(p_data.get("age", 35)),
        gender=str(p_data.get("gender", "male")),
        height_cm=float(p_data.get("height_cm", 175.0)),
        weight_kg=float(p_data.get("weight_kg", 75.0)),
        activity_level=str(p_data.get("activity_level", "moderate")),
        primary_goal=str(p_data.get("primary_goal", "maintenance")),
        health_conditions=p_data.get("health_conditions", []),
        allergies=p_data.get("allergies", []),
        dietary_preferences=p_data.get("dietary_preferences", []),
        raw_bio_text=p_data.get("raw_bio_text", ""),
    )
    db.add(profile)
    db.commit()
    db.refresh(user)

    log_audit_event(
        event_type="auth.register_success",
        request=request,
        user_id=user.id,
        email=user.email,
        status="success",
    )

    # Issue JWT access token
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role})
    return Token(access_token=access_token, token_type="bearer", user=user_to_out(user))


@app.post(
    "/api/auth/login",
    response_model=LoginResponse,
    dependencies=[Depends(rate_limit_dependency(max_requests=5, window_seconds=60, endpoint_label="login"))]
)
def login_user(req: UserLogin, request: Request, db: Session = Depends(get_db)):
    """
    Authenticates user with constant-time dummy verification (timing-attack defense)
    and IP-based rate limiting. Enforces 2FA challenge when two_factor_enabled.
    """
    clean_email = req.email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()

    is_valid_password = False
    if user:
        is_valid_password = verify_password(req.password, user.hashed_password)
    else:
        # Constant-time dummy verification prevents timing attacks and account enumeration
        verify_dummy_password(req.password)

    if not user or not is_valid_password:
        log_audit_event(
            event_type="auth.login_failed",
            request=request,
            email=clean_email,
            status="failure",
            details={"reason": "invalid_credentials"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        log_audit_event(
            event_type="auth.login_deactivated",
            request=request,
            user_id=user.id,
            email=user.email,
            status="blocked",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated.",
        )

    # Multi-Factor Authentication Check
    if getattr(user, "two_factor_enabled", False):
        temp_token = create_temp_2fa_token(user.id)
        if user.two_factor_method == "email":
            otp = generate_secure_otp(6)
            user.otp_code = otp
            user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
            user.otp_purpose = "login_2fa"
            user.otp_attempts = 0
            db.commit()
            logger.info("[DEV_EMAIL_OTP] Login 2FA code for %s: %s", user.email, otp)

        log_audit_event(
            event_type="auth.mfa_challenge_issued",
            request=request,
            user_id=user.id,
            email=user.email,
            status="pending",
            details={"method": user.two_factor_method}
        )
        return LoginResponse(
            mfa_required=True,
            temp_token=temp_token,
            two_factor_method=user.two_factor_method or "authenticator",
        )

    log_audit_event(
        event_type="auth.login_success",
        request=request,
        user_id=user.id,
        email=user.email,
        status="success",
    )

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role})
    return LoginResponse(access_token=access_token, token_type="bearer", user=user_to_out(user))


@app.post(
    "/api/auth/forgot-password",
    dependencies=[Depends(rate_limit_dependency(max_requests=3, window_seconds=60, endpoint_label="forgot_password"))]
)
def forgot_password(req: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """
    Initiates password reset via 6-digit cryptographic OTP.
    Enforces anti-enumeration blind response: returns identical success message
    regardless of whether the user exists.
    """
    clean_email = req.email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()

    if user and user.is_active:
        otp = generate_secure_otp(6)
        user.otp_code = otp
        user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        user.otp_purpose = "password_reset"
        user.otp_attempts = 0
        db.commit()

        # Log OTP clearly in dev console for instant developer verification
        print(f"\n[DEV_EMAIL_OTP] Password reset verification code for {user.email}: {otp}\n", flush=True)
        logger.info("[DEV_EMAIL_OTP] Password reset verification code for %s: %s", user.email, otp)
        log_audit_event(
            event_type="auth.forgot_password_requested",
            request=request,
            user_id=user.id,
            email=user.email,
            status="success",
        )
    else:
        # Constant-time dummy verification prevents timing attacks
        verify_dummy_password("dummy_password_timing_defense")
        log_audit_event(
            event_type="auth.forgot_password_unknown_email",
            request=request,
            email=clean_email,
            status="simulated",
        )

    # Standard anti-enumeration response (includes dev_code in local development if no SMTP server configured)
    response_payload = {
        "success": True,
        "message": "If an account with this email address exists, a 6-digit verification code has been sent."
    }
    if user and user.is_active and not os.getenv("SMTP_SERVER") and os.getenv("ENVIRONMENT") != "production":
        response_payload["dev_code"] = otp

    return response_payload


@app.post(
    "/api/auth/reset-password",
    dependencies=[Depends(rate_limit_dependency(max_requests=5, window_seconds=60, endpoint_label="reset_password"))]
)
def reset_password(req: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """
    Verifies 6-digit OTP, validates 10-minute expiration window, and updates password.
    Blocks brute-force attempts after 5 consecutive failures.
    """
    clean_email = req.email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()

    if not user or not user.otp_code or user.otp_purpose != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code. Please request a new code.",
        )

    # Check attempt limit
    if user.otp_attempts >= 5:
        user.otp_code = None
        user.otp_expires_at = None
        user.otp_purpose = None
        db.commit()
        log_audit_event(
            event_type="auth.password_reset_lockout",
            request=request,
            user_id=user.id,
            email=user.email,
            status="blocked",
            details={"reason": "max_otp_attempts_exceeded"}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many failed verification attempts. This code has been invalidated for security. Please request a new code.",
        )

    # Check expiration
    now_utc = datetime.now(timezone.utc)
    if user.otp_expires_at:
        otp_exp = user.otp_expires_at if user.otp_expires_at.tzinfo else user.otp_expires_at.replace(tzinfo=timezone.utc)
        if now_utc > otp_exp:
            user.otp_code = None
            user.otp_expires_at = None
            user.otp_purpose = None
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code has expired (valid for 10 minutes). Please request a new code.",
            )

    # Verify code in constant time
    clean_input = req.otp_code.strip()
    is_valid_code = secrets.compare_digest(user.otp_code, clean_input)

    if not is_valid_code:
        user.otp_attempts += 1
        db.commit()
        log_audit_event(
            event_type="auth.password_reset_failed_code",
            request=request,
            user_id=user.id,
            email=user.email,
            status="failure",
            details={"attempts": user.otp_attempts}
        )
        remaining = max(0, 5 - user.otp_attempts)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification code. {remaining} attempt(s) remaining.",
        )

    # Code is valid - update password and clear OTP
    user.hashed_password = hash_password(req.new_password)
    user.otp_code = None
    user.otp_expires_at = None
    user.otp_purpose = None
    user.otp_attempts = 0
    db.commit()

    log_audit_event(
        event_type="auth.password_reset_success",
        request=request,
        user_id=user.id,
        email=user.email,
        status="success",
    )

    return {
        "success": True,
        "message": "Password reset successfully. You may now sign in with your new credentials."
    }


@app.post(
    "/api/auth/mfa/verify",
    response_model=LoginResponse,
    dependencies=[Depends(rate_limit_dependency(max_requests=5, window_seconds=60, endpoint_label="mfa_verify"))]
)
def verify_mfa_login(req: MfaVerifyRequest, request: Request, db: Session = Depends(get_db)):
    """
    Completes 2FA login by verifying TOTP rolling code, email OTP, or emergency backup code.
    """
    user_id = decode_temp_2fa_token(req.temp_token)
    user = db.query(User).filter(User.id == user_id).first()

    if not user or not user.is_active or not user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA session or account is inactive.",
        )

    clean_code = req.code.strip()
    is_valid = False

    # 1. Try TOTP authenticator code
    if user.totp_secret:
        plain_secret = decrypt_data(user.totp_secret)
        if plain_secret and verify_totp_code(plain_secret, clean_code):
            is_valid = True

    # 2. Try single-use backup recovery code
    if not is_valid and user.backup_codes:
        normalized_code = clean_code.upper().strip()
        stored_hashes = list(user.backup_codes)
        for idx, h in enumerate(stored_hashes):
            if verify_password(normalized_code, h):
                is_valid = True
                stored_hashes.pop(idx)
                user.backup_codes = stored_hashes
                db.commit()
                logger.info("Consumed 1 backup recovery code for user %s", user.email)
                break

    # 3. Try email OTP (if method is email)
    if not is_valid and user.two_factor_method == "email" and user.otp_code:
        now_utc = datetime.now(timezone.utc)
        otp_exp = user.otp_expires_at if user.otp_expires_at.tzinfo else user.otp_expires_at.replace(tzinfo=timezone.utc)
        if now_utc <= otp_exp and secrets.compare_digest(user.otp_code, clean_code):
            is_valid = True
            user.otp_code = None
            user.otp_expires_at = None
            db.commit()

    if not is_valid:
        log_audit_event(
            event_type="auth.mfa_verify_failed",
            request=request,
            user_id=user.id,
            email=user.email,
            status="failure",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid two-factor authentication code or backup recovery code.",
        )

    log_audit_event(
        event_type="auth.mfa_login_success",
        request=request,
        user_id=user.id,
        email=user.email,
        status="success",
    )

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role})
    return LoginResponse(access_token=access_token, token_type="bearer", user=user_to_out(user))


@app.post("/api/auth/mfa/setup", response_model=MfaSetupResponse)
def setup_mfa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initializes 2FA setup by generating a fresh base32 TOTP secret,
    otpauth URI for QR codes, and 8 backup recovery codes.
    """
    secret = generate_totp_secret()
    backup_codes = generate_backup_codes(8)
    
    # Store encrypted secret and hashed backup codes (pending verification)
    current_user.totp_secret = encrypt_data(secret)
    current_user.backup_codes = [hash_password(c) for c in backup_codes]
    db.commit()

    otpauth_url = get_totp_uri(secret, current_user.email, issuer="NutriMenu AI")
    return MfaSetupResponse(
        secret_key=secret,
        secret=secret,
        otpauth_url=otpauth_url,
        otpauth_uri=otpauth_url,
        backup_codes=backup_codes,
    )


@app.post("/api/auth/mfa/enable")
def enable_mfa(
    req: MfaEnableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Confirms and permanently activates 2FA after user verifies code from authenticator app.
    """
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup has not been initiated. Please run setup first.",
        )

    secret = decrypt_data(current_user.totp_secret)
    if not secret or not verify_totp_code(secret, req.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 6-digit code. Please verify the code in your Authenticator app.",
        )

    current_user.two_factor_enabled = True
    current_user.two_factor_method = "authenticator"
    db.commit()

    return {"success": True, "message": "Two-factor authentication has been successfully enabled."}


@app.post("/api/auth/mfa/disable")
def disable_mfa(
    req: MfaDisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disables 2FA upon user password confirmation.
    """
    if not verify_password(req.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password. Cannot disable 2FA.",
        )

    current_user.two_factor_enabled = False
    current_user.totp_secret = None
    current_user.backup_codes = []
    db.commit()

    return {"success": True, "message": "Two-factor authentication has been disabled."}


@app.get("/api/auth/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Returns profile info of currently authenticated user."""
    return user_to_out(current_user)


@app.put("/api/auth/password")
def change_password(
    req: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Changes password after verifying existing credentials."""
    if not verify_password(req.old_password, current_user.hashed_password):
        log_audit_event(
            event_type="auth.password_change_failed",
            request=request,
            user_id=current_user.id,
            email=current_user.email,
            status="failure",
            details={"reason": "incorrect_current_password"}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    current_user.hashed_password = hash_password(req.new_password)
    db.commit()

    log_audit_event(
        event_type="auth.password_changed",
        request=request,
        user_id=current_user.id,
        email=current_user.email,
        status="success",
    )

    return {"success": True, "message": "Password changed successfully."}


@app.delete("/api/auth/account")
def delete_account(
    req: AccountDelete,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Permanently deletes user account, profile, and history upon password confirmation."""
    if not verify_password(req.password, current_user.hashed_password):
        log_audit_event(
            event_type="auth.account_delete_failed",
            request=request,
            user_id=current_user.id,
            email=current_user.email,
            status="failure",
            details={"reason": "incorrect_password"}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password. Account deletion aborted.",
        )

    user_id = current_user.id
    email = current_user.email

    db.delete(current_user)
    db.commit()

    log_audit_event(
        event_type="auth.account_deleted",
        request=request,
        user_id=user_id,
        email=email,
        status="success",
    )

    return {"success": True, "message": "Account permanently deleted."}



# =====================================================================
# 👤 USER PROFILE & HEALTH MATRIX STORAGE ENDPOINTS
# =====================================================================

@app.get("/api/profile", response_model=UserProfileOut)
def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetches user health profile and cached metabolic matrix."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@app.put("/api/profile", response_model=UserProfileOut)
def update_user_profile(
    req: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates user biometrics, allergies, conditions, and caches metabolic matrix."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    if req.age is not None:
        profile.age = req.age
    if req.gender is not None:
        profile.gender = req.gender
    if req.height_cm is not None:
        profile.height_cm = req.height_cm
    if req.weight_kg is not None:
        profile.weight_kg = req.weight_kg
    if req.activity_level is not None:
        profile.activity_level = req.activity_level
    if req.primary_goal is not None:
        profile.primary_goal = req.primary_goal
    if req.health_conditions is not None:
        profile.health_conditions = req.health_conditions
    if req.allergies is not None:
        profile.allergies = req.allergies
    if req.dietary_preferences is not None:
        profile.dietary_preferences = req.dietary_preferences
    if req.raw_bio_text is not None:
        profile.raw_bio_text = req.raw_bio_text
    if req.cached_matrix is not None:
        profile.cached_matrix = req.cached_matrix

    db.commit()
    db.refresh(profile)
    return profile


@app.post("/api/profile/apikey")
def update_encrypted_api_key(
    req: ApiKeyUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Securely stores user's Gemini/OpenRouter key encrypted at rest using Fernet AES."""
    if req.api_key and req.api_key.strip():
        current_user.encrypted_api_key = encrypt_data(req.api_key.strip())
    else:
        current_user.encrypted_api_key = None
    db.commit()

    log_audit_event(
        event_type="auth.apikey_updated",
        request=request,
        user_id=current_user.id,
        email=current_user.email,
        status="success",
        details={"has_custom_key": bool(current_user.encrypted_api_key)}
    )

    return {"success": True, "has_custom_api_key": bool(current_user.encrypted_api_key)}


# =====================================================================
# 🍱 LOGGED MEALS & CALENDAR HISTORY ENDPOINTS
# =====================================================================

@app.get("/api/meals", response_model=List[LoggedMealOut])
def get_user_meals(
    date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves authenticated user's logged meals, optionally filtered by date (YYYY-MM-DD)."""
    query = db.query(LoggedMeal).filter(LoggedMeal.user_id == current_user.id)
    if date:
        query = query.filter(LoggedMeal.date == date)
    meals = query.order_by(LoggedMeal.timestamp.desc()).all()
    return meals


@app.post("/api/meals", response_model=LoggedMealOut, status_code=status.HTTP_201_CREATED)
def save_user_meal(
    req: LoggedMealCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Persists a meal to the database with cumulative macro breakdown."""
    import uuid
    meal_id = req.id or str(uuid.uuid4())

    # Check if meal exists to update, or create new
    existing = db.query(LoggedMeal).filter(
        LoggedMeal.id == meal_id,
        LoggedMeal.user_id == current_user.id
    ).first()

    if existing:
        existing.name = req.name
        existing.meal_type = req.meal_type
        existing.date = req.date
        existing.dishes = req.dishes
        existing.total_calories = req.total_calories
        existing.total_protein = req.total_protein
        existing.total_carbs = req.total_carbs
        existing.total_fats = req.total_fats
        existing.total_sodium = req.total_sodium
        if req.timestamp:
            existing.timestamp = req.timestamp
        db.commit()
        db.refresh(existing)
        return existing

    new_meal = LoggedMeal(
        id=meal_id,
        user_id=current_user.id,
        name=req.name,
        meal_type=req.meal_type,
        date=req.date,
        dishes=req.dishes,
        total_calories=req.total_calories,
        total_protein=req.total_protein,
        total_carbs=req.total_carbs,
        total_fats=req.total_fats,
        total_sodium=req.total_sodium,
    )
    if req.timestamp:
        new_meal.timestamp = req.timestamp
    db.add(new_meal)
    db.commit()
    db.refresh(new_meal)
    return new_meal


@app.delete("/api/meals/{meal_id}")
def delete_user_meal(
    meal_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a logged meal belonging to the authenticated user."""
    meal = db.query(LoggedMeal).filter(
        LoggedMeal.id == meal_id,
        LoggedMeal.user_id == current_user.id
    ).first()

    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal record not found or access denied.",
        )

    db.delete(meal)
    db.commit()
    return {"success": True, "deleted_id": meal_id}


@app.get("/api/meals/export/csv")
def export_user_meals_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Exports authenticated user's logged meals as downloadable CSV."""
    import csv
    import io
    from fastapi.responses import Response

    meals = (
        db.query(LoggedMeal)
        .filter(LoggedMeal.user_id == current_user.id)
        .order_by(LoggedMeal.date.desc(), LoggedMeal.timestamp.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Date",
        "Meal Name",
        "Meal Type",
        "Total Calories (kcal)",
        "Protein (g)",
        "Carbs (g)",
        "Fats (g)",
        "Sodium (mg)",
        "Dishes Included",
    ])

    for m in meals:
        dish_names = []
        if isinstance(m.dishes, list):
            for d in m.dishes:
                if isinstance(d, dict):
                    dish_names.append(f"{d.get('name', 'Item')} (x{d.get('portion', 1)})")
                else:
                    dish_names.append(str(d))

        writer.writerow([
            m.date,
            m.name,
            m.meal_type,
            round(m.total_calories, 1),
            round(m.total_protein, 1),
            round(m.total_carbs, 1),
            round(m.total_fats, 1),
            round(m.total_sodium, 1),
            "; ".join(dish_names),
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=nutrimenu_meal_history.csv"}
    )


# =====================================================================
# 📋 SAVED MENUS & SCAN HISTORY ENDPOINTS
# =====================================================================

@app.get("/api/menus", response_model=List[SavedMenuOut])
def get_user_saved_menus(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves all saved menus belonging to the authenticated user."""
    menus = (
        db.query(SavedMenu)
        .filter(SavedMenu.user_id == current_user.id)
        .order_by(SavedMenu.created_at.desc())
        .all()
    )
    return menus


@app.post("/api/menus", response_model=SavedMenuOut, status_code=status.HTTP_201_CREATED)
def create_saved_menu(
    req: SavedMenuCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Explicitly saves a menu scan to the user's history."""
    menu = SavedMenu(
        id=req.id or str(uuid.uuid4()),
        user_id=current_user.id,
        title=req.title,
        dishes=req.dishes,
        image_url=req.image_url,
        filename=req.filename,
    )
    db.add(menu)
    db.commit()
    db.refresh(menu)
    return menu


@app.delete("/api/menus/{menu_id}")
def delete_saved_menu(
    menu_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a saved menu and cleans up its local image file if present."""
    menu = db.query(SavedMenu).filter(
        SavedMenu.id == menu_id,
        SavedMenu.user_id == current_user.id
    ).first()

    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu record not found or access denied.",
        )

    # Clean up local image file
    if menu.image_url and menu.image_url.startswith("/uploads/"):
        relative_path = menu.image_url.lstrip("/")
        full_path = Path(__file__).resolve().parent.parent / relative_path
        if full_path.exists():
            try:
                full_path.unlink()
            except Exception as e:
                logger.warning("Could not delete file %s: %s", full_path, e)

    db.delete(menu)
    db.commit()
    return {"success": True, "deleted_id": menu_id}


# =====================================================================
# 🥗 OCR & RECOMMENDATION PIPELINE (WITH AUTHENTICATED KEY RESOLUTION)
# =====================================================================

def resolve_effective_api_key(
    provided_key: Optional[str],
    optional_user: Optional[User]
) -> Optional[str]:
    """Resolves API key with priority: request param > user's encrypted key > env var."""
    if provided_key and len(provided_key.strip()) > 5:
        return provided_key.strip()
    if optional_user and optional_user.encrypted_api_key:
        decrypted = decrypt_data(optional_user.encrypted_api_key)
        if decrypted and len(decrypted.strip()) > 5:
            return decrypted.strip()
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("OPENROUTER_API_KEY")


@app.get("/")
def read_root():
    return {
        "status": "ok", 
        "service": "NutriMenu AI Full-Stack Platform", 
        "version": "2.0.0",
        "security": "Better Auth Standards (Rate Limiting, CSRF Origin Guard, Dummy Hash Timing Defense, Bcrypt, Fernet AES) Active",
    }


@app.get("/api/health")
def health_check(optional_user: Optional[User] = Depends(get_optional_current_user)):
    effective_key = resolve_effective_api_key(None, optional_user)
    return {
        "status": "ok",
        "gemini_available": bool(effective_key and len(effective_key.strip()) >= 10),
        "model": os.getenv("GEMINI_MODEL", "gemini-3.7-flash"),
        "user_authenticated": optional_user is not None,
        "security": {
            "rate_limiting": "enabled",
            "csrf_guard": "enabled",
            "timing_attack_defense": "enabled",
            "trusted_origins_count": len(trusted_origins),
        }
    }


# =====================================================================
# ⚡ ASYNCHRONOUS NON-BLOCKING AI JOBS & REAL-TIME PROGRESS STREAMING
# =====================================================================

def run_menu_analysis_task(
    job_id: str,
    dest_path: str,
    original_filename: str,
    image_url: str,
    api_key: Optional[str],
    user_id: Optional[int],
    profile_data: Optional[Dict[str, Any]],
):
    """Executes OCR extraction, matrix calculation, and 3-tier scoring asynchronously with progress updates."""
    try:
        job_manager.update_progress(job_id, 25, "Running Vision OCR & extracting menu dishes...", stage_id="ocr")
        pipeline = MenuRecognitionPipeline(api_key=api_key)
        recognized_menu = pipeline.process_image(dest_path)

        flat_items = recognized_menu.to_flat_items()
        flattened_dishes = []
        seen = set()

        for item in flat_items:
            item_str = item.name if hasattr(item, "name") else str(item)
            parts = re.split(r'[,/\n;]', item_str)
            for part in parts:
                clean_name = part.strip()
                clean_name = re.sub(
                    r'^(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Breakfast|Lunch|Snacks|Dinner)\s*[:\-]?\s*', 
                    '', 
                    clean_name, 
                    flags=re.IGNORECASE
                ).strip()

                if clean_name and len(clean_name) > 1 and not clean_name.isdigit():
                    title_name = clean_name.title()
                    if title_name.lower() not in seen:
                        seen.add(title_name.lower())
                        flattened_dishes.append(title_name)

        if not flattened_dishes and hasattr(recognized_menu, "get_item_names"):
            for item in recognized_menu.get_item_names():
                title_name = str(item).strip().title()
                if title_name.lower() not in seen:
                    seen.add(title_name.lower())
                    flattened_dishes.append(title_name)

        formatted_dishes = [
            {"id": idx + 1, "name": item, "section": "Menu Items"}
            for idx, item in enumerate(flattened_dishes)
        ]

        # Stage 3: Clinical Matrix Synthesis
        job_manager.update_progress(
            job_id,
            55,
            f"Extracted {len(flattened_dishes)} dishes. Calculating clinical metabolic matrix...",
            stage_id="matrix",
        )
        effective_profile = profile_data or {
            "age": 35,
            "gender": "male",
            "height_cm": 175,
            "weight_kg": 75,
            "activity_level": "moderate",
            "primary_goal": "maintenance",
        }

        try:
            generator = AIMatrixGenerator(api_key=api_key)
            matrix = generator.generate(effective_profile)
        except Exception:
            generator = AIMatrixGenerator()
            matrix = generator._generate_deterministic(effective_profile)

        # Stage 4: 3-Tier Safety & Recommendation Evaluation
        job_manager.update_progress(
            job_id,
            80,
            "Scoring dishes against allergens, sodium ceilings & glycemic sensitivity...",
            stage_id="recommend",
        )

        candidate_dishes = []
        for dish in formatted_dishes:
            name = dish["name"]
            valid, _ = is_valid_food_item(name, allow_beverages=True)
            if valid or (len(name) >= 2 and any(c.isalpha() for c in name)):
                candidate_dishes.append({"name": name, "price": "", "description": "", "tags": []})

        rec_result_dict = {}
        if candidate_dishes:
            recommender = TieredFoodRecommender(user_matrix=matrix, api_key=api_key)
            rec_result = recommender.recommend_menu(candidate_dishes)
            rec_result_dict = rec_result.to_dict()

        # Persist to database if authenticated user
        saved_menu_id = None
        if user_id:
            try:
                from backend.database import SessionLocal
                db = SessionLocal()
                try:
                    base_title = Path(original_filename or 'Scan').stem.replace('_', ' ').replace('-', ' ').title()
                    saved_menu = SavedMenu(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        title=f"Menu - {base_title}",
                        dishes=formatted_dishes,
                        image_url=image_url,
                        filename=original_filename,
                    )
                    db.add(saved_menu)
                    db.commit()
                    db.refresh(saved_menu)
                    saved_menu_id = saved_menu.id
                finally:
                    db.close()
            except Exception as save_err:
                logger.warning("Could not persist SavedMenu in background job: %s", save_err)

        job_manager.complete_job(job_id, {
            "filename": original_filename,
            "image_url": image_url,
            "saved_menu_id": saved_menu_id,
            "total_extracted": len(flattened_dishes),
            "dishes": formatted_dishes,
            "items": flattened_dishes,
            "matrix": matrix.to_dict(),
            "recommendations": rec_result_dict,
        })
    except Exception as e:
        logger.error("Menu analysis background job %s failed: %s", job_id, e)
        job_manager.fail_job(job_id, str(e))


@app.post("/api/jobs/menu-scan")
async def start_menu_scan_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    api_key: Optional[str] = Form(None),
    profile: Optional[str] = Form(None),
    optional_user: Optional[User] = Depends(get_optional_current_user),
):
    """Enqueues an asynchronous menu OCR and recommendation evaluation job."""
    is_image = (
        (file.content_type and file.content_type.startswith("image/"))
        or (file.filename and file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif')))
    )
    if not is_image:
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    effective_api_key = resolve_effective_api_key(api_key, optional_user)

    clean_original = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename or "menu.jpg")
    unique_filename = f"{uuid.uuid4().hex[:12]}_{clean_original}"
    dest_path = UPLOAD_MENUS_DIR / unique_filename

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    image_url = f"/uploads/menus/{unique_filename}"

    parsed_profile = None
    if profile:
        try:
            parsed_profile = json.loads(profile)
        except Exception:
            parsed_profile = None

    user_id = optional_user.id if optional_user else None

    job_id = job_manager.create_job(job_type="menu_scan", user_id=user_id)

    background_tasks.add_task(
        run_menu_analysis_task,
        job_id=job_id,
        dest_path=str(dest_path),
        original_filename=file.filename or "menu.jpg",
        image_url=image_url,
        api_key=effective_api_key,
        user_id=user_id,
        profile_data=parsed_profile,
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "progress": 10,
        "stage": "Job queued and processing started",
        "image_url": image_url,
        "filename": file.filename,
    }


@app.get("/api/jobs/{job_id}")
def get_job_status(
    job_id: str,
    optional_user: Optional[User] = Depends(get_optional_current_user),
):
    """Retrieves current job status, progress percentage, and final results when ready, isolated by tenant."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired.")
    
    # Enforce multi-tenant data isolation: users cannot inspect other users' jobs
    job_user_id = job.get("user_id")
    if job_user_id is not None:
        if not optional_user or optional_user.id != job_user_id:
            raise HTTPException(status_code=404, detail="Job not found or access denied.")
            
    return job


@app.get("/api/jobs/{job_id}/stream")
async def stream_job_progress(
    job_id: str,
    request: Request,
    optional_user: Optional[User] = Depends(get_optional_current_user),
):
    """Server-Sent Events (SSE) stream for real-time progress updates, isolated by tenant."""
    init_job = job_manager.get_job(job_id)
    if not init_job:
        raise HTTPException(status_code=404, detail="Job not found or expired.")
    job_user_id = init_job.get("user_id")
    if job_user_id is not None:
        if not optional_user or optional_user.id != job_user_id:
            raise HTTPException(status_code=404, detail="Job not found or access denied.")

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break

            job = job_manager.get_job(job_id)
            if not job:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                break

            yield f"data: {json.dumps(job)}\n\n"

            if job.get("status") in {"completed", "failed"}:
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/api/ocr/extract")
async def extract_menu_from_image(
    file: UploadFile = File(...), 
    api_key: Optional[str] = Form(None),
    optional_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    is_image = (
        (file.content_type and file.content_type.startswith("image/"))
        or (file.filename and file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif')))
    )
    if not is_image:
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    effective_api_key = resolve_effective_api_key(api_key, optional_user)

    # Persist the uploaded file to local disk
    clean_original = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename or "menu.jpg")
    unique_filename = f"{uuid.uuid4().hex[:12]}_{clean_original}"
    dest_path = UPLOAD_MENUS_DIR / unique_filename

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    image_url = f"/uploads/menus/{unique_filename}"

    try:
        pipeline = MenuRecognitionPipeline(api_key=effective_api_key)
        recognized_menu = pipeline.process_image(str(dest_path))

        flat_items = recognized_menu.to_flat_items()

        flattened_dishes = []
        seen = set()

        for item in flat_items:
            item_str = item.name if hasattr(item, "name") else str(item)
            parts = re.split(r'[,/\n;]', item_str)
            for part in parts:
                clean_name = part.strip()
                clean_name = re.sub(
                    r'^(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Breakfast|Lunch|Snacks|Dinner)\s*[:\-]?\s*', 
                    '', 
                    clean_name, 
                    flags=re.IGNORECASE
                ).strip()

                if clean_name and len(clean_name) > 1 and not clean_name.isdigit():
                    title_name = clean_name.title()
                    if title_name.lower() not in seen:
                        seen.add(title_name.lower())
                        flattened_dishes.append(title_name)

        if not flattened_dishes and hasattr(recognized_menu, "get_item_names"):
            for item in recognized_menu.get_item_names():
                title_name = str(item).strip().title()
                if title_name.lower() not in seen:
                    seen.add(title_name.lower())
                    flattened_dishes.append(title_name)

        formatted_dishes = [
            {"id": idx + 1, "name": item, "section": "Menu Items"}
            for idx, item in enumerate(flattened_dishes)
        ]

        saved_menu_id = None
        if optional_user and db:
            try:
                base_title = Path(file.filename or 'Scan').stem.replace('_', ' ').replace('-', ' ').title()
                saved_menu = SavedMenu(
                    id=str(uuid.uuid4()),
                    user_id=optional_user.id,
                    title=f"Menu - {base_title}",
                    dishes=formatted_dishes,
                    image_url=image_url,
                    filename=file.filename,
                )
                db.add(saved_menu)
                db.commit()
                db.refresh(saved_menu)
                saved_menu_id = saved_menu.id
            except Exception as save_err:
                logger.warning("Could not automatically persist SavedMenu: %s", save_err)

        return {
            "success": True,
            "filename": file.filename,
            "image_url": image_url,
            "saved_menu_id": saved_menu_id,
            "total_extracted": len(flattened_dishes),
            "dishes": formatted_dishes,
            "items": flattened_dishes,
            "metadata": recognized_menu.metadata,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("OCR extraction failed: %s", e)
        if dest_path.exists():
            try:
                dest_path.unlink()
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"OCR extraction failed: {str(e)}")


@app.post("/api/matrix/generate")
async def generate_matrix(
    req: Dict[str, Any],
    optional_user: Optional[User] = Depends(get_optional_current_user),
):
    user_prof = req.get("profile") or req.get("user_profile") or req
    api_key = resolve_effective_api_key(req.get("api_key"), optional_user)

    try:
        generator = AIMatrixGenerator(api_key=api_key)
        matrix = generator.generate(user_prof)
        return {"success": True, "matrix": matrix.to_dict()}
    except Exception as e:
        logger.warning("AI matrix generation fallback: %s", e)
        fallback_gen = AIMatrixGenerator()
        matrix = fallback_gen._generate_deterministic(user_prof)
        return {"success": True, "matrix": matrix.to_dict(), "fallback": True, "error": str(e)}


@app.post("/api/recommend/evaluate")
async def evaluate_recommendations(
    req: Dict[str, Any],
    optional_user: Optional[User] = Depends(get_optional_current_user),
):
    raw_items = req.get("dishes") or req.get("items") or []
    matrix_dict = req.get("matrix")
    user_prof = req.get("profile") or req.get("user_profile") or {}
    api_key = resolve_effective_api_key(req.get("api_key"), optional_user)

    matrix: Optional[UserNutritionalMatrix] = None
    if matrix_dict and isinstance(matrix_dict, dict) and "metabolic_targets" in matrix_dict:
        try:
            matrix = UserNutritionalMatrix.from_dict(matrix_dict)
        except Exception:
            matrix = None

    if matrix is None:
        generator = AIMatrixGenerator(api_key=api_key)
        matrix = generator.generate(user_prof or {
            "age": 35,
            "gender": "male",
            "height_cm": 175,
            "weight_kg": 75,
            "activity_level": "moderate",
            "primary_goal": "maintenance",
            "health_conditions": [],
            "allergies": [],
            "dietary_preferences": [],
        })

    dishes = []
    seen = set()

    for item in raw_items:
        if isinstance(item, dict):
            name = item.get("name") or item.get("label") or item.get("dish_name") or ""
            price = item.get("price") or item.get("raw_price") or ""
            desc = item.get("description") or ""
            tags = item.get("tags") or item.get("dietary_tags") or []
        else:
            name = str(item)
            price = ""
            desc = ""
            tags = []

        name = name.strip()
        if not name or name.lower() in seen:
            continue

        valid, _ = is_valid_food_item(name, allow_beverages=True)
        if not valid and (len(name) < 2 or not any(c.isalpha() for c in name)):
            continue

        seen.add(name.lower())
        dishes.append({
            "name": name,
            "price": price,
            "description": desc,
            "tags": tags,
        })

    if not dishes:
        empty_payload = {
            "user_summary": matrix.user_summary,
            "total_items_evaluated": 0,
            "tier_counts": {"GOOD": 0, "MEDIUM": 0, "BAD": 0},
            "good_items": [],
            "medium_items": [],
            "bad_items": [],
            "all_recommendations": [],
            "top_pick": None
        }
        return {"success": True, "result": empty_payload, "recommendations": empty_payload}

    recommender = TieredFoodRecommender(user_matrix=matrix, api_key=api_key)
    rec_result: TieredRecommendationResult = recommender.recommend_menu(dishes)
    result_dict = rec_result.to_dict()

    return {
        "success": True,
        "result": result_dict,
        "recommendations": result_dict,
    }


@app.post("/api/plate/evaluate")
async def evaluate_plate_meal(
    req: Dict[str, Any],
    optional_user: Optional[User] = Depends(get_optional_current_user),
):
    plate_items = req.get("plate") or req.get("items") or []
    matrix_dict = req.get("matrix")
    user_prof = req.get("profile") or {}
    api_key = resolve_effective_api_key(req.get("api_key"), optional_user)

    matrix: Optional[UserNutritionalMatrix] = None
    if matrix_dict and isinstance(matrix_dict, dict) and "metabolic_targets" in matrix_dict:
        try:
            matrix = UserNutritionalMatrix.from_dict(matrix_dict)
        except Exception:
            matrix = None

    if matrix is None:
        generator = AIMatrixGenerator(api_key=api_key)
        matrix = generator.generate(user_prof or {
            "age": 35,
            "gender": "male",
            "height_cm": 175,
            "weight_kg": 75,
        })

    from src.plate_optimizer import PlateOptimizer
    optimizer = PlateOptimizer(user_matrix=matrix, api_key=api_key)
    plate_summary = optimizer.evaluate_plate(plate_items, user_matrix=matrix)

    return {
        "success": True,
        "plate_evaluation": plate_summary,
    }


@app.post("/api/plate/complete")
async def complete_plate_suggestions(
    req: Dict[str, Any],
    optional_user: Optional[User] = Depends(get_optional_current_user),
):
    plate_items = req.get("plate") or []
    candidate_menu = req.get("menu_dishes") or req.get("dishes") or []
    matrix_dict = req.get("matrix")
    api_key = resolve_effective_api_key(req.get("api_key"), optional_user)

    matrix: Optional[UserNutritionalMatrix] = None
    if matrix_dict and isinstance(matrix_dict, dict) and "metabolic_targets" in matrix_dict:
        try:
            matrix = UserNutritionalMatrix.from_dict(matrix_dict)
        except Exception:
            matrix = None

    if matrix is None:
        user_prof = req.get("profile") or req.get("user_profile") or {}
        generator = AIMatrixGenerator(api_key=api_key)
        matrix = generator.generate(user_prof or {
            "age": 35,
            "gender": "male",
            "height_cm": 175,
            "weight_kg": 75,
        })

    from src.plate_optimizer import PlateOptimizer
    optimizer = PlateOptimizer(user_matrix=matrix, api_key=api_key)
    clean_candidates = [
        d["name"] if isinstance(d, dict) and "name" in d else str(d)
        for d in candidate_menu
    ]
    suggestions = optimizer.suggest_plate_companions(plate_items, clean_candidates, user_matrix=matrix)

    return {
        "success": True,
        "suggestions": suggestions,
    }
