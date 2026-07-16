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
  random code through `VerificationCodeValue`. To make this genuine single-sourcing rather
  than a second statement of the same rule, the digit count moves **into**
  `VerificationCodeValue` and `verification_code.py` imports it, replacing its own private
  `_CODE_DIGITS`/`_CODE_MODULUS` constants. `generate()` must keep returning a **`str`**
  (`VerificationCodeValue(...).value`), never the value object itself — see the Edge Cases
  table; this is the highest-risk line in the whole change and is guarded by a test that
  must land *before* it (see `red-usecase`).
- `backend/usecase/src/auth/verify_account.py`: `execute()` validates the code **before**
  any repository lookup, via a `_validate_code` helper mirroring `RegisterUser._validate_email`:
  `ValueError` → `ValidationException(error_code="INVALID_CODE", message="The verification code is not valid.")`
  → 400 through the generic `validation_exception_handler` wired since scenario 1.1. No new
  inbound-adapter mapping needed.
- `backend/usecase/src/auth/verify_account.py`: `execute()` also gains `_validate_email`, the
  exact twin of `RegisterUser._validate_email` (`ValueError` → `ValidationException("INVALID_EMAIL")`
  → 400). This is **not** scope creep bolted onto this decision — it closes a live defect the
  first draft of this ADR asserted was already fixed (see Edge Cases row 1). Mirroring
  `RegisterUser` is this decision's whole premise; mirroring it on only one of the two
  validated inputs would ship the inconsistency the decision exists to remove.
- `backend/adapters/rest/src/dto/auth/verify_request_dto.py`: `code: str` with no `Field`
  constraint, mirroring `RegisterRequestDto`.
- No change to `ProductSpecification/api-specs/auth_verify.yaml`.

## Edge Cases

| Case | Behavior |
|------|----------|
| Validation order: malformed code **and** malformed email | Email is validated first, so a request bad on both axes answers `INVALID_EMAIL`. Arbitrary but deterministic, and matches `RegisterUser`'s existing email-before-password order. **Correction (both review passes on `1583276`, verified against the code):** this ADR's first draft claimed that was already true today because `Email(email)` is `execute()`'s first line. It is not. That line is *bare* — `VerifyAccount` has no `_validate_email`, unlike `RegisterUser`, so `Email`'s `ValueError` is not a `ValidationException`, misses `validation_exception_handler`, and falls to `unhandled_exception_handler` → **500 `{"detail": "internal server error"}`**. `/verify` answers a client error with a server status today, and no test anywhere pins it (verified: `INVALID_EMAIL` appears only in `register_user.py`). The false claim was load-bearing — it was the ADR's reason for closing the ordering question, so no step would have added the mapping. Fixed by folding `_validate_email` into this scenario's `red-usecase`/`green-usecase` steps rather than deferring it. |
| Malformed code never touches the DB | Shape validation runs before `find_by_email`/`find_active_by_account_id`, so a malformed code costs zero queries. This is what replaces the discarded `never awaited` assertion: the domain test pins the rule, and the usecase test can assert both repositories were never called. |
| Does a distinct `INVALID_CODE` leak an oracle? | Not on its own. Shape rejection is a pure function of the submitted string and is independent of any account's existence or state — it reveals nothing a client didn't already send. This is unlike wrong-*value* rejection (3.2), whose error code must stay generic so it can't distinguish "wrong code" from "no such email". |
| …but the axis beside it does (premortem on `1583276`) | **The row above is true and insufficient**, and the gap is worth naming here precisely because this ADR is where `/verify`'s status taxonomy gets reasoned about. `find_by_email` is typed `Optional[Account]` yet `verify_account.py` dereferences `account.id` unconditionally → `AttributeError` → **500** for an unknown email; same shape one line down, where `find_active_by_account_id` is also `Optional` and `verification_code.matches(code)` → **500** for any account with no active code. Once `main.py` is wired, `/verify`'s observable taxonomy becomes 400-on-malformed-code, 500-on-unknown-email, 200-on-wrong-code (the known no-`else` bug) — i.e. the status line discriminates account existence. **Deliberately not fixed here:** `verify-account-design-decision.md` scoped the `None` branches to 3.2–3.6 on purpose, and pulling them into 3.1 would re-litigate an approved decision. Recorded so 3.5 inherits a named requirement instead of having to notice the `Optional` itself, and so this ADR's oracle analysis is not read as a clean bill of health for the endpoint. |
| Scenario 3.2's wrong-value error code | Deliberately **not** decided here. 3.2 owns it and may reuse a generic 400 code distinct from `INVALID_CODE`; nothing in this decision forces its hand, since the two rejections happen at different points on different inputs. |
| Leading zeros (`"042917"`) | Accepted — `VerificationCodeValue` validates and stores a `str` and never parses to `int`, so `"042917"` survives intact, preserving scenario 2.6's end-to-end guarantee. |
| Routing `generate()` through the new value object touches the **live** `/register` path (premortem on `1583276`, CREDIBLE) | `VerificationCode.generate()` is reached by `create_register_user`, which **is** wired in `main.py` — unlike `/verify`, which is not. It also has **zero test coverage**: there is no `backend/domain/tests/auth/test_verification_code.py`, and `.generate(` appears in no test in `backend/*/tests` or `acceptance/` (verified by grep, not assumed). The natural way to write this change is also the wrong way: if `generate()` stores the `VerificationCodeValue` instead of its `.value`, then `VerificationCode.matches()` compares a value object against a `str` and returns `False` for **every correct code** — a silent, total verification outage — or `VerificationCodeModel.from_domain` feeds a value object into a `String(6)` column and `/register` 500s on insert. Nothing in-module would go RED, and scenario 2.6's leading-zero guarantee (which this ADR leans on) rests on this untested function. **Guard, ordered explicitly:** `red-usecase` pins `generate()` *first* — asserting `VerificationCode.generate(...).code` is a 6-character ASCII-digit `str` (`isinstance(..., str)`, not merely truthy) and that a generated code round-trips through the DB model unchanged — and only then does `green-usecase` route it through the value object. A cleanup that cannot fail loudly does not get to ride along on a live path in a deploy-or-zero sprint. |
| Codes of the wrong length that are all digits (`"12345"`, `"1234567"`) | Rejected by the length half of the rule, not just the digit half — both halves need their own test case, since a regex typo could drop either. |
| Unicode digits (e.g. `"١٢٣٤٥٦"`, Arabic-Indic) | Rejected. The rule is ASCII `[0-9]` only, not `str.isdigit()` (which accepts many Unicode digit categories). Worth its own test case, since `isdigit()` is the obvious wrong implementation and would pass a naive all-ASCII test suite. |
