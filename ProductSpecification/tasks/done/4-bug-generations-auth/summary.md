# Task 4: Generations auth — Journey Summary

## fix (2026-07-17)

**Quirk:** A FastAPI dependency override written as `lambda mock=the_mock: mock` is not a closure — FastAPI inspects the override's signature, sees a parameter with a default, and resolves `mock` as a *query parameter*, passing its own value instead of the mock.
**Where:** `backend/adapters/rest/tests/router/generation/conftest.py` (`_returning`), and any `app.dependency_overrides[...]` assigned inside a loop.
**Implication:** Overrides must be zero-argument closures built by a helper. The failure is silent in the worst way: the endpoint still answers 201 and the body still matches, so only an `assert_awaited_once_with` on the mock reveals that nothing was recorded.

## fix (2026-07-17)

**Quirk:** `TRUNCATE accounts` fails with "cannot truncate a table referenced in a foreign key constraint" the moment any new table gains an `owner_id` FK — Postgres only permits it when every referencing table is truncated in the same statement.
**Where:** `backend/adapters/db/tests/conftest.py`, plus two private cleanup blocks in `tests/access/document/test_document_storage_cas_shape.py` and `test_document_storage_concurrency.py`.
**Implication:** Adding an owner-owning table means updating all three TRUNCATE sites, not just the shared conftest — the two concurrency tests open their own engines and clean up independently.

## discussion (2026-07-17)

**Decision:** Opening a generation in the editor needs no backend change: the frontend POSTs an empty document, then PUTs the generation's content into it.
**Why:** `POST /api/v1/documents` already creates an empty draft and `PUT` already sets content, so the bridge exists; adding `Document.generation_id` would contradict the deliberate no-link choice recorded in `document.py`'s docstring and the documents ownership ADR.
**Where applied:** `frontend` — no backend surface; the only missing piece was the history list, shipped in `feat: owner-scoped history`.

## discussion (2026-07-17)

**Decision:** With no `Document.generation_id`, re-opening the same generation creates a second document, and that is accepted.
**Why:** The link is what would make opening idempotent, and it was judged not worth contradicting the documents ADR for; the frontend can gate the button instead.
**Where applied:** `backend/domain/src/document/document.py` — the absent field is the decision.

## verified (2026-07-17)

**Quirk:** Git Bash on Windows mangles UTF-8 request bodies passed to `curl -d`, so a POST carrying Cyrillic answers `{"detail":"There was an error parsing the body"}` from a backend that is working correctly.
**Where:** any manual `curl` probe of `/api/v1/generations` or `/api/v1/documents` from the Bash tool.
**Implication:** Probe those endpoints from Python (`urllib`/`httpx`) or `--data-binary @file`; a parse error from a shell curl is not evidence of a backend bug.
