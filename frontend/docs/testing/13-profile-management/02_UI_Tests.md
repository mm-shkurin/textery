<!-- COPIED FILE. Source of truth: ProductSpecification/stories/13-profile-management/tests/02_UI_Tests.md
     Regenerate with `node scripts/sync-test-cases.mjs` from the monorepo.
     Edits made here are overwritten by the next sync. -->

> **Implementation Order**: sequential TDD — the menu entry and the route → the screen's
> read states → typing and the length counter → submission → validation feedback → server
> response and the header → the degraded header contract → navigation and unsaved input.

# Profile management — UI Tests

Screen: `/profile`. Mockups: `mockups/desktop/01`–`08` and their mobile twins. The
**save-failed** state (`13_ProfileManagement.md` § Screen States) has no mockup — these
scenarios are its definition.

> **The header is on every authenticated page.** Section 6 is therefore not "profile screen"
> coverage: it fixes what the whole application shell renders while `/me` is in flight,
> failing, or answering nonsense.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| User A (named) | `qa.profile@textery.test` / `Qa!Profile2026`, `name = "Анна Ковалёва"`, `created_at = 2025-02-03T10:15:00Z` |
| User C (unnamed) | `qa.noname@textery.test` / `Qa!NoName2026`, `name = null`, `created_at = 2026-01-20T08:00:00Z` |
| `/me` stub (named) | `200 {"email": "qa.profile@textery.test", "name": "Анна Ковалёва", "created_at": "2025-02-03T10:15:00Z"}` |
| `/me` stub (unnamed) | `200 {"email": "qa.noname@textery.test", "name": null, "created_at": "2026-01-20T08:00:00Z"}` |
| Screen texts | h1 «Мой профиль», subtitle «Данные вашей учётной записи», field label «Отображаемое имя», hint «Показывается в шапке и на этом экране вместо адреса почты.», buttons «Сохранить» / «Отмена» |
| Failure texts | screen «Не удалось загрузить профиль» + «Повторить»; header «Данные профиля недоступны»; saving «Сохраняем имя…» |
| Registration row | «На Textery с 3 февраля 2025» |
| Counter | `<span class="counter">N / 60</span>`, class `over` when N > 60 |
| Validation text | «Имя длиннее 60 символов — сейчас 61. Уберите хотя бы один символ.» |
| Menu items | «Мой профиль», «Выйти»; the address row is non-interactive |
| Test timezone | `TZ=Asia/Yekaterinburg` (UTC+5) unless the case pins another |

---

## 0. Prerequisite Guard

### TC-13-UI-0.1 — The profile route is not reachable without a session

| Field | Value |
|---|---|
| Description | The screen renders an email and a name; reaching it without a session would render someone's identity, or a crash, on a public URL. |
| Preconditions | `sessionStorage` empty — no session key, no tokens. |
| Test data | Direct navigation to `<app_url>/profile`. |
| Steps | 1. Clear `sessionStorage` and `localStorage`.<br>2. Navigate the browser to `/profile`.<br>3. Read the final URL and the full page text. |
| Expected result | The browser lands on the sign-in route (`/login`); no `@textery.test` address, no «Анна Ковалёва», and no avatar initials appear anywhere in the DOM; no `GET /api/v1/auth/me` is issued. |
| Status | Not run |

---

## 1. Entering the Screen

### TC-13-UI-1.1 — The avatar menu offers «Мой профиль» above «Выйти»

| Field | Value |
|---|---|
| Description | The one entry point to the screen. Order matters: the destructive item must not sit first, and the address row must not become a button by accident. |
| Preconditions | User A signed in, on `/projects`; `/me` stubbed as named. |
| Test data | Menu panel of `mockups/desktop/07-avatar-menu.html`. |
| Steps | 1. Open `/projects`.<br>2. Click the avatar in the header.<br>3. Read the panel's items in DOM order and inspect the address row. |
| Expected result | The panel contains «Мой профиль» and «Выйти» in that DOM order; «Мой профиль» is above «Выйти» visually (smaller `getBoundingClientRect().top`); the row showing `qa.profile@textery.test` has no `role="button"`/`href`, no pointer cursor and does not respond to a click. |
| Status | Not run |

### TC-13-UI-1.2 — «Мой профиль» navigates to the profile screen

| Field | Value |
|---|---|
| Description | Client-side navigation, and the menu must not stay open over the destination. |
| Preconditions | User A signed in on `/projects` with the avatar menu open. |
| Test data | Menu item «Мой профиль». |
| Steps | 1. Click «Мой профиль».<br>2. Read the URL, the `h1`, and the menu panel's presence. |
| Expected result | The URL is `/profile`; the page shows `h1` «Мой профиль» and subtitle «Данные вашей учётной записи»; the menu panel is no longer in the DOM (or is hidden); no full page reload occurred. |
| Status | Not run |

