<!-- COPIED FILE. Source of truth: ProductSpecification/stories/01-auto-generate-doklad/tests/extended/01_API_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Auto-generate: доклад — API Tests (Extended)

Endpoints: `POST /api/v1/generations`, `GET /api/v1/generations`.
Contracts: `ProductSpecification/api-specs/generations_create.yaml`, `generations_list.yaml`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.doklad@textery.test` / `Qa!Doklad2026` |
| Access token | `Authorization: Bearer <access token of account A>` |
| Valid create body | `{"document_type": "доклад", "topic": "Влияние искусственного интеллекта на образование", "volume_pages": 5}` |
| Error body shape | `{"error_code": "<CODE>", "message": "<text>"}` |
| Bounds | `volume_pages` 1–10, `requirements` ≤ 2000, `extra_wishes` ≤ 2000 |

## 1. Boundary Values

### TC-01-API-1.1 — Volume at the exact boundaries (1 and 10) is accepted

| Field | Value |
|---|---|
| Description | An off-by-one in the range check refuses the two values users pick most — the shortest and the longest document the product offers. |
| Preconditions | Account A signed in. |
| Test data | Valid body with `volume_pages: 1`, then the same body with `volume_pages: 10` |
| Steps | 1. `POST /api/v1/generations` with `volume_pages: 1`.<br>2. `POST /api/v1/generations` with `volume_pages: 10`. |
| Expected result | Both answer `201 Created` with `status: "pending"` and the submitted `volume_pages` echoed back (`1` and `10` respectively); neither returns a `400`. |
| Status | Not run |

### TC-01-API-1.2 — Requirements/extra_wishes at exactly the length limit are accepted

| Field | Value |
|---|---|
| Description | The limit is inclusive. A `>=` where a `>` belongs makes the documented allowance one character smaller than advertised, and the user who hits it has no way to know why. |
| Preconditions | Account A signed in. |
| Test data | `requirements` of exactly 2000 characters, and `extra_wishes` of exactly 2000 characters |
| Steps | 1. `POST /api/v1/generations` with the 2000-character `requirements`.<br>2. `POST /api/v1/generations` with the 2000-character `extra_wishes`. |
| Expected result | Both answer `201 Created` with `status: "pending"`; a subsequent `GET /api/v1/generations/{id}` returns the full 2000 characters unchanged and untruncated. |
| Status | Not run |

## 2. Whitespace & Encoding

### TC-01-API-2.1 — A topic consisting only of whitespace is rejected like an empty topic

| Field | Value |
|---|---|
| Description | A topic of spaces builds a prompt with no subject in it — a paid call for a document about nothing. It must be refused identically to an omitted topic. |
| Preconditions | Account A signed in; no generation exists for account A. |
| Test data | `topic` = `"   "` (three spaces), then `"\t\n"`, then `" "` (a non-breaking space) |
| Steps | 1. `POST /api/v1/generations` with `topic` = three spaces.<br>2. Repeat with a tab and a newline.<br>3. Repeat with a non-breaking space.<br>4. `GET /api/v1/generations`. |
| Expected result | All three answer `400` with `{"error_code": "VALIDATION_ERROR", "message": "topic is required"}` — byte-identical to the omitted-topic refusal; step 4 returns `{"items": [], "next_cursor": null}`. |
| Status | Not run |

> `2.2` (Cyrillic round-trip) was promoted to `01_API_Tests.md` §2.2 — hazard-catalogue
> scan (2026-07-06) found it closes a Core Requirement guard, so it belongs critical-path.

## 3. Idempotency Edge Cases

### TC-01-API-3.1 — Different idempotency keys for otherwise-identical requests create separate generations

| Field | Value |
|---|---|
| Description | The other half of the idempotency contract: deduplicating on the body rather than the key would silently refuse a user who genuinely wants a second take on the same topic. |
| Preconditions | Account A signed in; no generation exists for account A. |
| Test data | The identical valid body sent twice, with `Idempotency-Key: gen-key-1` and then `Idempotency-Key: gen-key-2` |
| Steps | 1. `POST /api/v1/generations` with `Idempotency-Key: gen-key-1`; record `generation_id`.<br>2. `POST /api/v1/generations` with the identical body and `Idempotency-Key: gen-key-2`.<br>3. `GET /api/v1/generations`. |
| Expected result | Both posts answer `201 Created` (neither is a `200` replay); the two `generation_id` values differ; step 3 returns exactly two items. |
| Status | Not run |

## 4. Pagination Edge Cases

### TC-01-API-4.1 — An empty generation list returns an empty page, not an error

| Field | Value |
|---|---|
| Description | A brand-new account hits this on its very first screen. A `404` or a `500` on an empty history turns the normal first-run state into an error banner. |
| Preconditions | Account A signed in with no generations at all. |
| Test data | No rows for account A; request with no `limit` and no `cursor` |
| Steps | 1. `GET /api/v1/generations` with account A's token. |
| Expected result | `200 OK`; body exactly `{"items": [], "next_cursor": null}`; the `null` cursor is the stop condition, so the client does not attempt a further page. |
| Status | Not run |
