import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from backend.db_models import VerificationCode
from backend.settings import settings


def hash_code(code: str) -> str:
    """Computes HMAC-SHA256 digest of 6-digit numeric verification code using server auth secret."""
    secret_bytes = settings.get_auth_secret().encode("utf-8")
    return hmac.new(secret_bytes, code.strip().encode("utf-8"), hashlib.sha256).hexdigest()


def generate_numeric_code(length: int = 6) -> str:
    """Generates cryptographically random numeric code."""
    digits = [str(secrets.randbelow(10)) for _ in range(length)]
    return "".join(digits)


def issue_verification_code(
    db: Session,
    user_id: int,
    purpose: str,
    new_email: Optional[str] = None,
    expires_minutes: int = 10,
) -> str:
    """
    Issues a fresh verification code for a specific user and purpose.
    Invalidates any prior pending codes for the same purpose and returns the plaintext code
    strictly for immediate transactional dispatch (code is never stored in plaintext).
    """
    # Invalidate previous unconsumed codes for this user and purpose
    now = datetime.now(timezone.utc)
    prior_codes = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.user_id == user_id,
            VerificationCode.purpose == purpose,
            VerificationCode.consumed_at.is_(None),
        )
        .all()
    )
    for c in prior_codes:
        c.consumed_at = now

    raw_code = generate_numeric_code(6)
    code_digest = hash_code(raw_code)

    record = VerificationCode(
        user_id=user_id,
        purpose=purpose,
        code_hash=code_digest,
        new_email=new_email.strip().lower() if new_email else None,
        attempts=0,
        expires_at=now + timedelta(minutes=expires_minutes),
        created_at=now,
    )
    db.add(record)
    db.commit()
    return raw_code


def verify_code(
    db: Session,
    user_id: int,
    purpose: str,
    candidate_code: str,
    max_attempts: int = 5,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Verifies candidate code against stored HMAC digest.
    Enforces maximum attempts and 10-minute expiration.
    Returns: (is_valid: bool, error_detail: Optional[str], new_email: Optional[str])
    """
    now = datetime.now(timezone.utc)
    record = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.user_id == user_id,
            VerificationCode.purpose == purpose,
            VerificationCode.consumed_at.is_(None),
        )
        .order_by(VerificationCode.created_at.desc())
        .first()
    )

    if not record:
        return False, "No active verification code found. Please request a new code.", None

    exp = record.expires_at if record.expires_at.tzinfo else record.expires_at.replace(tzinfo=timezone.utc)
    if now > exp:
        record.consumed_at = now
        db.commit()
        return False, "Verification code has expired. Please request a new code.", None

    if record.attempts >= max_attempts:
        record.consumed_at = now
        db.commit()
        return False, "Too many failed attempts. This code has been invalidated for security.", None

    candidate_digest = hash_code(candidate_code)
    is_match = hmac.compare_digest(record.code_hash, candidate_digest)

    if not is_match:
        record.attempts += 1
        db.commit()
        remaining = max(0, max_attempts - record.attempts)
        return False, f"Invalid verification code. {remaining} attempt(s) remaining.", None

    # Code is valid - mark consumed
    record.consumed_at = now
    db.commit()
    return True, None, record.new_email