---

## 2. Reading the Profile

### TC-13-UI-2.1 — The screen shows a defined placeholder while the profile is in flight

| Field | Value |
|---|---|
| Description | After the move to `/me`, the null identity is the state of *every* page for the duration of a request. A blank avatar that pops into initials is the default outcome if the loading state is not designed. |
| Preconditions | User A signed in; `GET /api/v1/auth/me` stubbed to delay 3000 ms before answering. |
| Test data | 3000 ms delayed `/me`; mockup `01-profile-loading.html`. |
| Steps | 1. Open `/profile`.<br>2. Within the delay window, screenshot the identity block and the avatar and read their classes. |
| Expected result | The identity and avatar render the shimmer placeholder («Загрузка» state — «мерцает, запрос в полёте»), not an empty box; no initials and no `—` are shown; when the response arrives the placeholder is replaced without a layout jump from empty to initials. |
| Status | Not run |

### TC-13-UI-2.2 — A profile with a name shows the name, the email and the registration date

| Field | Value |
|---|---|
| Description | The primary read state of the screen (`02-profile-named.html`). |
| Preconditions | User A signed in; `/me` stubbed as named. |
| Test data | `name = "Анна Ковалёва"`, `email = qa.profile@textery.test`, `created_at = 2025-02-03T10:15:00Z`. |
| Steps | 1. Open `/profile`.<br>2. Read the value of the «Отображаемое имя» input, the address text, and the registration row. |
| Expected result | The input's value is exactly `Анна Ковалёва`; `qa.profile@textery.test` is shown; the registration row reads «На Textery с 3 февраля 2025»; the avatar shows `АК`. |
| Status | Not run |

### TC-13-UI-2.3 — A profile with no name shows the email as the identity and an empty field

| Field | Value |
|---|---|
| Description | The NULL-keyed email fallback, on the screen (`03-profile-unnamed.html`). An empty string in the field must not be shown as a name. |
| Preconditions | User C signed in; `/me` stubbed as unnamed (`"name": null`). |
| Test data | `email = qa.noname@textery.test`. |
| Steps | 1. Open `/profile`.<br>2. Read the input's value, the identity text and the avatar. |
| Expected result | The input's value is `""` (and shows «Имя не задано» as its placeholder/identity label, not as a value); `qa.noname@textery.test` is shown as the identity; the avatar shows initials derived from the address (`QN`), never `null`, `undefined` or a blank circle. |
| Status | Not run |

### TC-13-UI-2.4 — The registration date renders through the product's existing date formatter

| Field | Value |
|---|---|
| Description | One date form across the product, and a defined answer for a date that cannot be parsed. |
| Preconditions | Browser `TZ=Asia/Yekaterinburg`; user A signed in. |
| Test data | `created_at = "2025-02-03T10:15:00Z"`; then `created_at = "not-a-date"`. |
| Steps | 1. Open `/profile` with the valid instant and read the registration row.<br>2. Restub `/me` with `created_at = "not-a-date"`, reload and read the row. |
| Expected result | Step 1: «На Textery с 3 февраля 2025» — `formatCardDate`'s ru-RU genitive month form. Step 2: the row shows the product's placeholder dash `—`, not `Invalid Date`, `NaN` or a blank. |
| Status | Not run |

### TC-13-UI-2.3a — The registration date always carries its year

| Field | Value |
|---|---|
| Description | The shared card formatter hides the year when it matches the current one, which is right for a feed of recent work and wrong for «На Textery с …» — a date with no year answers a different question than the one the row asks. |
| Preconditions | System date within 2026; user A signed in. |
| Test data | Current-year `created_at = "2026-04-11T12:00:00Z"`; earlier-year `created_at = "2025-02-03T10:15:00Z"`. |
| Steps | 1. Open `/profile` with the current-year instant and read the registration row.<br>2. Restub with the 2025 instant, reload and read the row. |
| Expected result | Step 1 reads «На Textery с 11 апреля 2026» — the year `2026` is present, not elided. Step 2 reads «На Textery с 3 февраля 2025». |
| Status | Not run |
| Note | Decided here rather than inherited: the formatter needs a year flag; accepting the hiding was rejected. |

### TC-13-UI-2.4a — The date shown is the local calendar date, at the boundary where that differs

