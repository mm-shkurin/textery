> **Implementation Order**: sequential TDD — feed display → view toggle → search →
> sort → retry → state persistence → empty and error states.

# Мои проекты — UI Tests

Screen: `/projects` («Мои проекты»), reached by clicking through the app shell — never by
typing the URL. Backed by `GET /api/v1/projects` and `POST /api/v1/generations/{id}/retry`.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Account A (the caller) | `qa.projects@textery.test` / `Qa!Projects2026` |
| Document D1 | id `3f8b1c07-5a2d-4e91-b6c4-9d0e7a1f2b53`, title `Отчёт по практике`, type `реферат` (card label «Реферат»), `updated_at 2026-08-18T09:00:00Z` |
| Document D2 | id `a1c46e2b-9d38-4f57-8b02-6e5c31a9d740`, title `Эссе о Пушкине`, type `эссе` |
| Untitled document D3 | id `0e5b7d23-8a41-4c96-b3f0-71d2c48e9a05`, `title: null`, preview `Введение. Настоящая работа посвящена…` |
| Generation G-failed | id `c72e5a90-3b14-4d6f-9e88-01af4c2d7b65`, `status: failed`, `retryable: true`, topic `Влияние климата на урожай` |
| Generation G-stale | id `9b3f0d54-1e87-4a2c-8d65-73c1f9e0a4b2`, `status: recovering`, `retryable: false` |
| Feed / card selectors | `[data-testid='projects-screen']`, `[data-testid='projects-recent']`, `[data-testid='project-card']`, `[data-testid='project-card-title']`, `[data-testid='project-card-type']`, `[data-testid='project-card-date']` |
| Control selectors | `[data-testid='projects-search']`, `[data-testid='projects-sort']`, `[data-testid='projects-view-grid']` / `'projects-view-list'`, `[data-testid='projects-pager']`, `[data-testid='projects-page-next']` / `'projects-page-prev'`, `[data-testid='projects-result-count']` |
| Retry selectors | `[data-testid='project-card-retry']` («Повторить», «Повторяем…» while in flight), `[data-testid='project-card-retry-error']` |
| Empty / error selectors | `[data-testid='projects-empty-search']` («Ничего не найдено.» + «Сбросить поиск»), `[data-testid='projects-empty-none']` («Здесь пока ничего нет» / «Начните работу здесь» + «Создать проект»), `[data-testid='projects-error']` + `[data-testid='projects-error-retry']`, `[data-testid='projects-loading']` |
| State in the URL | `/projects?q=…&sort=…&page=…` — search, sort and page are restored from the query string |

## 1. Page Display

### TC-12-UI-1.1 — The projects page shows the user's feed as a grid

| Field | Value |
|---|---|
| Description | The default landing state of the screen. A card missing its type or date is the mockup's whole identity gone. |
| Preconditions | Account A signed in and owns D1 and D2; the app shell is rendered. |
| Test data | D1 `Отчёт по практике` / `реферат` / `18.08.2026`; D2 `Эссе о Пушкине` / `эссе`. |
| Steps | 1. Click «Мои проекты» in the shell navigation to reach `/projects`.<br>2. Read every `[data-testid='project-card']`. |
| Expected result | Two cards render; D1's card shows the type label «Реферат» in `project-card-type`, the text `Отчёт по практике` in `project-card-title`, `18.08.2026` in `project-card-date`, and a folder icon; D2's card shows «Эссе» and `Эссе о Пушкине`. |
| Status | Not run |

### TC-12-UI-1.2 — A recent-projects section shows the newest four

| Field | Value |
|---|---|
| Description | «Недавние проекты» is the first four items of the same page, not a second request; a wrong slice size or a duplicate fetch is what this catches. |
| Preconditions | Account A owns 9 projects with distinct `updated_at` values. |
| Test data | The four newest are `Проект 9`, `Проект 8`, `Проект 7`, `Проект 6`. |
| Steps | 1. Open `/projects` through the navigation.<br>2. Read `[data-testid='projects-recent']` and the feed region below it. |
| Expected result | The heading «Недавние проекты» is visible; the recent section holds exactly 4 cards, titled `Проект 9`, `Проект 8`, `Проект 7`, `Проект 6` in that order; a separate section below lists all 9. |
| Status | Not run |

