> **Implementation Order**: sequential TDD — mint and reuse the visitor identity → freeze
> attribution → emit from the three browser surfaces → degrade without showing it → clean up
> after account deletion.

# Analytics Event Tracking — UI Tests

**This story renders nothing.** There is no screen, no button and no message to assert on, so
these cases assert what the browser *does*: which identity it carries, what it froze, what it
sent, and — as much as anything here — what it never shows the user. Every «Expected result»
below therefore names both halves: the observable data, and the absence of any visitor-facing
change.

> **Navigation is by clicking, never by typing a URL** (`.claude/guidelines/frontend-rules.md`).
> Where a case needs a marketing link, that is the initial page load, which is the one
> navigation a visitor really performs from outside.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Visitor identity key | `localStorage["textery.analytics.visitorId"]`, a lower-case v4 UUID |
| Attribution key | `localStorage["textery.analytics.attribution"]`, JSON of the frozen `utm_*` set |
| Theme key | `localStorage["textery.theme"]` |
| Events endpoint | `POST /api/v1/analytics/events` |
| Event body | `{"event_name": …, "visitor_id": …, "occurrence_key": …, "degraded": …, "payload": {}}` |
| Event names | `SITE_VISITED`, `REGISTRATION_STARTED`, `EDITOR_OPENED` |
| Marketing link | `<app_url>/?utm_source=vk&utm_medium=cpc&utm_campaign=spring2026&utm_content=banner_a&utm_term=диплом` |
| Second marketing link | `<app_url>/?utm_source=email&utm_campaign=newsletter_may` |
| User A | `qa.analytics@textery.test` / `Qa!Analytics2026`, holds one document «Доклад про Пушкина» |
| New registrant | `qa.newvisitor@textery.test` / `Qa!NewVisitor2026` |
| Landing CTA | «Попробовать бесплатно» → `/register` |
| Sign-in link | «Войти» → `/login` |
| Events stub | Stubbed per case; `200 {"status": "recorded"}` unless the case says otherwise |

---

## 1. Visitor Identity

### TC-14-UI-1.1 — A first-ever visitor is given an identity before anything is reported

| Field | Value |
|---|---|
| Description | The identity is the join key for every later event; minted after the first send, the site visit is orphaned and the funnel starts at step two. |
| Preconditions | `localStorage` and `sessionStorage` empty — no visitor identity, no session. Events endpoint stubbed `200`. |
| Test data | Landing page `<app_url>/`; key `textery.analytics.visitorId`. |
| Steps | 1. Clear `localStorage` and `sessionStorage`.<br>2. Open `<app_url>/` and wait for the landing page to finish loading.<br>3. Read `localStorage["textery.analytics.visitorId"]`.<br>4. Read the body of the recorded `POST /api/v1/analytics/events`. |
| Expected result | The stored value matches `^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`; exactly one request was recorded; its `event_name` is `SITE_VISITED` and its `visitor_id` equals the stored value character for character; its `degraded` is `false`. |
| Status | Not run |

### TC-14-UI-1.2 — A returning visitor keeps the identity it already had

| Field | Value |
|---|---|
| Description | A returning browser must be the same visitor, or every multi-day funnel reads as a stream of one-visit strangers. |
| Preconditions | `localStorage["textery.analytics.visitorId"]` pre-set to `11111111-2222-4333-8444-555555555555`. Events endpoint stubbed `200`. |
| Test data | The pre-set UUID above. |
| Steps | 1. Set the key to `11111111-2222-4333-8444-555555555555`.<br>2. Open `<app_url>/` and wait for it to finish loading.<br>3. Read the key again.<br>4. Read the recorded event body. |
| Expected result | The stored value is still exactly `11111111-2222-4333-8444-555555555555`; the recorded `SITE_VISITED` carries that same `visitor_id`; no second value was written under any analytics key. |
| Status | Not run |

### TC-14-UI-1.3 — A stored identity that is not well-formed is replaced, not reused

