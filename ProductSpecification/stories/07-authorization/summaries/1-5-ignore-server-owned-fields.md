## red-adapter db (2026-07-14)

**Quirk:** `Account.__init__` hardcodes `is_verified=False` with no constructor parameter and no setter, correct for *creating* a new account. `AccountModel.to_domain()` reuses this same constructor to *reconstruct* an account from a DB row, silently dropping the row's real `is_verified` value.
**Where:** `backend/domain/src/auth/account.py`, `backend/adapters/db/src/model/auth/account_model.py`.
**Implication:** Scenario 3.x (email verification) needs a domain-level way to represent a verified account on reconstruction (e.g. a `reconstitute` factory distinct from `create`), plus a round-trip test writing `is_verified=True` and asserting `to_domain().is_verified is True`.

## green-adapter db (2026-07-14)

**Quirk:** `SqlAlchemyAccountRepository.save()` has no exception handling around `session.commit()` — a raw SQLAlchemy/DB-driver exception (connection failure, or a future unique-constraint violation once scenario 2.2 lands) propagates unmapped.
**Where:** `backend/adapters/db/src/access/auth/account_storage.py`.
**Implication:** The ADR (`decisions/account-persistence-design-decision.md`, Edge Cases table) already commits to "persistence failure maps to a defined exception" as required behavior, but no red test forces it yet. A future step (likely green-adapter rest, or a dedicated exception-mapping scenario) needs a test that stubs `commit()` to raise and asserts `save()` translates it into a defined `AccountRepository`-level exception.

## green-adapter rest (2026-07-14)

**Quirk:** `container.py`'s `create_register_user()` now wires a real `SqlAlchemyAccountRepository`, closing the prior silent-data-loss gap — but this and its two sibling factories (`create_get_generation`, `create_request_generation`) have zero dedicated test coverage; `backend/application` has no `tests/` directory at all. The wiring is only exercised indirectly by acceptance tests.
**Where:** `backend/application/src/app/container.py`.
**Implication:** A future task should add `backend/application/tests/` covering the session-per-request generators (commit-then-close on success, close-on-exception) — flagged independently by agent-review and premortem, not scoped to story 7 alone since the two pre-existing generation factories share the same gap.

**Quirk:** `RegisterUser.execute` passes the raw validated password straight to `Account.create(password_hash=password, ...)` — no hashing exists anywhere in the codebase (confirmed via grep for bcrypt/passlib/argon2/hashlib). Before this step, the null-object `AccountRepository` fallback silently discarded every account, so this was inert; now that a real repository is wired, plaintext passwords are actually persisted to the database.
**Where:** `backend/usecase/src/auth/register_user.py`, `backend/domain/src/auth/password.py`.
**Implication:** This is a deliberate, tracked deferral — password hashing is `05_Security_Tests.md` Scenario 1, sequenced after Backend/Integration/Frontend per this project's lifecycle (`workflow.md`) — but premortem rated it BLOCK-severity since real rows now exist with plaintext credentials. Prioritize the Security phase's password-hashing scenario before any shared/prod-like environment is exposed to real user data.

## green-acceptance (2026-07-14)

**Quirk:** `given_registration_request_with_server_owned_fields()` (`acceptance/statements/auth_statements.py`) still uses a fixed email (`attacker@example.com`), not a per-run-unique one — the ADR's design called for a per-run-unique fixture so reruns don't accumulate duplicate rows, but this was never implemented (pre-existing from an earlier red-acceptance step, out of scope for green-acceptance's remove-marker-only rule).
**Where:** `acceptance/statements/auth_statements.py`.
**Implication:** Reruns of this acceptance test create additional `accounts` rows with the same email today (no unique constraint yet); once scenario 2.2 adds the constraint, reruns will start failing with a 409/conflict unless this fixture is made unique first.
