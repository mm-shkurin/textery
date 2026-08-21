> **Implementation Order**: hazard guards for the editor extension — fold into the same
> TDD cycles as 07. Autosave/title safety, then migration & dirty-state.

# Story 5 — Editor Extension Hazard Tests

Companion to 07. Forced guards from the hazard scan of the editor extension.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the owner) | `qa.manual@textery.test` / `Qa!Manual2026` |
| Document A1 | id `3d9b1f42-6c07-4a18-9e55-71b2c8d4a0f3`, `title` `Отчёт по практике`, `content` `<p>Первый абзац.</p>`, `version` `2` |
| Document A2 (legacy inline-only) | id `8c4e0a5d-19f7-4b62-8d31-c07a5e94b6f2`, `content` `Первая строка<br>Вторая строка`, saved pre-migration |
| Save request | `PUT /api/v1/documents/{document_id}` with `{"content": …, "title": …, "version": …}` |
| Title limit | 200 Unicode code points, NFC-normalized, trimmed; over-length rejected whole |
| Autosave debounce | 1 s idle after the last keystroke |
| Error bodies | `{"error_code": "VERSION_CONFLICT", "message": "The document was modified by another save. Refetch and retry."}`, `{"error_code": "INVALID_VERSION", …}`, `{"error_code": "UNAUTHORIZED", "message": "A valid access token is required."}` |

## 9. Autosave & Title Hazards

### TC-05-HAZ-9.1 — A content-only autosave does not wipe the title

| Field | Value |
|---|---|
| Description | Autosave sends content on every debounce tick. If an omitted `title` is read as "set it to null", every autosave silently erases the title the user typed once — and with it the export filename. The three states must stay distinguishable. |
| Preconditions | Document A1 exists with `title` `Отчёт по практике` at `version` `2`, open in the editor. |
| Test data | (a) `{"content": "<p>Абзац</p>", "version": 2}` — `title` omitted. (b) `{"content": "<p>Абзац</p>", "title": null, "version": <current>}`. (c) `{"content": "<p>Абзац</p>", "title": "Новый отчёт", "version": <current>}`. |
| Steps | 1. `PUT` body (a); then `GET /api/v1/documents/{A1}` and read `title`.<br>2. `PUT` body (b); then `GET` and read `title`.<br>3. `PUT` body (c); then `GET` and read `title`. |
| Expected result | Each `PUT` answers `200 OK`. After step 1 `title` is still `Отчёт по практике` (omitted → unchanged); after step 2 `title` is `null` (explicit null → cleared); after step 3 `title` is `Новый отчёт` (value → set). |
| Status | Not run |

### TC-05-HAZ-9.2 — Out-of-order autosaves preserve the newest content

| Field | Value |
|---|---|
| Description | Overlapping autosaves are routine. If the older response is allowed to win — in the store or in the UI — the newest paragraph the user typed disappears without any error being shown. |
| Preconditions | Document A1 is open in the editor; the two autosave responses can be released in a controlled order. |
| Test data | Content A `<p>Содержимое А</p>` autosaved first; content B `<p>Содержимое Б</p>` autosaved second; release order: B's response, then A's |
| Steps | 1. Autosave content A and hold its response.<br>2. Edit to content B and autosave it.<br>3. Release B's response, then A's.<br>4. `GET /api/v1/documents/{A1}` and inspect the editor. |
| Expected result | The persisted `content` is `<p>Содержимое Б</p>` and the editor shows B; A's late-arriving response neither overwrites the stored content nor the displayed status; B is not lost. |
| Status | Not run |

### TC-05-HAZ-9.3 — Autosave failures are handled per kind

| Field | Value |
|---|---|
| Description | Retrying a transient `500` forever hammers the backend; not retrying at all loses the edit. An expired session is not transient at all — retrying it silently leaves the user typing into a dead editor. |
| Preconditions | Document A1 is open with unsaved edits; the save endpoint can be stubbed per response. |
| Test data | (a) Stub `504`/`500` with `{"error_code": "INTERNAL_ERROR", …}`; backoff schedule and the pinned attempt cap. (b) Stub `401` with `{"error_code": "UNAUTHORIZED", "message": "A valid access token is required."}`. |
| Steps | 1. Let an autosave fire against stub (a); record every retry's timestamp and count them.<br>2. Let an autosave fire against stub (b); observe the UI. |
| Expected result | Step 1: the client retries with increasing backoff intervals and stops at the pinned attempt cap — it does not retry indefinitely and does not give up after the first failure; the edit remains in the editor throughout. Step 2: no blind retry loop; the user is prompted to re-authenticate, and the editor is not left showing a silent failed state or a bare `Сохранено`. |
| Status | Not run |