| Field | Value |
|---|---|
| Description | TC-13-UI-2.4 leaves the instant unspecified, so it stays green against the classic defect — a date bucketed on raw UTC — which is only observable within the zone offset of midnight. |
| Preconditions | User A signed in; the browser timezone set per sub-step. |
| Test data | (a) `created_at = "2025-02-03T23:30:00Z"` with `TZ=Asia/Yekaterinburg` (UTC+5). (b) `created_at = "2025-02-03T00:30:00Z"` with `TZ=America/Sao_Paulo` (UTC−3). |
| Steps | 1. Run the browser at UTC+5 with instant (a); open `/profile`; read the row.<br>2. Run the browser at UTC−3 with instant (b); open `/profile`; read the row. |
| Expected result | Step 1 reads «На Textery с 4 февраля 2025» (the following calendar day). Step 2 reads «На Textery с 2 февраля 2025» (the preceding calendar day). Neither reads «3 февраля 2025». |
| Status | Not run |

### TC-13-UI-2.4b — The screen holds its form under a hostile locale

| Field | Value |
|---|---|
| Description | Dotted-I casing and comma decimals both reach this screen — through the initials and through the counter — and neither is visible in any other scenario. |
| Preconditions | Browser locale set to `tr-TR` (dotless-ı casing, comma decimal separator); user A signed in. |
| Test data | Locale `tr-TR` vs the default `ru-RU`; account `qa.ivan@textery.test`, `name = "Ирина Ильина"`; a typed name of 12 characters. |
| Steps | 1. Open `/profile` under `ru-RU`; record the registration row, the counter text and the avatar initials.<br>2. Reopen under `tr-TR`; record the same three. |
| Expected result | All three are identical between the two runs: the row reads «На Textery с 3 февраля 2025», the counter reads `12 / 60` (never `12,0 / 60`), and the initials are the same two characters (never `ı`-cased or `İ`-cased differently). |
| Status | Not run |

### TC-13-UI-2.5 — A failed profile read offers a retry, not a perpetual spinner

| Field | Value |
|---|---|
| Description | Mockup `06-profile-load-failed.html`. A spinner that never ends is indistinguishable from a slow network and leaves the user no action. |
| Preconditions | User A signed in; `GET /api/v1/auth/me` stubbed to answer `500 {"error_code": "INTERNAL_ERROR", …}` on the first call and `200` (named) on the second. |
| Test data | First call `500`, second call the named stub. |
| Steps | 1. Open `/profile`.<br>2. Read the card text and locate the retry control.<br>3. Click «Повторить».<br>4. Read the screen again. |
| Expected result | Step 2 shows «Не удалось загрузить профиль» and a «Повторить» button, with no shimmer placeholder still animating. Step 4 shows the named profile: input value `Анна Ковалёва`, «На Textery с 3 февраля 2025», and the failure card gone. |
| Status | Not run |

---

## 3. Typing a Name

### TC-13-UI-3.1 — Save is inert until the typed value differs from the saved one

| Field | Value |
|---|---|
| Description | Prevents a no-op PATCH on every visit, and keeps the dirty flag honest for the unsaved-input guards in section 7. |
| Preconditions | User A on `/profile` with `name = "Анна Ковалёва"` loaded. |
| Test data | Typed value `Анна Ковалёва` → `Анна Ковалёв` → `Анна Ковалёва`. |
| Steps | 1. Read the «Сохранить» button's `disabled` attribute on load.<br>2. Delete the final `а` from the field; read it again.<br>3. Retype the `а` so the field matches the loaded value; read it again. |
| Expected result | Step 1: «Сохранить» is `disabled`. Step 2: «Сохранить» is enabled. Step 3: «Сохранить» is `disabled` again — the comparison is by value, not "has the field been touched". |
| Status | Not run |

### TC-13-UI-3.2 — The length counter counts what the server counts

| Field | Value |
|---|---|
| Description | `String.length` counts UTF-16 units, so 60 emoji read as `120 / 60` and the button locks on a value the server accepts. |
| Preconditions | User A on `/profile`, field cleared. |
| Test data | `"😀" × 60` (60 code points, 120 UTF-16 units), then `"😀" × 61`. |
| Steps | 1. Type/paste `"😀" × 60` into the «Отображаемое имя» field.<br>2. Read the counter text, its class, and «Сохранить»'s state.<br>3. Add one more `😀`.<br>4. Read the counter and the button again. |
| Expected result | Step 2: the counter reads `60 / 60` without the `over` class (never `120 / 60`) and «Сохранить» is enabled. Step 4: the counter reads `61 / 60` with class `over` and «Сохранить» is `disabled`. |
| Status | Not run |

