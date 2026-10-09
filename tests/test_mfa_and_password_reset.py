import pytest
import pyotp
import secrets
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.db_models import User
from backend.security import (
    hash_password,
    verify_password,
    generate_secure_otp,
    generate_totp_secret,
    get_totp_uri,
    verify_totp_code,
    generate_backup_codes,
    create_temp_2fa_token,
    decode_temp_2fa_token,
    rate_limiter,
)
from backend.api import app

# Setup isolated in-memory test DB
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clean_state():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def client():
    return TestClient(app)


# --- 1. Unit Tests: OTP & TOTP Engine ---

def test_generate_secure_otp():
    otp = generate_secure_otp(6)
    assert len(otp) == 6
    assert otp.isdigit()

    # Verify randomness across runs
    samples = {generate_secure_otp(6) for _ in range(50)}
    assert len(samples) > 40


def test_totp_generation_and_verification():
    secret = generate_totp_secret()
    assert len(secret) == 32

    uri = get_totp_uri(secret, "user@example.com")
    assert "otpauth://totp/NutriMenu%20AI:user%40example.com" in uri
    assert secret in uri

    totp = pyotp.TOTP(secret)
    valid_code = totp.now()

    assert verify_totp_code(secret, valid_code) is True
    assert verify_totp_code(secret, "000000") is False


def test_backup_codes_generation_and_hashing():
    plain_codes = generate_backup_codes(8)
    assert len(plain_codes) == 8
    hashed_codes = [hash_password(c) for c in plain_codes]
    assert len(hashed_codes) == 8

    for plain, hashed in zip(plain_codes, hashed_codes):
        assert len(plain) == 9  # XXXX-XXXX
        assert "-" in plain
        assert verify_password(plain, hashed) is True


def test_temp_2fa_token_lifecycle():
    token = create_temp_2fa_token(123)
    user_id = decode_temp_2fa_token(token)
    assert user_id == 123

    # Invalid token check raises exception
    with pytest.raises(Exception):
        decode_temp_2fa_token("invalid.token.here")


# --- 2. Integration Tests: Forgot Password Flow & Anti-Enumeration ---

def test_forgot_password_anti_enumeration_nonexistent_email(client):
    """Ensure nonexistent email returns identical success response without leaking user status."""
    res = client.post("/api/auth/forgot-password", json={"email": "nonexistent_ghost@example.com"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "If an account with this email address exists" in data["message"]


def test_forgot_password_and_reset_success(client):
    """Complete end-to-end reset password workflow."""
    # Register user
    reg = client.post("/api/auth/register", json={"email": "reset_user@example.com", "password": "OriginalPassword123!"})
    assert reg.status_code == 201

    # Request reset
    req = client.post("/api/auth/forgot-password", json={"email": "reset_user@example.com"})
    assert req.status_code == 200

    # Retrieve OTP directly from database record
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "reset_user@example.com").first()
    assert user is not None
    otp_code = user.otp_code
    assert otp_code is not None
    assert len(otp_code) == 6
    db.close()

    # Reset password with correct OTP
    reset_res = client.post("/api/auth/reset-password", json={
        "email": "reset_user@example.com",
        "otp_code": otp_code,
        "new_password": "NewSecurePassword456!",
    })
    assert reset_res.status_code == 200
    assert reset_res.json()["success"] is True

    # Confirm OTP was cleared upon use (single-use)
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "reset_user@example.com").first()
    assert user.otp_code is None
    db.close()

    # Old password must now fail
    old_login = client.post("/api/auth/login", json={"email": "reset_user@example.com", "password": "OriginalPassword123!"})
    assert old_login.status_code == 401

    # New password must succeed
    new_login = client.post("/api/auth/login", json={"email": "reset_user@example.com", "password": "NewSecurePassword456!"})
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()


def test_forgot_password_lockout_after_5_attempts(client):
    """Verify brute-force protection locks out after 5 wrong OTP entries."""
    client.post("/api/auth/register", json={"email": "lockout_user@example.com", "password": "Password123!"})
    client.post("/api/auth/forgot-password", json={"email": "lockout_user@example.com"})

    # 5 failed attempts with rate limiter reset between calls if needed
    for _ in range(5):
        rate_limiter.reset()
        fail_res = client.post("/api/auth/reset-password", json={
            "email": "lockout_user@example.com",
            "otp_code": "000000",
            "new_password": "NewPassword123!",
        })
        assert fail_res.status_code == 400

    # 6th attempt should fail with lockout / invalidation error
    rate_limiter.reset()
    lockout_res = client.post("/api/auth/reset-password", json={
        "email": "lockout_user@example.com",
        "otp_code": "000000",
        "new_password": "NewPassword123!",
    })
    assert lockout_res.status_code == 400
    assert "too many failed" in lockout_res.json()["detail"].lower() or "invalid" in lockout_res.json()["detail"].lower()


def test_forgot_password_expired_otp(client):
    """Verify expired OTP code is rejected."""
    client.post("/api/auth/register", json={"email": "expired_user@example.com", "password": "Password123!"})
    client.post("/api/auth/forgot-password", json={"email": "expired_user@example.com"})

    # Artificially expire the token in the database
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "expired_user@example.com").first()
    user.otp_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    otp = user.otp_code
    db.close()

    res = client.post("/api/auth/reset-password", json={
        "email": "expired_user@example.com",
        "otp_code": otp,
        "new_password": "NewPassword123!",
    })
    assert res.status_code == 400
    assert "expired" in res.json()["detail"].lower()


