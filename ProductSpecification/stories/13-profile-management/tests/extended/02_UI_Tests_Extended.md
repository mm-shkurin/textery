> These are additional edge case tests. Implement after core tests pass.

# Profile management — UI Tests (Extended)

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| User A (named) | `qa.profile@textery.test` / `Qa!Profile2026`, `name = "Анна Ковалёва"`, `created_at = 2025-02-03T10:15:00Z` |
| User C (unnamed) | `qa.noname@textery.test` / `Qa!NoName2026`, `name = null` |
| Screen texts | «Мой профиль», «Отображаемое имя», «Сохранить», «Отмена», «Повторить», «Выйти» |
| Degraded texts | header «Данные профиля недоступны»; screen «Не удалось загрузить профиль» |
| Counter | `<span class="counter">N / 60</span>`, class `over` when N > 60 |
| Shell widths | profile screen 1240 px single column; project feed 1640 px (story 12) |
| Desktop viewport | 1440 × 900 |
| Narrow viewport | 375 × 812 |
| Name bound | 60 code points |

---

## 1. Layout and Presentation

### TC-13-UI-1.1e — The profile screen holds its single-column shell width

| Field | Value |
|---|---|
| Description | The feed's 1640 px shell is wrong for a two-field form; inheriting it stretches the card across the viewport. |
| Preconditions | User A signed in; viewport 1440 × 900. |
| Test data | Expected shell width 1240 px (`ProductSpecification/ui/ui-conventions.md`); the feed's 1640 px as the negative. |
| Steps | 1. Open `/profile` at 1440 × 900.<br>2. Read the computed `max-width` / `getBoundingClientRect().width` of the page's content container. |
| Expected result | The container's `max-width` is the 1240 px single-column shell, not 1640 px; the card is centred within it and does not span the full 1440 px viewport. |
| Status | Not run |

### TC-13-UI-1.2e — The screen is usable on a narrow viewport

| Field | Value |
|---|---|
| Description | The form must not force horizontal scrolling on a phone — a control off-screen is a control that does not exist. |
| Preconditions | User A signed in; viewport 375 × 812. |
| Test data | Elements: the identity block, the «Отображаемое имя» input, «Сохранить», «Отмена». |
| Steps | 1. Open `/profile` at 375 × 812.<br>2. Read `document.documentElement.scrollWidth` and `clientWidth`.<br>3. Read each of the four elements' `getBoundingClientRect()`. |
| Expected result | `scrollWidth <= clientWidth` — no horizontal scrollbar; each of the four elements has `left >= 0` and `right <= 375`, is visible, and is clickable at its centre point after vertical scrolling only. |
| Status | Not run |

### TC-13-UI-1.3e — A very long name does not break the header

| Field | Value |
|---|---|
| Description | 60 characters in a fixed-width header row overflows or pushes «Выйти» off the panel unless the name is truncated. |
| Preconditions | User A signed in with `name = "я" × 60`; viewport 1440 × 900. |
| Test data | `name = "я" × 60`; the header identity row and the avatar menu panel. |
| Steps | 1. Load `/projects`; read the header's `getBoundingClientRect()` height and the identity element's computed `text-overflow` / `overflow`.<br>2. Compare the header height and the position of «Выйти» against a load with `name = "Анна Ковалёва"`.<br>3. Open `/profile` and read the input's value. |
| Expected result | The header height and «Выйти»'s position are unchanged from the short-name run; the identity element carries `overflow: hidden` with `text-overflow: ellipsis` (or a line clamp) and its `scrollWidth` exceeds its `clientWidth` — visually truncated, not overflowing its box; step 3 shows all 60 characters in the input. |
| Status | Not run |

---

## 2. Menu Behaviour

### TC-13-UI-2.1e — The avatar menu dismisses without navigating

| Field | Value |
|---|---|
| Description | An outside click must close the panel and nothing else — a click that navigates loses whatever the user was doing. |
| Preconditions | User A signed in on `/projects` with the avatar menu open. |
| Test data | Click point: page background at (20, 400), outside the panel's bounding box. |
| Steps | 1. Record the URL and the page's load id.<br>2. Click at (20, 400).<br>3. Read the panel's presence, the URL and the load id. |
| Expected result | The panel is removed from the DOM (or hidden); the URL is still `/projects` and the load id is unchanged — no navigation and no reload. |
| Status | Not run |

### TC-13-UI-2.2e — «Мой профиль» is offered while the header is degraded