### TC-05-HAZ-9.4 — Rapid typing coalesces to a bounded save rate

| Field | Value |
|---|---|
| Description | One request per keystroke turns a fast typist into a load test against the save endpoint and guarantees version conflicts against itself. |
| Preconditions | Document A1 is open in the editor; the network panel is recording. |
| Test data | 100 keystrokes typed continuously over 10 s with no pause longer than the 1 s debounce |
| Steps | 1. Type the 100 characters continuously.<br>2. Stop and wait past the debounce.<br>3. Count the `PUT /api/v1/documents/{A1}` requests issued. |
| Expected result | The number of `PUT` requests is bounded and far below 100 — collapsed to a handful by the debounce/coalescing window, with a final save carrying the full 100 characters; no request-per-keystroke pattern. |
| Status | Not run |

### TC-05-HAZ-9.5 — An autosave with an absent or unparseable version fails closed

| Field | Value |
|---|---|
| Description | If a missing or malformed version is treated as "no concurrency check", an autosave becomes an unconditional overwrite of whatever another session just saved. |
| Preconditions | Document A1 exists at `version` `2` with `content` `<p>Первый абзац.</p>`. |
| Test data | Bodies `{"content": "<p>Перезапись</p>"}` (version absent), and the same with `"version": "2"`, `2.5`, `true`, `null` |
| Steps | 1. `PUT /api/v1/documents/{A1}` with each of the five bodies.<br>2. `GET /api/v1/documents/{A1}`. |
| Expected result | Every one answers `422 Unprocessable Entity` with `{"error_code": "INVALID_VERSION", …}` — never `200`; step 2 shows `content` still `<p>Первый абзац.</p>` and `version` still `2`, so no silent overwrite occurred. |
| Status | Not run |

### TC-05-HAZ-9.6 — Server-owned fields on save are ignored (title added)

| Field | Value |
|---|---|
| Description | Adding `title` to the writable set is the moment the save DTO's allowlist is most likely to slip and admit the neighbouring server-owned fields with it. |
| Preconditions | Document A1 exists with `status` `draft`, owned by account A, with a known `created_at`. |
| Test data | Body `{"content": "<p>Абзац</p>", "title": "Новый отчёт", "version": 2, "id": "11111111-1111-4111-8111-111111111111", "status": "completed", "owner_id": "<account B's user id>", "created_at": "2000-01-01T00:00:00Z"}` |
| Steps | 1. `PUT /api/v1/documents/{A1}` with that body.<br>2. `GET /api/v1/documents/{A1}` as account A.<br>3. `GET /api/v1/documents/{A1}` as account B. |
| Expected result | `200 OK`; only `content` and `title` are written (`<p>Абзац</p>` and `Новый отчёт`), with `version` advanced to `3`; `id` is still `3d9b1f42-…`, `status` still `draft`, `created_at` unchanged, and the document still belongs to account A — step 3 answers `404 Not Found`. |
| Status | Not run |

### TC-05-HAZ-9.7 — The title length limit is measured in the pinned unit

| Field | Value |
|---|---|
| Description | Bytes, UTF-16 units and code points give three different answers for the same Cyrillic or emoji title; whichever the boundary uses must be the one pinned, or a legitimate title is refused (or an over-long one admitted). |
| Preconditions | Document A1 is open in the editor. The pinned unit is Unicode code points, NFC-normalized after trimming, cap 200. |
| Test data | (a) 200 Cyrillic characters (400 bytes UTF-8, 200 code points). (b) 200 `🎓` characters (800 bytes, 400 UTF-16 units, 200 code points). (c) 201 Cyrillic characters. (d) A 200-code-point title whose NFD form is 210 code points. |
| Steps | 1. Save each of (a)–(d) as document A1's title.<br>2. `GET /api/v1/documents/{A1}` after each and read the stored `title`. |
| Expected result | (a) and (b) are accepted with `200 OK` and stored in full — the byte and UTF-16 lengths do not cause a rejection; (c) is refused with a `4xx` carrying the `{"error_code", "message"}` shape and nothing is stored; (d) is accepted, since the count is taken on the NFC form; no accepted title is stored truncated. |
| Status | Not run |

