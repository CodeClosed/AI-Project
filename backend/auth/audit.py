import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import Request
from sqlalchemy.orm import Session
from backend.db_models import AuditLog
from backend.security import get_client_ip

logger = logging.getLogger("nutrimenu.audit")


def record_audit_log(
    db: Session,
    event: str,
    status: str = "success",
    user_id: Optional[int] = None,
    request: Optional[Request] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Persists structured security audit entry to database and logs to application stream.
    Safely captures IP and User-Agent, never raising an unhandled exception to client.
    """
    client_ip = get_client_ip(request) if request else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")[:255] if request else "unknown"

    entry_data = details or {}

    try:
        log_entry = AuditLog(
            user_id=user_id,
            event=event,
            status=status,
            ip_address=client_ip,
            user_agent=user_agent,
            details=entry_data,
            created_at=datetime.now(timezone.utc),
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error("Failed to commit audit log entry to database: %s", e)
        db.rollback()

    # Mirror to console / stdout stream
    log_msg = f"[SECURITY_AUDIT] event={event} status={status} user_id={user_id} ip={client_ip} details={json.dumps(entry_data)}"
    if status in {"failure", "blocked", "error", "unauthorized"}:
        logger.warning(log_msg)
    else:
        logger.info(log_msg)


def get_user_activity(db: Session, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves recent audit log events for user account review."""
    records = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
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
            "event": r.event,
            "status": r.status,
            "ip_address": masked_ip,
            "created_at": r.created_at,
            "details": r.details or {},
        })
    return out
