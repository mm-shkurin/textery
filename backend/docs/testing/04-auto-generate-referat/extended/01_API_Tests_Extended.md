<!-- COPIED FILE. Source of truth: ProductSpecification/stories/04-auto-generate-referat/tests/extended/01_API_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Auto-generate: реферат — API Tests (Extended)

> These are additional edge case tests. Implement after core tests pass.

Endpoint: `POST /api/v1/generations`. Sink: the domain `build_prompt`.
Contract: `ProductSpecification/api-specs/generations_create.yaml`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.referat@textery.test` / `Qa!Referat2026` |
| Access token | `Authorization: Bearer <access token of account A>` |
| Field caps | `topic` ≤ 500 chars (`MAX_TOPIC_LENGTH`), `requirements` ≤ 2000, `extra_wishes` ≤ 2000 |
| Optional-field labels | `Требования к работе` and `Дополнительные пожелания` |
| Реферат structural lines | `Во введении обоснуй актуальность темы и сформулируй цель работы.` / `В основной части раскрой разделы по теме.` / `В заключении сформулируй выводы по проделанной работе.` |
| Ban sentence | `Не включай список литературы и не ссылайся на источники.` |
| Error body shape | `{"error_code": "<CODE>", "message": "<text>"}` |

---

## 1. Prompt Text Handling

### TC-04-API-EXT-1.1 — The template survives storage and transport byte-exact

| Field | Value |
|---|---|
| Description | The template is Cyrillic literal text in source, and the topic is arbitrary user text. Both cross a file encoding, an HTTP body, and a JSON serializer before reaching GigaChat. Mojibake or a `?` substitution would reach the model, not just the log. |
| Preconditions | Account A signed in; the GigaChat stub records the raw request bytes it receives. |
| Test data | `topic = "Цифровизация é (e + U+0301) 🎓 в образовании"`, `document_type="реферат"`, `volume_pages=5` |
| Steps | 1. `POST /api/v1/generations` with that topic.<br>2. Let the worker dispatch it.<br>3. NFC-normalize both the stored topic and the prompt captured at the stub, then compare. |
| Expected result | The NFC-normalized topic in the captured prompt equals the NFC-normalized submitted topic exactly; all three structural lines and the ban sentence are present unchanged; no `?`, no `U+FFFD` replacement character, and no HTML/unicode escape sequence appears anywhere in the captured prompt. |
| Status | Not run |

### TC-04-API-EXT-1.2 — A maximum-length request stays within the prompt bound

| Field | Value |
|---|---|
| Description | The field caps are story 1's; what is new is the fixed template overhead added on top. The bound is the sum, and nothing asserts it unless this does. |
| Preconditions | None — pure domain call, at the maximum accepted input. |
| Test data | `topic` = 500 characters, `requirements` = 2000 characters, `extra_wishes` = 2000 characters (all `я` repeated), `document_type="реферат"`, `volume_pages=10` |
| Steps | 1. Call `build_prompt` with the maximal request.<br>2. Measure `len(prompt)` in characters.<br>3. Compare it with the pinned bound (4500 field characters + the pinned реферат template constant, including labels, fences and the ban sentence). |
| Expected result | The prompt length is ≤ 4500 + the pinned template constant, and the test names that constant as a literal so any change to the template text reddens this case; the prompt is not truncated — all three fields appear in full inside their fences. |
| Status | Not run |

### TC-04-API-EXT-1.3 — An empty optional field does not leave a dangling label in the prompt

| Field | Value |
|---|---|
| Description | Absent-vs-empty: a template that always interpolates both fields emits `Требования к работе: ` with nothing after it, which reads to the model as an instruction with a blank answer. |
| Preconditions | None — pure domain call. |
| Test data | Three requests, `document_type="реферат"`, topic `Влияние цифровизации на образование`: (a) `requirements=None, extra_wishes=None`; (b) `requirements="", extra_wishes=""`; (c) `requirements="   ", extra_wishes="\t"` |
| Steps | 1. Call `build_prompt` for each of the three requests.<br>2. Search each prompt for the two labels.<br>3. Check the structural lines. |
| Expected result | In all three prompts the substrings `Требования к работе` and `Дополнительные пожелания` are absent, and no empty fenced block appears; all three реферат structural lines are present and the ban sentence is the final line. |
| Status | Not run |

---

## 2. Type Boundary

### TC-04-API-EXT-2.1 — A type differing only by case or whitespace is rejected

| Field | Value |
|---|---|
| Description | The domain allowlist matches exactly after NFC normalization — deliberately case-sensitive, since the client picks from an enum rather than typing free text. A tolerant match here would let a client's stray whitespace pick a template by accident. |
| Preconditions | Account A signed in. |
| Test data | `document_type` values `"Реферат"`, `"реферат "`, `" реферат"`, `"РЕФЕРАТ"`; topic `Влияние цифровизации на образование`, `volume_pages=5` |
| Steps | 1. `POST /api/v1/generations` with `document_type="Реферат"` and a fresh `Idempotency-Key`.<br>2. Repeat with `"реферат "`.<br>3. Repeat with `" реферат"`.<br>4. Repeat with `"РЕФЕРАТ"`. |
| Expected result | Each of the four answers `422 Unprocessable Entity` with body `{"error_code": "INVALID_DOCUMENT_TYPE", "message": "document_type must be one of: доклад, эссе, сочинение, реферат"}`; no generation row is created and the provider stub records zero calls. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `byte-exact after normalization` | NFC-normalized comparison at the stub |
| `the documented bound` | Field caps (500 + 2000 + 2000) plus the pinned template constant |
| `rejected as an unsupported document type` | 422 `INVALID_DOCUMENT_TYPE` |
