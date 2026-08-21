> These are additional edge case tests. Implement after core tests pass.

# Мои проекты — UI Tests (Extended)

Shared test data is inherited from `02_UI_Tests.md` (account A `qa.projects@textery.test`,
route `/projects`, selectors `[data-testid='project-card']`, `'projects-search'`,
`'projects-sort'`, `'projects-view-grid'` / `'projects-view-list'`, `'projects-recent'`,
`'projects-result-count'`, `'project-card-retry'`, `'projects-empty-search'`). Cases that
need their own values name them below.

---

## 1. Layout

### TC-12-UI-EXT-1.1 — The grid collapses to one column on a phone

| Field | Value |
|---|---|
| Description | The mobile frame is a single column; a grid that keeps its desktop track count forces sideways scrolling, which on a feed means half of every card is unreachable. |
| Preconditions | Account A owns 6 projects; the mockup `mockups/mobile/01-projects-grid.html` is the reference. |
| Test data | Viewport 375 × 812 CSS px. |
| Steps | 1. Set the viewport to 375 × 812.<br>2. Open `/projects` through the navigation.<br>3. Compare the `offsetTop` of consecutive cards and read `document.documentElement.scrollWidth`. |
| Expected result | Every `[data-testid='project-card']` starts on its own row (no two share a top offset); `scrollWidth` is ≤ the 375 px viewport width, so no horizontal scrollbar appears. |
| Status | Not run |

### TC-12-UI-EXT-1.2 — A long project title is truncated without breaking the card layout

| Field | Value |
|---|---|
| Description | An untruncated title pushes the card wider than its grid track and shifts every neighbour — one document with a pasted heading deforms the whole feed. |
| Preconditions | Account A owns a document whose title is 300 characters of continuous Cyrillic text, plus 3 normal projects. |
| Test data | Title = `Отчёт` repeated to 300 characters; desktop viewport 1440 × 900. |
| Steps | 1. Open `/projects` through the navigation.<br>2. Measure the long card's bounding box against its neighbours'. |
| Expected result | The long card's width and height equal its neighbours'; the title is clipped inside the card bounds with an ellipsis; the page has no horizontal overflow. |
| Status | Not run |

### TC-12-UI-EXT-1.3 — Both source kinds are visually distinguishable

| Field | Value |
|---|---|
| Description | A user scanning the feed must see at a glance which rows are finished documents and which are runs that failed — reading each card's text defeats the point of a grid. |
| Preconditions | Account A owns document D1 (`Отчёт по практике`) and failed generation G-failed. |
| Test data | D1 `3f8b1c07-…`; G-failed `c72e5a90-…` with `retryable: true`. |
| Steps | 1. Open `/projects` through the navigation.<br>2. Compare the two cards' non-textual affordances. |
| Expected result | The two cards differ without reading their titles: the generation card carries the failed-state treatment and the «Повторить» control, and the document card carries neither; the difference is visible in a screenshot comparison. |
| Status | Not run |

---

## 2. Search and Sort

### TC-12-UI-EXT-2.1 — Clearing the search restores the recent-projects section

| Field | Value |
|---|---|
| Description | The recent section is hidden while searching; if clearing the query does not bring it back, the user loses it permanently for the session. |
| Preconditions | Account A owns 9 projects; `q=отчёт` is active and `[data-testid='projects-recent']` is hidden. |
| Test data | Query `отчёт`; full feed of 9. |
| Steps | 1. Clear the search input (or click «Сбросить поиск»).<br>2. Let the request settle. |
| Expected result | All 9 projects render again; `q` is gone from the URL; `[data-testid='projects-recent']` is present once more with 4 cards. |
| Status | Not run |

### TC-12-UI-EXT-2.2 — The recent section under an active search

| Field | Value |
|---|---|
| Description | Pins the story's rule rather than leaving it to the implementation: «Недавние проекты» is the head of the unfiltered feed and must not be shown beside filtered results. |
| Preconditions | Account A owns 9 projects, 3 matching `отчёт`. |
| Test data | Query `отчёт`. |
| Steps | 1. Type `отчёт` into the search field.<br>2. Let the results render and inspect `[data-testid='projects-recent']`. |
| Expected result | `[data-testid='projects-recent']` is absent from the DOM while results are shown; exactly the 3 matching cards render, with no non-matching card above them. |
| Status | Not run |

