# NutriMenu AI - Production Readiness & Deployment Guide

This document provides a comprehensive, step-by-step checklist to take NutriMenu AI's account management system, API backend, and frontend live in a secure, production-grade environment.

---

## 1. Architectural Summary

NutriMenu AI incorporates an enterprise-grade, high-security account management architecture:

- **Session Management:**
  - Short-lived JSON Web Tokens (15-minute access tokens).
  - Long-lived cryptographically hashed refresh tokens (30-day rotation).
  - Server-side `auth_sessions` tracking with family-based reuse detection (revoking an entire chain if an expired/reused token is presented).
  - Remote session termination across all or individual devices.
- **Database Architecture:**
  - Managed PostgreSQL via modern `psycopg3` (`postgresql+psycopg://`) with native connection pooling (`pool_pre_ping=True`, `pool_size=10`, `max_overflow=20`) and mandatory SSL encryption (`sslmode=require`).
  - Automated database schema migrations powered by Alembic.
  - Backward-compatible SQLite fallback for rapid local testing.
- **Security & Privacy (GDPR/CCPA):**
  - Persistent sliding-window rate limiting stored in `rate_limit_buckets` table.
  - 10-attempt failed login lockout (15-minute freeze) with constant-time password verification defense against timing attacks and account enumeration.
  - Client IP extraction hardened against spoofing via `TRUSTED_PROXY_COUNT`.
  - Comprehensive persistent security audit logging (`audit_logs` table).
  - Self-service personal data export (GDPR JSON archive).
  - 14-day account deletion grace period with instant restoration if cancelled within 14 days.
  - 6-digit cryptographic verification codes for email sign-up and password reset (rate limited to 5 attempts, 10-minute expiry, zero `dev_code` disclosure).
- **Email Delivery:**
  - Production `SMTPEmailBackend` using STARTTLS/SSL with branded HTML transactional email templates.
  - Development/test `ConsoleEmailBackend` outbox with zero external dependencies.

---

## 2. Managed PostgreSQL Setup (Neon / Supabase)

### Option A: Neon Postgres (Serverless)
1. Navigate to [neon.tech](https://neon.tech) and create a project.
2. Under **Connection Details**, select **SQLAlchemy** or **Connection String**.
3. Copy the URL (starts with `postgresql://`).
4. In your `.env` or cloud dashboard, format it as:
   ```env
   DATABASE_URL=postgresql+psycopg://<user>:<password>@<ep-xyz>.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

### Option B: Supabase Postgres
1. Create a project at [supabase.com](https://supabase.com).
2. Go to **Project Settings** > **Database** > **Connection Pooling**.
3. Copy the pooled or direct connection string:
   ```env
   DATABASE_URL=postgresql+psycopg://postgres.<project_ref>:<password>@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
   ```

### Applying Database Migrations
Run the Alembic migration command:
```bash
python -m alembic upgrade head
```
*Note: In production builds, FastAPI automatically verifies that the database schema is at `head` on startup.*

---

## 3. Transactional Email Setup (SMTP)

Configure any standard transactional SMTP provider (SendGrid, Postmark, Resend, Mailgun, or AWS SES):

### Recommended Providers:
- **Resend:**
  ```env
  SMTP_HOST=smtp.resend.com
  SMTP_PORT=587
  SMTP_USER=resend
  SMTP_PASSWORD=re_YourApiKeyHere
  SMTP_FROM=NutriMenu AI <auth@yourverifieddomain.com>
  SMTP_USE_TLS=true
  SMTP_USE_SSL=false
  ```
- **Postmark:**
  ```env
  SMTP_HOST=smtp.postmarkapp.com
  SMTP_PORT=587
  SMTP_USER=your_server_token_here
  SMTP_PASSWORD=your_server_token_here
  SMTP_FROM=NutriMenu AI <auth@yourverifieddomain.com>
  SMTP_USE_TLS=true
  SMTP_USE_SSL=false
  ```

---

## 4. Production Environment Invariants

When `ENVIRONMENT=production`, NutriMenu AI executes strict invariant assertions (`assert_production_ready()` in `backend/settings.py`) before booting. If any invariant is violated, startup aborts immediately to prevent compromised deployments:

| Setting | Required In Production | Rationale |
| :--- | :--- | :--- |
| `DATABASE_URL` | Must be PostgreSQL (`postgresql+psycopg://` with SSL) | SQLite is strictly blocked from production |
| `SECRET_KEY` / `BETTER_AUTH_SECRET` | Minimum 32 random characters | Prevents JWT forgery |
| `ALLOWED_ORIGINS` | Explicit HTTPS URLs (No wildcard `*`, no regex) | Prevents CSRF & credential interception |
| `REQUIRE_EMAIL_VERIFICATION` | `true` | Prevents fake/unverified account spam |
| `SMTP_HOST` | Configured and non-empty | Ensures verification and reset emails reach users |
| `TRUSTED_PROXY_COUNT` | `1` (or count matching cloud proxy topology) | Protects rate limiting against IP spoofing |

Generate strong 32-character secrets using:
```bash
openssl rand -base64 32
```

---

## 5. Render Cloud Deployment

The repository includes a ready-to-use [`render.yaml`](../render.yaml) blueprint:

1. Connect your GitHub repository to [Render](https://render.com).
2. Choose **New Blueprint Instance**.
3. Set the environment variables in the Render dashboard:
   - `DATABASE_URL`: Your managed PostgreSQL connection URL.
   - `SECRET_KEY`: Generated 32-character base64 secret.
   - `ENCRYPTION_SECRET_KEY`: Generated 32-character secret.
   - `ALLOWED_ORIGINS`: `https://your-frontend-domain.com`
   - `APP_URL`: `https://your-frontend-domain.com`
   - `SMTP_HOST`: `smtp.resend.com` (or your chosen provider)
   - `SMTP_USER`: SMTP username
   - `SMTP_PASSWORD`: SMTP password
   - `SMTP_FROM`: `NutriMenu AI <auth@yourdomain.com>`
   - `GEMINI_API_KEY`: Your production Google Gemini API key
4. Render will automatically:
   - Build backend dependencies (`pip install -r requirements.txt`).
   - Run Alembic migrations (`python -m alembic upgrade head`).
   - Launch Uvicorn with the background maintenance worker.

---

## 6. Pre-Launch Verification Runbook

Before directing public user traffic:

1. **Verify Full Test Suite:**
   ```bash
   python -m pytest -v
   ```
   *(Expect 113+ passed tests)*

2. **Verify Frontend Bundle Build:**
   ```bash
   cd frontend
   npm run build
   ```
   *(Ensure 0 errors in Vite build output)*

3. **Verify Security Invariant Guard:**
   ```bash
   python -c "from backend.settings import settings; print('Production settings valid:', settings.environment)"
   ```

4. **Verify Health Endpoint:**
   ```bash
   curl -i https://your-backend-api.com/health
   ```
   *(Expect HTTP 200 with database status `healthy`)*
