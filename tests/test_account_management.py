import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.api import app
from backend.database import SessionLocal
from backend.db_models import User, AuthSession, VerificationCode, LoggedMeal, UserProfile
from backend.security import hash_password
from backend.auth.sessions import create_auth_session
from backend.email_service import dev_email_backend

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    db = SessionLocal()
    dev_email_backend.clear()
    try:
        db.query(AuthSession).delete()
        db.query(VerificationCode).delete()
        users = db.query(User).filter(User.email.like("%@accountmgmt.com")).all()
        for u in users:
            db.delete(u)
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    dev_email_backend.clear()
    try:
        db.query(AuthSession).delete()
        db.query(VerificationCode).delete()
        users = db.query(User).filter(User.email.like("%@accountmgmt.com")).all()
        for u in users:
            db.delete(u)
        db.commit()
    finally:
        db.close()


def test_sessions_list_and_revocation():
    db = SessionLocal()
    try:
        user = User(
            email="sess_tester@accountmgmt.com",
            hashed_password=hash_password("Password123!"),
            is_active=True,
            is_verified=True,
            email_verified_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create 2 sessions
        token_1, _, session_1 = create_auth_session(db, user)
        token_2, _, session_2 = create_auth_session(db, user)

        # Get sessions list with token_1
        res = client.get("/api/account/sessions", headers={"Authorization": f"Bearer {token_1}"})
        assert res.status_code == 200
        sessions = res.json()
        assert len(sessions) == 2

        current_sess = next(s for s in sessions if s["id"] == session_1.id)
        other_sess = next(s for s in sessions if s["id"] == session_2.id)
        assert current_sess["is_current"] is True
        assert other_sess["is_current"] is False

        # Revoke session 2 from session 1
        del_res = client.delete(f"/api/account/sessions/{session_2.id}", headers={"Authorization": f"Bearer {token_1}"})
        assert del_res.status_code == 200

        # Session 2 token now rejected
        check_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_2}"})
        assert check_res.status_code == 401

        # Session 1 remains active
        check_1 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_1}"})
        assert check_1.status_code == 200
    finally:
        db.close()


def test_email_change_flow():
    db = SessionLocal()
    try:
        user = User(
            email="initial@accountmgmt.com",
            hashed_password=hash_password("Password123!"),
            is_active=True,
            is_verified=True,
            email_verified_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token, _, _ = create_auth_session(db, user)

        # Request email change
        req_res = client.post(
            "/api/account/email/change",
            headers={"Authorization": f"Bearer {token}"},
            json={"new_email": "updated@accountmgmt.com", "password": "Password123!"},
        )
        assert req_res.status_code == 200

        # Check outbox: confirmation to new email, security notice to old email
        assert len(dev_email_backend.outbox) == 2
        confirm_msg = next(m for m in dev_email_backend.outbox if m.to == "updated@accountmgmt.com")
        assert "Confirm Your New Email Address" in confirm_msg.subject

        # Extract code from DB
        vcode = db.query(VerificationCode).filter(VerificationCode.user_id == user.id, VerificationCode.purpose == "email_change").first()
        assert vcode is not None

        # Call confirm
        from backend.auth.codes import issue_verification_code
        import re
        match = re.search(r"Verification code:\s*(\d{6})", confirm_msg.text_body)
        if match:
            clean_code = match.group(1)
        else:
            for cand in range(0, 1000000):
                from backend.auth.codes import hash_code
                code_str = f"{cand:06d}"
                if hash_code(code_str) == vcode.code_hash:
                    clean_code = code_str
                    break

        assert clean_code is not None

        confirm_res = client.post(
            "/api/account/email/confirm",
            headers={"Authorization": f"Bearer {token}"},
            json={"code": clean_code},
        )
        assert confirm_res.status_code == 200
        db.refresh(user)
        assert user.email == "updated@accountmgmt.com"
    finally:
        db.close()


def test_account_data_export_security():
    db = SessionLocal()
    try:
        user = User(
            email="export_user@accountmgmt.com",
            hashed_password=hash_password("Password123!"),
            is_active=True,
            is_verified=True,
            email_verified_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token, _, _ = create_auth_session(db, user)

        # Wrong password fails
        fail_res = client.post(
            "/api/account/export",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "WrongPassword!"},
        )
        assert fail_res.status_code == 400

        # Valid password returns export payload
        succ_res = client.post(
            "/api/account/export",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "Password123!"},
        )
        assert succ_res.status_code == 200
        data = succ_res.json()
        assert "account" in data
        assert "export_metadata" in data
        assert data["account"]["email"] == "export_user@accountmgmt.com"
        # Confirm password hash or secrets are never exported
        assert "hashed_password" not in data["account"]
        assert "totp_secret" not in data["account"]
    finally:
        db.close()


def test_account_deletion_grace_period_and_cancellation():
    db = SessionLocal()
    try:
        user = User(
            email="delete_user@accountmgmt.com",
            hashed_password=hash_password("Password123!"),
            is_active=True,
            is_verified=True,
            email_verified_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token, _, session_rec = create_auth_session(db, user)

        # Schedule deletion
        del_res = client.request(
            "DELETE",
            "/api/account",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "Password123!"},
        )
        assert del_res.status_code == 200
        assert "14 days" in del_res.json()["message"]

        db.refresh(user)
        assert user.deletion_requested_at is not None

        # Existing session revoked
        check_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert check_res.status_code == 401

        # Logging in prompts cancellation option
        login_res = client.post("/api/auth/login", json={"email": "delete_user@accountmgmt.com", "password": "Password123!"})
        assert login_res.status_code == 200
        login_data = login_res.json()
        assert login_data["deletion_pending"] is True
        assert login_data["scheduled_deletion_date"] is not None

        # Cancel deletion directly with email + password (no session token required)
        cancel_res = client.post(
            "/api/account/deletion/cancel",
            json={"email": "delete_user@accountmgmt.com", "password": "Password123!"},
        )
        assert cancel_res.status_code == 200
        assert cancel_res.json()["deletion_pending"] is False
        assert cancel_res.json()["access_token"] is not None

        db.refresh(user)
        assert user.deletion_requested_at is None
    finally:
        db.close()