### TC-13-UI-3.3 — The counter and the changed-flag judge the normalized value

| Field | Value |
|---|---|
| Description | An NFD name of 60 characters is 120 raw code points; a counter measuring the raw value shows `120 / 60` and disables saving on a name the server stores. |
| Preconditions | User A on `/profile`, field cleared. |
| Test data | `"е́" × 60` written as base + combining acute — 120 raw code points, 60 after NFC. |
| Steps | 1. Paste the 120-code-point NFD value into the field.<br>2. Read the counter text and class, and «Сохранить»'s state. |
| Expected result | The counter reads `60 / 60` without the `over` class — never `120 / 60`; «Сохранить» is enabled. |
| Status | Not run |

---

## 4. Saving

### TC-13-UI-4.1 — Saving shows a working state and refuses a second submission

| Field | Value |
|---|---|
| Description | Mockup `04-profile-saving.html`. Without a locked working state the user has no feedback and the form accepts a second PATCH mid-flight. |
| Preconditions | User A on `/profile`; `PATCH /api/v1/auth/me` stubbed to delay 3000 ms. |
| Test data | Typed name `Анна Волкова`. |
| Steps | 1. Change the name to `Анна Волкова`.<br>2. Click «Сохранить».<br>3. Within the delay window read the button's text and `disabled` state, and try clicking it again. |
| Expected result | The button reads «Сохраняем имя…» and is `disabled`; the input is read-only or disabled; the second click issues no request — exactly one `PATCH /api/v1/auth/me` is recorded during the window. |
| Status | Not run |

### TC-13-UI-4.2 — A double click and a double Enter each save once

| Field | Value |
|---|---|
| Description | The keyboard path is a separate submit handler from the click path; guarding only the button leaves Enter unguarded. |
| Preconditions | User A on `/profile`; `PATCH` stubbed with a 2000 ms delay; the request counter reset before each half. |
| Test data | Typed name `Анна Волкова`; two clicks within 100 ms; two `Enter` presses within 100 ms. |
| Steps | 1. Change the name; click «Сохранить» twice within 100 ms; count `PATCH /api/v1/auth/me` requests.<br>2. Reload, change the name again, focus the field and press `Enter` twice within 100 ms; count requests. |
| Expected result | Exactly `1` `PATCH /api/v1/auth/me` in each half — never 2. |
| Status | Not run |

### TC-13-UI-4.3 — A successful save leaves nothing unsaved

| Field | Value |
|---|---|
| Description | The dirty flag must be recomputed against the **response**, not the typed text — otherwise a name with a trailing space stays "unsaved" forever after a successful save. |
| Preconditions | User A on `/profile`; `PATCH` stubbed to answer `200 {"email": "qa.profile@textery.test", "name": "Анна Волкова", "created_at": "2025-02-03T10:15:00Z"}`. |
| Test data | Typed value `"Анна Волкова  "` (two trailing spaces); server returns the trimmed `Анна Волкова`. |
| Steps | 1. Type `Анна Волкова  ` and click «Сохранить».<br>2. After the response, read the field's value and «Сохранить»'s state.<br>3. Navigate away within the app. |
| Expected result | The field holds exactly `Анна Волкова` (trimmed, the stored value); «Сохранить» is `disabled` again; step 3 raises no unsaved-changes confirmation. |
| Status | Not run |

### TC-13-UI-4.4 — Clearing the name falls back to the address everywhere

| Field | Value |
|---|---|
| Description | Clearing is first-class; every identity sink on the screen must fall back together, or the header and the card disagree. |
| Preconditions | User A on `/profile` with `name = "Анна Ковалёва"`; `PATCH` stubbed to answer `200` with `"name": null`. |
| Test data | Empty the field, then save. |
| Steps | 1. Select all in the «Отображаемое имя» field and delete.<br>2. Click «Сохранить».<br>3. Read the screen identity, the screen avatar and the header avatar. |
| Expected result | `PATCH` body is `{"name": ""}` (or `{"name": null}`); after the `200`, the identity shows `qa.profile@textery.test` and «Имя не задано»; both the screen avatar and the header avatar show initials derived from the address (`QP`), never blank, never the stale `АК`. |
| Status | Not run |

---

## 5. Validation and Save Failure

### TC-13-UI-5.1 — A refused name is reported inline and the typed value survives

