## red-adapter db (2026-07-14)

**Quirk:** `Account.__init__` hardcodes `is_verified=False` with no constructor parameter and no setter, correct for *creating* a new account. `AccountModel.to_domain()` reuses this same constructor to *reconstruct* an account from a DB row, silently dropping the row's real `is_verified` value.
**Where:** `backend/domain/src/auth/account.py`, `backend/adapters/db/src/model/auth/account_model.py`.
**Implication:** Scenario 3.x (email verification) needs a domain-level way to represent a verified account on reconstruction (e.g. a `reconstitute` factory distinct from `create`), plus a round-trip test writing `is_verified=True` and asserting `to_domain().is_verified is True`.

## green-adapter db (2026-07-14)

**Quirk:** `SqlAlchemyAccountRepository.save()` has no exception handling around `session.commit()` — a raw SQLAlchemy/DB-driver exception (connection failure, or a future unique-constraint violation once scenario 2.2 lands) propagates unmapped.
**Where:** `backend/adapters/db/src/access/auth/account_storage.py`.
**Implication:** The ADR (`decisions/account-persistence-design-decision.md`, Edge Cases table) already commits to "persistence failure maps to a defined exception" as required behavior, but no red test forces it yet. A future step (likely green-adapter rest, or a dedicated exception-mapping scenario) needs a test that stubs `commit()` to raise and asserts `save()` translates it into a defined `AccountRepository`-level exception.
