> These are additional edge case tests. Implement after core tests pass.

# Profile management — Integration Tests (Extended)

No external service. These extend the internal browser-to-backend seam covered in the main
file.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Stack | browser → nginx (`infra/docker/nginx/frontend.conf`) → FastAPI → Postgres; entry point `app_url`, never `BACKEND_PORT` |
| Account A | `qa.integ13@textery.test` / `Qa!Integ2026` |
| Account B | `qa.integ13b@textery.test` / `Qa!Integ2026`, `name = "Иван Петров"` |
| Screen texts | «Мой профиль», «Отображаемое имя», «Сохранить», «Выйти» |
| Authenticated pages | `/projects`, `/profile`, a document page — all mount the header |
| Access-token TTL | 15 minutes; renewal via the refresh flow in `authorizedRequest.ts` |
| Test timezone | browser `TZ=Asia/Yekaterinburg` (UTC+5) unless the case pins another |

---

## 1. Multiple Surfaces on One Session

### TC-13-INT-1.1e — A rename in one tab is seen by another after it re-reads

| Field | Value |
|---|---|
| Description | Two tabs share one account and one backend; the second must eventually converge on the stored name rather than holding its boot-time snapshot forever. |
| Preconditions | Account A signed in through the application in tab 1 and tab 2, both showing `qa.integ13@textery.test` with no name. |
| Test data | Tab 1 saves `Мария Соколова`; tab 2 then performs a full page load of `/projects`. |
| Steps | 1. In tab 1, open `/profile`, save `Мария Соколова`, confirm `200`.<br>2. In tab 2, trigger a full page load of `/projects`.<br>3. Read tab 2's header identity and avatar. |
| Expected result | Tab 2's header shows `Мария Соколова` with initials `МС` after the load — not the address, not blank. |
| Status | Not run |

### TC-13-INT-1.1ae — The staleness window on another surface is the one this contract states

| Field | Value |
|---|---|
| Description | The identity snapshot is fetched once per page and never refreshed within it (main UI file TC-13-UI-6.4, 6.7), so a second surface is stale for an unbounded time by design. TC-13-INT-1.1e asserts only that it eventually catches up, which lets any lag pass; this names the single refresh point the design actually has. |
| Preconditions | Account A signed in in two tabs, both showing the address with no name. |
| Test data | Tab 1 saves `Мария Соколова`; tab 2 does in-app navigation first, then a full page load. |
| Steps | 1. Tab 1 saves `Мария Соколова`.<br>2. In tab 2, wait 30 s without navigating; read the header.<br>3. In tab 2, navigate in-app between authenticated routes; read the header after each.<br>4. In tab 2, perform a full page load; read the header.<br>5. Continue navigating in tab 2 in-app; read the header after each. |
| Expected result | Steps 2 and 3 may still show the address (the stale snapshot is permitted — no `/me` is re-issued on in-app navigation); step 4 shows `Мария Соколова`; step 5 shows `Мария Соколова` on every subsequent view — the previous identity never reappears after a full load. |
| Status | Not run |

### TC-13-INT-1.2e — Browser history navigation does not resurrect a stale identity

| Field | Value |
|---|---|
| Description | A bfcache-restored page or a history entry holding its own snapshot repaints the old identity on Back, which looks like the rename was undone. |
| Preconditions | Account A signed in through the application; renamed to `Мария Соколова` during this session; several authenticated pages visited after the rename. |
| Test data | History: `/projects` → `/profile` (rename) → `/projects` → a document page. Then `Back` ×2 and `Forward` ×2. |
| Steps | 1. Rename to `Мария Соколова` and visit two more authenticated pages.<br>2. Press the browser Back button twice, reading the header identity on each page.<br>3. Press Forward twice, reading the header identity on each page. |
| Expected result | Every page in steps 2 and 3 shows `Мария Соколова` with initials `МС`; no page reverts to `qa.integ13@textery.test` or to a blank identity, including a page restored from the back/forward cache. |
| Status | Not run |

---

## 2. Session Transitions Against a Live Backend

### TC-13-INT-2.1e — Signing in as another account replaces the identity everywhere

| Field | Value |
|---|---|
| Description | The snapshot must be tied to the session; a survivor across a sign-out/sign-in shows one account's identity to another user of the same machine. |
| Preconditions | Account A signed in through the application with `name = "Мария Соколова"`, `/profile` visited so the snapshot is populated; account B available with `name = "Иван Петров"`. |
| Test data | A (`qa.integ13@textery.test` / `Мария Соколова`) → B (`qa.integ13b@textery.test` / `Иван Петров`), same tab. |
| Steps | 1. As A, visit `/profile` and `/projects`.<br>2. Choose «Выйти»; sign in as B through the real form.<br>3. Read the header identity and the `/profile` screen as B.<br>4. Search the whole DOM and browser storage for A's address and name. |
| Expected result | The header and `/profile` both show `Иван Петров` / `qa.integ13b@textery.test` with initials `ИП`; `Мария Соколова` and `qa.integ13@textery.test` appear nowhere in the DOM and in no storage value. |
| Status | Not run |

### TC-13-INT-2.2e — An expired access token is renewed without disturbing the identity

| Field | Value |
|---|---|
| Description | The boot `/me` fires before the user touches anything, so an expired token at that moment must renew silently — not surface as a degraded header and not end the session. |
| Preconditions | Account A signed in through the application with `name = "Мария Соколова"`; its access token expired (clock advanced past the 15-minute TTL) while the refresh token is still valid. |
| Test data | Expired access token; valid refresh token; page `/projects`. |
| Steps | 1. Expire the access token.<br>2. Load `/projects`; observe the `/me` call, the `401`, and the refresh call.<br>3. Read the header identity, the URL and `sessionStorage`. |
| Expected result | The refresh flow issues `POST /api/v1/auth/refresh`, receives new tokens, and the retried `GET /api/v1/auth/me` answers `200`; the header shows `Мария Соколова`; the URL is still `/projects` and the session key is still present — no return to the sign-in screen and no degraded identity left on screen. |
| Status | Not run |

---

## 3. Registration Date End to End

### TC-13-INT-3.1e — The date shown is the instant the account was created

| Field | Value |
|---|---|
| Description | The instant crosses registration, the column, the serializer and the browser formatter; only the whole trip catches a shift introduced by any one of them. |
| Preconditions | The full stack up; the browser at `TZ=Asia/Yekaterinburg` (UTC+5). |
| Test data | Register `qa.datestamp@textery.test` / `Qa!Date2026` at a recorded instant, e.g. `2026-08-20T18:40:00Z` (which is `2026-08-20 23:40` local, same calendar day). |
| Steps | 1. Record the wall-clock UTC instant; register and verify the account through the application.<br>2. Read the stored `created_at` directly from `accounts`.<br>3. `GET /api/v1/auth/me` directly and read `created_at`.<br>4. Open `/profile` in the UTC+5 browser and read the registration row. |
| Expected result | The stored `created_at` matches the recorded instant to the second; step 3 returns it as `"2026-08-20T18:40:00Z"`; step 4 reads «На Textery с 20 августа 2026» — the local calendar date of that instant, with its year. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `signed in through the application` | Selenium drives the real sign-in flow against the acceptance stack |
| `an authenticated page` | Any route behind the session guard, all of which mount the header |
| `the session is renewed` | Refresh flow in `authorizedRequest.ts` |
| `a timezone other than UTC` | Browser/session `TZ` pinned away from UTC |
