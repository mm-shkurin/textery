## green-selenium (2026-07-14)

**Quirk:** `display: flex` on a container whose children are meant to read as one continuous line (here `.me-breadcrumb-chips` wrapping two chips + separator, and each `.me-breadcrumb-chip` wrapping an icon + label) makes the browser's innerText/Selenium `.text` insert a newline between every flex item, even though visually they render side by side.
**Where:** `ManualEditor.css` — `.me-breadcrumb-chips` and `.me-breadcrumb-chip` were `display: flex`/`inline-flex`; changed to `inline-block` + `white-space: nowrap` with `vertical-align`/`margin` for icon alignment instead of `gap`.
**Implication:** Any future breadcrumb-style or inline-badge component whose text is asserted via Selenium `.text` must avoid `flex`/`inline-flex` on the text-bearing container — use inline-block/vertical-align instead, or normalize whitespace in the Statements assertion.

## green-selenium (2026-07-22)

**Quirk:** a seeded sessionStorage token is enough for a purely client-side screen (type/mode modals send no request that could reject it) but NOT for any screen that calls the API on mount/submit — the editor's `createDocument` 401s on a fake token, the client clears the session, and the app collapses to the landing.
**Where:** `acceptance/statements/frontend/base_frontend_statements.py` (`_establish_logged_in_precondition`, `live_session` flag) + `live_auth_session.py` (`issue_live_session`: real register→verify→login over HTTP, code read from the register response body since the email adapter is mocked).
**Implication:** any future Selenium flow that reaches an API-calling screen must pass `live_session=True` to mint a real backend-issued JWT; the seeded path is valid only up to the last purely-client screen.
