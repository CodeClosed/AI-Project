import os
import shutil
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.db_models import User, AuthSession, VerificationCode, AuditLog, RateLimitBucket, SavedMenu
from backend.settings import settings

logger = logging.getLogger("nutrimenu.maintenance")


def run_maintenance_cycle(db: Session) -> dict:
    """
    Executes one maintenance sweep:
    1. Permanently purges accounts whose 14-day deletion grace period has elapsed.
    2. Deletes expired/revoked sessions older than 30 days.
    3. Deletes consumed/expired verification codes older than 24 hours.
    4. Purges audit log rows older than audit_retention_days (default: 180 days).
    5. Clears stale rate limit buckets older than 1 hour.
    """
    now = datetime.now(timezone.utc)
    results = {
        "accounts_purged": 0,
        "sessions_cleaned": 0,
        "codes_cleaned": 0,
        "audit_logs_purged": 0,
        "rate_buckets_cleaned": 0,
    }

    # 1. Permanent Account Purge (14-Day Deletion Grace Period Elapsed)
    grace_cutoff = now - timedelta(days=settings.deletion_grace_days)
    expired_users = (
        db.query(User)
        .filter(User.deletion_requested_at.is_not(None), User.deletion_requested_at <= grace_cutoff)
        .all()
    )

    for user in expired_users:
        logger.info("Executing permanent account deletion for user %s (id=%s)", user.email, user.id)
        # Delete user uploaded menu files
        user_menus = db.query(SavedMenu).filter(SavedMenu.user_id == user.id).all()
        for m in user_menus:
            if m.filename:
                file_path = Path("uploads/menus") / m.filename
                if file_path.exists():
                    try:
                        file_path.unlink()
                    except Exception as e:
                        logger.warning("Could not delete file %s during user purge: %s", file_path, e)

        db.delete(user)
        results["accounts_purged"] += 1
    db.commit()

    # 2. Expired / Revoked Sessions (Older than 30 days)
    session_cutoff = now - timedelta(days=settings.refresh_token_absolute_days)
    deleted_sessions = (
        db.query(AuthSession)
        .filter((AuthSession.revoked_at.is_not(None)) | (AuthSession.absolute_expires_at <= now))
        .filter(AuthSession.last_used_at <= session_cutoff)
        .delete(synchronize_session=False)
    )
    results["sessions_cleaned"] = deleted_sessions
    db.commit()

    # 3. Old Verification Codes (> 24 hours old)
    codes_cutoff = now - timedelta(hours=24)
    deleted_codes = (
        db.query(VerificationCode)
        .filter((VerificationCode.consumed_at.is_not(None)) | (VerificationCode.expires_at <= codes_cutoff))
        .delete(synchronize_session=False)
    )
    results["codes_cleaned"] = deleted_codes
    db.commit()

    # 4. Audit Log Purge (> audit_retention_days)
    audit_cutoff = now - timedelta(days=settings.audit_retention_days)
    deleted_audit = (
        db.query(AuditLog)
        .filter(AuditLog.created_at <= audit_cutoff)
        .delete(synchronize_session=False)
    )
    results["audit_logs_purged"] = deleted_audit
    db.commit()

    # 5. Stale Rate Limit Buckets (> 1 hour old)
    bucket_cutoff = now - timedelta(hours=1)
    deleted_buckets = (
        db.query(RateLimitBucket)
        .filter(RateLimitBucket.updated_at <= bucket_cutoff)
        .delete(synchronize_session=False)
    )
    results["rate_buckets_cleaned"] = deleted_buckets
    db.commit()

    logger.info("Maintenance cycle complete: %s", results)
    return results


async def background_maintenance_worker(interval_seconds: int = 3600):
    """Async background worker running maintenance sweeps periodically."""
    while True:
        try:
            db = SessionLocal()
            try:
                run_maintenance_cycle(db)
            finally:
                db.close()
        except Exception as e:
            logger.error("Error during scheduled maintenance worker run: %s", e)

        await asyncio.sleep(interval_seconds)
