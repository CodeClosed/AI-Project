import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
from backend.db_models import RateLimitBucket, User
from backend.security import get_client_ip
from backend.email_service import send_account_locked_alert

logger = logging.getLogger("nutrimenu.ratelimit")


def check_db_rate_limit(
    db: Session,
    key: str,
    max_requests: int,
    window_seconds: int,
) -> Tuple[bool, int]:
    """
    Evaluates persistent rate limit for a key (e.g. IP + endpoint) against rate_limit_buckets.
    Returns (allowed: bool, retry_after_seconds: int).
    """
    now = time.time()
    now_dt = datetime.now(timezone.utc)

    bucket = db.query(RateLimitBucket).filter(RateLimitBucket.key == key).first()

    if not bucket:
        bucket = RateLimitBucket(
            key=key,
            window_start=now,
            count=1,
            updated_at=now_dt,
        )
        db.add(bucket)
        db.commit()
        return True, 0

    elapsed = now - bucket.window_start

    if elapsed >= window_seconds:
        # Window expired - reset window
        bucket.window_start = now
        bucket.count = 1
        bucket.updated_at = now_dt
        db.commit()
        return True, 0

    if bucket.count >= max_requests:
        retry_after = max(1, int(window_seconds - elapsed))
        return False, retry_after

    bucket.count += 1
    bucket.updated_at = now_dt
    db.commit()
    return True, 0


def record_failed_login(db: Session, user: User, request: Optional[Request] = None) -> Tuple[bool, int]:
    """
    Tracks consecutive failed login attempts on a specific user account.
    If 10 consecutive failures occur, locks account for 15 minutes and dispatches alert email.
    Returns (is_locked: bool, remaining_lock_minutes: int).
    """
    now = datetime.now(timezone.utc)
    user.failed_login_count = (user.failed_login_count or 0) + 1

    if user.failed_login_count >= 10:
        lock_minutes = 15
        user.locked_until = now + timedelta(minutes=lock_minutes)
        db.commit()

        try:
            send_account_locked_alert(user.email, lock_minutes)
        except Exception as e:
            logger.error("Failed to send account lockout alert: %s", e)

        return True, lock_minutes

    db.commit()
    return False, 0


def check_account_lockout(user: User) -> Tuple[bool, int]:
    """
    Checks if an account is currently locked.
    Returns (is_locked: bool, remaining_seconds: int).
    """
    if not user.locked_until:
        return False, 0

    now = datetime.now(timezone.utc)
    lock_exp = user.locked_until if user.locked_until.tzinfo else user.locked_until.replace(tzinfo=timezone.utc)

    if now < lock_exp:
        remaining = int((lock_exp - now).total_seconds())
        return True, max(1, remaining)

    # Lock period has elapsed
    user.locked_until = None
    user.failed_login_count = 0
    return False, 0


def reset_account_failures(db: Session, user: User) -> None:
    """Resets failed login counter upon successful authentication."""
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