| Field | Value |
|---|---|
| Description | Mockup `05-profile-validation-error.html`: exactly one channel — inline under the field — for a `400 {error_code, message}`. Retyping a refused name from scratch is the failure this catches. |
| Preconditions | User A on `/profile`; `PATCH` stubbed to answer `400 {"error_code": "INVALID_NAME", "message": "Имя длиннее 60 символов — сейчас 61. Уберите хотя бы один символ."}`. |
| Test data | Typed name `"я" × 61`. |
| Steps | 1. Type a 61-character name and click «Сохранить».<br>2. Read the `.field-error` text under the input, the input's value and class, and the identity block. |
| Expected result | `.field-error` reads «Имя длиннее 60 символов — сейчас 61. Уберите хотя бы один символ.»; the input carries class `is-error` and still holds the 61 typed characters; the identity block and avatar still show `Анна Ковалёва` / `АК`; no banner over the card. |
| Status | Not run |

### TC-13-UI-5.2 — A failed save blames the attempt, not the input

| Field | Value |
|---|---|
| Description | This state has no mockup — the scenario is its definition. A `500` reported beside the field would tell the user their name is wrong. |
| Preconditions | User A on `/profile`; `PATCH` stubbed to answer `500 {"error_code": "INTERNAL_ERROR", …}` on the first call and `200` on the second. |
| Test data | Typed name `Анна Волкова`. |
| Steps | 1. Type `Анна Волкова`; click «Сохранить».<br>2. Read the banner, the field value, the field's error slot and the form's interactivity.<br>3. Click the retry affordance.<br>4. Read the screen again. |
| Expected result | Step 2: a failure banner is rendered above/over the filled card with a retry control; `.field-error` is empty; the input still holds `Анна Волкова` and is enabled; «Сохранить» is enabled. Step 4: the banner is gone and the identity shows `Анна Волкова`. |
| Status | Not run |

### TC-13-UI-5.3 — A refused name and a failed save are told apart

| Field | Value |
|---|---|
| Description | If both render the same way, the user cannot tell "fix your input" from "try again later". |
| Preconditions | User A on `/profile`. |
| Test data | Save 1: `PATCH` → `400 INVALID_NAME`. Save 2: `PATCH` → `500 INTERNAL_ERROR`. |
| Steps | 1. Provoke the `400`; screenshot the card and record which elements are present.<br>2. Provoke the `500`; screenshot and record again.<br>3. Compare the two. |
| Expected result | The `400` renders `.field-error` under the input with `is-error` on the input and **no** banner; the `500` renders the failure banner with a retry control and **no** `.field-error`. The two DOM element sets are disjoint on those markers — neither state renders the other's. |
| Status | Not run |

### TC-13-UI-5.3a — A refusal this client version does not know falls to the defined default

| Field | Value |
|---|---|
| Description | The two sides deploy independently, so the backend emitting a code the shipped bundle does not define is a routine deploy state. The default branch of a failure-code switch is exactly where a screen silently mislabels or dies. |
| Preconditions | User A on `/profile`; `PATCH` stubbed to answer `400 {"error_code": "NAME_POLICY_VIOLATION", "message": "…"}` — a code the bundle does not define. |
| Test data | Typed name `Анна Волкова`; unknown `error_code` `NAME_POLICY_VIOLATION`. |
| Steps | 1. Type `Анна Волкова`; click «Сохранить».<br>2. Read the banner, the `.field-error` slot, the field value, and the browser console. |
| Expected result | The failed-save banner (the TC-13-UI-5.2 screen) is shown; `.field-error` is empty — the unknown code is **not** reported as an invalid name beside the field; the input still holds `Анна Волкова`; the card is still rendered (not blanked) and no uncaught exception appears in the console. |
| Status | Not run |

### TC-13-UI-5.4 — A save refused for body size is reported as a failed save

| Field | Value |
|---|---|
| Description | The `413` arrives without the canonical body from some proxies; a screen keyed only on `error_code` blanks on it. |
| Preconditions | User A on `/profile`; `PATCH` stubbed to answer `413 {"error_code": "REQUEST_BODY_TOO_LARGE", "message": …}`. |
| Test data | Typed name `Анна Волкова`; response `413`. |
| Steps | 1. Type `Анна Волкова`; click «Сохранить».<br>2. Read the card, the field value and the banner. |
| Expected result | The failed-save banner with its retry control is shown over the filled card — not a blank screen and not an empty card; the input still holds `Анна Волкова`. |
| Status | Not run |

---

## 6. The Header Across `/me` States

### TC-13-UI-6.1 — Each profile state has its own defined header