### TC-12-UI-1.3 — An untitled document is labelled by its first line

| Field | Value |
|---|---|
| Description | Naming every untitled доклад «Доклад» made them indistinguishable in the old «Мои работы» and therefore unopenable. |
| Preconditions | Account A owns D3 with `title: null` and `preview: "Введение. Настоящая работа посвящена…"`. |
| Test data | D3 id `0e5b7d23-8a41-4c96-b3f0-71d2c48e9a05`, type `реферат`. |
| Steps | 1. Open `/projects` through the navigation.<br>2. Read that card's `project-card-title`. |
| Expected result | The title element shows `Введение. Настоящая работа посвящена…` — the start of the document's own text; it does not show «Реферат» or an empty string; the type label «Реферат» still appears separately in `project-card-type`. |
| Status | Not run |

### TC-12-UI-1.4 — A failed generation shows a retry action

| Field | Value |
|---|---|
| Description | «Повторить» is the only recovery path for paid work that failed; a card that just says "ошибка" strands the user. |
| Preconditions | Account A owns G-failed; the feed returns it with `"status":"failed","retryable":true`. |
| Test data | G-failed id `c72e5a90-3b14-4d6f-9e88-01af4c2d7b65`. |
| Steps | 1. Open `/projects` through the navigation.<br>2. Read the card for `c72e5a90-…`. |
| Expected result | The card shows the failed state and contains an enabled `[data-testid='project-card-retry']` button labelled «Повторить», alongside the «Тот же стиль» and «Тот же объём» selects. |
| Status | Not run |

### TC-12-UI-1.5 — A recovering generation shows no retry action

| Field | Value |
|---|---|
| Description | `retryable` is read as the server sent it and never recomputed from `status`; offering the button on a row the sweep is re-running duplicates paid work. |
| Preconditions | Account A owns G-stale; the feed returns it with `"status":"recovering","retryable":false`. |
| Test data | G-stale id `9b3f0d54-1e87-4a2c-8d65-73c1f9e0a4b2`. |
| Steps | 1. Open `/projects` through the navigation.<br>2. Read the card for `9b3f0d54-…`. |
| Expected result | The card shows it is recovering (not «Ошибка», not «Готово»); no `[data-testid='project-card-retry']` element exists inside that card — absent, not merely disabled. |
| Status | Not run |

### TC-12-UI-1.6 — Inert controls are shown as unavailable

| Field | Value |
|---|---|
| Description | The mockup draws controls this story does not implement; a live-looking control that does nothing reads as a broken app, and a focusable one traps keyboard users. |
| Preconditions | Account A signed in on `/projects`. |
| Test data | The category tabs, the per-project actions («…») menu, and the business document types in the create picker. |
| Steps | 1. Open `/projects` through the navigation.<br>2. Click each inert control.<br>3. Tab through the page from the first focusable element to the last. |
| Expected result | Each inert control carries `aria-disabled="true"` and is visually dimmed; clicking sends no network request and changes no route; none of them ever receives focus during the Tab sweep. |
| Status | Not run |

---

### TC-12-UI-1.7 — A card's date is shown in the viewer's own day