### TC-12-UI-EXT-2.3 — The result count updates as the query narrows

| Field | Value |
|---|---|
| Description | A count left over from the previous query tells the user the filter matched more than it did, which is worse than showing none at all. |
| Preconditions | Account A owns projects where `отч` matches 5 and `отчёт по` matches 2. |
| Test data | Query `отч` (5), extended to `отчёт по` (2). |
| Steps | 1. Type `отч` and let the results settle; read `[data-testid='projects-result-count']`.<br>2. Extend the query to `отчёт по` and let it settle; read the count again. |
| Expected result | After step 1 the count states `5` and 5 cards render; after step 2 it states `2` and 2 cards render — the count always equals the number of rendered cards. |
| Status | Not run |

### TC-12-UI-EXT-2.4 — Pressing Enter in the search field does not submit a page reload

| Field | Value |
|---|---|
| Description | A search input inside an unguarded `<form>` triggers a native submit; the app shell reloads and the user loses their scroll, their view choice and the SPA session state. |
| Preconditions | Account A on `/projects` with `отчёт` typed into the search field. |
| Test data | Query `отчёт`; a sentinel set on `window` before the key press. |
| Steps | 1. Focus `[data-testid='projects-search']` and press Enter.<br>2. Check whether the `window` sentinel survived and read the URL. |
| Expected result | The sentinel is still present, so no full page reload occurred; the filtered feed is rendered in place; the URL is `/projects?q=отчёт` without a form-encoded submit. |
| Status | Not run |

### TC-12-UI-EXT-2.5 — Sorting is reachable by keyboard

| Field | Value |
|---|---|
| Description | A custom dropdown built from `<div>`s cannot be operated without a mouse, which puts the only ordering control out of reach for keyboard and screen-reader users. |
| Preconditions | Account A on `/projects` in the default `created_desc` order. |
| Test data | Target order `title_asc` («По названию»). |
| Steps | 1. From the top of the page, Tab until `[data-testid='projects-sort']` has focus.<br>2. Open it and choose «По названию» using only the keyboard (arrows plus Enter). |
| Expected result | The sort control receives visible focus during the Tab sweep; the keyboard selection applies `sort=title_asc` to the URL and re-orders the feed by title — no pointer event is needed. |
| Status | Not run |

### TC-12-UI-EXT-2.6 — An empty search result keeps the sort selection visible

| Field | Value |
|---|---|
| Description | An empty state that swallows the toolbar makes the user think their sort was reset, and they re-apply it after clearing the query. |
| Preconditions | Account A on `/projects` with `sort=title_asc` chosen and a query matching nothing. |
| Test data | `sort=title_asc`, `q=крыжовник`. |
| Steps | 1. Choose «По названию».<br>2. Search `крыжовник` and let the empty state render. |
| Expected result | `[data-testid='projects-empty-search']` renders with «Ничего не найдено.»; `[data-testid='projects-sort']` is still visible and still displays «По названию»; the URL still carries `sort=title_asc`. |
| Status | Not run |

---

## 3. Retry

### TC-12-UI-EXT-3.1 — The retry button is disabled while its request is in flight

| Field | Value |
|---|---|
| Description | A button that stays live through the wait invites the double click that this endpoint charges for twice. |
| Preconditions | Account A on `/projects` with G-failed rendered; the retry response is held. |
| Test data | G-failed `c72e5a90-…`; response held ~2 s. |
| Steps | 1. Click `[data-testid='project-card-retry']`.<br>2. Inspect the button before the response arrives. |
| Expected result | The button carries the `disabled` attribute and reads «Повторяем…»; the two retry selects are disabled too; a further click sends no additional request. |
| Status | Not run |

### TC-12-UI-EXT-3.2 — The retry action is absent on an unknown status