| Field | Value |
|---|---|
| Description | «Недоступна» is itself a definite state, unlike emptiness — and it must not look like loading. A body with fields missing must not push `undefined` into the initials. |
| Preconditions | User A signed in on `/projects`. |
| Test data | (a) `/me` delayed 3000 ms. (b) `/me` → `500`. (c) `/me` → `200 {}` (no `email`, no `name`). |
| Steps | 1. Load `/projects` with (a); screenshot the header identity within the delay.<br>2. Reload with (b); read the panel text and the avatar's classes.<br>3. Reload with (c); read the avatar's text and `aria-label`, and check the console. |
| Expected result | (a) shimmer placeholder, animated. (b) «Данные профиля недоступны» with the dashed-outline static avatar of `08-header-degraded.html` — visibly distinct from (a): different class, no animation, dashed border. (c) the header renders, no uncaught exception; the avatar shows no `undefined` and its `aria-label` does not end in «Меню профиля: ». |
| Status | Not run |

### TC-13-UI-6.1a — A profile answering with an unknown extra field renders normally

| Field | Value |
|---|---|
| Description | TC-13-UI-6.1 covers only the missing-field direction. The response is expected to grow — the verification status is excluded today by decision, not permanently — and during any rolling deploy the old bundle reads the new body. |
| Preconditions | User A signed in on `/projects`. |
| Test data | `/me` → `200 {"email": "qa.profile@textery.test", "name": "Анна Ковалёва", "created_at": "2025-02-03T10:15:00Z", "is_verified": true, "plan": "pro"}`. |
| Steps | 1. Load `/projects` with that stub.<br>2. Read the header identity, the avatar and the console.<br>3. Compare against a load with the three-field body. |
| Expected result | The header shows `Анна Ковалёва` and `АК`, byte-identical to the three-field run; no degraded state, no «Данные профиля недоступны», no console error — the extra keys are ignored, not treated as a malformed body. |
| Status | Not run |

### TC-13-UI-6.2 — «Выйти» works in every profile state

| Field | Value |
|---|---|
| Description | If the menu's contents are gated on a successful fetch, a `/me` outage traps the user in a session they cannot end. |
| Preconditions | User A signed in on `/projects`; the menu opened in each sub-step. |
| Test data | (a) `/me` delayed 10 s. (b) `/me` → `500`. (c) `/me` → `401 UNAUTHORIZED`. |
| Steps | 1. For each of (a), (b), (c): load `/projects`, open the avatar menu, confirm «Выйти» is present and enabled, click it.<br>2. After each click read the URL and `sessionStorage`. |
| Expected result | «Выйти» is offered and enabled in all three states; after each click the browser is on the sign-in route and the session key is gone from `sessionStorage`. |
| Status | Not run |

### TC-13-UI-6.3 — A failing profile read never signs the user out

| Field | Value |
|---|---|
| Description | The header fires this call on every authenticated page including at boot. Routing its failure through `performRenewal`'s catch turns a rolling-deploy blip into a mass sign-out plus the loss of typed-but-unsaved editor content. |
| Preconditions | User A signed in on `/projects` with a valid session in `sessionStorage`. |
| Test data | (a) `/me` → `500`. (b) `/me` never answers (request aborted at the client timeout). (c) `/me` → `401`, and the subsequent `POST /api/v1/auth/refresh` → `500`. |
| Steps | 1. Load `/projects` under (a); read `sessionStorage` and the URL.<br>2. Repeat under (b).<br>3. Repeat under (c). |
| Expected result | In all three the session key is still present in `sessionStorage`, `clearSession()` was not reached, and the URL is still `/projects` — never the sign-in route. The header shows the degraded identity in each. |
| Status | Not run |

### TC-13-UI-6.4 — One profile read per page, not one per header

| Field | Value |
|---|---|
| Description | `/me` becomes the highest-rate endpoint in the product; one request per mounted `ProfileMenu`, or one per in-app navigation, multiplies that rate directly. |
| Preconditions | A page mounting two `ProfileMenu` instances (desktop header + mobile drawer); user A signed in. |
| Test data | Request counter against the stubbed `GET /api/v1/auth/me`. |
| Steps | 1. Load the page; count `GET /api/v1/auth/me` requests.<br>2. Navigate in-app to `/profile` and back to `/projects`; count again. |
| Expected result | Step 1: exactly `1` request, with both menus mounted. Step 2: the total is still `1` — no further read on in-app navigation. |
| Status | Not run |

### TC-13-UI-6.5 — Both mounted menus agree in every state

