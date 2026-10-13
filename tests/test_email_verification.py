import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.api import app
from backend.database import SessionLocal
from backend.db_models import User, VerificationCode, AuthSession
from backend.settings import settings
from backend.email_service import dev_email_backend
from backend.auth.codes import issue_verification_code

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    db = SessionLocal()
    dev_email_backend.clear()
    try:
        db.query(VerificationCode).delete()
        db.query(AuthSession).delete()
        users = db.query(User).filter(User.email.like("%@verifytest.com")).all()
        for u in users:
            db.delete(u)
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    dev_email_backend.clear()
    try:
        db.query(VerificationCode).delete()
        db.query(AuthSession).delete()
        users = db.query(User).filter(User.email.like("%@verifytest.com")).all()
        for u in users:
            db.delete(u)
        db.commit()
    finally:
        db.close()


def test_registration_with_verification_enforced():
    original_setting = settings.require_email_verification
    settings.require_email_verification = True
    try:
        reg_payload = {
            "email": "newuser@verifytest.com",
            "password": "StrongPassword123!",
        }
        res = client.post("/api/auth/register", json=reg_payload)
        assert res.status_code == 201
        data = res.json()
        assert data["verification_required"] is True
        assert data["email"] == "newuser@verifytest.com"
        assert "access_token" not in data  # No tokens issued prior to email verification

        # Check that email was sent to dev outbox
        assert len(dev_email_backend.outbox) == 1
        msg = dev_email_backend.outbox[0]
        assert msg.to == "newuser@verifytest.com"
        assert "Verify Your NutriMenu AI Account" in msg.subject

        # Attempt to login prior to verification should prompt for verification
        login_res = client.post("/api/auth/login", json=reg_payload)
        assert login_res.status_code == 200
        login_data = login_res.json()
        assert login_data["verification_required"] is True
        assert "access_token" not in login_data or login_data["access_token"] is None
    finally:
        settings.require_email_verification = original_setting


def test_verify_email_flow_and_token_issuance():
    db = SessionLocal()
    try:
        user = User(
            email="to_verify@verifytest.com",
            hashed_password="hashed_pw",
            is_active=True,
            is_verified=False,
            email_verified_at=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        code = issue_verification_code(db, user.id, purpose="email_verify")

        # Submit wrong code
        fail_res = client.post("/api/auth/verify-email", json={
            "email": "to_verify@verifytest.com",
            "code": "000000",
        })
        assert fail_res.status_code == 400
        assert "remaining" in fail_res.json()["detail"].lower()

        # Submit correct code
        succ_res = client.post("/api/auth/verify-email", json={
            "email": "to_verify@verifytest.com",
            "code": code,
        })
        assert succ_res.status_code == 200
        data = succ_res.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["is_verified"] is True

        db.refresh(user)
        assert user.is_verified is True
        assert user.email_verified_at is not None
    finally:
        db.close()


def test_resend_verification_code():
    db = SessionLocal()
    try:
        user = User(
            email="resend@verifytest.com",
            hashed_password="hashed_pw",
            is_active=True,
            is_verified=False,
            email_verified_at=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        dev_email_backend.clear()
        res = client.post("/api/auth/resend-verification", json={"email": "resend@verifytest.com"})
        assert res.status_code == 200
        assert len(dev_email_backend.outbox) == 1
        assert dev_email_backend.outbox[0].to == "resend@verifytest.com"
    finally:
        db.close()
