## design (2026-07-14)

**Decision:** Password value object lives in backend/domain, mirroring Email's constructor-validation pattern (raise ValueError on invalid input); single INVALID_PASSWORD error code for all sub-violations.
**Why:** Keeps error taxonomy consistent with INVALID_EMAIL and reuses a proven validation-at-construction shape instead of inventing a new one.
**Where applied:** `backend/domain/src/auth/password.py`, `backend/usecase/src/auth/register_user.py`.

## green-usecase (2026-07-14)

**Quirk:** `RegisterUser.execute` accepts `confirm_password` as a parameter but never compares it against `password` — no code path enforces the match, and no test in this scenario's fixtures can catch a mismatch since they always set both fields equal.
**Where:** `backend/usecase/src/auth/register_user.py`.
**Implication:** Scenario 1.4 (password/confirm_password mismatch) must add the actual comparison and a dedicated red test — nothing from Scenario 1.3 exercises or guards this path.
