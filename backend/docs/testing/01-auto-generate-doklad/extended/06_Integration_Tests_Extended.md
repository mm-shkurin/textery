<!-- COPIED FILE. Source of truth: ProductSpecification/stories/01-auto-generate-doklad/tests/extended/06_Integration_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Auto-generate: доклад — Integration Tests (Extended)

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the owner) | `qa.doklad@textery.test` / `Qa!Doklad2026` |
| Generation G1 | id `3f8a1d02-9c47-4b6e-8e10-5d2c7a91f430`, `topic` `Влияние искусственного интеллекта на образование`, `volume_pages` 5 |
| Stub provider | a stub GigaChat server returning a scripted body and counting calls |
| Attempt budget | `MAX_PROVIDER_ATTEMPTS = 2` |
| Generic failure text | `Не удалось сгенерировать документ. Попробуйте позже.` |

## 1. Partial Provider Responses

### TC-01-INT-1.1 — A provider response that succeeds but returns suspiciously short content is still accepted

| Field | Value |
|---|---|
| Description | A well-formed short answer is a legitimate result. An invented minimum-length rule would reject it, re-spend at the provider, and eventually fail a generation that had already succeeded. |
| Preconditions | Generation G1 is `pending`; the stub provider returns `200` with the short body below. |
| Test data | Stub response `200`, body `Доклад.` (7 characters); a second run with a single-word body `Кратко` |
| Steps | 1. Reset the stub's call counter and run the job for G1 with the 7-character body.<br>2. `GET /api/v1/generations/{G1}` and read `status` and `content`.<br>3. Read the stub's call count.<br>4. Repeat with the single-word body. |
| Expected result | `status` is `"completed"` in both runs; `content` is exactly the short string the stub returned (`Доклад.` / `Кратко`), neither padded nor rejected; the stub is called exactly once per run — no retry is triggered by the length; `error_message` is `null`. |
| Status | Not run |

> `2.1` (retry jitter under concurrent shared outage) was promoted to
> `06_Integration_Tests.md` §8.1 — hazard-catalogue scan (2026-07-06) found it closes a
> named Core Requirement (randomized jitter) and a real thundering-herd risk against a
> paid external API, so it belongs critical-path.