| Field | Value |
|---|---|
| Description | `retryable` is read as the server sent it and never derived from `status`; a client that guessed from an enum it does not fully know would fail open on a paid operation. |
| Preconditions | The feed returns an item with `"status":"unknown","retryable":false`. |
| Test data | Generation `b7c48f30-2e61-4a95-8d0c-73f19b2e5a64`, `status: unknown`, `retryable: false`. |
| Steps | 1. Open `/projects` through the navigation.<br>2. Inspect that card. |
| Expected result | The card renders; no `[data-testid='project-card-retry']` element exists inside it — absent, not merely disabled; no console error is raised by the unrecognised status. |
| Status | Not run |

### TC-12-UI-EXT-3.3 — A retry shows progress until it resolves

| Field | Value |
|---|---|
| Description | Between the `201` and the worker's outcome the new row is real work in flight; showing nothing makes the user click «Повторить» again on the source. |
| Preconditions | Account A retried G-failed; the new generation `N` is returned by the feed with `"status":"pending"`. |
| Test data | New generation `N`, `status: pending`, `retryable: false`. |
| Steps | 1. Click retry and let the `201` arrive.<br>2. Reload or let the feed refresh while `N` is still `pending`.<br>3. Inspect `N`'s card. |
| Expected result | `N`'s card shows an in-progress state (not «Ошибка», not «Готово»); it offers no retry control; the original failed card is still rendered beside it. |
| Status | Not run |

---

## 4. Restored State

### TC-12-UI-EXT-4.1 — The chosen view survives a reload

| Field | Value |
|---|---|
| Description | The grid/list choice is a per-device preference read from client storage on mount; if it is only React state it resets on every navigation. |
| Preconditions | Account A on `/projects`; the stored view preference is unset (default grid). |
| Test data | Stored view preference key for the grid/list choice. |
| Steps | 1. Click `[data-testid='projects-view-list']`.<br>2. Reload the page.<br>3. Read the rendered layout. |
| Expected result | After the reload the feed renders as rows in list layout and `projects-view-list` is the selected toggle. |
| Status | Not run |

### TC-12-UI-EXT-4.2 — The page number survives a return from the editor

| Field | Value |
|---|---|
| Description | Being thrown back to page 1 after opening one document makes a long feed unusable — the user re-pages for every project they touch. |
| Preconditions | Account A owns 45 projects and is on page 3. |
| Test data | `page=3&limit=20`. |
| Steps | 1. Page forward to page 3 with `[data-testid='projects-page-next']`.<br>2. Click a document card to open the editor.<br>3. Navigate back. |
| Expected result | The restored URL carries `page=3`; `[data-testid='projects-page-position']` reports page 3; the same 20 items render as before the navigation. |
| Status | Not run |

### TC-12-UI-EXT-4.3 — A shared link reproduces the same filtered feed

| Field | Value |
|---|---|
| Description | Search, sort and page live in the query string precisely so the view is addressable; if any of them lives only in memory the link is a different screen for the recipient. |
| Preconditions | Account A signed in; the feed contains items matching `отчёт`. |
| Test data | `/projects?q=отчёт&sort=title_asc&page=2`. |
| Steps | 1. Reach that state through the UI and copy the address.<br>2. Open the address in a fresh tab of the same session.<br>3. Compare the two screens. |
| Expected result | The fresh tab renders the same items in the same order as the original: the search input holds `отчёт`, the sort control shows «По названию», and the pager reports page 2. |
| Status | Not run |

---

## 5. Inert Controls

### TC-12-UI-EXT-5.1 — Inert controls do not navigate

| Field | Value |
|---|---|
| Description | A dimmed control that still fires its handler is worse than a live one — the user is told it is unavailable and then loses their place when it acts anyway. |
| Preconditions | Account A on `/projects`; the category filters and the per-project actions menu are rendered as unavailable. |
| Test data | The category filter tabs and the «…» actions menu on a card. |
| Steps | 1. Reset the network capture and record the current URL.<br>2. Click each category filter tab.<br>3. Click the per-project actions menu. |
| Expected result | The URL is unchanged after every click; zero outgoing requests are recorded; no menu or panel opens; each control still reports `aria-disabled="true"`. |
| Status | Not run |

---

## DSL Technical Reference

Inherits `02_UI_Tests.md`.
