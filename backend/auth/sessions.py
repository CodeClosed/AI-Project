import uuid
import hashlib
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Request
from backend.db_models import User, AuthSession
from backend.settings import settings
from backend.security import create_access_token, get_client_ip
from backend.email_service import send_token_reuse_alert

logger = logging.getLogger("nutrimenu.sessions")


def hash_refresh_token(token: str) -> str:
    """Computes SHA-256 digest of refresh token for safe database persistence."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


def generate_opaque_token() -> str:
    """Generates 256-bit cryptographically secure URL-safe opaque token."""
    return secrets.token_urlsafe(32)


def parse_device_label(user_agent: Optional[str]) -> str:
    """Extracts human-readable device/browser label from User-Agent string."""
    if not user_agent:
        return "Unknown Device"
    ua = user_agent.lower()
    os_name = "Desktop"
    if "iphone" in ua or "ipad" in ua:
        os_name = "iOS Device"
    elif "android" in ua:
        os_name = "Android Device"
    elif "windows" in ua:
        os_name = "Windows PC"
    elif "macintosh" in ua or "mac os" in ua:
        os_name = "Mac"
    elif "linux" in ua:
        os_name = "Linux"

    browser_name = "Browser"
    if "edg" in ua:
        browser_name = "Edge"
    elif "chrome" in ua:
        browser_name = "Chrome"
    elif "safari" in ua and "chrome" not in ua:
        browser_name = "Safari"
    elif "firefox" in ua:
        browser_name = "Firefox"

    return f"{browser_name} on {os_name}"


def create_auth_session(
    db: Session,
    user: User,
    family_id: Optional[str] = None,
    request: Optional[Request] = None,
) -> Tuple[str, str, AuthSession]:
    """
    Creates a new authenticated session with paired JWT access token and opaque rotating refresh token.
    Enforces user token_version and returns (access_token, raw_refresh_token, session_record).
    """
    now = datetime.now(timezone.utc)
    session_id = str(uuid.uuid4())
    active_family_id = family_id or str(uuid.uuid4())

    raw_refresh = generate_opaque_token()
    token_digest = hash_refresh_token(raw_refresh)

    idle_ttl = timedelta(days=settings.refresh_token_idle_days)
    abs_ttl = timedelta(days=settings.refresh_token_absolute_days)

    client_ip = get_client_ip(request) if request else "127.0.0.1"
    raw_ua = request.headers.get("user-agent") if request else None
    device_label = parse_device_label(raw_ua)

    session_rec = AuthSession(
        id=session_id,
        user_id=user.id,
        family_id=active_family_id,
        refresh_token_hash=token_digest,
        created_at=now,
        last_used_at=now,
        idle_expires_at=now + idle_ttl,
        absolute_expires_at=now + abs_ttl,
        ip_address=client_ip,
        user_agent=raw_ua[:255] if raw_ua else None,
        device_label=device_label,
    )
    db.add(session_rec)
    db.commit()
    db.refresh(session_rec)

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "sid": session_id,
            "ver": user.token_version,
            "email": user.email,
            "role": user.role,
            "typ": "access",
        },
        expires_delta=timedelta(minutes=settings.access_token_ttl_minutes),
    )

    return access_token, raw_refresh, session_rec


def rotate_refresh_token(
    db: Session,
    raw_refresh_token: str,
    request: Optional[Request] = None,
) -> Tuple[Optional[str], Optional[str], Optional[User], Optional[str]]:
    """
    Rotates refresh token for a session.
    Detects token reuse: if a previously revoked refresh token is presented,
    the entire family chain is immediately invalidated as a security defense.
    Returns: (new_access_token, new_refresh_token, user, error_code)
    """
    token_digest = hash_refresh_token(raw_refresh_token)
    session_rec = db.query(AuthSession).filter(AuthSession.refresh_token_hash == token_digest).first()

    if not session_rec:
        return None, None, None, "invalid_token"

    user = db.query(User).filter(User.id == session_rec.user_id).first()
    if not user or not user.is_active:
        return None, None, None, "account_inactive"

    now = datetime.now(timezone.utc)

    # 1. Reuse Detection: If session was already revoked, check for benign rotation race (60-second grace window)
    if session_rec.revoked_at is not None:
        revoked_time = session_rec.revoked_at if session_rec.revoked_at.tzinfo else session_rec.revoked_at.replace(tzinfo=timezone.utc)
        elapsed_seconds = (now - revoked_time).total_seconds()

        # If it was rotated less than 60s ago and was rotated normally, this is a benign network retry or race condition!
        if session_rec.revoked_reason == "rotated" and elapsed_seconds <= 60.0:
            logger.info(
                "Benign refresh retry detected within grace window (%.1fs) for user_id=%s, family_id=%s. Re-issuing tokens.",
                elapsed_seconds,
                session_rec.user_id,
                session_rec.family_id,
            )
            # Find the active unrevoked session in the same family, or create a fresh one
            active_sibling = (
                db.query(AuthSession)
                .filter(
                    AuthSession.family_id == session_rec.family_id,
                    AuthSession.revoked_at.is_(None),
                )
                .order_by(AuthSession.created_at.desc())
                .first()
            )
            if active_sibling:
                # Mark sibling rotated to advance chain safely
                active_sibling.revoked_at = now
                active_sibling.revoked_reason = "rotated_via_grace_retry"

            new_access, new_refresh, _ = create_auth_session(
                db=db,
                user=user,
                family_id=session_rec.family_id,
                request=request,
            )
            return new_access, new_refresh, user, None

        logger.warning(
            "CRITICAL SECURITY: Refresh token reuse detected for user_id=%s, family_id=%s (elapsed: %.1fs, reason=%s). Revoking entire family chain.",
            session_rec.user_id,
            session_rec.family_id,
            elapsed_seconds,
            session_rec.revoked_reason,
        )
        # Invalidate all sessions in this family
        family_sessions = db.query(AuthSession).filter(AuthSession.family_id == session_rec.family_id).all()
        for s in family_sessions:
            if s.revoked_at is None:
                s.revoked_at = now
                s.revoked_reason = "family_reuse_security_revocation"
        db.commit()

        # Send security notification email
        try:
            send_token_reuse_alert(user.email)
        except Exception as e:
            logger.error("Failed to send token reuse security alert: %s", e)

        return None, None, None, "reuse_detected"

    # 2. Expiration check
    idle_exp = session_rec.idle_expires_at if session_rec.idle_expires_at.tzinfo else session_rec.idle_expires_at.replace(tzinfo=timezone.utc)
    abs_exp = session_rec.absolute_expires_at if session_rec.absolute_expires_at.tzinfo else session_rec.absolute_expires_at.replace(tzinfo=timezone.utc)

    if now > idle_exp or now > abs_exp:
        session_rec.revoked_at = now
        session_rec.revoked_reason = "expired"
        db.commit()
        return None, None, None, "expired"

    # 3. Successful rotation: mark current session rotated
    session_rec.revoked_at = now
    session_rec.revoked_reason = "rotated"
    session_rec.last_used_at = now

    # Spawn next session in same family chain
    new_access, new_refresh, _ = create_auth_session(
        db=db,
        user=user,
        family_id=session_rec.family_id,
        request=request,
    )

    return new_access, new_refresh, user, None


def revoke_session(db: Session, session_id: str, reason: str = "user_revoked") -> bool:
    """Revokes a single active session by ID."""
    session_rec = db.query(AuthSession).filter(AuthSession.id == session_id).first()
    if session_rec and session_rec.revoked_at is None:
        session_rec.revoked_at = datetime.now(timezone.utc)
        session_rec.revoked_reason = reason
        db.commit()
        return True
    return False


def revoke_all_user_sessions(
    db: Session,
    user_id: int,
    except_session_id: Optional[str] = None,
    reason: str = "revoke_all",
) -> int:
    """Revokes all active sessions for a user, optionally preserving the current active session."""
    now = datetime.now(timezone.utc)
    query = (
        db.query(AuthSession)
        .filter(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
    )
    if except_session_id:
        query = query.filter(AuthSession.id != except_session_id)

    sessions = query.all()
    for s in sessions:
        s.revoked_at = now
        s.revoked_reason = reason
    db.commit()
    return len(sessions)


def list_user_sessions(
    db: Session,
    user_id: int,
    current_session_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Returns active and unrevoked sessions for user."""
    now = datetime.now(timezone.utc)
    records = (
        db.query(AuthSession)
        .filter(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.absolute_expires_at > now,
        )
        .order_by(AuthSession.last_used_at.desc())
        .all()
    )

    out = []
    for r in records:
        masked_ip = r.ip_address
        if masked_ip and "." in masked_ip:
            parts = masked_ip.split(".")
            if len(parts) == 4:
                masked_ip = f"{parts[0]}.{parts[1]}.*.*"

        out.append({
            "id": r.id,
            "device_label": r.device_label or "Web Browser",
            "ip_address": masked_ip,
            "created_at": r.created_at,
            "last_used_at": r.last_used_at,
            "is_current": bool(current_session_id and r.id == current_session_id),
        })
    return out
