# Profile management — Integration Tests

**No external service is involved.** The seam this story creates is internal and new: the
application shell gains a hard dependency on a backend route that did not exist, on every
authenticated page. Before this story a profile-endpoint outage was not a concept; after it,
one degrades the whole authenticated shell at once
(`13_ProfileManagement_Notes.md` § Integration Notes). These scenarios exercise the browser
against a live backend through the real origin — not stubs.

Shared test data for every case below, unless the case names its own:

| Name | Value |
|---|---|
| Stack | browser → nginx (`infra/docker/nginx/frontend.conf`) → FastAPI → Postgres; entry point `app_url`, never `BACKEND_PORT` |
| Account A | `qa.integ13@textery.test` / `Qa!Integ2026`, registered and verified through the real sign-in flow |
| Account B | `qa.integ13b@textery.test` / `Qa!Integ2026`, `name = "Иван Петров"` |
| Screen texts | «Мой профиль», «Отображаемое имя», «Сохранить», «Отмена», «Повторить» |
| Degraded texts | header «Данные профиля недоступны»; screen «Не удалось загрузить профиль» |
| Canonical failure form | `{"error_code": "<CODE>", "message": "<generic text>"}` |
| Name bound | 60 code points after trim + NFC |
| Body cap | 2 MiB in the app; nginx `client_max_body_size` set above it |
| Client bounded wait | the shared profile fetch's timeout (expected `<= 10 s`) |

---

## 1. The Screen Against a Live Backend

### TC-13-INT-1.1 — A name saved in the browser is the name the backend stored

| Field | Value |
|---|---|
| Description | The end-to-end proof that the screen, the route, the domain and the column agree — a normalization or trim mismatch anywhere shows here and nowhere in the unit suites. |
| Preconditions | Account A registered and verified; signed in through the real sign-in form at `app_url`; no name set. |
| Test data | Typed name `Мария Соколова`. |
| Steps | 1. Open the avatar menu, choose «Мой профиль».<br>2. Type `Мария Соколова` into «Отображаемое имя»; click «Сохранить».<br>3. Read the screen identity and the header.<br>4. `GET /api/v1/auth/me` directly with account A's token.<br>5. Close the browser session, sign in again in a fresh session, read the header. |
| Expected result | Step 3: the screen and header both show `Мария Соколова`, avatar `МС`. Step 4: `200` with `"name": "Мария Соколова"`. Step 5: the header shows `Мария Соколова` on first paint after sign-in. |
| Status | Not run |

### TC-13-INT-1.2 — A name with astral characters survives the whole round trip

| Field | Value |
|---|---|
| Description | The counter, the domain bound and the column each count a different unit if anyone gets it wrong; only the whole round trip catches a mismatch between them. |
| Preconditions | Account A signed in through the application, on `/profile`. |
| Test data | `"😀" × 60` — 60 code points, 120 UTF-16 units, 240 UTF-8 bytes. |
| Steps | 1. Paste `"😀" × 60` into «Отображаемое имя»; confirm the counter reads `60 / 60` and «Сохранить» is enabled.<br>2. Click «Сохранить».<br>3. Read the screen identity and the header text.<br>4. `GET /api/v1/auth/me` directly and compare the returned `name` code point by code point. |
| Expected result | The save answers `200`; the screen and header show all 60 emoji with no `�` (U+FFFD) and no truncation; step 4's `name` is exactly `"😀" × 60`, 60 code points long. |
| Status | Not run |

### TC-13-INT-1.3 — Clearing a name in the browser clears it in the backend

| Field | Value |
|---|---|
| Description | The clearing path across the full stack — an empty field must reach the column as `NULL`, not `''`. |
| Preconditions | Account A signed in through the application with `name = "Мария Соколова"`, on `/profile`. |
| Test data | Empty the field, then save. |
| Steps | 1. Select all in «Отображаемое имя» and delete; click «Сохранить».<br>2. Read the screen identity, the screen avatar and the header avatar.<br>3. `GET /api/v1/auth/me` directly. |
| Expected result | Step 2: the screen and header both show `qa.integ13@textery.test` with initials derived from the address, never a blank circle and never the stale `МС`. Step 3: `200` with `"name": null` — the key present, value `null`. |
| Status | Not run |

### TC-13-INT-1.4 — An oversized save is refused through the origin the browser uses