| Field | Value |
|---|---|
| Description | The server column is a native `uuid`. A value it cannot parse is an event refused on every send, forever, for that browser — a silent permanent outage of one visitor's analytics. |
| Preconditions | `localStorage["textery.analytics.visitorId"]` pre-set to `not-a-uuid`. Events endpoint stubbed `200`. |
| Test data | Stored value `not-a-uuid`. |
| Steps | 1. Set the key to `not-a-uuid`.<br>2. Open `<app_url>/` and wait for it to finish loading.<br>3. Read the key.<br>4. Read the recorded event body and the response status. |
| Expected result | The stored value is no longer `not-a-uuid` and matches the v4 UUID pattern; the recorded `SITE_VISITED` carries the new value; the stub answered `200`; nothing on the page mentions a replaced identity. |
| Status | Not run |

### TC-14-UI-1.4 — Signing in does not change the visitor identity

| Field | Value |
|---|---|
| Description | The identity spans the anonymous and the signed-in halves of the funnel; minting a new one at sign-in cuts every conversion measurement exactly where it matters. |
| Preconditions | Clean `localStorage`; User A registered and holding «Доклад про Пушкина». Events endpoint stubbed `200`. |
| Test data | User A credentials; document title «Доклад про Пушкина». |
| Steps | 1. Clear storage and open `<app_url>/`.<br>2. Record `visitor_id` from the `SITE_VISITED` request.<br>3. Click «Войти» and sign in as User A.<br>4. Open «Мои проекты» and click the card «Доклад про Пушкина».<br>5. Read the body and headers of the `EDITOR_OPENED` request. |
| Expected result | `EDITOR_OPENED` carries the same `visitor_id` recorded in step 2 and an `Authorization: Bearer …` header; `localStorage["textery.analytics.visitorId"]` is unchanged from step 2. |
| Status | Not run |

---

## 2. First-Touch Attribution

> **The freeze is best-effort and silent.** Nothing in this section may block, delay or show
> anything to the visitor: campaign parameters that cannot be read or cannot be stored are
> simply not frozen, the page behaves exactly as it does for a visitor arriving with no
> parameters, and a later readable link can still become the first touch. Those two cases are
> owned by `extended/02_UI_Tests_Extended.md` §2 and by the Governing Decision in
> `14_AnalyticsEventTracking.md`.

### TC-14-UI-2.1 — The first visit carrying campaign parameters freezes them

| Field | Value |
|---|---|
| Description | The freeze is what makes attribution survive to a registration that happens days later, from an address that no longer carries the link. |
| Preconditions | `localStorage` empty. Events endpoint stubbed `200`. |
| Test data | `<app_url>/?utm_source=vk&utm_medium=cpc&utm_campaign=spring2026&utm_content=banner_a&utm_term=диплом`. |
| Steps | 1. Clear `localStorage`.<br>2. Open the marketing link above.<br>3. Read `localStorage["textery.analytics.attribution"]` and parse it as JSON. |
| Expected result | The parsed object equals `{"utm_source":"vk","utm_medium":"cpc","utm_campaign":"spring2026","utm_content":"banner_a","utm_term":"диплом"}` — five keys, no extras; the landing page renders exactly as it does without parameters. |
| Status | Not run |

### TC-14-UI-2.2 — A later visit from a different campaign does not overwrite the first

| Field | Value |
|---|---|
| Description | FIRST touch, not last: last-touch credits a newsletter for an audience a paid ad bought, the most expensive number in a CAC report to get wrong. |
| Preconditions | `localStorage["textery.analytics.attribution"]` already holds the five-key set of TC-14-UI-2.1. |
| Test data | `<app_url>/?utm_source=email&utm_campaign=newsletter_may`. |
| Steps | 1. Arrive from the first marketing link and confirm the frozen set.<br>2. Open the second marketing link in the same browser.<br>3. Read and parse the attribution key. |
| Expected result | The parsed object still equals the five-key set from step 1 — `utm_source` is `vk`, not `email`; `newsletter_may` appears under no key. |
| Status | Not run |

### TC-14-UI-2.3 — A visit with no campaign parameters leaves the browser open to a later first touch

