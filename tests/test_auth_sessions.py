import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.api import app
from backend.database import SessionLocal
from backend.db_models import User, AuthSession
from backend.security import hash_password
from backend.auth.sessions import create_auth_session, rotate_refresh_token, list_user_sessions

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    db = SessionLocal()
    try:
        db.query(AuthSession).delete()
        users = db.query(User).filter(User.email.like("%@testsession.com")).all()
        for u in users:
            db.delete(u)
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(AuthSession).delete()
        users = db.query(User).filter(User.email.like("%@testsession.com")).all()
        for u in users:
            db.delete(u)
        db.commit()
    finally:
        db.close()


def test_session_creation_and_jwt_claims():
    db = SessionLocal()
    try:
        user = User(
            email="user1@testsession.com",
            hashed_password=hash_password("Password123!"),
            is_active=True,
            is_verified=True,
            email_verified_at=datetime.now(timezone.utc),
            token_version=1,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        access_token, refresh_token, session_rec = create_auth_session(db, user)
        assert access_token is not None
        assert refresh_token is not None
        assert session_rec.user_id == user.id
        assert session_rec.revoked_at is None

        # Verify access token works with protected endpoint
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert res.status_code == 200
        assert res.json()["email"] == "user1@testsession.com"
    finally:
        db.close()


def test_refresh_token_rotation():
    db = SessionLocal()
    try:
        user = User(
            email="rotator@testsession.com",
            hashed_password=hash_password("Password123!"),
            is_active=True,
            is_verified=True,
            email_verified_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        access_1, refresh_1, session_1 = create_auth_session(db, user)

        # Call refresh endpoint
        res = client.post("/api/auth/refresh", json={"refresh_token": refresh_1})
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data
        refresh_2 = data["refresh_token"]
        assert refresh_2 != refresh_1

        # Old refresh token should now be revoked
        db.refresh(session_1)
        assert session_1.revoked_at is not None
        assert session_1.revoked_reason == "rotated"

        # New refresh token works for next rotation
        res2 = client.post("/api/auth/refresh", json={"refresh_token": refresh_2})
        assert res2.status_code == 200
    finally:
        db.close()


def test_refresh_token_reuse_detection_revokes_family():
    db = SessionLocal()
    try:
        user = User(
            email="reuse@testsession.com",
            hashed_password=hash_password("Password123!"),
            is_active=True,
            is_verified=True,
            email_verified_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        access_1, refresh_1, session_1 = create_auth_session(db, user)

        # Legitimate rotation
        res = client.post("/api/auth/refresh", json={"refresh_token": refresh_1})
        assert res.status_code == 200
        refresh_2 = res.json()["refresh_token"]

        # Simulate time passing beyond the 60-second grace window (e.g., 5 minutes later)
        from datetime import timedelta
        db.refresh(session_1)
        session_1.revoked_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        db.commit()

        # Attack: Adversary attempts to use old refresh_1 after grace window
        reuse_res = client.post("/api/auth/refresh", json={"refresh_token": refresh_1})
        assert reuse_res.status_code == 401
        assert "reuse detected" in reuse_res.json()["detail"].lower()

        # Both session 1 and session 2 must now be revoked due to family reuse detection
        res_after = client.post("/api/auth/refresh", json={"refresh_token": refresh_2})
        assert res_after.status_code == 401
    finally:
        db.close()


def test_logout_and_session_invalidation():
    db = SessionLocal()
    try:
        user = User(
            email="logout@testsession.com",
            hashed_password=hash_password("Password123!"),
            is_active=True,
            is_verified=True,
            email_verified_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        access_token, _, session_rec = create_auth_session(db, user)

        # Access me endpoint works
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert res.status_code == 200

        # Logout current session
        logout_res = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {access_token}"})
        assert logout_res.status_code == 200

        # Session should now be rejected immediately
        res_after = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert res_after.status_code == 401
    finally:
        db.close()


def test_password_change_bumps_token_version():
    db = SessionLocal()
    try:
        user = User(
            email="pwdchange@testsession.com",
            hashed_password=hash_password("OldPassword123!"),
            is_active=True,
            is_verified=True,
            email_verified_at=datetime.now(timezone.utc),
            token_version=0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        old_access, _, old_session = create_auth_session(db, user)

        # Change password
        change_res = client.put(
            "/api/auth/password",
            headers={"Authorization": f"Bearer {old_access}"},
            json={"old_password": "OldPassword123!", "new_password": "NewSecurePassword999!"},
        )
        assert change_res.status_code == 200
        new_access = change_res.json()["access_token"]

        # User token_version incremented
        db.refresh(user)
        assert user.token_version == 1

        # Old access token with ver=0 is immediately rejected
        res_old = client.get("/api/auth/me", headers={"Authorization": f"Bearer {old_access}"})
        assert res_old.status_code == 401

        # New access token works
        res_new = client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_access}"})
        assert res_new.status_code == 200
    finally:
        db.close()
