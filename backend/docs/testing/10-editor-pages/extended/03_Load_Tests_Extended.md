<!-- COPIED FILE. Source of truth: ProductSpecification/stories/10-editor-pages/tests/extended/03_Load_Tests_Extended.md
     Regenerate with `python scripts/sync_test_cases.py` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Editor pages — Load Tests (Extended)

Profile: **Throughput** (`ProductSpecification/ExpectedLoad.md`). These two cases put the
save path under rate alongside the heavier export path, which shares one request-thread
budget with it.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Load accounts | 50 seeded accounts `qa.load001@textery.test` … `qa.load050@textery.test`, password `Qa!Load2026` |
| Document pool | 200 caller-owned documents of ~8 000 characters, 4 pages at the default preset |
| Settings `S1` | A5, landscape, margins 35/15/25/40 mm, 11 pt, line height 1.15, header `Кафедра ИВТ`, footer `Текстери` |
| Target sustained save rate | the project's configured baseline for `PUT /api/v1/documents/{id}` (record it before the run; the runs below use **40 req/s**) |
| Target sustained export rate | **10 req/s** |
| Measurement window | 60 s at rate, after a 30 s ramp |
| Error-rate ceiling | < 1 % of responses outside `{200, 409}` |
| Render-concurrency bound | story 17's configured limit, **4** |
| Conflict band | derived from the writers-per-document count in the scenario setup (2 writers per document → 409s expected on roughly half the contended saves) |

## 1. Save Path Under Rate

### TC-10-LOAD-1.1 — Page-settings saves sustain their rate alongside content autosaves

| Field | Value |
|---|---|
| Description | Conflict responses are an expected outcome under contention, not an error — the ceiling applies to failures other than 409. What must not happen is a save that neither lands nor is refused. |
| Preconditions | Prod-copy up with one backend instance; the 200-document pool seeded; each document has exactly 2 concurrent writers (one issuing content autosaves, one issuing page-settings saves). |
| Test data | 40 save req/s sustained for 60 s after a 30 s ramp; mix 70 % content-only `PUT` (no `page_settings` key) / 30 % `page_settings` `PUT` carrying `S1`; each writer refetches `version` on 409 and retries once |
| Steps | 1. Ramp to 40 save req/s over 30 s against the pool.<br>2. Hold 40 req/s for 60 s, recording every request, its status and its response.<br>3. Compute the achieved rate, the 409 share, and the share of responses that are neither `200` nor `409`.<br>4. For every request that answered `200`, read the document afterwards and confirm its effect is present. |
| Expected result | Achieved rate ≥ 40 req/s across the full window with no 10 s bucket below it; responses outside `{200, 409}` are < 1 %; the 409 share falls inside the band predicted for 2 writers per document; every `200` response's effect is present in the final document state — no accepted save is missing, and no request is left without a response. |
| Status | Not run |

---

## 2. Mixed Workload

### TC-10-LOAD-2.1 — Sustained exports do not starve the interactive save path

| Field | Value |
|---|---|
| Description | Catches the regression where the heavier render path consumes the shared request-thread budget and turns an export queue into an editor that cannot save. |
| Preconditions | Prod-copy up with one backend instance; the pool seeded with settings `S1`; export load is already running at the render-concurrency bound before the save load starts. |
| Test data | Export load 25 req/s (saturating the bound of 4 concurrent renders) for the whole run; save load 40 req/s held for 60 s inside it; save baseline measured in a save-only run beforehand |
| Steps | 1. Measure the save path alone at 40 req/s for 60 s and record the achieved rate.<br>2. Start the export load at 25 req/s and let the in-flight-render gauge reach the bound of 4.<br>3. With that load running, drive 40 save req/s for 60 s.<br>4. Compare the achieved save rate and its non-`{200,409}` share with step 1. |
| Expected result | The save path still achieves ≥ 40 req/s during step 3, with no 10 s bucket below it and no degradation beyond 10 % of the step-1 baseline; save responses outside `{200, 409}` stay < 1 %; no save times out or is rejected because a render worker held its thread. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the configured throughput baseline` | The project's declared sustained-rate baseline from `ExpectedLoad.md` |
| `the render-concurrency bound` | Story 17's concurrent-render limit |
| `the expected band for the contention level` | Derived from the number of writers per document in the scenario setup |