| Field | Value |
|---|---|
| Description | Writing an empty set on a direct visit would permanently block attribution for every marketing link that follows — the common case for anyone who bookmarks the landing page. |
| Preconditions | `localStorage` empty. |
| Test data | Plain `<app_url>/`, then the marketing link of TC-14-UI-2.1. |
| Steps | 1. Clear `localStorage` and open `<app_url>/` with no parameters.<br>2. Read `localStorage["textery.analytics.attribution"]`.<br>3. In the same browser, open the marketing link.<br>4. Read and parse the key again. |
| Expected result | After step 2 the key is absent (`null`), not `"{}"`; after step 4 it parses to the full five-key set from the link. |
| Status | Not run |

### TC-14-UI-2.4 — Registration carries the frozen set, not the current address

| Field | Value |
|---|---|
| Description | By the time the form is submitted the address has long lost the campaign parameters; reading them from the current URL would attribute every registration to «direct». |
| Preconditions | `localStorage` empty; `qa.newvisitor@textery.test` not registered. `POST /api/v1/auth/register` recorded. |
| Test data | Marketing link of TC-14-UI-2.1; `qa.newvisitor@textery.test` / `Qa!NewVisitor2026`. |
| Steps | 1. Clear storage and open the marketing link.<br>2. Click «Попробовать бесплатно» to reach `/register` and confirm the address carries no `utm_`.<br>3. Fill the form with the new registrant's email and password and submit.<br>4. Read the body of the recorded `POST /api/v1/auth/register`. |
| Expected result | The registration body carries `utm_source=vk`, `utm_medium=cpc`, `utm_campaign=spring2026`, `utm_content=banner_a`, `utm_term=диплом`; registration succeeds with the same status and the same redirect it has with no campaign parameters at all. |
| Status | Not run |

### TC-14-UI-2.5 — Multibyte campaign parameters survive the freeze unchanged

| Field | Value |
|---|---|
| Description | The client half of the round trip — percent-decode, serialize into storage, read back, put in the request body — crosses three encode/decode boundaries and had no fixture with any character content specified. |
| Preconditions | `localStorage` empty; the registrant of TC-14-UI-2.4 not registered. |
| Test data | `<app_url>/?utm_source=vk&utm_campaign=%D0%B2%D0%B5%D1%81%D0%BD%D0%B0%F0%9F%8E%93` — decoded `весна🎓`. |
| Steps | 1. Clear storage and open the link above.<br>2. Read and parse `localStorage["textery.analytics.attribution"]`.<br>3. Click through to `/register` and submit the new registrant's credentials.<br>4. Read `utm_campaign` in the recorded registration body. |
| Expected result | Both the stored value and the value in the registration body are exactly `весна🎓` after NFC — not `%D0%B2…`, not `весна?`, not a value split across a lone surrogate. |
| Status | Not run |

---

## 3. What the Browser Reports

### TC-14-UI-3.1 — One page load reports exactly one site visit

| Field | Value |
|---|---|
| Description | The whole occurrence-key design rests on «one event per page load»; a second `SITE_VISITED` inflates the denominator of every conversion rate in the product. |
| Preconditions | `localStorage` empty; events endpoint stubbed `200` and counting requests. Build served with `<StrictMode>` active, as `main.tsx` mounts it. |
| Test data | Landing page `<app_url>/`. |
| Steps | 1. Clear storage and reset the request counter.<br>2. Open `<app_url>/` and wait until the page is idle (no pending requests for 2 s).<br>3. Count the recorded requests whose `event_name` is `SITE_VISITED` and read their `occurrence_key` values. |
| Expected result | Exactly one `SITE_VISITED` row is stored server-side; if two requests were issued under `<StrictMode>`, both carry the *same* `occurrence_key` so the server collapses them; no `REGISTRATION_STARTED` or `EDITOR_OPENED` was sent. |
| Status | Not run |

### TC-14-UI-3.2 — Reaching the registration screen reports it once per arrival

