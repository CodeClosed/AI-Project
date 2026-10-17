# NutriMenu AI — Security & Regression Test Plan

This test plan documents automated test coverage, execution commands, security regression cases, and authorization verification across the entire NutriMenu AI stack.

---

## 1. Test Suite Overview

| Test Module | Coverage Area | Test Count | Status |
|---|---|:---:|:---:|
| `tests/test_security_and_auth.py` | Bcrypt hashing, AES encryption, dummy hash timing defense, brute-force lockout, rate limits | 15 | **Passed** |
| `tests/test_auth_sessions.py` | Session family creation, token rotation, reuse detection, 60s race grace window | 5 | **Passed** |
| `tests/test_account_management.py` | Multi-device session revocation, email change dual-alert, deletion grace period, audit logs | 4 | **Passed** |
| `tests/test_email_verification.py` | Code issuance, HMAC-SHA256 validation, single-use enforcement, anti-enumeration | 3 | **Passed** |
| `tests/test_mfa_and_password_reset.py` | TOTP verification, backup code consumption, password reset token version rotation | 11 | **Passed** |
| `tests/test_production_config.py` | Production security invariants, secret strength checks, SQLite rejection in prod | 5 | **Passed** |
| `tests/test_recommendation_engine.py` | 3-tier Good/Medium/Bad scoring, clinical thresholding, macro calculation | 7 | **Passed** |
| `tests/test_safety_and_rules.py` | Strict allergen and dietary hard exclusions (fit_score=0; AI cannot override) | 7 | **Passed** |
| `tests/test_matrix_generator.py` | Deterministic BMR/TDEE calculation and AI clinical matrix generation | 3 | **Passed** |
| `tests/test_plate_optimizer.py` | Plate macronutrient synthesis, portion adjustments, target adherence | 4 | **Passed** |
| `tests/test_extraction_validator.py` | OCR extraction validation, non-food rejection, hallucination defense | 12 | **Passed** |
| `tests/test_noise_filter.py` | OCR noise filtering, layout line removal, special symbol sanitization | 6 | **Passed** |
| `tests/test_nutrition_ai.py` | Clinical nutrition assessment logic and heuristic fallback | 5 | **Passed** |
| `tests/test_gemini_client.py` | Gemini 2.5/3.7 Vision API client mock and error handling | 9 | **Passed** |
| `tests/test_openrouter_extractor.py` | OpenRouter multi-model extraction, schema parsing, fallback strategies | 6 | **Passed** |
| `tests/test_recognizer.py` | End-to-end menu recognition pipeline and flat dish formatting | 5 | **Passed** |
| `tests/test_integration_pipeline.py` | End-to-end integrated scan -> extract -> matrix -> score -> plate pipeline | 2 | **Passed** |
| `tests/test_config.py` | Environment variable resolution, API key fallback priority | 4 | **Passed** |
| **Total** | **Comprehensive Full-Stack Coverage** | **113** | **100% Passed** |

---

## 2. Test Execution Commands

### Run Entire Test Suite (All 19 Modules)
```bash
python -m pytest tests/
```

### Run Authentication & Security Regression Tests
```bash
python -m pytest tests/test_security_and_auth.py tests/test_auth_sessions.py tests/test_account_management.py tests/test_email_verification.py tests/test_mfa_and_password_reset.py tests/test_production_config.py
```

### Run Domain & Recommendation Tests
```bash
python -m pytest tests/test_recommendation_engine.py tests/test_safety_and_rules.py tests/test_matrix_generator.py tests/test_plate_optimizer.py tests/test_extraction_validator.py
```

---

## 3. Multi-Tenant Authorization Test Matrix

To prevent Insecure Direct Object References (IDOR) and broken object-level authorization:

| Action | User Alice | User Bob | Enforced Behavior |
|---|---|---|---|
| Read Saved Menu | Own Menu (ID 1) | Alice's Menu (ID 1) | **404 / Access Denied** for Bob |
| Delete Saved Menu | Own Menu (ID 1) | Alice's Menu (ID 1) | **404 / Access Denied** for Bob |
| Read Logged Meal | Own Meal (ID A) | Alice's Meal (ID A) | Query explicitly filters `user_id == current_user.id` |
| Export Meals CSV | Own CSV | Alice's CSV | Export only aggregates records matching `user_id` |
| View Active Sessions | Own Sessions | Alice's Sessions | Query explicitly filters `AuthSession.user_id == current_user.id` |
| Terminate Session | Own Session | Alice's Session | **404 / Access Denied** if session does not belong to user |
| Inspect Background Job | Own Job (ID J) | Alice's Job (ID J) | **404 / Access Denied** if `job.user_id != user.id` |
