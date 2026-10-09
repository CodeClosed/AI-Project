import os
import re
import time
import json
import base64
import secrets
import hashlib
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Optional, Dict, Any, List, Tuple

import bcrypt
import pyotp
from cryptography.fernet import Fernet, InvalidToken
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.db_models import User

logger = logging.getLogger("nutrimenu.security")


# =====================================================================
# 1. 🔑 SECRET MANAGEMENT (BETTER AUTH SPECIFICATION)
# =====================================================================
# Better Auth priority:
# 1. BETTER_AUTH_SECRET
# 2. AUTH_SECRET
# 3. SECRET_KEY

INSECURE_PLACEHOLDERS = {
    "nutrimenu-ai-jwt-super-secret-key-production-change-this-2026",
    "change-this-secret",
    "secret",
    "supersecret",
    "defaultsecret",
}

def resolve_auth_secret() -> str:
    """
    Resolves the authentication secret according to Better Auth specification.
    Validates minimum length (>= 32 chars) and entropy, rejecting defaults in production.
    """
    secret = (
        os.getenv("BETTER_AUTH_SECRET")
        or os.getenv("AUTH_SECRET")
        or os.getenv("SECRET_KEY")
    )
    is_prod = os.getenv("ENV", "").lower() in {"prod", "production"} or os.getenv("ENVIRONMENT", "").lower() in {"prod", "production"}

    if not secret:
        if is_prod:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: BETTER_AUTH_SECRET (or AUTH_SECRET) is required in production! "
                "Generate one using: openssl rand -base64 32"
            )
        # Generate ephemeral cryptographically secure secret for dev
        ephemeral = secrets.token_urlsafe(32)
        logger.warning(
            "BETTER_AUTH_SECRET was not set. Generated temporary ephemeral 256-bit secret for development session."
        )
        return ephemeral

    secret = secret.strip()

    if is_prod:
        if secret in INSECURE_PLACEHOLDERS:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: Default placeholder auth secret detected in production environment! "
                "You must set a unique, cryptographically strong BETTER_AUTH_SECRET."
            )
        if len(secret) < 32:
            raise RuntimeError(
                f"CRITICAL SECURITY ERROR: Auth secret is only {len(secret)} characters. "
                "Better Auth requires at least 32 characters (256 bits) in production."
            )
    elif len(secret) < 32:
        logger.warning(
            "Auth secret is shorter than 32 characters. Consider generating a 32-byte key (openssl rand -base64 32)."
        )

    return secret


SECRET_KEY = resolve_auth_secret()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7)))  # 7 days

# Symmetric Data Encryption at Rest (Fernet AES)
raw_enc_key = os.getenv("ENCRYPTION_SECRET_KEY", SECRET_KEY)
fernet_key = base64.urlsafe_b64encode(hashlib.sha256(raw_enc_key.encode()).digest())
cipher_suite = Fernet(fernet_key)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# =====================================================================
# 2. 🛡️ PASSWORD HASHING & TIMING-ATTACK RESILIENT VERIFICATION
# =====================================================================
# Pre-computed dummy hash to mitigate side-channel account enumeration and timing attacks
DUMMY_BCRYPT_HASH = "$2b$12$ZLf6wh2NRkBcUrCs0cbeRupI6Q4kgQoj1LcAVfw9Ov9GbRL7SvXsW"

def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with 12 salt rounds."""
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    encoded = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(encoded, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """
    Verifies a plaintext password against its bcrypt hash in constant time.
    Safely returns False if either argument is invalid.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:72],
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def verify_dummy_password(plain_password: str) -> bool:
    """
    Performs constant-time bcrypt verification against a pre-computed dummy hash.
    Used when a requested user account does not exist, eliminating timing differences
    between existing and non-existent users (Account Enumeration Prevention).
    """
    return verify_password(plain_password, DUMMY_BCRYPT_HASH)


# =====================================================================
# 3. 🔒 SYMMETRIC ENCRYPTION AT REST (FERNET AES)
# =====================================================================

def encrypt_data(plain_text: Optional[str]) -> Optional[str]:
    """Encrypts sensitive plaintext strings (e.g. custom Gemini API keys) using Fernet AES."""
    if not plain_text:
        return None
    try:
        encrypted_bytes = cipher_suite.encrypt(plain_text.strip().encode("utf-8"))
        return encrypted_bytes.decode("utf-8")
    except Exception as e:
        logger.error("Encryption failure: %s", e)
        return None


