> These are additional edge case tests. Implement after core tests pass.

# Generate → edit — Integration Tests (Extended)

End-to-end across the generation flow, the conversion, and the editor, using the
deterministic fake generation provider.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.convert@textery.test` / `Qa!Convert2026` |
| Fake provider | the deterministic CI generation provider, returning the fixture named per case |
| Document type / topic | `доклад` / `История Москвы` |
| Flow endpoints | `POST /api/v1/generations` → `GET /api/v1/generations/{id}` → `POST /api/v1/documents/from-generation` → `PUT /api/v1/documents/{id}` |
| Editor surface | `[data-testid="manual-editor"]`, body `[data-testid="doc-body"]` |
| History | `[data-testid="history-page"]`, rows `[data-testid="history-document-row"]` |
| Error body shape | flat `{"error_code": "<CODE>", "message": "<generic text>"}` |

## 1. Conversion Fidelity Variants

### TC-18-INT-EXT-1.1 — Mixed markdown and multibyte content converts faithfully

| Field | Value |
|---|---|
| Description | Markdown rendering and sanitization each re-encode the text. A pass that is byte-oriented, or a sanitizer that strips what it cannot decode, produces mojibake or drops structure — and both failures survive into the stored document forever. |
| Preconditions | Account A signed in; the fake provider configured to return the mixed fixture below; no document linked to this generation yet. |
| Test data | Provider markdown `## Введение 🎓\n\nПервый **абзац** с *акцентом* и é (e + U+0301).\n\n- Пункт один\n- Пункт два\n\n> Цитата «ёлки»`; `Idempotency-Key: 7d0a4e63-1c85-4b29-9f34-6a2e0c8b5713` |
| Steps | 1. `POST /api/v1/generations` for type `доклад`, topic `История Москвы`; poll `GET /api/v1/generations/{id}` until completed.<br>2. `POST /api/v1/documents/from-generation` with the generation id and the key above.<br>3. `GET /api/v1/documents/{document_id}` and read the sanitized `content`. |
| Expected result | Step 2 answers `201 Created`; the `content` in step 3 carries the structure as HTML — an `<h2>` (or `<h1>`) holding `Введение 🎓`, a `<strong>абзац</strong>`, an `<em>акцентом</em>`, a `<ul>` with exactly two `<li>` (`Пункт один`, `Пункт два`) and a `<blockquote>` with `Цитата «ёлки»` — and no literal `##`, `**` or `- ` markdown syntax remains; every multibyte character (`Введение`, the graduation-cap emoji, `é`, `«»`, `ё`) is present exactly as generated, with no `?` and no `�`. |
| Status | Not run |

## 2. Idempotent End-to-End

### TC-18-INT-EXT-2.1 — A double auto-transition yields one document end to end

| Field | Value |
|---|---|
| Description | The auto-transition fires from the client on generation completion, so a double-resolved poll or a fast double render fires it twice. Without end-to-end idempotency the user gets two documents in history for one generation — the failure the idempotency key exists to prevent, verified through the whole real flow rather than at the endpoint alone. |
| Preconditions | Account A signed in with an empty history; the deterministic fake provider configured; the client fires the conversion twice with the **same** `Idempotency-Key`, both requests in flight concurrently. |
| Test data | Provider markdown `## Введение\n\nПервый абзац.`; `Idempotency-Key: e5b28c71-3f04-4a96-b8d2-19c7a03e6d84` sent on both calls; concurrency 2 |
| Steps | 1. Start the generation and let it complete.<br>2. Fire `POST /api/v1/documents/from-generation` twice concurrently with the same generation id and the same key.<br>3. Record both responses' status and `document_id`.<br>4. Open `[data-testid="history-page"]` and count `[data-testid="history-document-row"]`.<br>5. Open the document and read `[data-testid="doc-body"]`. |
| Expected result | Step 3 shows both calls returning the **same** `document_id` — one `201 Created` and one `200 OK` replay of the stored response (never two distinct ids, never a `409` left unhandled); step 4 shows exactly one `[data-testid="history-document-row"]`; step 5 opens the editor showing `Введение` and `Первый абзац.`. |
| Status | Not run |
