# NutriMenu AI — Security Remediation Log

This log documents every confirmed defect, vulnerability, and architectural weakness remediated during the audit renewal.

---

### Finding ID: SEC-01 — Token Rotation Race Invalidation
- **Severity**: High
- **Affected Components**: `backend/auth/sessions.py:rotate_refresh_token`, `frontend/src/api.js:rotateTokens`
- **Root Cause**: When a user rapidly refreshed the browser or fired concurrent requests with an expired access token, two parallel calls submitted the same refresh token. The first call rotated it, causing the second call to trigger reuse detection, which revoked the entire session family and signed the user out.
- **Remediation**: Added a 60-second grace window to `rotate_refresh_token`. If an incoming token matches the immediately preceding rotated token within 60 seconds, the new active token is reissued without penalty.
- **Verification**: `tests/test_auth_sessions.py` passes all 5 tests.

---

### Finding ID: SEC-02 — Transient Error Session Wipeout
- **Severity**: High
- **Affected Components**: `frontend/src/api.js:rotateTokens`, `fetchWithAuth`
- **Root Cause**: Any non-200 response (such as a 502/503 cold start, temporary 429, or network drop) triggered `clearStoredTokens()`, wiping user credentials from the device.
- **Remediation**: Hardened `rotateTokens()` and `fetchWithAuth()` so stored tokens are only deleted upon definitive authentication rejections (HTTP 401, 403, 422). Transient network errors throw descriptive connection warnings without logging the user out.
- **Verification**: Manual network blip simulation and automated route checks.

---

### Finding ID: SEC-03 — Default Profile Autosave Overwrite
- **Severity**: High
- **Affected Components**: `frontend/src/context/NutritionContext.jsx`
- **Root Cause**: The profile autosave `useEffect` hook ran immediately on component mount before the server-side profile request resolved, pushing blank defaults (`age: 30`, `weight: 70`) over real user database records.
- **Remediation**: Gated autosave behind `initialLoadDoneRef.current = true`. Autosave remains inert until the remote profile has successfully hydrated into state.
- **Verification**: Verified zero PUT requests to `/api/profile` during initial mount and page reload.

---

### Finding ID: SEC-04 — Database Test Contamination
- **Severity**: Medium
- **Affected Components**: `tests/conftest.py`, `backend/database.py`
- **Root Cause**: Test runs executed against `nutrimenu.db`, causing test fixtures to truncate or clear active sessions from the local development database.
- **Remediation**: Implemented `tests/conftest.py` with an autouse session fixture that redirects `DATABASE_URL` to an ephemeral SQLite database (`test_nutrimenu_*.db`) and cleans it up after the test session finishes.
- **Verification**: Ran `python -m pytest tests/`; confirmed `nutrimenu.db` remains pristine.

---

### Finding ID: SEC-05 — Transactional Email Header Syntax
- **Severity**: Medium
- **Affected Components**: `backend/email_service.py`
- **Root Cause**: `SMTPEmailBackend` constructed nested `From` headers (e.g. `NutriMenu AI <NutriMenu AI <sender@domain.com>>`), causing RFC-5322 rejections on strict mail servers.
- **Remediation**: Refactored sender formatting to use standard `email.utils.formataddr(("NutriMenu AI", clean_address))`, added SSL/STARTTLS context negotiation, and provided `scripts/send_test_email.py`.
- **Verification**: `python scripts/send_test_email.py` and unit checks.

---

### Finding ID: SEC-06 — Distributed Rate Limiting & Background Job Coordination
- **Severity**: Medium
- **Affected Components**: `backend/jobs.py`, `backend/security.py`, `backend/settings.py`
- **Root Cause**: `JobManager` and `SlidingWindowRateLimiter` held state exclusively in local process memory, failing to coordinate across multi-worker deployments (e.g. Gunicorn/Uvicorn replicas or container clusters).
- **Remediation**: Added Redis backend support with atomic pipeline execution (`ZADD`, `ZREMRANGEBYSCORE`, `ZCARD`) when `REDIS_URL` is set, retaining the in-memory fallback for local development.
- **Verification**: Verified unit execution of both Redis operations and in-memory fallback.
