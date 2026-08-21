<!-- COPIED FILE. Source of truth: ProductSpecification/stories/04-auto-generate-referat/tests/06_Integration_Tests.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

# Auto-generate: реферат — Integration Tests

> **Implementation Order**: 1.x proves the prompt reaches GigaChat intact; 2.x proves the
> hand-off did not disturb the failure handling story 1 built.

Boundary under test: `GenerateDocument` (usecase) ↔ `GigaChatProvider` (adapter) ↔ the
GigaChat stub standing in for `POST /api/v1/chat/completions`. Never the live API.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.referat@textery.test` / `Qa!Referat2026` |
| Generation R1 | id `3d7a41f6-8c02-4e19-b5aa-71f0c2d94e83`, `document_type=реферат`, topic `Влияние цифровизации на образование`, `volume_pages=5` |
| Реферат structural lines | `Во введении обоснуй актуальность темы и сформулируй цель работы.` / `В основной части раскрой разделы по теме.` / `В заключении сформулируй выводы по проделанной работе.` |
| Ban sentence | `Не включай список литературы и не ссылайся на источники.` |
| Retry budget | `MAX_PROVIDER_ATTEMPTS = 2`; backoff `1.0 s` base, doubling, plus up to `0.5 s` jitter (sleep injected in tests) |
| Read timeout | `GIGACHAT_READ_TIMEOUT_SECONDS = 180.0` (`gigachat_defaults.toml`) |
| Terminal failure state | `status: "failed"`, `error_message: "Не удалось сгенерировать документ. Попробуйте позже."` |
| Client read | `GET /api/v1/generations/{generation_id}` |

---

## 1. Provider Success Path

### TC-04-INT-1.1 — The реферат prompt reaches the provider

| Field | Value |
|---|---|
| Description | The domain template is worthless if the adapter drops, rewrites or truncates it in transit. This is the only case that reads the bytes on the wire. |
| Preconditions | Account A signed in; the GigaChat stub records every request body it receives; generation R1 created and `pending`. |
| Test data | Generation R1; the three structural lines and the topic string above |
| Steps | 1. Let the worker dispatch generation R1.<br>2. Read the recorded request body at the stub and extract the message content sent as the prompt. |
| Expected result | The stub received exactly one completion request; its prompt contains all three реферат structural lines verbatim, the ban sentence, and the topic `Влияние цифровизации на образование` inside its data fence. |
| Status | Not run |

### TC-04-INT-1.2 — The provider's document becomes the generation's content

| Field | Value |
|---|---|
| Description | Closes the loop: what the model returned is what the user reads, and the type recorded on the row is the type asked for. |
| Preconditions | Account A signed in; the stub returns the completion body below; generation R1 created. |
| Test data | Stub completion content `Реферат о цифровизации образования.` |
| Steps | 1. Let the worker dispatch generation R1 to completion.<br>2. `GET /api/v1/generations/3d7a41f6-8c02-4e19-b5aa-71f0c2d94e83` with account A's token. |
| Expected result | `200 OK`; `status: "completed"`; `content: "Реферат о цифровизации образования."` character for character; `document_type: "реферат"`; `error_message: null`. |
| Status | Not run |

---

## 2. Provider Failure Modes

### TC-04-INT-2.1 — A provider error still ends the generation as failed

| Field | Value |
|---|---|
| Description | The refactor edits the one method the retry logic wraps. A behaviour change hidden inside a "mechanical" move would surface as a row stuck in `in_progress`, not as a prompt bug. |
| Preconditions | Account A signed in; the stub answers `500 Internal Server Error` to every completion request; the injected sleep records its calls instead of waiting. |
| Test data | Generation R1; `MAX_PROVIDER_ATTEMPTS = 2` |
| Steps | 1. Let the worker dispatch generation R1.<br>2. Count the completion requests recorded at the stub.<br>3. `GET /api/v1/generations/{R1}`. |
| Expected result | The stub recorded exactly 2 completion requests with one backoff sleep between them; the `GET` answers `200 OK` with `status: "failed"` and `error_message: "Не удалось сгенерировать документ. Попробуйте позже."` — never left at `pending` or `in_progress`. |
| Status | Not run |

### TC-04-INT-2.2 — A provider timeout still ends the generation as failed

| Field | Value |
|---|---|
| Description | A timeout raised as `httpx.ReadTimeout` rather than the adapter's own error type is exactly the kind of escape that strands a row; and an aborted call left running keeps a connection out of the pool. |
| Preconditions | Account A signed in; the stub accepts the connection and never sends a response body; the read timeout is lowered for the test (e.g. `GIGACHAT_READ_TIMEOUT_SECONDS=1.0`). |
| Test data | Generation R1; read timeout `1.0 s` in-test (`180.0 s` in production) |
| Steps | 1. Let the worker dispatch generation R1.<br>2. Wait past the attempt budget.<br>3. `GET /api/v1/generations/{R1}`.<br>4. Inspect the HTTP client's open connections/tasks. |
| Expected result | `status: "failed"` with the generic `error_message`; each attempt aborted at ~1 s rather than hanging; no in-flight request or task remains after the worker returns, and the connection is released back to the pool. |
| Status | Not run |

### TC-04-INT-2.3 — A malformed provider body still ends the generation as failed

| Field | Value |
|---|---|
| Description | A `200` carrying a body the client cannot parse is the failure most likely to be swallowed into an empty-but-completed document. |
| Preconditions | Account A signed in; the stub answers `200 OK` with body `{"unexpected":"shape"}` (no `choices` array). |
| Test data | Generation R1; malformed body `{"unexpected":"shape"}` |
| Steps | 1. Let the worker dispatch generation R1.<br>2. `GET /api/v1/generations/{R1}`.<br>3. Read the captured server log records at ERROR level. |
| Expected result | `status: "failed"` with the generic `error_message` and `content: null` — never `completed` with empty content; exactly one ERROR record names generation R1's id and identifies the malformed-response category, distinguishably from the error-status and timeout categories, while the client still sees only a bare `failed`. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the provider stub` | GigaChat stub server — never the live API |
| `a реферат generation is dispatched` | Worker processes a `Generation` with `document_type="реферат"` |
| `the реферат structural instructions` | введение / разделы / заключение directives plus the bibliography ban |
| `the retry budget` | Bounded retries with jittered backoff, per story 1 |
| `the failure category` | Server-side distinguishable category (timeout / malformed / error status), client still sees a bare `failed` |
