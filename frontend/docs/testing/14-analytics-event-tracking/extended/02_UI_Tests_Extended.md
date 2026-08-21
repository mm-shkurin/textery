<!-- COPIED FILE. Source of truth: ProductSpecification/stories/14-analytics-event-tracking/tests/extended/02_UI_Tests_Extended.md
     Regenerate with `node scripts/sync-test-cases.mjs` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> These are additional edge case tests. Implement after core tests pass.

# Analytics Event Tracking — UI Tests (Extended)

> **UNBLOCKED 2026-08-19.** Both outcomes are now recorded in `endpoints.md` § "The five
> decisions the test spec was blocked on": an unreadable or over-bound campaign parameter is
> **not frozen and not stored**, and the visitor's journey is untouched.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Visitor identity key | `localStorage["textery.analytics.visitorId"]`, a lower-case v4 UUID |
| Attribution key | `localStorage["textery.analytics.attribution"]` |
| Events endpoint | `POST /api/v1/analytics/events`, stubbed `200 {"status": "recorded"}` unless stated |
| Marketing link A | `<app_url>/?utm_source=vk&utm_campaign=spring2026` |
| Marketing link B | `<app_url>/?utm_source=email&utm_campaign=newsletter_may` |
| User A | `qa.analytics@textery.test` / `Qa!Analytics2026`, holds «Доклад про Пушкина» |
| New registrant | `qa.newvisitor@textery.test` / `Qa!NewVisitor2026` |
| Landing CTA | «Попробовать бесплатно» → `/register` |

---

## 1. Several Tabs at Once

### TC-14-UI-1.1e — Two tabs opening together settle on one visitor identity

| Field | Value |
|---|---|
| Description | Two tabs racing on an empty store can each mint an identity and each win the write; the browser would then be two visitors at once, and every funnel joining on the id would split. |
| Preconditions | `localStorage` empty; both tabs share one browser profile and one origin. Events endpoint stubbed `200` and counting. |
| Test data | Two tabs opening `<app_url>/` within the same 100 ms. |
| Steps | 1. Clear `localStorage`.<br>2. Open `<app_url>/` in two tabs simultaneously (both started before either finishes loading).<br>3. After both are idle, read `localStorage["textery.analytics.visitorId"]`.<br>4. Read the `visitor_id` of both recorded `SITE_VISITED` requests. |
| Expected result | The key holds exactly one well-formed UUID; both recorded site visits carry that same `visitor_id`; two rows are stored (two loads are two visits) under one identity. |
| Status | Not run |

### TC-14-UI-1.2e — A second tab stops using an identity a first tab has erased

| Field | Value |
|---|---|
| Description | The deleted account's identity must not keep being reported from a tab that happened to be open — that is exactly the id the deletion was meant to erase. |
| Preconditions | User A signed in in two open tabs; both hold the same visitor identity; the profile screen open in tab 1. |
| Test data | Deletion flow on `/profile`; identity recorded before deletion. |
| Steps | 1. Sign in as User A in tab 1 and tab 2 and record the shared identity.<br>2. In tab 1, complete the account-deletion flow.<br>3. In tab 2, trigger any tracked action (navigate to the landing page).<br>4. Read the `visitor_id` of the event tab 2 reports, and read the storage key. |
| Expected result | Tab 2 reports under a different, well-formed identity — never the erased one; the storage key holds that new value, not the pre-deletion one; tab 2 shows no error about the deletion. |
| Status | Not run |

### TC-14-UI-1.3e — Two tabs arriving from different campaigns freeze one set

| Field | Value |
|---|---|
| Description | First touch means one set. Two tabs racing must not leave the browser holding a set that is a mix of both links, nor let the second link overwrite the first. |
| Preconditions | `localStorage` empty; both tabs on one browser profile. |
| Test data | Marketing link A and marketing link B, opened within the same 100 ms; new registrant credentials. |
| Steps | 1. Clear `localStorage`.<br>2. Open marketing link A in tab 1 and marketing link B in tab 2 simultaneously.<br>3. Read and parse `localStorage["textery.analytics.attribution"]`.<br>4. From either tab, click «Попробовать бесплатно» and register the new registrant.<br>5. Read the recorded `POST /api/v1/auth/register` body. |
| Expected result | The stored set is exactly one of the two links' sets, complete and unmixed (`utm_source` and `utm_campaign` from the *same* link); the registration body carries that same set; no key from the other link appears anywhere. |
| Status | Not run |

---

## 2. Hostile and Awkward Entry Points

### TC-14-UI-2.1e — Campaign parameters that are not valid text are not frozen