| Field | Value |
|---|---|
| Description | Reported on arrival, not on submit: the interesting number is how many people who saw the form finished it, which is unanswerable if the event fires only when they do. |
| Preconditions | `localStorage` empty; events endpoint stubbed `200` and counting. |
| Test data | CTA «Попробовать бесплатно»; sign-in link «Войти»; registration link on `/login`. |
| Steps | 1. Clear storage and open `<app_url>/`.<br>2. Click «Попробовать бесплатно» and wait for `/register`.<br>3. Count `REGISTRATION_STARTED` requests.<br>4. Click «Войти» to reach `/login`, then click the link back to registration.<br>5. Count `REGISTRATION_STARTED` rows again. |
| Expected result | After step 3 exactly one `REGISTRATION_STARTED` is recorded; after step 5 exactly two are recorded — one per arrival at the screen, and no extra row for the visit to `/login`. |
| Status | Not run |

### TC-14-UI-3.3 — Opening a document in the editor reports it once

| Field | Value |
|---|---|
| Description | Keyed on the document, so the funnel can tell «opened three documents» from «opened one and re-rendered three times». |
| Preconditions | User A signed in on «Мои проекты», holding «Доклад про Пушкина»; events endpoint stubbed `200` and counting. |
| Test data | Document «Доклад про Пушкина» and its id. |
| Steps | 1. Sign in as User A and open «Мои проекты».<br>2. Click the card «Доклад про Пушкина» once and wait for the editor to render.<br>3. Count `EDITOR_OPENED` rows and read the `payload` of each. |
| Expected result | Exactly one `EDITOR_OPENED` row for that document id; the editor renders normally; no `SITE_VISITED` is emitted by the in-app navigation. |
| Status | Not run |

### TC-14-UI-3.4 — Opening a document twice in one gesture reports one opening

| Field | Value |
|---|---|
| Description | Every other duplicate-suppression case here is mount-driven. Two rapid activations are two distinct open-intents, and if each mints its own occurrence key the server-side collapse has nothing to collapse. |
| Preconditions | As TC-14-UI-3.3. The card's rendered props recorded before the story, for comparison. |
| Test data | Two clicks on the same card with no wait between them (< 100 ms apart). |
| Steps | 1. Open «Мои проекты» as User A.<br>2. Click «Доклад про Пушкина» twice in rapid succession without waiting for the first to open.<br>3. Count `EDITOR_OPENED` rows for that document id.<br>4. Read the card control's rendered attributes. |
| Expected result | Exactly one `EDITOR_OPENED` row is recorded for that document; the control carries no `disabled` and no `aria-busy` that it did not carry before this story — the dedupe lives in how the occurrence is derived, not in new UI state. |
| Status | Not run |

### TC-14-UI-3.5 — Moving within the site reports no further site visit

| Field | Value |
|---|---|
| Description | If the emitter hangs off a route effect rather than the app mount, a back navigation re-mounts it with a *fresh* key, the collapse never fires, and every funnel's denominator inflates silently. |
| Preconditions | `localStorage` empty; events endpoint stubbed `200` and counting. |
| Test data | CTA «Попробовать бесплатно»; the browser's own back control (history navigation, not an in-app link). |
| Steps | 1. Clear storage and open `<app_url>/`.<br>2. Click «Попробовать бесплатно» to reach `/register`.<br>3. Press the browser's back control to return to the landing page.<br>4. Count all `SITE_VISITED` rows recorded since step 1. |
| Expected result | Exactly one `SITE_VISITED` row in total; the landing page renders normally after the back navigation. |
| Status | Not run |

### TC-14-UI-3.6 — Two reports on the wire together keep their dispatch order

| Field | Value |
|---|---|
| Description | The order key is assigned on **arrival**, so arrival order is the wrong order when the second send wins the race — a funnel that reads backwards. |
| Preconditions | `localStorage` empty. Events endpoint stubbed to hold the first request for 3000 ms and answer the second immediately. |
| Test data | `SITE_VISITED` delayed 3000 ms; `REGISTRATION_STARTED` answered at once. |
| Steps | 1. Clear storage and open `<app_url>/` against the stub above.<br>2. While the first report is still in flight, click «Попробовать бесплатно».<br>3. Wait until both requests have answered.<br>4. Read the two stored rows for that `visitor_id` in stored order. |
| Expected result | Both events are stored for that visitor; read in order, `SITE_VISITED` comes before `REGISTRATION_STARTED` despite answering later — the order is carried by the client's dispatch, not by arrival. |
| Status | Not run |

