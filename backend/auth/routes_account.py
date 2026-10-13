from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.db_models import User, UserProfile, LoggedMeal, SavedMenu
from backend.security import verify_password
from backend.auth.deps import get_current_user_and_session
from backend.auth.sessions import (
    list_user_sessions,
    revoke_session,
    revoke_all_user_sessions,
    create_auth_session,
)
from backend.auth.codes import issue_verification_code, verify_code
from backend.auth.audit import record_audit_log, get_user_activity
from backend.email_service import (
    send_email_change_confirmation,
    send_email_change_notice,
    send_deletion_scheduled_alert,
    send_deletion_cancelled_alert,
)
from backend.schemas import (
    SessionOut,
    ActivityOut,
    EmailChangeRequest,
    EmailChangeConfirmRequest,
    AccountDelete,
    CancelDeletionRequest,
    LoginResponse,
)

router = APIRouter(prefix="/api/account", tags=["Account Management"])


# =====================================================================
# 1. 📱 ACTIVE SESSIONS MANAGEMENT
# =====================================================================

@router.get("/sessions", response_model=List[SessionOut])
def get_sessions(
    current: tuple[User, str] = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
):
    """Lists all active, unrevoked sessions for the current authenticated user."""
    user, session_id = current
    return list_user_sessions(db, user.id, current_session_id=session_id)


