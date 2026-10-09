import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.db_models import User, UserProfile, LoggedMeal
from backend.security import (
    hash_password,
    verify_password,
    verify_dummy_password,
    encrypt_data,
    decrypt_data,
    create_access_token,
    decode_access_token,
    rate_limiter,
    resolve_auth_secret,
)
from backend.api import app

# Setup shared in-memory SQLite database using StaticPool for thread-safe test isolation
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
def reset_rate_limits():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def client():
    return TestClient(app)


# --- 1. Unit Tests: Password Hashing ---

def test_password_hashing_and_verification():
    raw_pass = "SuperSecretPassword123!"
    hashed = hash_password(raw_pass)
    assert hashed != raw_pass
    assert hashed.startswith("$2")  # bcrypt prefix
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword", hashed) is False
    assert verify_password("", hashed) is False


# --- 2. Unit Tests: Fernet AES Encryption at Rest ---

def test_fernet_encryption_and_decryption():
    secret_key = "AIzaSy_demo_gemini_api_key_secret"
    cipher_text = encrypt_data(secret_key)
    assert cipher_text is not None
    assert cipher_text != secret_key
    
    decrypted = decrypt_data(cipher_text)
    assert decrypted == secret_key
    assert decrypt_data(None) is None
    assert decrypt_data("invalid_cipher_text") is None


# --- 3. Unit Tests: JWT Tokens ---

def test_jwt_token_generation_and_decoding():
    payload = {"sub": "42", "email": "test@nutrimenu.ai", "role": "user"}
    token = create_access_token(payload)
    decoded = decode_access_token(token)
    assert decoded["sub"] == "42"
    assert decoded["email"] == "test@nutrimenu.ai"
    assert "exp" in decoded
    assert "iat" in decoded


# --- 4. Integration Tests: Auth Endpoints ---