| Field | Value |
|---|---|
| Description | The proxy in front of the API answers its own HTML page if its cap is not set above the app's — a backend-port test goes green on a path no user takes. |
| Preconditions | The full stack up with nginx `client_max_body_size` above the 2 MiB app cap; account A signed in through the application, on `/profile`. |
| Test data | A `PATCH <app_url>/api/v1/auth/me` body of 10 MiB, issued from the page's own origin. |
| Steps | 1. From the browser, trigger a save whose body is 10 MiB (a pasted 10 MiB value, or the same request issued from page script).<br>2. Read the response status, `Content-Type` and body.<br>3. Read the screen. |
| Expected result | `413` with `Content-Type: application/json` and body `{"error_code": "REQUEST_BODY_TOO_LARGE", "message": …}` — not nginx's `text/html` `413 Request Entity Too Large` page; the screen shows the failed-save banner with the typed value intact, not a blank card. |
| Status | Not run |

---

## 2. Ordering Across the Seam

### TC-13-INT-2.1 — A stale profile read never overwrites a completed rename

| Field | Value |
|---|---|
| Description | The boot-time `/me` and a rename race on every visit to the screen; the read losing to the write is the only correct outcome. |
| Preconditions | Account A signed in with `name = "Мария Соколова"`; the boot `GET /api/v1/auth/me` held open at the proxy so it has not answered. |
| Test data | Held read returns `"name": "Мария Соколова"`; the rename sets `Мария Волкова`. |
| Steps | 1. Load `/profile` with the `/me` response held.<br>2. Save the name `Мария Волкова`; let the `PATCH` complete.<br>3. Read the header and screen identity.<br>4. Release the held `/me` response (carrying the old name).<br>5. Read the header and screen identity again. |
| Expected result | Step 3 and step 5 both show `Мария Волкова` — the released stale read never repaints the header or the field back to `Мария Соколова`. |
| Status | Not run |

### TC-13-INT-2.2 — An out-of-order rename response never wins

| Field | Value |
|---|---|
| Description | Two saves in flight and the responses returning reversed is the classic last-response-wins defect; the last *request* must win, not the last response. |
| Preconditions | Account A signed in on `/profile`; the proxy able to hold and release each `PATCH` response independently. |
| Test data | Save 1 → `Мария Волкова` (response held). Save 2 → `Мария Орлова` (response released first). |
| Steps | 1. Save `Мария Волкова`; hold its response.<br>2. Save `Мария Орлова`; release its response first.<br>3. Read the screen and header.<br>4. Release save 1's response.<br>5. Read the screen and header again. |
| Expected result | Step 3 shows `Мария Орлова`; step 5 still shows `Мария Орлова` — save 1's late response does not repaint it to `Мария Волкова`. |
| Status | Not run |

### TC-13-INT-2.2a — A superseded profile read never repaints the header

| Field | Value |
|---|---|
| Description | Every other ordering scenario pairs a read with a write, a write with a write, or a read across a session boundary. Read-versus-read is created by this spec's own retry paths and is the case where a stale or degraded result repaints a healthy header. |
| Preconditions | Account A signed in with `name = "Мария Волкова"`; the first `GET /api/v1/auth/me` held open at the proxy. |
| Test data | Held read returns the stale `"name": "Мария Соколова"`; the retry returns `"name": "Мария Волкова"`. Run twice: once with a user-triggered «Повторить», once with the automatic retry policy. |
| Steps | 1. Load `/projects` with the first `/me` held.<br>2. Trigger the retry (user-initiated, then in a second run the automatic policy); let it answer first with `Мария Волкова`.<br>3. Read the header and, on `/profile`, the screen identity.<br>4. Release the first, superseded read carrying `Мария Соколова`.<br>5. Read both again. |
| Expected result | Steps 3 and 5 both show `Мария Волкова` in the header and on the screen, in both runs — the superseded read is discarded, never painted. |
| Status | Not run |

### TC-13-INT-2.3 — An identity from a superseded session is dropped

| Field | Value |
|---|---|
| Description | A cross-account identity leak across a sign-out boundary — strictly worse than a stale name. |
| Preconditions | Account A signed in with the boot `GET /api/v1/auth/me` held open; account B available. |
| Test data | Held read carries account A (`qa.integ13@textery.test`); account B (`qa.integ13b@textery.test` / `Иван Петров`). |
| Steps | 1. Sign in as A with the `/me` held.<br>2. Sign out; sign in as B in the same tab.<br>3. Read the header identity.<br>4. Release A's held `/me` response.<br>5. Read the header and search the DOM for A's address. |
| Expected result | Steps 3 and 5 both show `Иван Петров` / `qa.integ13b@textery.test`; `qa.integ13@textery.test` appears nowhere in the DOM at any point after the switch. |
| Status | Not run |

