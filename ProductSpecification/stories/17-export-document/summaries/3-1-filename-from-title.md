# Scenario 3.1 — filename derived from title: journey summary

## red-acceptance (2026-07-27)

**Quirk:** A title-bearing save (`PUT /api/v1/documents/{id}` with a `title` field) returns 200 while silently discarding the title — `SaveDocumentRequestDto` is a Pydantic model with `extra="ignore"`, so an unknown field is dropped, not rejected.
**Where:** `backend/adapters/rest/src/dto/document/document_dtos.py` (`SaveDocumentRequestDto`).
**Implication:** The red-acceptance setup could send a title and still get a green transport, so the RED lands on the export filename, not on a save error; and green must add `title` to the DTO to make the field actually persist — a dropped field looks like success.

## red-adapter db (2026-07-27)

**Quirk:** A save-then-find in the SAME db session does not exercise a real SELECT — the CAS UPDATE's `RETURNING` loads the row into the identity map, and the session is built `expire_on_commit=False`, so a following `find_by_id_and_owner` returns the cached instance instead of re-hydrating from the database.
**Where:** `backend/adapters/db/src/session.py` (`async_sessionmaker(..., expire_on_commit=False)`); surfaces in `document_storage.py` `save_content_if_version_matches` (RETURNING) → `find_by_id_and_owner`.
**Implication:** Any db-adapter round-trip test that claims to verify persistence must call `session.expire_all()` (or use a fresh session) between the write and the read, or a durability/mapping bug reads green off the cached object.