| Field | Value |
|---|---|
| Description | With one shared fetch, two menus reading their own local state can diverge — one degraded, one still shimmering. |
| Preconditions | A page mounting two `ProfileMenu` instances; user A signed in; `/me` → `500`. |
| Test data | Both menus made visible simultaneously (wide viewport with the drawer forced open). |
| Steps | 1. Load the page with the failing `/me`.<br>2. Open both menus and read each one's identity text and avatar classes. |
| Expected result | Both read «Данные профиля недоступны» and both carry the dashed-outline degraded avatar class — identical text and identical class list. |
| Status | Not run |

### TC-13-UI-6.6 — A rename updates every mounted header without a reload

| Field | Value |
|---|---|
| Description | PATCH answers with the full profile precisely so no second `GET /me` is needed; a reload or a refetch here would defeat that. |
| Preconditions | User A on `/profile` with a second header mounted; `/me` count recorded after load. |
| Test data | Typed name `Анна Волкова`; `PATCH` → `200` with `"name": "Анна Волкова"`. |
| Steps | 1. Record the `/me` request count and the page's `performance.navigation` / load id.<br>2. Change the name to `Анна Волкова` and click «Сохранить».<br>3. Read both headers' identity text; re-read the `/me` count and the load id. |
| Expected result | Both headers show `Анна Волкова` and initials `АВ`; the load id is unchanged (no reload); the `/me` request count is unchanged from step 1. |
| Status | Not run |

### TC-13-UI-6.7 — The identity survives in-app navigation and is not refetched

| Field | Value |
|---|---|
| Description | An identity held only in the screen's local state is lost on navigation and the header falls back to the address, or refetches. |
| Preconditions | User A has just renamed themselves to `Анна Волкова` on `/profile`; `/me` request count recorded. |
| Test data | Navigate `/profile` → `/projects` → `/profile` via in-app links. |
| Steps | 1. Rename to `Анна Волкова`.<br>2. Click an in-app link to `/projects`; read the header identity and the `/me` count.<br>3. Navigate back to `/profile`; read the identity and the count. |
| Expected result | `Анна Волкова` is shown in both steps 2 and 3; the `/me` request count never increases beyond the single boot-time read. |
| Status | Not run |

### TC-13-UI-6.8 — Initials never split a character

| Field | Value |
|---|---|
| Description | `word[0]` slices UTF-16 code units and is safe only because email local parts are ASCII-ish. A name is not — an astral first character yields a lone surrogate rendered as U+FFFD. |
| Preconditions | User A signed in; `/me` stubbed with each name in turn. |
| Test data | (a) `name = "😀нна Ковалёва"` (astral first character). (b) `name = "Е́лена Ковалёва"` (base + combining acute first). |
| Steps | 1. Load `/projects` with name (a); read the avatar's rendered text.<br>2. Reload with name (b); read the avatar's rendered text. |
| Expected result | (a) the avatar shows `😀` as one whole grapheme (plus `К`), not a half-surrogate. (b) the avatar shows `Е́` with its combining mark intact. Neither renders `�` (U+FFFD). |
| Status | Not run |

---

## 7. Navigation and Unsaved Input

### TC-13-UI-7.1 — Leaving with a typed but unsaved name is guarded

| Field | Value |
|---|---|
| Description | The guard already exists for registration; reusing it unparameterized names the wrong screen in the prompt. |
| Preconditions | User A on `/profile` with `name = "Анна Ковалёва"` loaded. |
| Test data | Typed value `Анна Волкова`, not saved; in-app link to `/projects`. |
| Steps | 1. Change the field to `Анна Волкова` without saving.<br>2. Click the in-app «К проектам» link.<br>3. Read the confirmation prompt's text.<br>4. Choose the cancel option. |
| Expected result | A confirmation appears whose text refers to the profile screen / the unsaved name — not to the registration screen; after cancelling the URL is still `/profile` and the field still holds `Анна Волкова`. |
| Status | Not run |

### TC-13-UI-7.2 — A reload with a typed but unsaved name does not lose it silently

| Field | Value |
|---|---|
| Description | The in-app router guard does not fire on a browser reload; that needs `beforeunload`. |
| Preconditions | User A on `/profile` with `Анна Волкова` typed and unsaved. |
| Test data | Browser reload (F5). |
| Steps | 1. Type `Анна Волкова` without saving.<br>2. Trigger a page reload.<br>3. Observe the browser's leave-confirmation dialog. |
| Expected result | The browser's native "Leave site? Changes you made may not be saved" dialog is raised (a `beforeunload` handler is registered and returns a value); the reload does not proceed unattended. |
| Status | Not run |

### TC-13-UI-7.3 — A header profile failure mid-edit does not drop the typed name