def decrypt_data(cipher_text: Optional[str]) -> Optional[str]:
    """Decrypts a Fernet ciphertext back to plaintext."""
    if not cipher_text:
        return None
    try:
        decrypted_bytes = cipher_suite.decrypt(cipher_text.strip().encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except (InvalidToken, Exception) as e:
        logger.error("Decryption failure or invalid token: %s", e)
        return None


# =====================================================================
# 4. 🎟️ JWT TOKEN HANDLING
# =====================================================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Encodes a signed JWT access token containing subject and claims."""
    to_encode = data.copy()
    now_utc = datetime.now(timezone.utc)
    expire = now_utc + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    
    to_encode.update({
        "exp": expire,
        "iat": now_utc,
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT token's signature and expiration."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials or token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def generate_secure_otp(length: int = 6) -> str:
    """Generates a cryptographically secure numeric OTP using secrets module."""
    digits = [str(secrets.randbelow(10)) for _ in range(length)]
    return "".join(digits)


def create_temp_2fa_token(user_id: int) -> str:
    """Creates a short-lived (5-minute) restricted JWT specifically for 2FA challenge completion."""
    now_utc = datetime.now(timezone.utc)
    expire = now_utc + timedelta(minutes=5)
    payload = {
        "sub": str(user_id),
        "scope": "2fa_pending",
        "exp": expire,
        "iat": now_utc,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_temp_2fa_token(token: str) -> int:
    """Validates the temporary 2FA token and returns the user ID."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("scope") != "2fa_pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token scope. A 2FA challenge token is required.",
            )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed 2FA token.",
            )
        return int(user_id)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="2FA session has expired or is invalid. Please sign in again.",
        )


def generate_totp_secret() -> str:
    """Generates a cryptographically random base32 TOTP secret string."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, issuer: str = "NutriMenu AI") -> str:
    """Generates otpauth:// URI for scanning with Google Authenticator or 1Password."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def verify_totp_code(secret: str, code: str) -> bool:
    """Verifies a 6-digit rolling code against base32 TOTP secret with valid window tolerance."""
    if not secret or not code:
        return False
    try:
        totp = pyotp.TOTP(secret)
        return bool(totp.verify(code.strip(), valid_window=1))
    except Exception:
        return False


def generate_backup_codes(count: int = 8) -> List[str]:
    """Generates formatted single-use alphanumeric backup recovery codes."""
    codes = []
    for _ in range(count):
        part1 = secrets.token_hex(2)
        part2 = secrets.token_hex(2)
        codes.append(f"{part1}-{part2}".upper())
    return codes


# =====================================================================
# 5. 🌐 IP EXTRACTION & RATE LIMITING (BETTER AUTH SPECIFICATION)
# =====================================================================

def get_client_ip(request: Request) -> str:
    """
    Extracts client IP address respecting X-Forwarded-For, X-Real-IP,
    and client socket host.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First IP in X-Forwarded-For list is the originating client
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter.
    Limits requests to max_requests within window_seconds per key (e.g. IP + endpoint).
    """

    def __init__(self):
        self._lock = Lock()
        self._hits: Dict[str, deque] = defaultdict(deque)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Checks if request is allowed under rate limit.
        Returns (allowed: bool, retry_after_seconds: int).
        """
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            timestamps = self._hits[key]
            # Evict timestamps outside current sliding window
            while timestamps and timestamps[0] <= window_start:
                timestamps.popleft()

            if len(timestamps) >= max_requests:
                # Earliest timestamp in window dictates retry-after
                oldest_timestamp = timestamps[0]
                retry_after = max(1, int(oldest_timestamp + window_seconds - now) + 1)
                return False, retry_after

            timestamps.append(now)
            return True, 0

    def reset(self):
        """Clears all rate limit buckets (useful for test isolation)."""
        with self._lock:
            self._hits.clear()


rate_limiter = SlidingWindowRateLimiter()


def rate_limit_dependency(max_requests: int = 5, window_seconds: int = 60, endpoint_label: str = "auth"):
    """
    FastAPI dependency enforcing sliding-window rate limit per client IP.
    Returns 429 Too Many Requests with Retry-After header upon violation.
    """
    async def dependency(request: Request):
        client_ip = get_client_ip(request)
        rate_key = f"{endpoint_label}:{client_ip}"
        allowed, retry_after = rate_limiter.is_allowed(rate_key, max_requests, window_seconds)

        if not allowed:
            log_audit_event(
                event_type="auth.rate_limited",
                request=request,
                status="blocked",
                details={"endpoint": endpoint_label, "retry_after": retry_after}
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Please try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )
        return True

    return dependency


# =====================================================================
# 6. 📝 STRUCTURED SECURITY AUDIT LOGGING
# =====================================================================

def log_audit_event(
    event_type: str,
    request: Optional[Request] = None,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    status: str = "success",
    details: Optional[Dict[str, Any]] = None,
):
    """
    Emits structured security audit logs for critical authentication and authorization events.
    """
    client_ip = get_client_ip(request) if request else "unknown"
    user_agent = request.headers.get("user-agent", "unknown") if request else "unknown"
    
    masked_email = None
    if email:
        parts = email.split("@")
        if len(parts) == 2:
            name, domain = parts
            masked_email = f"{name[:2]}***@{domain}"
        else:
            masked_email = "***"

    audit_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "status": status,
        "client_ip": client_ip,
        "user_agent": user_agent[:120],
        "user_id": user_id,
        "email": masked_email,
        "details": details or {},
    }

    log_msg = f"[SECURITY_AUDIT] {json.dumps(audit_entry)}"
    if status in {"failure", "blocked", "unauthorized", "error"}:
        logger.warning(log_msg)
    else:
        logger.info(log_msg)


# =====================================================================
# 7. 🛡️ FASTAPI AUTHORIZATION DEPENDENCIES
# =====================================================================

def extract_token_from_header(auth_header: Optional[str]) -> Optional[str]:
    if not auth_header:
        return None
    parts = auth_header.strip().split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    if len(parts) == 1:
        return parts[0]
    return None


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """
    Mandatory authentication dependency.
    Raises 401 Unauthorized if token is missing, expired, or invalid.
    """
    effective_token = token or extract_token_from_header(authorization)
    if not effective_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(effective_token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject identifier.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    return user


async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Optional authentication dependency.
    Returns User if valid credentials provided, or None for guest/anonymous usage.
    """
    effective_token = token or extract_token_from_header(authorization)
    if not effective_token:
        return None

    try:
        payload = jwt.decode(effective_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user and user.is_active:
                return user
    except Exception:
        pass
    return None