@router.delete("/sessions/{target_session_id}")
def revoke_single_session(
    target_session_id: str,
    request: Request,
    current: tuple[User, str] = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
):
    """Revokes a specific session belonging to the user."""
    user, current_session_id = current
    from backend.db_models import AuthSession

    target = db.query(AuthSession).filter(AuthSession.id == target_session_id, AuthSession.user_id == user.id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or access denied.")

    revoke_session(db, target_session_id, reason="user_manual_revoke")
    record_audit_log(
        db=db,
        event="account.session_revoked",
        user_id=user.id,
        request=request,
        details={"revoked_session_id": target_session_id},
    )
    return {"success": True, "message": "Session successfully terminated."}


@router.post("/sessions/revoke-all")
def revoke_other_sessions(
    request: Request,
    current: tuple[User, str] = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
):
    """Terminates all sessions across all devices except the current active session."""
    user, current_session_id = current
    revoked_count = revoke_all_user_sessions(db, user.id, except_session_id=current_session_id, reason="user_revoke_all")
    record_audit_log(
        db=db,
        event="account.sessions_revoke_all",
        user_id=user.id,
        request=request,
        details={"terminated_count": revoked_count},
    )
    return {"success": True, "message": f"Successfully terminated {revoked_count} other active session(s)."}


# =====================================================================
# 2. ✉️ EMAIL ADDRESS UPDATE (WITH DUAL NOTIFICATION)
# =====================================================================

@router.post("/email/change")
def request_email_change(
    req: EmailChangeRequest,
    request: Request,
    current: tuple[User, str] = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
):
    """Initiates email change by validating current password and dispatching verification code to new email."""
    user, _ = current
    clean_new_email = req.new_email.strip().lower()

    if not verify_password(req.password, user.hashed_password):
        record_audit_log(
            db=db,
            event="account.email_change_failed_auth",
            status="failure",
            user_id=user.id,
            request=request,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")

    if clean_new_email == user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New email must be different from current email.")

    # Check if target email is already claimed
    existing = db.query(User).filter(User.email == clean_new_email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This email address is already associated with another account.")

    code = issue_verification_code(db, user.id, purpose="email_change", new_email=clean_new_email)

    # Dispatch to both old (security notice) and new (verification code)
    try:
        send_email_change_confirmation(clean_new_email, code)
        send_email_change_notice(user.email, clean_new_email)
    except Exception as e:
        record_audit_log(db=db, event="email.dispatch_error", status="error", user_id=user.id, details={"err": str(e)})

    record_audit_log(
        db=db,
        event="account.email_change_requested",
        user_id=user.id,
        request=request,
        details={"new_email": clean_new_email},
    )

    return {"success": True, "message": f"Verification code sent to {clean_new_email}. Please confirm to complete change."}


@router.post("/email/confirm")
def confirm_email_change(
    req: EmailChangeConfirmRequest,
    request: Request,
    current: tuple[User, str] = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
):
    """Confirms email change using the 6-digit code received at new email address."""
    user, current_session_id = current
    is_valid, err_msg, new_email = verify_code(db, user.id, purpose="email_change", candidate_code=req.code)

    if not is_valid or not new_email:
        record_audit_log(
            db=db,
            event="account.email_change_confirm_failed",
            status="failure",
            user_id=user.id,
            request=request,
            details={"reason": err_msg},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg or "Verification failed.")

    old_email = user.email
    user.email = new_email
    user.email_verified_at = datetime.now(timezone.utc)
    # Increment token_version to invalidate other active sessions
    user.token_version = (user.token_version or 0) + 1
    db.commit()

    record_audit_log(
        db=db,
        event="account.email_changed",
        user_id=user.id,
        request=request,
        details={"old_email": old_email, "new_email": new_email},
    )

    return {"success": True, "message": "Email address updated successfully.", "email": new_email}


# =====================================================================
# 3. 🛡️ SECURITY ACTIVITY HISTORY
# =====================================================================

@router.get("/activity", response_model=List[ActivityOut])
def get_activity_log(
    current: tuple[User, str] = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
):
    """Returns recent security audit events for user account transparency."""
    user, _ = current
    return get_user_activity(db, user.id, limit=50)


# =====================================================================
# 4. 📦 GDPR DATA EXPORT
# =====================================================================

@router.post("/export")
def export_user_data(
    req: AccountDelete,  # Reuses schema requiring password
    request: Request,
    current: tuple[User, str] = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
):
    """Compiles and exports all user account, clinical profile, meal logs, and menus as a GDPR-compliant JSON payload."""
    user, _ = current
    if not verify_password(req.password, user.hashed_password):
        record_audit_log(db=db, event="account.export_failed_auth", status="failure", user_id=user.id, request=request)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is incorrect.")

    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    meals = db.query(LoggedMeal).filter(LoggedMeal.user_id == user.id).all()
    menus = db.query(SavedMenu).filter(SavedMenu.user_id == user.id).all()
    sessions = list_user_sessions(db, user.id)

    payload = {
        "export_metadata": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "export_version": "1.0",
            "system": "NutriMenu AI Clinical Platform",
        },
        "account": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "is_verified": user.is_verified or bool(user.email_verified_at),
            "two_factor_enabled": user.two_factor_enabled,
        },
        "health_profile": {
            "age": profile.age if profile else None,
            "gender": profile.gender if profile else None,
            "height_cm": profile.height_cm if profile else None,
            "weight_kg": profile.weight_kg if profile else None,
            "activity_level": profile.activity_level if profile else None,
            "primary_goal": profile.primary_goal if profile else None,
            "health_conditions": profile.health_conditions if profile else [],
            "allergies": profile.allergies if profile else [],
            "dietary_preferences": profile.dietary_preferences if profile else [],
        } if profile else None,
        "logged_meals": [
            {
                "id": m.id,
                "name": m.name,
                "meal_type": m.meal_type,
                "date": m.date,
                "dishes": m.dishes,
                "total_calories": m.total_calories,
                "total_protein": m.total_protein,
                "total_carbs": m.total_carbs,
                "total_fats": m.total_fats,
                "total_sodium": m.total_sodium,
            }
            for m in meals
        ],
        "saved_menus": [
            {
                "id": sm.id,
                "title": sm.title,
                "dishes": sm.dishes,
                "created_at": sm.created_at.isoformat() if sm.created_at else None,
            }
            for sm in menus
        ],
        "sessions": sessions,
    }

    record_audit_log(db=db, event="account.data_exported", user_id=user.id, request=request)
    return payload


# =====================================================================
# 5. ⏳ ACCOUNT DELETION WITH 14-DAY GRACE PERIOD
# =====================================================================

@router.delete("")
def schedule_account_deletion(
    req: AccountDelete,
    request: Request,
    current: tuple[User, str] = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
):
    """
    Schedules account for permanent deletion with a 14-day grace period.
    Revokes all active sessions immediately. User can cancel anytime within 14 days by signing in.
    """
    user, _ = current
    if not verify_password(req.password, user.hashed_password):
        record_audit_log(db=db, event="account.deletion_schedule_failed_auth", status="failure", user_id=user.id, request=request)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is incorrect.")

    now = datetime.now(timezone.utc)
    scheduled_date = now + timedelta(days=14)
    user.deletion_requested_at = now
    # Terminate all active sessions
    revoke_all_user_sessions(db, user.id, reason="account_deletion_scheduled")
    db.commit()

    date_str = scheduled_date.strftime("%B %d, %Y")
    try:
        send_deletion_scheduled_alert(user.email, date_str)
    except Exception as e:
        record_audit_log(db=db, event="email.dispatch_error", status="error", user_id=user.id, details={"err": str(e)})

    record_audit_log(
        db=db,
        event="account.deletion_scheduled",
        user_id=user.id,
        request=request,
        details={"scheduled_date": date_str},
    )

    return {
        "success": True,
        "message": f"Account scheduled for permanent deletion on {date_str}. You have 14 days to cancel if you change your mind.",
        "scheduled_deletion_date": date_str,
    }


@router.post("/deletion/cancel", response_model=LoginResponse)
def cancel_account_deletion(
    req: CancelDeletionRequest,
    request: Request,
    current: tuple[User, str] = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
):
    """Cancels a pending account deletion and restores active standing."""
    user, _ = current
    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is incorrect.")

    user.deletion_requested_at = None
    db.commit()

    # Create fresh session for restored account
    access_token, refresh_token, session_rec = create_auth_session(db, user, request=request)

    try:
        send_deletion_cancelled_alert(user.email)
    except Exception:
        pass

    record_audit_log(db=db, event="account.deletion_cancelled", user_id=user.id, request=request)

    from backend.api import user_to_out
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user_to_out(user),
        deletion_pending=False,
    )