| Field | Value |
|---|---|
| Description | Mojibake frozen as the first touch would occupy the slot permanently, and first touch is never overwritten — so the honest outcome is to freeze nothing and let the next readable link win. |
| Preconditions | `localStorage` empty. Events endpoint stubbed `200`. |
| Test data | `<app_url>/?utm_source=vk&utm_campaign=%E2%E5%F1%ED%E0` — percent-encoded cp1251, which `URLSearchParams` decodes to U+FFFD replacement characters; afterwards marketing link A. |
| Steps | 1. Clear `localStorage` and open the cp1251 link above.<br>2. Read `localStorage["textery.analytics.attribution"]`; read the full page text and the browser console.<br>3. In the same browser, open marketing link A.<br>4. Read and parse the attribution key again. |
| Expected result | After step 2 the key is absent (`null`) — nothing was written, not written-then-emptied — and no value containing `�` is stored anywhere; the page renders and behaves exactly as for a visitor with no parameters, with `SITE_VISITED` still reported and no console error; after step 4 the key holds marketing link A's set, which became the first touch. |
| Status | Not run |

### TC-14-UI-2.2e — Campaign parameters far over the bound do not become a frozen value

| Field | Value |
|---|---|
| Description | A truncated campaign value is a campaign that never existed; and an over-bound value must never turn `POST /auth/register` into a new way for registration to fail. |
| Preconditions | `localStorage` empty; `qa.newvisitor@textery.test` not registered. `POST /api/v1/auth/register` recorded. |
| Test data | `<app_url>/?utm_source=vk&utm_campaign=<400 × "a">` — 400 characters, far over the 200-code-point bound; new registrant credentials. |
| Steps | 1. Clear `localStorage` and open the over-bound link.<br>2. Read `localStorage["textery.analytics.attribution"]`.<br>3. Click «Попробовать бесплатно» and register the new registrant.<br>4. Read the registration response status and body, and the account's stored campaign values.<br>5. Read the full page text at every step. |
| Expected result | Registration succeeds with its normal status — no `400` invented by an analytics attribute; the account's five `utm_*` read as unset (NULL); no truncated 200-character value is stored either in the browser or on the account; nothing about the arrival or the registration is visible to the visitor. |
| Status | Not run |

---

## 3. Recovery Paths

### TC-14-UI-3.1e — Recovering from an editor crash does not re-report the opening

| Field | Value |
|---|---|
| Description | The recovery re-mounts the editor. If the emitter hangs off the mount rather than the opening, one crash silently doubles the story's headline number. |
| Preconditions | User A signed in with «Доклад про Пушкина»; the editor's `ErrorBoundary` reachable via an injected render failure. |
| Test data | Injected editor render failure; the boundary's own recovery action. |
| Steps | 1. Sign in as User A and open «Доклад про Пушкина» from «Мои проекты»; count `EDITOR_OPENED` rows.<br>2. Trigger the injected failure so the editor's `ErrorBoundary` renders.<br>3. Click the boundary's offered recovery action.<br>4. Open the same document again from «Мои проекты».<br>5. Count `EDITOR_OPENED` rows for that document id. |
| Expected result | The stored count equals the number of times the document was *opened* — one after step 1, still one after the recovery in step 3, two after step 4; the recovery itself adds no row. |
| Status | Not run |

### TC-14-UI-3.2e — A reload during a failed send does not duplicate the visit

| Field | Value |
|---|---|
| Description | A failed send must not leave a pending report that a reload re-issues under the same occurrence — nor be counted as a visit that never reached the server. |
| Preconditions | `localStorage` empty. Events endpoint stubbed to fail with a network error on the first load, then answer `200`. |
| Test data | One failing load, then one succeeding load, of `<app_url>/`. |
| Steps | 1. Clear storage and open `<app_url>/` with the endpoint failing; confirm no row was stored.<br>2. Restore the endpoint to `200` and reload the page.<br>3. Read all `SITE_VISITED` rows stored for that `visitor_id` and their `occurrence_key` values.<br>4. Inspect `localStorage` for any queued or pending report. |
| Expected result | Exactly one row is stored — the successful load's; no occurrence key appears twice; storage holds nothing awaiting a later attempt, so the failed send was dropped rather than replayed. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `at the same moment` | Two client contexts over one shared storage, both starting empty |
| `no longer reports under the erased identity` | `storage`-event adoption in the second context |
| `a legacy character set` | Percent-encoded cp1251 in the query string, which `URLSearchParams` decodes to U+FFFD |
| `the browser holds no campaign parameters` | The frozen-UTM storage key is absent — nothing written, not written-then-emptied |
| `behaves as it does for a visitor arriving with no parameters` | Asserted against that load: same rendered page, no banner, no console error, `SITE_VISITED` still reported |
| `recovers through the offered action` | The editor's own `ErrorBoundary` recovery target |
| `far longer than the bound` | Over the 200-code-point cap `endpoints.md` sets for each `utm_*` |