# --- 3. Integration Tests: 2FA Setup, Activation & Login Challenge ---

def test_mfa_setup_enable_and_login_flow(client):
    """End-to-end test of enabling 2FA, receiving MFA challenge on login, and verifying."""
    # Register and login to obtain JWT
    reg = client.post("/api/auth/register", json={"email": "mfa_tester@example.com", "password": "Password123!"})
    jwt_token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {jwt_token}"}

    # Setup MFA
    setup_res = client.post("/api/auth/mfa/setup", headers=headers)
    assert setup_res.status_code == 200
    setup_data = setup_res.json()
    secret = setup_data["secret"]
    backup_codes = setup_data["backup_codes"]
    assert len(secret) == 32
    assert len(backup_codes) == 8

    # Attempt to enable with bad code
    bad_enable = client.post("/api/auth/mfa/enable", headers=headers, json={"code": "000000"})
    assert bad_enable.status_code == 400

    # Enable with valid TOTP code
    totp = pyotp.TOTP(secret)
    good_code = totp.now()
    good_enable = client.post("/api/auth/mfa/enable", headers=headers, json={"code": good_code})
    assert good_enable.status_code == 200
    assert good_enable.json()["success"] is True

    # Verify user profile reflects 2FA active
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["two_factor_enabled"] is True

    # Subsequent Login now challenges for MFA
    rate_limiter.reset()
    login_res = client.post("/api/auth/login", json={"email": "mfa_tester@example.com", "password": "Password123!"})
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["mfa_required"] is True
    assert "temp_token" in login_data
    assert login_data["access_token"] is None
    temp_token = login_data["temp_token"]

    # Verify MFA challenge with TOTP
    verify_res = client.post("/api/auth/mfa/verify", json={
        "temp_token": temp_token,
        "code": totp.now()
    })
    assert verify_res.status_code == 200
    auth_data = verify_res.json()
    assert auth_data["access_token"] is not None
    assert auth_data["user"]["email"] == "mfa_tester@example.com"


def test_mfa_backup_code_consumption(client):
    """Test using a backup code to fulfill 2FA challenge and ensure it's single-use."""
    reg = client.post("/api/auth/register", json={"email": "backup_user@example.com", "password": "Password123!"})
    jwt_token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {jwt_token}"}

    # Setup & enable MFA
    setup_res = client.post("/api/auth/mfa/setup", headers=headers)
    setup_data = setup_res.json()
    backup_code = setup_data["backup_codes"][0]
    secret = setup_data["secret"]

    totp = pyotp.TOTP(secret)
    client.post("/api/auth/mfa/enable", headers=headers, json={"code": totp.now()})

    # Login to get temp_token
    rate_limiter.reset()
    login_res = client.post("/api/auth/login", json={"email": "backup_user@example.com", "password": "Password123!"})
    temp_token = login_res.json()["temp_token"]

    # Verify using backup code (case and hyphen insensitive)
    verify_res = client.post("/api/auth/mfa/verify", json={
        "temp_token": temp_token,
        "code": backup_code.lower()
    })
    assert verify_res.status_code == 200
    assert verify_res.json()["access_token"] is not None

    # Login again and attempt to REUSE the same backup code
    rate_limiter.reset()
    login_res2 = client.post("/api/auth/login", json={"email": "backup_user@example.com", "password": "Password123!"})
    temp_token2 = login_res2.json()["temp_token"]

    reuse_res = client.post("/api/auth/mfa/verify", json={
        "temp_token": temp_token2,
        "code": backup_code
    })
    assert reuse_res.status_code == 400
    assert "invalid" in reuse_res.json()["detail"].lower()


def test_mfa_disable_flow(client):
    """Test disabling 2FA with password confirmation."""
    reg = client.post("/api/auth/register", json={"email": "disable_user@example.com", "password": "Password123!"})
    jwt_token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {jwt_token}"}

    # Setup & enable
    setup_res = client.post("/api/auth/mfa/setup", headers=headers)
    totp = pyotp.TOTP(setup_res.json()["secret"])
    client.post("/api/auth/mfa/enable", headers=headers, json={"code": totp.now()})

    # Disable with wrong password
    bad_disable = client.post("/api/auth/mfa/disable", headers=headers, json={"password": "WrongPassword"})
    assert bad_disable.status_code in [400, 401]

    # Disable with correct password
    good_disable = client.post("/api/auth/mfa/disable", headers=headers, json={"password": "Password123!"})
    assert good_disable.status_code == 200
    assert good_disable.json()["success"] is True

    # User profile should have two_factor_enabled False
    me = client.get("/api/auth/me", headers=headers)
    assert me.json()["two_factor_enabled"] is False

    # Login no longer challenges for MFA
    rate_limiter.reset()
    direct_login = client.post("/api/auth/login", json={"email": "disable_user@example.com", "password": "Password123!"})
    assert direct_login.status_code == 200
    assert direct_login.json()["access_token"] is not None
    assert direct_login.json()["mfa_required"] is False
