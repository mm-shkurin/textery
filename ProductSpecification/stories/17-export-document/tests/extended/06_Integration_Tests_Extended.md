> These are additional edge case tests. Implement after core tests pass.

# Export document — Integration Tests (Extended)

End-to-end from a stored document through the real render pipeline.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.export@textery.test` / `Qa!Export2026` |
| Fake provider | the deterministic CI generation provider (markdown output) |
| Export request | `GET /api/v1/documents/{id}/export?format=pdf|docx` with account A's Bearer token |
| PDF signature | first five bytes `%PDF-`, `Content-Type: application/pdf` |
| DOCX signature | first two bytes `PK`, `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document` |

## 1. Generated-Document Export

### TC-17-INT-EXT-1.1 — A generated-then-edited document exports faithfully

| Field | Value |
|---|---|
| Description | The generation path (story 18) produces sanitized HTML through a different writer than the manual editor. Exporting only hand-authored fixtures would miss a renderer that chokes on, or silently drops, generation-shaped markup — and would miss an export that serves the pre-edit content. |
| Preconditions | Account A signed in; the deterministic fake generation provider configured; no document exists yet for this run. |
| Test data | Generation topic `История Москвы`, type `доклад`; provider markdown `## Введение\n\nПервый **абзац**.\n\n- Пункт один\n- Пункт два`; edited content adds `<p>Добавленный абзац 🎓</p>` and sets the title to `Доклад о Москве` |
| Steps | 1. `POST /api/v1/generations` and poll `GET /api/v1/generations/{id}` until it completes.<br>2. `POST /api/v1/documents/from-generation` with the generation id and an `Idempotency-Key`; record the returned `document_id`.<br>3. `PUT /api/v1/documents/{document_id}` appending `<p>Добавленный абзац 🎓</p>` and setting the title to `Доклад о Москве`.<br>4. Export that document as `pdf` and extract its text layer.<br>5. Export the same document as `docx` and read `word/document.xml`. |
| Expected result | Steps 4 and 5 both answer `200 OK` with their format's signature bytes and `Content-Disposition` naming `Доклад о Москве.pdf` / `.docx`; both files contain `Введение`, `Первый абзац.`, `Пункт один`, `Пункт два` and `Добавленный абзац 🎓` — the edited content, not the pre-edit generation output; the heading, bold run and list survive as structure (heading text, a bold run, two list items), and no `?` or `�` appears. |
| Status | Not run |
