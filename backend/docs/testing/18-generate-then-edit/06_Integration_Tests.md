<!-- COPIED FILE. Source of truth: ProductSpecification/stories/18-generate-then-edit/tests/06_Integration_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Generate → edit — Integration Tests

End-to-end across the generation flow, the conversion, and the editor, using the
deterministic fake generation provider.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.convert@textery.test` / `Qa!Convert2026` |
| Fake provider | the deterministic CI generation provider, returning the fixture named per case |
| Document type / topic | `доклад` / `История Москвы` |
| Flow endpoints | `POST /api/v1/generations` → `GET /api/v1/generations/{id}` → `POST /api/v1/documents/from-generation` → `PUT /api/v1/documents/{id}` |
| Markdown fixture | `## Введение\n\nПервый **абзац**.\n\n- Пункт один\n- Пункт два` |
| Plain-text fixture | `Первый абзац.\n\nВторой абзац.` (no markdown syntax) |
| Empty fixture | `` (empty string) |
| Error body shape | `{"error_code": "<CODE>", "message": "<generic text>"}` |

---

## 1. Generate → Convert → Edit

### TC-18-INT-1.1 — A generated document flows from type selection to a saved edit

| Field | Value |
|---|---|
| Description | Each step passes in isolation and the chain can still break at a seam — a lost generation link, a second document, or an edit that lands on the wrong row. This runs the whole path once, for real. |
| Preconditions | Account A signed in; the fake provider configured with the markdown fixture; account A has no documents. |
| Test data | Type `доклад`, topic `История Москвы`, appended edit `Мой собственный абзац.` |
| Steps | 1. `POST /api/v1/generations` with the type and topic.<br>2. Poll `GET /api/v1/generations/{id}` until `completed`.<br>3. `POST /api/v1/documents/from-generation` with that generation id.<br>4. `PUT /api/v1/documents/{document_id}` appending the edit at `version` `1`.<br>5. `GET /api/v1/documents` and `GET /api/v1/generations/{id}`. |
| Expected result | Step 3 answers `201` with `version` `1` and `generation_id` set; step 4 answers `2xx` with `version` `2`; step 5 lists exactly one document for account A, whose content carries both the generated text and `Мой собственный абзац.`; the generation row is retained unchanged — same status, same content as at step 2. |
| Status | Not run |

---

## 2. Content Conversion Fidelity

### TC-18-INT-2.1 — Markdown output converts to the expected sanitized HTML

| Field | Value |
|---|---|
| Description | The editor stores HTML; if markdown is not converted, the user sees `##` and `**` as literal characters in their document. |
| Preconditions | A generation completed with the markdown fixture, owned by account A; the degrade-path signal is captured. |
| Test data | Markdown fixture above; expected HTML `<h2>Введение</h2><p>Первый <strong>абзац</strong>.</p><ul><li>Пункт один</li><li>Пункт два</li></ul>` |
| Steps | 1. `POST /api/v1/documents/from-generation` for that generation.<br>2. Compare the stored `content` with the expected HTML.<br>3. Read the operational signals emitted during the conversion. |
| Expected result | `201`; the stored content is the expected sanitized HTML — heading, paragraph with `<strong>`, and a two-item `<ul>` in order; no literal `##`, `**` or `-` markers remain in the text; no plain-text degrade signal was emitted on this path. |
| Status | Not run |

### TC-18-INT-2.2 — Plain-text output degrades safely

| Field | Value |
|---|---|
| Description | Production GigaChat output is unverified and may carry no markdown at all; the parser must produce a real document from it rather than one unbroken blob or an error — and operations must be able to see which path ran. |
| Preconditions | A generation completed with the plain-text fixture, owned by account A; the operational signals are captured. |
| Test data | Plain-text fixture `Первый абзац.\n\nВторой абзац.` |
| Steps | 1. `POST /api/v1/documents/from-generation` for that generation.<br>2. Read the stored content.<br>3. Read the operational signals emitted during the conversion and compare with TC-18-INT-2.1's. |
| Expected result | `201` with valid sanitized HTML — two separate paragraphs, not one blob and not an error; a distinguishable degrade signal (metric or log line) is emitted, distinct from the one on the markdown path and absent from that path. |
| Status | Not run |

### TC-18-INT-2.3 — Empty output converts without crashing

| Field | Value |
|---|---|
| Description | An empty model answer is a state the parser must survive; an unguarded index or a null dereference here turns a degenerate case into a `500`. |
| Preconditions | A generation owned by account A whose content is empty. |
| Test data | Empty fixture; the generation's stored `content = ""` |
| Steps | 1. `POST /api/v1/documents/from-generation` for that generation.<br>2. Read the response and the stored row.<br>3. Open the document in the editor. |
| Expected result | The request is answered deterministically — either `201` with a valid document whose content is empty or an empty paragraph, or `409` `{"error_code": "GENERATION_NOT_COMPLETED", …}` refusing an empty generation — never a `500` and never a partially written row; if a document was created, the editor opens it without error. |
| Status | Not run |

---

## 3. Operability

### TC-18-INT-3.1 — A conversion failure after completion is observable

| Field | Value |
|---|---|
| Description | The user pays for a generation that completes and then never becomes a document; without a signal keyed by the generation, operations cannot even find which one failed. |
| Preconditions | Generation G15 completed and owned by account A, with the conversion made to fail; generation G1 completed and converting normally. |
| Test data | Generation G15 id `c7a51e38-9b40-4d26-8f13-06e4b2c9a780`; generation G1 id `4d2a8f16-7c53-4e09-b1a7-58e3c0d9b426` |
| Steps | 1. `POST /api/v1/documents/from-generation` for G15 and capture the server log and metrics.<br>2. `POST /api/v1/documents/from-generation` for G1 and capture the same.<br>3. Search both captures for the generation ids. |
| Expected result | Step 1 emits exactly one error-level record carrying G15's generation id (and the client sees only the generic internal-error body); step 2 emits no error-level record and no such signal for G1; the two are distinguishable by the generation id alone. |
| Status | Not run |