## 10. Migration & Dirty State

### TC-05-HAZ-10.1 — A legacy document survives load-edit-save without content loss

| Field | Value |
|---|---|
| Description | The load-edit-save cycle is where an inline-only document meets the block schema. A transform that drops what it cannot represent destroys the user's existing document on their first edit of it. |
| Preconditions | Document A2 exists with the pre-migration inline-only content and has never been opened in the upgraded editor. |
| Test data | Stored content `Первая строка<br>Вторая строка`; the edit appends ` — дополнение` to the second line |
| Steps | 1. Open document A2 in the upgraded editor.<br>2. Append ` — дополнение` to the second line.<br>3. Save and reload the document.<br>4. Compare the reloaded content with the original. |
| Expected result | Both original lines and the line break are still present alongside the appended text — nothing from the pre-migration content is dropped. If the schema upgrade is lossy for any construct, that transform is written down explicitly (e.g. `<br>` becomes a paragraph split) and the reloaded content matches that stated transform exactly, rather than losing text silently. |
| Status | Not run |

### TC-05-HAZ-10.2 — Multibyte content round-trips byte-exact after normalization

| Field | Value |
|---|---|
| Description | A normalization applied on one side of the round-trip and not the other, or a column collation that rewrites the input, shows up as a changed byte sequence for text the user never edited. |
| Preconditions | Document A1 is open in the upgraded editor. |
| Test data | Content `<p>Café é (e + U+0301) 🎓 漢字テスト</p>` — a combining accent, a 4-byte emoji and CJK |
| Steps | 1. Enter that content and save.<br>2. Reload and read the returned `content`.<br>3. NFC-normalize both the source and the returned string and compare them byte for byte. |
| Expected result | The two NFC-normalized strings are byte-identical; no `?`, no `�`, no dropped combining mark, no split surrogate pair, and the CJK characters are unchanged. |
| Status | Not run |

### TC-05-HAZ-10.3 — Leaving with unsaved or failed-autosave edits is guarded

| Field | Value |
|---|---|
| Description | Autosave creates the false confidence that leaving is always safe. The dangerous window is exactly when the last autosave failed or is still in flight — a plain navigation there discards work the user believes is saved. |
| Preconditions | Document A1 is open in the editor in three separate runs: (a) edits typed within the debounce window, not yet autosaved; (b) an autosave that failed with `500`; (c) an autosave in flight when the session expires (`401`). |
| Test data | Typed text `Несохранённый текст`; exits: in-app navigation away, a browser refresh (F5), and a session expiry mid-save |
| Steps | 1. In run (a), navigate away in-app; then repeat with a refresh.<br>2. In run (b), navigate away and refresh.<br>3. In run (c), let the session expire mid-save and observe. |
| Expected result | In every combination the user is either warned before leaving (a beforeunload/route-guard prompt naming unsaved changes) or the draft is restored on return with `Несохранённый текст` intact — never a silent discard and never a clean-looking editor that has lost the text. |
| Status | Not run |

### TC-05-HAZ-10.4 — The title column tolerates rolling deploy

| Field | Value |
|---|---|
| Description | During a rolling deploy, old and new code serve the same rows at once. A non-nullable column, or a migration that is not idempotent, takes the old instances down mid-rollout. |
| Preconditions | The `title` column is added as an additive **nullable** migration; at least one document row predates it and has `title` `NULL`; one pre-migration and one post-migration backend instance both point at the database. |
| Test data | Document A2 id `8c4e0a5d-19f7-4b62-8d31-c07a5e94b6f2` with `title` `NULL`; the Alembic migration applied twice, concurrently from two sessions |
| Steps | 1. `GET /api/v1/documents/{A2}` against the pre-migration instance.<br>2. `GET /api/v1/documents/{A2}` against the post-migration instance.<br>3. Run the migration a second time, and run it from two sessions at once. |
| Expected result | Steps 1 and 2 both answer `200 OK` — the pre-migration instance ignores the unknown column and the post-migration one returns `title` as `null` rather than erroring on the untitled row; step 3 leaves the schema in the same state with no duplicate-column error and no failed migration, whether re-run or applied concurrently. |
| Status | Not run |