def test_user_registration_and_login(client):
    reg_payload = {
        "email": "sarah.connor@example.com",
        "password": "Password99!",
        "profile": {
            "age": 40,
            "gender": "female",
            "height_cm": 168,
            "weight_kg": 62,
            "activity_level": "moderate",
            "primary_goal": "fat_loss",
            "health_conditions": ["hypertension"],
            "allergies": ["peanuts"],
            "dietary_preferences": ["vegetarian"]
        }
    }

    # Register
    res = client.post("/api/auth/register", json=reg_payload)
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "sarah.connor@example.com"
    token = data["access_token"]

    # Duplicate registration should fail
    dup_res = client.post("/api/auth/register", json=reg_payload)
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]

    # Login with valid credentials
    login_res = client.post("/api/auth/login", json={
        "email": "sarah.connor@example.com",
        "password": "Password99!"
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data

    # Login with incorrect password should fail
    bad_login = client.post("/api/auth/login", json={
        "email": "sarah.connor@example.com",
        "password": "WrongPassword!"
    })
    assert bad_login.status_code == 401


# --- 5. Integration Tests: Protected Routes & Scoping ---

def test_protected_routes(client):
    # Unauthenticated /api/auth/me should fail
    unauth = client.get("/api/auth/me")
    assert unauth.status_code == 401

    # Register User A
    res_a = client.post("/api/auth/register", json={
        "email": "alice@example.com",
        "password": "AliceSecret123"
    })
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Verify /api/auth/me
    me_res = client.get("/api/auth/me", headers=headers_a)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "alice@example.com"

    # Verify /api/profile GET and PUT
    prof_res = client.get("/api/profile", headers=headers_a)
    assert prof_res.status_code == 200
    assert prof_res.json()["age"] == 35

    update_prof = client.put("/api/profile", json={
        "age": 42,
        "allergies": ["gluten", "dairy"],
        "dietary_preferences": ["vegan"]
    }, headers=headers_a)
    assert update_prof.status_code == 200
    assert update_prof.json()["age"] == 42
    assert "gluten" in update_prof.json()["allergies"]

    # Test Encrypted API Key Storage
    api_key_res = client.post("/api/profile/apikey", json={
        "api_key": "AIzaSyCustomKeyForAlice"
    }, headers=headers_a)
    assert api_key_res.status_code == 200
    assert api_key_res.json()["has_custom_api_key"] is True


def test_meal_logging_and_tenant_isolation(client):
    # Register User 1
    res1 = client.post("/api/auth/register", json={"email": "user1@example.com", "password": "User1Password"})
    token1 = res1.json()["access_token"]
    h1 = {"Authorization": f"Bearer {token1}"}

    # Register User 2
    res2 = client.post("/api/auth/register", json={"email": "user2@example.com", "password": "User2Password"})
    token2 = res2.json()["access_token"]
    h2 = {"Authorization": f"Bearer {token2}"}

    # User 1 logs a meal
    meal_payload = {
        "name": "Power Salad Lunch",
        "meal_type": "Lunch",
        "date": "2026-09-18",
        "dishes": [{"name": "Greek Salad", "calories": 320, "protein_g": 12}],
        "total_calories": 320.0,
        "total_protein": 12.0,
        "total_carbs": 15.0,
        "total_fats": 22.0,
        "total_sodium": 480.0
    }
    create_meal = client.post("/api/meals", json=meal_payload, headers=h1)
    assert create_meal.status_code == 201
    meal_id = create_meal.json()["id"]

    # User 1 fetches meals -> sees 1 meal
    meals1 = client.get("/api/meals", headers=h1)
    assert len(meals1.json()) == 1
    assert meals1.json()[0]["id"] == meal_id

    # User 2 fetches meals -> MUST see 0 meals (isolation guarantee)
    meals2 = client.get("/api/meals", headers=h2)
    assert len(meals2.json()) == 0

    # User 2 tries to delete User 1's meal -> MUST return 404
    del_attempt = client.delete(f"/api/meals/{meal_id}", headers=h2)
    assert del_attempt.status_code == 404

    # User 1 deletes their own meal -> 200 OK
    del_success = client.delete(f"/api/meals/{meal_id}", headers=h1)
    assert del_success.status_code == 200

    # Verify list is now empty for User 1
    empty_meals = client.get("/api/meals", headers=h1)
    assert len(empty_meals.json()) == 0


# --- 6. Better Auth Security Tests: Password Hardening ---

def test_password_strength_and_validation(client):
    # Passwords under 8 characters must fail schema validation (422)
    short_res = client.post("/api/auth/register", json={
        "email": "shortpass@example.com",
        "password": "123"
    })
    assert short_res.status_code == 422

    # Trivial / common passwords must be rejected
    trivial_res = client.post("/api/auth/register", json={
        "email": "trivial@example.com",
        "password": "password"
    })
    assert trivial_res.status_code == 422


# --- 7. Better Auth Security Tests: Timing Attack & Account Enumeration Defense ---

def test_account_enumeration_and_timing_defense(client):
    # Non-existent user login should return 401 with generic message
    res = client.post("/api/auth/login", json={
        "email": "nonexistent_user_for_enumeration@example.com",
        "password": "RandomPassword123!"
    })
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]

    # Verify dummy password evaluation runs cleanly
    assert verify_dummy_password("AnyPassword") is False


# --- 8. Better Auth Security Tests: Rate Limiting ---

def test_rate_limiting_enforcement(client):
    # Rate limit on login is 5 requests per 60s
    for i in range(5):
        res = client.post("/api/auth/login", json={
            "email": f"brute_force_{i}@example.com",
            "password": "WrongPassword123!"
        })
        assert res.status_code == 401

    # 6th attempt must be blocked by rate limiter with 429 Too Many Requests
    blocked_res = client.post("/api/auth/login", json={
        "email": "brute_force_6@example.com",
        "password": "WrongPassword123!"
    })
    assert blocked_res.status_code == 429
    assert "Too many requests" in blocked_res.json()["detail"]
    assert "Retry-After" in blocked_res.headers


# --- 9. Better Auth Security Tests: CSRF & Trusted Origins Guard ---

def test_csrf_untrusted_origin_blocked(client):
    # Mutative request with untrusted origin should be rejected with 403 Forbidden
    res = client.post(
        "/api/auth/login",
        json={"email": "attacker@example.com", "password": "Password123!"},
        headers={"Origin": "https://malicious-phishing-site.com"}
    )
    assert res.status_code == 403
    assert "Untrusted Origin" in res.json()["detail"]

    # Request with trusted origin (e.g. localhost frontend) is accepted
    valid_origin_res = client.post(
        "/api/auth/login",
        json={"email": "attacker@example.com", "password": "Password123!"},
        headers={"Origin": "http://localhost:5173"}
    )
    assert valid_origin_res.status_code != 403


# --- 10. Better Auth Security Tests: Secret Resolution & Production Safeguards ---

def test_better_auth_secret_safeguards(monkeypatch):
    # Priority resolution: BETTER_AUTH_SECRET takes precedence
    monkeypatch.setenv("BETTER_AUTH_SECRET", "custom_better_auth_secret_with_32_characters_min!!")
    monkeypatch.setenv("SECRET_KEY", "fallback_secret_key_that_should_not_be_used")
    secret = resolve_auth_secret()
    assert secret == "custom_better_auth_secret_with_32_characters_min!!"

    # Production safeguards: Insecure placeholder secrets are strictly rejected
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("BETTER_AUTH_SECRET", "nutrimenu-ai-jwt-super-secret-key-production-change-this-2026")
    with pytest.raises(RuntimeError, match="Default placeholder auth secret detected"):
        resolve_auth_secret()

    # Production safeguards: Secrets shorter than 32 chars are strictly rejected
    monkeypatch.setenv("BETTER_AUTH_SECRET", "short_secret_123")
    with pytest.raises(RuntimeError, match="requires at least 32 characters"):
        resolve_auth_secret()


# --- 11. Saved Menu CRUD & History Persistence Tests ---

def test_saved_menu_crud(client):
    # 1. Register a test user
    reg = client.post("/api/auth/register", json={"email": "menutester@example.com", "password": "SecurePassword123!"})
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 2. Get initial empty saved menus
    get_res = client.get("/api/menus", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json() == []

    # 3. Create a saved menu
    menu_payload = {
        "title": "Bistro Lunch Special",
        "dishes": [{"name": "Grilled Salmon", "price": "$18"}, {"name": "Garden Salad", "price": "$8"}],
        "image_url": "/uploads/menus/test_menu.jpg",
        "filename": "test_menu.jpg",
    }
    create_res = client.post("/api/menus", json=menu_payload, headers=auth_headers)
    assert create_res.status_code == 201
    created_menu = create_res.json()
    assert created_menu["title"] == "Bistro Lunch Special"
    assert len(created_menu["dishes"]) == 2
    menu_id = created_menu["id"]

    # 4. Verify listed menus contains created menu
    list_res = client.get("/api/menus", headers=auth_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["id"] == menu_id

    # 5. Delete saved menu
    del_res = client.delete(f"/api/menus/{menu_id}", headers=auth_headers)
    assert del_res.status_code == 200
    assert del_res.json()["deleted_id"] == menu_id

    # 6. Verify menu list is now empty again
    empty_res = client.get("/api/menus", headers=auth_headers)
    assert empty_res.status_code == 200
    assert len(empty_res.json()) == 0


# --- 12. Asynchronous Job Manager & Real-Time Status Tests ---

def test_background_job_manager_and_endpoints(client):
    from backend.jobs import job_manager

    # 1. Direct JobManager unit verification
    jid = job_manager.create_job(job_type="menu_scan")
    assert jid is not None
    job = job_manager.get_job(jid)
    assert job["status"] == "pending"
    assert len(job["stages"]) == 4

    # 2. Update progress
    job_manager.update_progress(jid, 50, "Testing stage...", stage_id="ocr")
    job = job_manager.get_job(jid)
    assert job["status"] == "processing"
    assert job["progress"] == 50

    # 3. Complete job
    job_manager.complete_job(jid, {"test": "result"})
    job = job_manager.get_job(jid)
    assert job["status"] == "completed"
    assert job["progress"] == 100
    assert job["result"] == {"test": "result"}

    # 4. Query via FastAPI endpoint (anonymous job allowed)
    res = client.get(f"/api/jobs/{jid}")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["progress"] == 100

    # 5. Multi-tenant Job Isolation: User-scoped job cannot be accessed by another user or guest
    res_u1 = client.post("/api/auth/register", json={"email": "job_user1@example.com", "password": "User1Password"})
    t1 = res_u1.json()["access_token"]
    u1_id = res_u1.json()["user"]["id"]
    h1 = {"Authorization": f"Bearer {t1}"}

    res_u2 = client.post("/api/auth/register", json={"email": "job_user2@example.com", "password": "User2Password"})
    t2 = res_u2.json()["access_token"]
    h2 = {"Authorization": f"Bearer {t2}"}

    user1_job_id = job_manager.create_job(job_type="menu_scan", user_id=u1_id)
    job_manager.complete_job(user1_job_id, {"private": "user1_health_data"})

    # User 2 tries to fetch User 1's job -> 404 (Access Denied / Isolated)
    unauthorized_res = client.get(f"/api/jobs/{user1_job_id}", headers=h2)
    assert unauthorized_res.status_code == 404

    # Anonymous guest tries to fetch User 1's job -> 404 (Access Denied / Isolated)
    guest_res = client.get(f"/api/jobs/{user1_job_id}")
    assert guest_res.status_code == 404

    # User 1 fetches their own job -> 200 OK
    authorized_res = client.get(f"/api/jobs/{user1_job_id}", headers=h1)
    assert authorized_res.status_code == 200
    assert authorized_res.json()["result"] == {"private": "user1_health_data"}

# --- 13. User Lifecycle: Password Change & Account Deletion ---

def test_user_password_change(client):
    # 1. Register a user
    res = client.post("/api/auth/register", json={
        "email": "lifecycle_pass@example.com",
        "password": "InitialPassword123!"
    })
    assert res.status_code == 201
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Attempt change with incorrect old password -> should fail 400
    bad_res = client.put("/api/auth/password", json={
        "old_password": "WrongOldPassword!",
        "new_password": "BrandNewPassword123!"
    }, headers=headers)
    assert bad_res.status_code == 400
    assert "incorrect" in bad_res.json()["detail"].lower()

    # 3. Change password with valid old password -> should succeed 200
    good_res = client.put("/api/auth/password", json={
        "old_password": "InitialPassword123!",
        "new_password": "BrandNewPassword123!"
    }, headers=headers)
    assert good_res.status_code == 200
    assert good_res.json()["success"] is True

    # 4. Verify login works with new password and fails with old password
    fail_login = client.post("/api/auth/login", json={
        "email": "lifecycle_pass@example.com",
        "password": "InitialPassword123!"
    })
    assert fail_login.status_code == 401

    succ_login = client.post("/api/auth/login", json={
        "email": "lifecycle_pass@example.com",
        "password": "BrandNewPassword123!"
    })
    assert succ_login.status_code == 200
    assert "access_token" in succ_login.json()


def test_user_account_deletion(client):
    # 1. Register a user
    res = client.post("/api/auth/register", json={
        "email": "delete_me@example.com",
        "password": "DeleteMePassword123!"
    })
    assert res.status_code == 201
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Attempt deletion with wrong password -> should fail 400
    bad_del = client.request("DELETE", "/api/auth/account", json={
        "password": "WrongPassword!"
    }, headers=headers)
    assert bad_del.status_code == 400

    # 3. Delete account with correct password -> should succeed 200
    good_del = client.request("DELETE", "/api/auth/account", json={
        "password": "DeleteMePassword123!"
    }, headers=headers)
    assert good_del.status_code == 200
    assert good_del.json()["success"] is True

    # 4. Verify user can no longer log in
    login_after_del = client.post("/api/auth/login", json={
        "email": "delete_me@example.com",
        "password": "DeleteMePassword123!"
    })
    assert login_after_del.status_code == 401



