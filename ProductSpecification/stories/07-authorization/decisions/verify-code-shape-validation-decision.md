# Decision: Where `/verify` rejects a malformed `code` (shape validation layer)

**Date**: 2026-07-16 **Scenarios**: 3.1 (and constrains 3.2–3.6)

Scenario 3.1's `green-adapter rest` (commit `5e00d2f`) gave `VerifyRequestDto` a
`code: str = Field(pattern=r"^[0-9]{6}$")` constraint, folding in the shape-validation
finding premortem raised on `5be64e9`. The constraint was added but never exercised: the
only `/verify` DTO test posts a valid `"042917"`, so deleting `pattern=` leaves the whole
suite green (coverage.py is structurally blind here — a declarative Pydantic constraint
compiles to no branch, so the gap can never surface as an uncovered line).

Pinning it with a test forced a conflict between two artifacts, flagged by agent-review on
`5e00d2f`:

- `Field(pattern=...)` makes FastAPI answer **422** with Pydantic's own error envelope.
- `ProductSpecification/api-specs/auth_verify.yaml` documents only **200/400/409/500** for
  this endpoint — no 422 — while its `VerifyRequest` schema *does* carry
  `pattern: '^[0-9]{6}$'`, i.e. the shape rule is specified but the rejection status is not.

Writing the test without settling this would have baked in whichever status the code
happens to produce today.

| Rejected | Why |
|----------|-----|
| Keep the DTO constraint, add a documented `422` to `auth_verify.yaml` | Honors the `5be64e9` premortem finding verbatim and keeps rejection provably at the adapter boundary (the usecase is never reached, so `mock_usecase.execute` can be asserted never-awaited). But it makes `/verify` the only endpoint in this story that rejects request shape at the REST layer with a Pydantic 422 envelope, while `/register` rejects shape in the domain with a `{error_code, message}` 400. Two validation taxonomies on one auth surface, and the 422 body shape is Pydantic's, not this story's. |
| Keep the DTO constraint **and** add domain validation (defense-in-depth) | Duplicates the 6-digit rule in two layers that can drift independently, and still ships the 422/400 inconsistency for every malformed request, since the DTO rejects first. |

**Chosen**: drop `pattern=` from `VerifyRequestDto` and validate the code's shape in the
**domain**, exactly as `Email` and `Password` already do. `RegisterRequestDto` carries no
field constraints at all — `/register`'s malformed-email case (scenario 1.1) is a
**400 `INVALID_EMAIL`** raised by the `Email` value object and mapped by the usecase, never
a 422. Matching that precedent keeps one taxonomy across the auth surface and needs **no
change to `auth_verify.yaml`**: its documented 400 ("Code incorrect or expired — generic
client-safe error") already covers a malformed code.

The cost is accepted explicitly: the `never awaited` assertion the coverage step originally
planned no longer holds, because rejection now happens inside the usecase rather than at
the adapter boundary. The rest-layer test still goes genuinely RED (422 today → 400
expected), and the load-bearing proof moves to a domain test that pins the rule directly.

## Model

- **New** `backend/domain/src/auth/verification_code_value.py`: `VerificationCodeValue`
  value object. Constructor validates a 6-character ASCII-digit string
  (`^[0-9]{6}$`), rejecting non-`str` input (mirroring `Email`/`Password`'s `isinstance`
  guard), wrong length, and any non-digit character; raises `ValueError` on violation.
  `.value` returns the string. **Never coerced to `int`** — `auth_verify.yaml`'s
  never-coerce note and scenario 2.6's leading-zero guarantee both depend on this.
- `backend/domain/src/auth/verification_code.py`: `VerificationCode.generate()` builds its
  random code through `VerificationCodeValue` so the 6-digit rule is single-sourced rather
  than restated by the `f"{...:06d}"` format string alone.
- `backend/usecase/src/auth/verify_account.py`: `execute()` validates the code **before**
  any repository lookup, via a `_validate_code` helper mirroring `RegisterUser._validate_email`:
  `ValueError` → `ValidationException(error_code="INVALID_CODE", message="The verification code is not valid.")`
  → 400 through the generic `validation_exception_handler` wired since scenario 1.1. No new
  inbound-adapter mapping needed.
- `backend/adapters/rest/src/dto/auth/verify_request_dto.py`: `code: str` with no `Field`
  constraint, mirroring `RegisterRequestDto`.
- No change to `ProductSpecification/api-specs/auth_verify.yaml`.

## Edge Cases

| Case | Behavior |
|------|----------|
| Validation order: malformed code **and** malformed email | `execute()` validates email first (`Email(email)`, already the first line today), so a request bad on both axes answers `INVALID_EMAIL`. Arbitrary but deterministic, and matches `RegisterUser`'s existing email-before-password order. |
| Malformed code never touches the DB | Shape validation runs before `find_by_email`/`find_active_by_account_id`, so a malformed code costs zero queries. This is what replaces the discarded `never awaited` assertion: the domain test pins the rule, and the usecase test can assert both repositories were never called. |
| Does a distinct `INVALID_CODE` leak an oracle? | No. Shape rejection is a pure function of the submitted string and is independent of any account's existence or state — it reveals nothing a client didn't already send. This is unlike wrong-*value* rejection (3.2), whose error code must stay generic so it can't distinguish "wrong code" from "no such email". |
| Scenario 3.2's wrong-value error code | Deliberately **not** decided here. 3.2 owns it and may reuse a generic 400 code distinct from `INVALID_CODE`; nothing in this decision forces its hand, since the two rejections happen at different points on different inputs. |
| Leading zeros (`"042917"`) | Accepted — `VerificationCodeValue` validates and stores a `str` and never parses to `int`, so `"042917"` survives intact, preserving scenario 2.6's end-to-end guarantee. |
| Codes of the wrong length that are all digits (`"12345"`, `"1234567"`) | Rejected by the length half of the rule, not just the digit half — both halves need their own test case, since a regex typo could drop either. |
| Unicode digits (e.g. `"١٢٣٤٥٦"`, Arabic-Indic) | Rejected. The rule is ASCII `[0-9]` only, not `str.isdigit()` (which accepts many Unicode digit categories). Worth its own test case, since `isdigit()` is the obvious wrong implementation and would pass a naive all-ASCII test suite. |