---

## 4. Degrading Without Showing It

### TC-14-UI-4.1 — A browser that cannot store still reports, and says so in the data

| Field | Value |
|---|---|
| Description | Private-mode Safari throws on `setItem`. Reporting nothing loses the visitor; reporting without saying so makes every degraded load look like a fresh person with no way to tell. |
| Preconditions | `localStorage.setItem` stubbed to throw `QuotaExceededError` on every call; events endpoint stubbed `200`. |
| Test data | The throwing storage stub; landing page `<app_url>/`. |
| Steps | 1. Install the throwing `setItem` stub before the app loads.<br>2. Open `<app_url>/`.<br>3. Read the recorded event body.<br>4. Read the full page text and screenshot the landing page. |
| Expected result | One `SITE_VISITED` is recorded, carrying a well-formed `visitor_id` and `degraded: true`; the landing page is byte-identical in rendered text to a normal load — no banner, no error, no spinner, nothing in the console the visitor would see. |
| Status | Not run |

### TC-14-UI-4.2 — Two loads from a browser that cannot store are two different visitors

| Field | Value |
|---|---|
| Description | Analytics that cannot tell «two loads from one blocked browser» from «two people» is analytics that lies; the honest answer is two visitors, marked degraded. |
| Preconditions | As TC-14-UI-4.1, storage throwing on write. |
| Test data | Two consecutive loads of `<app_url>/`. |
| Steps | 1. With the throwing stub installed, open `<app_url>/` and record `visitor_id`.<br>2. Reload the page.<br>3. Record `visitor_id` from the second `SITE_VISITED`. |
| Expected result | The two identities differ; both are well-formed UUIDs; both events carry `degraded: true`; within a single load the identity does not change between events. |
| Status | Not run |

### TC-14-UI-4.3 — An unreachable analytics endpoint is invisible to the visitor

| Field | Value |
|---|---|
| Description | Analytics is the least important thing the page does; it may never cost the visitor a screen, a message or a keystroke. |
| Preconditions | `POST /api/v1/analytics/events` stubbed to fail with a network error on every call. `qa.newvisitor@textery.test` not registered. |
| Test data | Network-error stub; new registrant credentials; document «Доклад про Пушкина» after signing in as User A. |
| Steps | 1. Open `<app_url>/` against the failing stub.<br>2. Register the new registrant through the form.<br>3. Sign out, sign in as User A.<br>4. Open «Доклад про Пушкина» from «Мои проекты».<br>5. After each of steps 1–4 read the full page text and screenshot. |
| Expected result | Every screen behaves exactly as it does with a healthy analytics endpoint — same content, same timing to interactive; no error text, no banner, no spinner appears at any point; registration, sign-in and the editor all succeed. |
| Status | Not run |

### TC-14-UI-4.4 — A visitor who leaves immediately is still counted

| Field | Value |
|---|---|
| Description | A normal request in an unloading document is cancelled by the browser; without the beacon/keepalive path every bounce disappears, which is precisely the population a landing page is measured on. |
| Preconditions | `localStorage` empty; events endpoint recording requests server-side (not only in-page). |
| Test data | Landing page `<app_url>/`, closed immediately after load. |
| Steps | 1. Clear storage and open `<app_url>/`.<br>2. As soon as the page has loaded, close the tab (trigger unload).<br>3. Read the events recorded server-side for that `visitor_id`. |
| Expected result | The `SITE_VISITED` row is present server-side; the request was issued with `keepalive` so the unload did not cancel it. |
| Status | Not run |

### TC-14-UI-4.5 — An analytics endpoint that never answers blocks nothing