---

## 3. Degradation of the Seam

### TC-13-INT-3.1 — A failing profile endpoint degrades the shell without ending the session

| Field | Value |
|---|---|
| Description | An outage of this one route must not become a fleet-wide sign-out. The session may only end when the user ends it. |
| Preconditions | Account A signed in through the application; `GET /api/v1/auth/me` then made to answer `500` for every call. |
| Test data | `/me` → `500 {"error_code": "INTERNAL_ERROR", …}`; pages `/projects`, `/profile`, and one document page. |
| Steps | 1. With `/me` failing, navigate to each of the three pages.<br>2. On each, read the header identity and confirm the page body rendered.<br>3. Read `sessionStorage` after each navigation.<br>4. Open the avatar menu and choose «Выйти». |
| Expected result | Every page renders with «Данные профиля недоступны» in the header and its own content present (not a blank shell); the session key is still in `sessionStorage` throughout — `clearSession()` never reached; step 4 ends the session and lands on the sign-in route. |
| Status | Not run |

### TC-13-INT-3.2 — A slow profile endpoint is abandoned rather than waited on forever

| Field | Value |
|---|---|
| Description | Without a bounded wait the header shimmers forever and the user has no identity and no failure to act on. |
| Preconditions | Account A signed in; `GET /api/v1/auth/me` held open indefinitely at the proxy (connection accepted, never answered). |
| Test data | Client bounded wait (expected `<= 10 s`); stopwatch started at page load. |
| Steps | 1. Load `/projects` with `/me` held indefinitely.<br>2. Start a stopwatch; watch the header state.<br>3. Record the moment the shimmer placeholder is replaced and by what. |
| Expected result | Within the client's bounded wait (`<= 10 s`) the request is aborted and the header switches to the degraded identity «Данные профиля недоступны» with the dashed-outline avatar; the loading shimmer is gone — it does not persist past the timeout. |
| Status | Not run |

### TC-13-INT-3.3 — Retries after an outage are capped and spread out

| Field | Value |
|---|---|
| Description | Every open tab in the fleet re-reads this endpoint at boot, so retries in lockstep after a rolling deploy are a self-inflicted load spike on the endpoint that just came back. |
| Preconditions | Account A signed in; `GET /api/v1/auth/me` answering `503` for the first N calls, then `200`. |
| Test data | `/me` → `503` × 10, then `200` with `"name": "Мария Соколова"`; the request timestamps recorded; three browser instances loaded simultaneously. |
| Steps | 1. Load the page with `/me` failing; record every `/me` request timestamp until the client stops.<br>2. Compute the gaps between successive attempts.<br>3. Load three instances at the same instant and compare their attempt timestamps.<br>4. Restore `/me` to `200` and observe the identity. |
| Expected result | The attempt count is bounded (it stops at the configured cap, it does not retry indefinitely); successive gaps grow (each at least the previous, e.g. ~1 s → 2 s → 4 s); the three instances' attempt timestamps are **not** aligned — jitter separates them by a measurable margin; after step 4 the header shows `Мария Соколова` without a manual reload. |
| Status | Not run |

### TC-13-INT-3.3a — A save is never re-sent on its own, and a manual retry stores one name

| Field | Value |
|---|---|
| Description | The read's retry policy must not extend to the write. This is the direction the re-run guards in the API file do not reach: they cover a duplicate the caller sends deliberately, not one a client policy sends on its behalf after an ambiguous outcome. |
| Preconditions | Account A signed in on `/profile`; `PATCH /api/v1/auth/me` made to commit server-side but its response withheld past the client's bounded wait. |
| Test data | Typed name `Мария Волкова`; the `PATCH` request counter at the proxy. |
| Steps | 1. Save `Мария Волкова`; withhold the response until the client's bounded wait elapses.<br>2. Count `PATCH /api/v1/auth/me` requests reaching the backend.<br>3. Read the screen and the field value.<br>4. Click the retry affordance; let it succeed.<br>5. `GET /api/v1/auth/me` directly and `SELECT count(*) FROM accounts WHERE email = 'qa.integ13@textery.test'`. |
| Expected result | Step 2: exactly `1` `PATCH` — no automatic re-send. Step 3: the failed-save banner with `Мария Волкова` still in the field. Step 5: the profile reports `"name": "Мария Волкова"` and the account row count is exactly `1`. |
| Status | Not run |