| Field | Value |
|---|---|
| Description | Formatting a UTC instant without converting shows yesterday's date to anyone east of UTC — on a card whose whole job is "when did I last touch this". |
| Preconditions | The browser's time zone is `Europe/Moscow` (UTC+3); account A owns a project with `updated_at = 2026-08-17T22:30:00Z`. |
| Test data | `updated_at` `2026-08-17T22:30:00Z` = `2026-08-18 01:30` local. |
| Steps | 1. Open `/projects` through the navigation with the browser zone set to `Europe/Moscow`.<br>2. Read that card's `project-card-date`. |
| Expected result | The card shows `18.08.2026` (the viewer's local calendar day), not `17.08.2026`. |
| Status | Not run |

---

## 2. View Toggle

### TC-12-UI-2.1 — Switching to list view re-renders the same feed

| Field | Value |
|---|---|
| Description | The toggle is a presentation change over data already in hand; a refetch here doubles the request rate on every click. |
| Preconditions | Account A signed in on `/projects` in grid view with 6 projects loaded. |
| Test data | The 6 loaded `(kind,id)` pairs; network capture armed. |
| Steps | 1. Record the rendered `(kind,id)` set and reset the network capture.<br>2. Click `[data-testid='projects-view-list']`. |
| Expected result | The same 6 projects render as rows in list layout with the same ids in the same order; zero requests to `/api/v1/projects` are observed during the switch. |
| Status | Not run |

### TC-12-UI-2.2 — Switching views keeps the active search and scroll position

| Field | Value |
|---|---|
| Description | Losing the query or jumping to the top on a layout toggle makes the toggle feel like a page reload. |
| Preconditions | Account A on `/projects` having typed a search and scrolled down. |
| Test data | Query `отчёт`; scroll offset ≈ 800 px. |
| Steps | 1. Type `отчёт` into `[data-testid='projects-search']` and scroll down 800 px.<br>2. Click `projects-view-list`, then click `projects-view-grid`. |
| Expected result | After each switch the search input still holds `отчёт`, the URL still carries `q=отчёт`, only matching projects are rendered, and the scroll offset is within a few pixels of 800 — not reset to 0. |
| Status | Not run |

---

## 3. Search

### TC-12-UI-3.1 — Searching filters the feed and shows the result count

| Field | Value |
|---|---|
| Description | The count is how the user knows the filter did something; without it an empty-looking screen is ambiguous. |
| Preconditions | Account A owns 8 projects, 3 of which contain `отчёт`. |
| Test data | Query `отчёт`; server `total` = 3. |
| Steps | 1. Open `/projects` and type `отчёт` into `[data-testid='projects-search']`.<br>2. Wait for the debounced request to settle. |
| Expected result | Exactly 3 `[data-testid='project-card']` elements render, all matching `отчёт`; `[data-testid='projects-result-count']` is visible and states `3`. |
| Status | Not run |

### TC-12-UI-3.2 — The recent-projects section is hidden while searching

| Field | Value |
|---|---|
| Description | «Недавние проекты» is the head of the unfiltered feed; leaving it up during a search shows non-matching cards above the results. |
| Preconditions | Account A on `/projects` with the recent section visible. |
| Test data | Query `отчёт`. |
| Steps | 1. Confirm `[data-testid='projects-recent']` is present.<br>2. Type `отчёт` into the search field and let the request settle. |
| Expected result | `[data-testid='projects-recent']` is no longer in the DOM; only the filtered feed section is rendered. |
| Status | Not run |

### TC-12-UI-3.3 — The latest search wins regardless of response order

| Field | Value |
|---|---|
| Description | Out-of-order responses are the default on a debounced input; without sequencing, the screen settles on results for a query the user has already replaced. |
| Preconditions | Account A on `/projects`; the responses for `от` and `отчёт` are held so the earlier one returns last. |
| Test data | Query `от` (5 matches) typed first, then `отчёт` (3 matches); `от`'s response released after `отчёт`'s. |
| Steps | 1. Type `от`, then extend it to `отчёт`.<br>2. Release the `отчёт` response, then release the stale `от` response. |
| Expected result | The feed shows the 3 `отчёт` results after the first release and still shows exactly those 3 after the stale `от` response arrives; the count stays `3`. |
| Status | Not run |

### TC-12-UI-3.4 — Typing does not fire a request per keystroke

| Field | Value |
|---|---|
| Description | The search runs an unindexed content scan; one request per character is what the 300 ms debounce and the per-account cap exist to prevent. |
| Preconditions | Account A on `/projects`; network capture armed at the request layer. |
| Test data | The 6-character term `отчёты` typed at ~50 ms per character; debounce 300 ms. |
| Steps | 1. Reset the capture.<br>2. Type all 6 characters within ~300 ms.<br>3. Wait 1 s and count the requests to `/api/v1/projects`. |
| Expected result | Fewer than 6 requests are sent over the typing window — in practice 1 — and the final request carries `q=отчёты`. |
| Status | Not run |

---

### TC-12-UI-3.5 — A search term carrying markup is displayed inert

| Field | Value |
|---|---|
| Description | The query is echoed into the results header, the empty state and the input, and it survives into the URL — four places one payload could execute. |
| Preconditions | Account A on `/projects`; no project matches the payload. |
| Test data | Query `<img src=x onerror=alert(1)>`; dialog listener armed. |
| Steps | 1. Type the payload into `[data-testid='projects-search']` and let the request settle.<br>2. Read `[data-testid='projects-empty-search']` and the input's value.<br>3. Reload the page from the address bar with `?q=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E`. |
| Expected result | «Ничего не найдено.» is shown with the payload rendered as literal text; the input's value is the payload verbatim; no `<img>` node is created and no dialog fires — before or after the reload; after the reload the input still holds the payload unchanged. |
| Status | Not run |

---

## 4. Sorting

### TC-12-UI-4.1 — Choosing a sort order re-orders the feed and resets to the first page

| Field | Value |
|---|---|
| Description | Page 3 of one order is a meaningless offset in another; staying on it shows the user an arbitrary slice. |
| Preconditions | Account A owns 45 projects and is on page 3 sorted `created_desc`. |
| Test data | New sort `title_asc`; `limit` 20. |
| Steps | 1. Navigate to page 3 with `[data-testid='projects-page-next']`.<br>2. Choose «По названию» in `[data-testid='projects-sort']`. |
| Expected result | The URL becomes `/projects?sort=title_asc&page=1`; `[data-testid='projects-page-position']` reports page 1; the rendered titles are in ascending order. |
| Status | Not run |

### TC-12-UI-4.2 — Sorting keeps the active search

| Field | Value |
|---|---|
| Description | Changing the order must not silently widen the result set back to the whole feed. |
| Preconditions | Account A on `/projects` with `q=отчёт` active and 3 results shown. |
| Test data | Query `отчёт`; new sort `title_asc`. |
| Steps | 1. With the search active, choose «По названию» in the sort control. |
| Expected result | The URL carries both `q=отчёт` and `sort=title_asc`; the search input still holds `отчёт`; exactly the same 3 matching projects render, now in title order; the result count still states `3`. |
| Status | Not run |

---

### TC-12-UI-4.3 — The latest sort wins regardless of response order

| Field | Value |
|---|---|
| Description | Same race as the search, on a control that is easy to click twice; a late first response would silently overwrite the order the user chose. |
| Preconditions | Account A on `/projects`; both sort responses are held. |
| Test data | `sort=title_asc` chosen first, then `sort=type_asc`; the `title_asc` response released last. |
| Steps | 1. Choose «По названию», then immediately «По типу».<br>2. Release the `type_asc` response.<br>3. Release the stale `title_asc` response. |
| Expected result | The feed renders in `type_asc` order after step 2 and is still in `type_asc` order after step 3; the sort control still displays «По типу» and the URL still carries `sort=type_asc`. |
| Status | Not run |

---

## 5. Retry

### TC-12-UI-5.1 — Retrying a failed generation starts a new one

| Field | Value |
|---|---|
| Description | Nothing is deleted by a retry — the failed card stays beside the new one, which is what keeps the user from thinking their work vanished. |
| Preconditions | Account A on `/projects` with G-failed rendered and retryable. |
| Test data | G-failed `c72e5a90-…`; defaults «Тот же стиль» / «Тот же объём». |
| Steps | 1. Click `[data-testid='project-card-retry']` on that card.<br>2. Wait for the response and the feed refresh. |
| Expected result | One `POST /api/v1/generations/c72e5a90-…/retry` is sent carrying an `Idempotency-Key` header and no body fields for style or volume; a new in-progress card appears; the `c72e5a90-…` failed card is still rendered. |
| Status | Not run |

### TC-12-UI-5.2 — A double click starts only one generation

| Field | Value |
|---|---|
| Description | Retry is the one action that spends money; the in-flight guard plus the disabled button must make a double click impossible to pay for twice. |
| Preconditions | Account A on `/projects` with G-failed rendered; the retry response is held ~1 s. |
| Test data | Two clicks ~100 ms apart on `project-card-retry`. |
| Steps | 1. Click the retry button twice in quick succession.<br>2. Count the `POST …/retry` requests and the resulting generations. |
| Expected result | Exactly one `POST` is sent (the button reads «Повторяем…» and is `disabled` after the first click); exactly one new generation appears in the feed. |
| Status | Not run |

### TC-12-UI-5.3 — A failed retry restores the card and reports the error

| Field | Value |
|---|---|
| Description | An optimistic pending card left behind after a rejection is a project the user will wait on forever. |
| Preconditions | Account A on `/projects` with G-failed rendered; the retry endpoint answers `409 {"error_code":"NOT_RETRYABLE"}`. |
| Test data | Rejection `409 NOT_RETRYABLE`. |
| Steps | 1. Click retry on that card.<br>2. Let the `409` arrive. |
| Expected result | `[data-testid='project-card-retry-error']` appears on that card with `role="alert"` and a readable Russian message; the retry button is enabled again and reads «Повторить»; no pending/optimistic project card remains in the feed. |
| Status | Not run |

---

### TC-12-UI-5.4 — A shed retry does not re-arm the button immediately

| Field | Value |
|---|---|
| Description | Re-arming on the next paint invites the user to hammer a shed endpoint; the server told the client exactly how long to wait. |
| Preconditions | Account A on `/projects`; the retry answers `429` with `{"error_code":"RETRY_LIMIT_REACHED"}` and `Retry-After: 10`. |
| Test data | `Retry-After: 10` seconds. |
| Steps | 1. Click retry and let the `429` arrive.<br>2. Inspect the button on the next paint.<br>3. Inspect it again after 10 s. |
| Expected result | The button is `disabled` immediately after the `429` and remains `disabled` for the full 10 s stated by `Retry-After`; a click during that window sends no request; after 10 s it is clickable again. |
| Status | Not run |

### TC-12-UI-5.5 — Retrying work that has since finished refreshes instead of dead-ending

| Field | Value |
|---|---|
| Description | The card is a snapshot; when the server answers "this is no longer retryable", the honest move is to show the current state, not an error the user can only stare at. |
| Preconditions | Account A rendered the card while the generation was `failed`; the generation has since completed and become a document; the retry answers `409 NOT_RETRYABLE`. |
| Test data | G-failed `c72e5a90-…`, now completed as document `7a4d0e19-…`. |
| Steps | 1. Click retry on the stale card.<br>2. Let the `409` arrive. |
| Expected result | No new project card appears; the feed re-fetches and renders the work in its current state — a document card for `7a4d0e19-…` — rather than leaving the failed card with a dead button. |
| Status | Not run |

---

## 6. State Persistence

### TC-12-UI-6.1 — Search, sort and page survive opening a project and returning

| Field | Value |
|---|---|
| Description | Losing the query on a round trip to the editor makes browsing a long feed unusable — the user re-types and re-pages for every document they open. |
| Preconditions | Account A owns 45 projects; the state lives in the URL query string. |
| Test data | `q=отчёт`, `sort=title_asc`, `page=2`. |
| Steps | 1. Search `отчёт`, choose «По названию», page forward to page 2.<br>2. Click a document card to open the editor.<br>3. Use the browser Back navigation. |
| Expected result | The restored URL is `/projects?q=отчёт&sort=title_asc&page=2`; the search input holds `отчёт`, the sort control shows «По названию», the pager reports page 2, and the same filtered items render. |
| Status | Not run |

### TC-12-UI-6.2 — Search, sort and page survive a reload

| Field | Value |
|---|---|
| Description | Same state, restored from the address bar rather than from in-memory history — a shared or bookmarked link must reproduce the view. |
| Preconditions | Account A on `/projects?q=отчёт&sort=title_asc&page=2`. |
| Test data | `q=отчёт`, `sort=title_asc`, `page=2`. |
| Steps | 1. Reach that state through the UI.<br>2. Reload the page. |
| Expected result | After the reload the search input holds `отчёт`, the sort control shows «По названию», the pager reports page 2, and the rendered items are the same page of the same filtered feed. |
| Status | Not run |

### TC-12-UI-6.3 — The chosen view survives a reload

| Field | Value |
|---|---|
| Description | Grid/list is a per-device preference, not part of the shareable query — it belongs in client storage and must be read back on mount. |
| Preconditions | Account A on `/projects` having clicked `projects-view-list`. |
| Test data | Stored view preference key set to the list value. |
| Steps | 1. Click `[data-testid='projects-view-list']`.<br>2. Reload the page. |
| Expected result | The feed renders as rows in list layout after the reload; `projects-view-list` is the selected toggle. |
| Status | Not run |

### TC-12-UI-6.4 — A corrupted stored view falls back to the default

| Field | Value |
|---|---|
| Description | Client storage is user-writable and survives deploys; an unrecognised value must not throw during render and leave a blank screen. |
| Preconditions | Account A owns 6 projects; the stored view preference holds `carousel`. |
| Test data | Stored value `carousel` (unrecognised). |
| Steps | 1. Set the stored view preference to `carousel`.<br>2. Open `/projects` through the navigation. |
| Expected result | The grid view renders (the documented default); all 6 `[data-testid='project-card']` elements are present; no console error and no empty state. |
| Status | Not run |

---

## 7. Empty and Error States

### TC-12-UI-7.1 — A search with no matches offers to clear the search

| Field | Value |
|---|---|
| Description | The dead end of a filtered feed needs the one action that gets the user out of it. |
| Preconditions | Account A owns 6 projects, none matching the term. |
| Test data | Query `крыжовник`. |
| Steps | 1. Type `крыжовник` into the search field and let the request settle.<br>2. Click the offered action. |
| Expected result | `[data-testid='projects-empty-search']` renders with «Ничего не найдено.» and a «Сбросить поиск» button (`projects-clear-search`); clicking it empties the search input, drops `q` from the URL, and re-renders all 6 projects. |
| Status | Not run |

### TC-12-UI-7.2 — A user with no projects is offered to create one

| Field | Value |
|---|---|
| Description | Two empty states, never one: shipping the search-reset arm for a new user strands them on a button that does nothing. |
| Preconditions | Account A owns no documents and no generations; no search is active. |
| Test data | Feed response `{"items":[],"total":0}`. |
| Steps | 1. Open `/projects` through the navigation.<br>2. Click the offered action. |
| Expected result | `[data-testid='projects-empty-none']` renders with «Здесь пока ничего нет», «Начните работу здесь» and a «Создать проект» button; `[data-testid='projects-empty-search']` is absent; clicking «Создать проект» starts the create flow. |
| Status | Not run |

### TC-12-UI-7.3 — A failed load offers a retry that keeps search and sort

| Field | Value |
|---|---|
| Description | A retry that drops the query answers a different question than the one that failed, and the user has to set the view up again. |
| Preconditions | Account A on `/projects?q=отчёт&sort=title_asc`; the feed request answers `503 QUERY_TIMEOUT`. |
| Test data | `q=отчёт`, `sort=title_asc`; failure `503`. |
| Steps | 1. Reach that filtered state and let the request fail.<br>2. Click `[data-testid='projects-error-retry']`.<br>3. Inspect the repeated request. |
| Expected result | `[data-testid='projects-error']` renders with a retry affordance; the repeated request is `GET /api/v1/projects?q=отчёт&sort=title_asc&page=1&limit=20` — carrying the same query and sort, not the defaults. |
| Status | Not run |

### TC-12-UI-7.4 — The feed shows a loading state while it fetches

| Field | Value |
|---|---|
| Description | An empty region during the fetch is indistinguishable from "you have no projects", which is the one message a returning user must not be shown by mistake. |
| Preconditions | Account A owns projects; the feed response is held. |
| Test data | Response delayed ~1 s. |
| Steps | 1. Open `/projects` through the navigation.<br>2. Inspect the feed region before the response arrives. |
| Expected result | `[data-testid='projects-loading']` is rendered in place of the cards; no `[data-testid='project-card']` and neither empty state is present; after the response the placeholder is replaced by the cards. |
| Status | Not run |

---

### TC-12-UI-7.5 — A failed later page keeps the rows already shown

| Field | Value |
|---|---|
| Description | Replacing a screen of loaded work with a whole-page error throws away data the client already has, for a failure that affects only the next page. |
| Preconditions | Account A owns 45 projects; page 1 is loaded; the page-2 request answers `503`. |
| Test data | 20 rendered rows; failure on `page=2`. |
| Steps | 1. Load page 1 and count the rendered cards.<br>2. Click `[data-testid='projects-page-next']` and let the request fail. |
| Expected result | The 20 already-rendered projects stay visible; an error with a retry affordance is shown scoped to the failed page; `[data-testid='projects-error']` does not replace the whole screen. |
| Status | Not run |

### TC-12-UI-7.7 — Repeated retries against a failing backend back off

| Field | Value |
|---|---|
| Description | A retry button with no backoff turns one user staring at an error into a load generator against a backend that is already failing. |
| Preconditions | Every `GET /api/v1/projects` answers `503`. |
| Test data | 6 consecutive clicks on `projects-error-retry`; timestamps recorded per attempt. |
| Steps | 1. Click the retry action repeatedly, as fast as it allows, 6 times.<br>2. Record the interval between consecutive outbound requests. |
| Expected result | Each interval is strictly greater than the one before it (e.g. ~1 s, 2 s, 4 s, 8 s); the intervals stop growing at the configured cap; after the cap is reached no further automatic attempt is issued. |
| Status | Not run |

### TC-12-UI-7.6 — A row repeated across two pages is rendered once

| Field | Value |
|---|---|
| Description | Offset paging over a live set can return the same row on two pages — the contract tells the client to dedupe on `(kind,id)`, and dedupe on `id` alone would swallow a legitimate second row. |
| Preconditions | Account A's page 1 and page 2 both contain `{"kind":"document","id":"3f8b1c07-…"}`; they also contain a document and a generation that share id `d4f27a68-3c90-4b15-a7e2-8f60c93d1b47`. |
| Test data | Repeated pair `("document","3f8b1c07-…")`; colliding id `d4f27a68-…` across the two kinds. |
| Steps | 1. Load page 1.<br>2. Load page 2 and let it append.<br>3. Count the cards for `3f8b1c07-…` and for `d4f27a68-…`. |
| Expected result | Exactly one card renders for `("document","3f8b1c07-…")`; exactly two cards render for id `d4f27a68-…`, one per `kind`. |
| Status | Not run |

---

## 8. Navigation

### TC-12-UI-8.1 — Opening a project card opens it in the editor

| Field | Value |
|---|---|
| Description | The feed's whole purpose is getting back into a document; a card that is not a real focusable control cannot be opened by keyboard at all. |
| Preconditions | Account A on `/projects` with D1 rendered. |
| Test data | D1 id `3f8b1c07-5a2d-4e91-b6c4-9d0e7a1f2b53`, title `Отчёт по практике`. |
| Steps | 1. Click D1's card title button.<br>2. Read the resulting screen. |
| Expected result | The editor opens for document `3f8b1c07-5a2d-4e91-b6c4-9d0e7a1f2b53` with the title `Отчёт по практике` and its stored content loaded; the same card is reachable and activatable by keyboard (Tab to the title `<button>`, then Enter). |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `a signed-in user` | Session with a valid access token; app shell rendered |
| `the projects page` | `/projects` route |
| `they retry it` | Click «Повторить» → `POST /api/v1/generations/{id}/retry` |
| `no new data is fetched` | No outgoing request observed during the interaction |
| `the stale threshold` | `GENERATION_STALE_AFTER_MINUTES`, default 10 |
| `the same search, sort order and page are still applied` | Restored from the URL query string |
| `opens the projects page` | Navigates to `/projects` through the UI, never by typing a URL |
| `a card` / `a row` | `[data-testid='project-card']` / `[data-testid='project-row']` |
| `the feed region` | `[data-testid='projects-feed']` |
| `a no-matches message` / `a no-projects-yet message` | `[data-testid='projects-empty-search']` / `[data-testid='projects-empty-none']` |
| `announced as unavailable` | `aria-disabled` and not reachable by keyboard focus |
| `the stored view preference` | Per-device client storage key for the grid/list choice |
| `fewer requests than characters` | Requests counted at the network layer over the typing window |