| Field | Value |
|---|---|
| Description | A hang holds one of the browser's few per-host connections, starving the product's own calls, and a naive await turns it into a delayed route transition. `4.3` stubs only the fast failures. |
| Preconditions | Events endpoint stubbed to accept requests and never answer them. User A registered with «Доклад про Пушкина». |
| Test data | Hanging stub; the landing → registration → editor path; a baseline timing recorded against a healthy stub. |
| Steps | 1. Open `<app_url>/` against the hanging stub and time to interactive.<br>2. Click «Попробовать бесплатно» and time the transition.<br>3. Sign in as User A, open «Доклад про Пушкина», and time the editor render.<br>4. Watch the network panel: confirm the product's own requests (`/auth/*`, `/projects`, `/documents/*`) complete while the analytics calls are still open.<br>5. Confirm the later report is still issued while the first hangs. |
| Expected result | Every screen renders and accepts input within the healthy-stub baseline (no added delay attributable to analytics); no spinner, banner or error appears at any point; the product's own requests complete normally; the second report is issued even though the first has never answered. |
| Status | Not run |

### TC-14-UI-4.6 — Every refusal from the analytics endpoint is inert in the browser

| Field | Value |
|---|---|
| Description | The concrete incident: a token expires mid-editing, the analytics call returns `401`, and — if the emitter shares the product's HTTP client — an invisible telemetry call signs the user out of the editor and discards their unsaved content. |
| Preconditions | User A signed in, in the editor on «Доклад про Пушкина», with unsaved typed changes present. Events endpoint stubbed to answer `401`, then `429`, then `400`. |
| Test data | Typed text «черновик, не сохранён»; refusal sequence `401` → `429` → `400`. |
| Steps | 1. Sign in as User A and open «Доклад про Пушкина».<br>2. Type «черновик, не сохранён» and do not save.<br>3. Trigger a report under each refusal in turn (`401`, `429`, `400`).<br>4. After each, read the URL, the session keys, the editor content and the full page text.<br>5. Count the requests issued per report. |
| Expected result | After every refusal the visitor is still signed in (`textery.auth.accessToken` still present), still on the editor URL, and the typed text is still in the document; no error, banner or spinner appears; exactly one request was issued per report — no retry, and no token refresh was triggered by the `401`. |
| Status | Not run |

### TC-14-UI-4.7 — Each send-failure family is counted, and a success is not

| Field | Value |
|---|---|
| Description | Two requirements in one case because they fail together: without the attempt-count half a recovering backend meets every visitor's backlog at once; without the drop-signal half a broken ingest route looks byte-identical to a quiet day. The repo already ships a four-attempt retry policy for autosave — the precedent an implementer will copy. |
| Preconditions | Failure tally reset before each run. Events endpoint stubbed in turn: hang past the client's deadline, `500`, network error, then `200`. |
| Test data | Tally readable as `{ok, refused, unreachable}`; one landing load per failure mode; then one editor opening after recovery. |
| Steps | 1. Reset the tally and open `<app_url>/` with the endpoint hanging; count requests and read the tally.<br>2. Repeat with the endpoint answering `500`.<br>3. Repeat with the endpoint failing at the network level.<br>4. Inspect storage for any queued or pending report.<br>5. Restore the endpoint to `200`, sign in as User A and open «Доклад про Пушкина»; count requests and read the tally. |
| Expected result | Each failure mode records exactly one attempt and no retry; the three modes increment distinguishable counters (`refused` for `500`, `unreachable` for the network error and the hang); nothing is held in storage awaiting a later attempt; after recovery exactly one request is issued, carrying only that editor opening, and the success increments only `ok`. |
| Status | Not run |

---

## 5. After Account Deletion

### TC-14-UI-5.1 — Deleting the account clears the identity and the frozen attribution

| Field | Value |
|---|---|
| Description | The identity and everything keyed to it belong to the account that was deleted; leaving them behind ties the next registration from that browser to a person who asked to be gone. |
| Preconditions | User A signed in in a browser holding both a visitor identity and the frozen five-key attribution set. |
| Test data | Deletion flow on `/profile`; keys `textery.analytics.visitorId` and `textery.analytics.attribution`. |
| Steps | 1. Arrive from the marketing link, register/sign in as User A, and confirm both keys are present.<br>2. Open «Мой профиль» and complete the account-deletion flow.<br>3. Read both analytics keys.<br>4. Open `<app_url>/` again and read the identity key. |
| Expected result | After step 3 both keys are absent (`null`); after step 4 the identity key holds a well-formed UUID different from the one recorded in step 1. |
| Status | Not run |