| Field | Value |
|---|---|
| Description | The header's own `/me` refusal must not remount or clear the form the user is typing into. |
| Preconditions | User A on `/profile`, mid-edit with `Анна Волко` typed. |
| Test data | The header's background `GET /api/v1/auth/me` refetch stubbed to answer `401 UNAUTHORIZED`. |
| Steps | 1. Type `Анна Волко` into the field without saving.<br>2. Trigger the header's `/me` refetch, which answers `401`.<br>3. Read the field value, the URL and `sessionStorage`. |
| Expected result | The field still holds `Анна Волко`; the URL is still `/profile`; the session key is still in `sessionStorage` — no return to the sign-in screen. |
| Status | Not run |

### TC-13-UI-7.3a — Signing out with a typed but unsaved name is guarded like any other exit

| Field | Value |
|---|---|
| Description | «Выйти» is mounted on this page like every other, which makes it a third exit over the same dirty state. TC-13-UI-7.1 guards in-app navigation and 7.2 guards reload; TC-13-UI-6.2 pins that sign-out always works, and the two together currently imply silent loss. |
| Preconditions | User A on `/profile` with `Анна Волкова` typed and unsaved; a valid session in `sessionStorage`. |
| Test data | Menu item «Выйти»; cancel the confirmation. |
| Steps | 1. Type `Анна Волкова` without saving.<br>2. Open the avatar menu and choose «Выйти».<br>3. Read the confirmation prompt.<br>4. Cancel it; read the URL, the field value and `sessionStorage`. |
| Expected result | A confirmation is raised **before** the session ends; after cancelling the URL is `/profile`, the field still holds `Анна Волкова`, and the session key is still present in `sessionStorage` — untouched. |
| Status | Not run |

### TC-13-UI-7.3b — A save refused as unauthorized does not discard the typed name silently

| Field | Value |
|---|---|
| Description | TC-13-UI-6.3 deliberately keeps a failing **read** from ending the session; the write path is the one the interceptor still owns, and it is where typed text is standing on the screen. |
| Preconditions | User A on `/profile` with `Анна Волкова` typed; `PATCH /api/v1/auth/me` → `401`, and the subsequent `POST /api/v1/auth/refresh` → `500`. |
| Test data | Typed value `Анна Волкова`; refused save; failed renewal. |
| Steps | 1. Type `Анна Волкова` and click «Сохранить».<br>2. Observe the response to the `401` and the failed renewal.<br>3. Read what the user is shown and whether the typed value is recoverable. |
| Expected result | Either the typed value `Анна Волкова` is still available after the session ends (retained in storage or shown on the sign-in screen), **or** a message announces the loss before the session ends. An unannounced redirect to the sign-in screen with the field discarded fails this case. |
| Status | Not run |

### TC-13-UI-7.4 — Save and cancel are reached in that order by keyboard

| Field | Value |
|---|---|
| Description | On a narrow viewport the buttons stack, and a CSS reorder can make the reading order disagree with the visual order. |
| Preconditions | User A on `/profile`, viewport 375 × 812. |
| Test data | Buttons «Сохранить» and «Отмена»; `Tab` from the «Отображаемое имя» field. |
| Steps | 1. Set the viewport to 375 × 812 and focus the name field.<br>2. Press `Tab` and record `document.activeElement`.<br>3. Press `Tab` again and record it. |
| Expected result | The tab order matches the visual top-to-bottom order of the two buttons as rendered at 375 px — the first `Tab` focuses the visually-first button and the second `Tab` the visually-second one; no `tabindex` reorder makes them disagree. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `a signed-in user` | Session in `sessionStorage` + stubbed `GET /api/v1/auth/me` |
| `the profile screen` | Route `/profile` |
| `the avatar menu` | `ProfileMenu` in `AppHeader` |
| `the profile read` | `GET /api/v1/auth/me` from the shared identity fetch |
| `a rename` / `they save` | `PATCH /api/v1/auth/me` |
| `the bound` | 60 code points |
| `astral characters` | U+1F600 — `.length` counts 2 per character, the counter must not |
| `this product's date form` | `formatCardDate` (ru-RU genitive month, `—` on unparseable); test `TZ` pinned to a non-UTC zone |
| `the degraded identity` | Dashed-outline avatar state of `08-header-degraded.html`, asserted distinct from the loading placeholder |
| `nothing is reported as unsaved` | `useUnsavedGuard` dirty flag cleared, compared against the normalized server value |
| `they are asked to confirm leaving` | `useUnsavedGuard` `confirmLeave`, message parameterized per screen |
| `exactly one profile read is issued` | Request count against the stubbed endpoint, both `ProfileMenu` instances mounted |
| `the stored session survives` | `clearSession()` not reached; session key still present |