### TC-13-INT-3.3b — A save the client abandons does not leave the screen lying

| Field | Value |
|---|---|
| Description | The screen must never assert a value the server did not store — nor keep asserting a value after the server stored a different one. |
| Preconditions | Account A signed in on `/profile` with `name = "Мария Соколова"`; the `PATCH` response delayed past the client's bounded wait while the server commits `Мария Волкова`. |
| Test data | Typed name `Мария Волкова`; the abandoned request observed at the proxy. |
| Steps | 1. Save `Мария Волкова`; let the client's bounded wait elapse.<br>2. Observe at the proxy whether the client's connection was closed/aborted.<br>3. Read what identity the screen and header claim.<br>4. Trigger the next profile read (navigate away and back, or «Повторить»).<br>5. Read the screen and header again, and `GET /api/v1/auth/me` directly. |
| Expected result | Step 2: the abandoned request is cancelled at the client (connection aborted), not left hanging. Step 3: the header shows the failed/degraded state or the last known stored value — it does not display `Мария Волкова` as if saved. Step 5: after reconciliation both show `Мария Волкова`, matching the direct `GET`'s `"name": "Мария Волкова"`. |
| Status | Not run |

### TC-13-INT-3.3c — A non-JSON answer from the proxy degrades rather than breaks

| Field | Value |
|---|---|
| Description | TC-13-INT-3.4 covers a body that is valid JSON with fields missing. The proxy's own 502 and 504 pages during a rolling deploy are not JSON at all, and that is the shape the whole fleet sees at once. |
| Preconditions | Account A signed in; the backend stopped so nginx answers `/api/v1/auth/me` from its own error pages. |
| Test data | `502 Bad Gateway` and `504 Gateway Time-out`, `Content-Type: text/html`, nginx's default body. |
| Steps | 1. Stop the backend; load `/projects`.<br>2. Read the header and confirm the page body rendered; check the console for an uncaught exception.<br>3. Repeat with the `504` page.<br>4. Open the avatar menu and choose «Выйти». |
| Expected result | Both cases render every page with «Данные профиля недоступны» in the header; the console shows no uncaught `SyntaxError: Unexpected token '<'` or similar parse failure escaping into the shell; step 4 ends the session and lands on the sign-in route. |
| Status | Not run |

### TC-13-INT-3.4 — A malformed profile body does not break the shell

| Field | Value |
|---|---|
| Description | A `200` with fields missing is what a partial rollout or a proxy rewrite can produce; `undefined` reaching the initials blanks the identity or throws. |
| Preconditions | Account A signed in; `GET /api/v1/auth/me` made to answer `200 {}` and then `200 {"email": null, "created_at": null}`. |
| Test data | Bodies `{}` and `{"email": null, "name": null, "created_at": null}`. |
| Steps | 1. Load `/projects` with body `{}`; read the header, the avatar text and its `aria-label`; check the console.<br>2. Repeat with the all-null body.<br>3. Open the avatar menu and choose «Выйти». |
| Expected result | Both cases render the page with a defined header state; the avatar text contains no `undefined`, `null` or `NaN` and the `aria-label` does not end in the bare «Меню профиля: »; no uncaught exception in the console; step 3 ends the session and lands on the sign-in route. |
| Status | Not run |

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `signed in through the application` | Selenium drives the real sign-in flow; no injected session |
| `against a live backend` | Acceptance stack: browser → nginx → FastAPI → Postgres |
| `the application's origin` | `app_url` (through `infra/docker/nginx/frontend.conf`), never `BACKEND_PORT` |
| `reading the profile back from the backend` | Direct `GET /api/v1/auth/me` with the same account's token |
| `the profile read is held open` | Response delayed at the test double / proxy until released |
| `the bound` | 60 code points |
| `astral characters` | U+1F600 — 1 code point, 2 UTF-16 units, 4 UTF-8 bytes |
| `this product's canonical failure form` | `{"error_code": …, "message": …}` |
| `its bounded wait` | The client-side timeout on the shared profile fetch |
| `the stored session survives` | Session key still present; `clearSession()` not reached |
