# Scenario 1.4: Reject password/confirm_password mismatch — Journey Summary

## green-usecase (2026-07-14)

**Quirk:** `RegisterUser.execute` validates Email → Password → confirm_password equality as three sequential guard blocks with no test asserting this precedence; a request invalid on both email/password and confirm_password has no test locking which error code wins.
**Where:** `backend/usecase/src/auth/register_user.py`.
**Implication:** A future reorder (including a later `/refactor` pass) could silently flip which error_code is returned for a multi-invalid-field request, with nothing catching it. Flagged by premortem at both red-usecase and green-usecase phases, still unresolved as of this commit.