| Field | Value |
|---|---|
| Description | Either the item survives the degraded state deliberately or it is hidden; drifting into one of the two is what this pins (`13_ProfileManagement_Notes.md` § UI/UX Warnings). |
| Preconditions | User A signed in on `/projects`; `GET /api/v1/auth/me` answering `500` for every call. |
| Test data | Header degraded text «Данные профиля недоступны»; screen failure text «Не удалось загрузить профиль» + «Повторить». |
| Steps | 1. Load `/projects` with `/me` failing; open the avatar menu.<br>2. Confirm the panel reads «Данные профиля недоступны» and locate «Мой профиль».<br>3. Click «Мой профиль».<br>4. Read the resulting screen. |
| Expected result | «Мой профиль» is present and enabled in the degraded panel; clicking it navigates to `/profile`, which renders its load-failed state — «Не удалось загрузить профиль» with a «Повторить» button — not a blank page and not a perpetual shimmer. |
| Status | Not run |

---

## 3. Field Behaviour

### TC-13-UI-3.1e — The counter reads zero on an empty field

| Field | Value |
|---|---|
| Description | A counter initialized from `undefined` reads `NaN / 60` or flags the empty field as over the limit, locking «Сохранить» on a legitimate clearing. |
| Preconditions | User C signed in (`name = null`); `/profile` freshly opened. |
| Test data | Empty «Отображаемое имя» field. |
| Steps | 1. Open `/profile` as user C.<br>2. Read the counter's text and class list. |
| Expected result | The counter reads exactly `0 / 60` — never `NaN / 60`, `undefined / 60` or blank; it does **not** carry the `over` class. |
| Status | Not run |

### TC-13-UI-3.2e — Cancelling restores the saved value

| Field | Value |
|---|---|
| Description | «Отмена» must reset to the loaded value and clear the dirty flag, or the unsaved-changes guard fires on a screen with nothing unsaved. |
| Preconditions | User A on `/profile` with `name = "Анна Ковалёва"` loaded. |
| Test data | Typed value `Анна Волкова`; then «Отмена». |
| Steps | 1. Change the field to `Анна Волкова`.<br>2. Click «Отмена».<br>3. Read the field's value, the counter and «Сохранить»'s state.<br>4. Navigate away within the app. |
| Expected result | The field holds `Анна Ковалёва` again; the counter reads `13 / 60`; «Сохранить» is `disabled`; step 4 raises no unsaved-changes confirmation. |
| Status | Not run |

### TC-13-UI-3.3e — Pasting an over-long name is reported, not silently truncated

| Field | Value |
|---|---|
| Description | A silent `maxlength` truncation saves a name the user did not type and never tells them; the over-limit state must be visible instead. |
| Preconditions | User A on `/profile`, field cleared. |
| Test data | Paste `"я" × 75` (15 past the bound). |
| Steps | 1. Paste the 75-character value into «Отображаемое имя».<br>2. Read the field's value length, the counter text and class, and «Сохранить»'s state. |
| Expected result | The field still holds all 75 characters — no `maxlength` truncation to 60; the counter reads `75 / 60` with class `over`; «Сохранить» is `disabled`. |
| Status | Not run |

### TC-13-UI-3.4e — An unrenderable registration date announces itself

| Field | Value |
|---|---|
| Description | The dash is a fallback rendering as ordinary data — indistinguishable from a legitimately dashed value, and silent about a serializer that started producing garbage. |
| Preconditions | User A signed in; the client-side error channel (`reportError` / the error-reporting hook) spied on. |
| Test data | (a) `/me` → `created_at = "2026-13-45T99:99:99Z"`. (b) `/me` → `created_at = "2025-02-03T10:15:00Z"`. |
| Steps | 1. Open `/profile` with (a); read the registration row and the error-channel spy.<br>2. Reload with (b); read the row and the spy again. |
| Expected result | (a) the row shows the placeholder dash `—` **and** exactly one report reaches the client-side error channel, naming `created_at` and the unparseable value. (b) the row reads «На Textery с 3 февраля 2025» and the error channel receives nothing. |
| Status | Not run |

---

## 4. Avatar

### TC-13-UI-4.1e — Initials follow the name once it is set and the address when it is cleared

| Field | Value |
|---|---|
| Description | The initials source must switch with the name's presence in both directions; a one-way binding leaves stale initials after a clear. |
| Preconditions | User C signed in (`name = null`), on `/profile`; `PATCH` answering with the value sent. |
| Test data | Address `qa.noname@textery.test` → initials `QN`; name `Анна Ковалёва` → initials `АК`. |
| Steps | 1. Read the avatar's rendered text on load.<br>2. Type `Анна Ковалёва` and click «Сохранить»; read the screen and header avatars.<br>3. Clear the field and click «Сохранить»; read both avatars again. |
| Expected result | Step 1: initials derived from `qa.noname@textery.test` (`QN`). Step 2: both avatars read `АК`. Step 3: both avatars read `QN` again — never the stale `АК`, never blank. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the single-column page width` | 1240px shell (`ProductSpecification/ui/ui-conventions.md`) |
| `the project feed's width` | 1640px shell of story 12 |
| `the bound` | 60 code points |
| `the counter` | Client-side code-point counter on the name field |
| `nothing is reported as unsaved` | `useUnsavedGuard` dirty flag cleared |