### TC-14-UI-5.2 — Deleting the account leaves the visitor's other preferences alone

| Field | Value |
|---|---|
| Description | Deletion clears what belongs to the account, not the browser: wiping storage wholesale takes the device's colour theme with it, which the visitor never asked for. |
| Preconditions | User A signed in with the dark theme chosen (`localStorage["textery.theme"]` set accordingly). |
| Test data | Theme key `textery.theme`; the theme's own control on the app shell. |
| Steps | 1. Sign in as User A and choose the non-default colour theme.<br>2. Read `localStorage["textery.theme"]` and record it.<br>3. Complete the account-deletion flow.<br>4. Read the theme key and screenshot the page. |
| Expected result | The theme key holds exactly the value recorded in step 2; the page still renders in the chosen theme after deletion. |
| Status | Not run |

### TC-14-UI-5.3 — A registration after a deletion is not attributed to the deleted account's campaign

| Field | Value |
|---|---|
| Description | Carrying the dead account's first touch into the next registration invents a campaign conversion no marketing link produced. |
| Preconditions | A browser whose account registered from the marketing link of TC-14-UI-2.1 and has since been deleted. `qa.newvisitor@textery.test` not registered. |
| Test data | New registrant `qa.newvisitor@textery.test` / `Qa!NewVisitor2026`; plain `<app_url>/` with no parameters. |
| Steps | 1. In the prepared browser, open `<app_url>/` with no campaign parameters.<br>2. Click «Попробовать бесплатно» and register the new registrant.<br>3. Read the body of the recorded `POST /api/v1/auth/register`. |
| Expected result | The registration body carries none of the five `utm_*` (all absent or NULL) — in particular no `spring2026`; registration succeeds as it does for any direct visitor. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the browser holds a stored visitor identity` | `localStorage["textery.analytics.visitorId"]` read through `readStored('local', …)` |
| `not well-formed` | A stored value that does not match the v4 UUID pattern |
| `arrives from a link carrying campaign parameters` | Initial page load with `?utm_source=…&utm_campaign=…` |
| `the browser holds those campaign parameters` | `localStorage["textery.analytics.attribution"]`, JSON of the frozen set |
| `characters outside the basic plane` | Astral-plane code points, asserted byte-exact end to end |
| `navigates within the site` | In-app flow transitions — never a typed URL |
| `exactly one site visit is reported` | One `POST /api/v1/analytics/events` with `SITE_VISITED`, asserted under `<StrictMode>` as `main.tsx` mounts it |
| `activates that document twice in rapid succession` | Two clicks with no await between them, against the control exactly as it renders today |
| `gaining no disabled or busy state` | The control's rendered props are unchanged from the pre-story component |
| `the browser's back control` | History navigation, not an in-app link |
| `recorded in total` | Counted on stored rows, so the server-side collapse cannot satisfy the assertion |
| `storage refuses to be written` | `localStorage.setItem` stubbed to throw, as in private-mode Safari |
| `marked as coming from a browser that could not store` | `degraded: true` on the event body |
| `the analytics endpoint refuses every request` | Route stubbed to 5xx / network failure |
| `accepts requests and never answers them` | Route stubbed to hang past the client's own deadline |
| `refused as unauthorized / rate limited / invalid` | `401`, `429` and `400` from the events route |
| `a distinguishable drop signal` | `sendOutcomes()` — a per-family client counter, readable without the visitor seeing it |
| `leaves the page immediately` | Unload right after load; the send uses the `keepalive` path |
| `the chosen colour theme` | `localStorage["textery.theme"]` (`shared/theme/theme.ts`) |
| `deletes its account` | The existing deletion flow on the profile screen |
