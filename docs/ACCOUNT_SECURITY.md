# NutriMenu AI — Account Security & Lifecycle Specification

This specification documents the complete account lifecycle, authentication mechanics, multi-factor authentication, cryptographic algorithms, and security policies for NutriMenu AI.

---

## 1. Password Storage & Cryptography

- **Algorithm**: Adaptive Bcrypt with minimum cost factor 12.
- **Salting**: Cryptographically random 16-byte salt generated per password by `bcrypt`.
- **Pre-hashing & Length**: Truncation-safe handling up to 72 bytes. Input policy requires >= 8 characters.
- **Trivial Password Defense**: Common passwords (`password`, `12345678`, `admin123`, `letmein`, `welcome`, etc.) are actively rejected via Pydantic validators.
- **Timing Attack Defense**: Non-existent user logins run a constant-time dummy verification hash (`verify_dummy_password`) to ensure response times remain indistinguishable from legitimate logins, preventing account enumeration.

---

## 2. Session Management & Token Rotation

- **Access Tokens**: Short-lived JWTs (15-minute TTL) containing `sub` (User ID), `sid` (Session ID), and `token_version`. Signed with HMAC-SHA256 (`HS256`).
- **Refresh Tokens**: Cryptographically random 64-character hex strings stored hashed via SHA-256 in the `sessions` database table.
- **Idle Timeout**: 7 days.
- **Absolute Timeout**: 30 days.
- **Rotation Mutex & Grace Window**: On every refresh call, a new access token and refresh token are issued. A **60-second grace window** allows benign concurrent reload requests to receive the new token rather than falsely triggering reuse revocation.
- **Reuse Detection**: If a revoked token outside the grace window is submitted, the system flags token theft, terminates the entire session family, and writes an audit log event.
- **Multi-Tab Sync**: `AuthContext.jsx` listens to browser `storage` events to ensure logins, logouts, and token rotations synchronize instantly across open tabs.

---

## 3. Two-Factor Authentication (MFA)

- **Standard**: RFC 6238 Time-Based One-Time Password (TOTP) algorithm compatible with Google Authenticator, Authy, and 1Password.
- **Secrets Encryption**: TOTP secrets are encrypted at rest using AES-256-CBC via Python `cryptography.fernet`.
- **Enrollment Flow**: Secrets are only permanently saved after the user proves successful configuration by verifying their first rolling 6-digit TOTP code.
- **Backup Recovery Codes**: 10 high-entropy alphanumeric emergency recovery codes are generated upon setup, hashed individually with Bcrypt, and popped/invalidated single-use upon successful redemption.
- **Email 2FA**: Optional fallback method dispatching 6-digit cryptographic OTPs with a 10-minute TTL.

---

## 4. Account Lifecycle & Recovery

### Password Reset
1. User requests reset via `/api/auth/forgot-password`.
2. Anti-enumeration blind response is returned regardless of email existence.
3. If the account exists, a 6-digit cryptographic code is stored as HMAC-SHA256 with a 10-minute expiration.
4. Submission of code + new password rotates `token_version`, revoking all active sessions across all devices.

### Email Address Change
1. Dual notification: Confirmation code dispatched to the new email address; alert notice dispatched to the old address.
2. Verification confirms ownership of the new inbox, updates `email`, invalidates other active sessions, and reissues fresh tokens.

### Account Lockout
- After 10 consecutive failed password attempts, the account is temporarily locked for 15 minutes.
- A security notification is dispatched to the user's registered email address.
