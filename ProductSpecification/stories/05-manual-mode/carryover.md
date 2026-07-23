## Quirk: flex containers break Selenium text assertions

**Quirk:** `display: flex` on a container whose children are meant to read as one continuous line makes the browser's innerText/Selenium `.text` insert a newline between every flex item, even though visually they render side by side.
**Where:** Was in `ManualEditor.css` (`.me-breadcrumb-chips`, `.me-breadcrumb-chip`); fixed by switching to `inline-block` + `white-space: nowrap` with `vertical-align`/`margin` for icon alignment instead of `gap`.
**Implication:** Any future breadcrumb-style or inline-badge component whose text is asserted via Selenium `.text` must avoid `flex`/`inline-flex` on the text-bearing container — use inline-block/vertical-align instead, or normalize whitespace in the Statements assertion.
**From:** scenario 1.2 (manual-editor-opens)

## Quirk: save-error banner falsely claims local persistence

**Quirk:** The inline save-error banner text claims "введённый текст сохранён локально в редакторе" (entered text is saved locally), but no localStorage/sessionStorage/IndexedDB persistence exists anywhere in the manual-mode feature — content only survives in in-memory Tiptap/React state.
**Where:** `ManualEditor.tsx`'s `SAVE_ERROR_MESSAGE` constant, mockup `06-editor-error.html:85`.
**Implication:** A refresh, tab close, or navigation after a failed save loses content the banner claims is safe. Scenario 6.2 (reopening a saved document) and any future persistence/offline work should treat this as an open, unresolved BLOCK-severity gap rather than a resolved one.
**From:** scenario 5.2 (failed-save-inline-error)

## Quirk: save rejections carry no distinguishable status/kind

**Quirk:** `saveDocument`'s rejection is a plain `Error` with only a message string — no HTTP status code or error kind is attached.
**Where:** `frontend/src/features/generation/api/httpClient.ts`'s `request()`/`readErrorMessage()`, consumed by `documentApi.ts`'s `saveDocument`.
**Implication:** `ManualEditor` cannot distinguish a 409 version-conflict from a network failure or a 500 today. Any scenario needing conflict-specific UX (reload-and-merge prompts, distinguishing retryable vs. fatal errors) must first extend `saveDocument`/`request()` to propagate a status/kind.
**From:** scenario 5.2 (failed-save-inline-error)

## Quirk: StarterKit's Heading node silently competes with Heading3Mark

**Quirk:** StarterKit's built-in `Heading` node stays enabled, so its `parseHTML` competes with `Heading3Mark`'s rule for `<h3>`; neither declares a priority and both render byte-identical output.
**Where:** `ManualEditor.tsx:95-102` (StarterKit config, `Document.extend({ content: 'inline*' })`), `lineWrapMark.ts:21`.
**Implication:** The mark wins only because the `inline*` doc schema makes the block node unreachable — an implicit tiebreak that flips silently if the schema ever gains block content. The H1/H2 toolbar buttons are already inert for this reason. Any scenario adding block content to the doc, or wiring up H1/H2, must make the tiebreak explicit (disable `heading` in StarterKit, or declare a priority).
**From:** scenario 7.6 (h3-heading-active-toolbar)

## Quirk: line coverage cannot see a mark's parseHTML round-trip

**Quirk:** A mark whose `parseHTML` returns a bare tag rule (`{ tag: 'h3' }`) reports 100% line/branch coverage while nothing verifies that saved content round-trips — the rule is declarative data, so its hits are schema-build time, not document-parse time.
**Where:** `lineWrapMark.ts`-derived marks (`heading3Mark.ts`, `blockquoteMark.ts`); contrast `codeBlockMark.ts:23`, whose `getAttrs` arrow *is* code and so was correctly flagged uncovered in 7.4.
**Implication:** Coverage numbers are not evidence for or against a round-trip — `<pre>` broke silently in 7.4 at 100%. Every mark needs an explicit `*.parseHTML.test.tsx` round-trip test. `blockquoteMark.ts` still has none (belongs to 7.2), and strike's is missing too (7.1).
**From:** scenario 7.6 (h3-heading-active-toolbar)

## Quirk: `tsc --noEmit` checks NOTHING in this repo

**Quirk:** The root `tsconfig.json` is `{ "files": [], "references": [...] }`. Without `-b`, the compiler resolves **zero files** and exits 0. Every "tsc clean" claim made with `npx tsc --noEmit` is vacuous — including several recorded in `progress-frontend.md` above.
**Where:** `frontend/tsconfig.json`. The correct commands already exist and are correct: `npm run typecheck` (`tsc -b --noEmit`) and `npm run build` (`tsc -b && vite build`). The tooling was never the problem; bypassing it was.
**Implication:** Never invoke `tsc` directly. Vitest sees no type errors either (esbuild strips types without checking), so a broken build is invisible from both directions. This hid 7 real errors that made `npm run build` exit 2 on a merged branch.
**From:** the Story 7 auth merge (2026-07-17)

## Quirk: CI never runs on feature branches

**Quirk:** `frontend-ci.yml` triggers on `push` to `[main, dev]` and on `pull_request`. Feature branches are neither, and `.claude/rules/workflow.md` says the project does **not** use PRs — so the four gates (lint / typecheck / test / build) fire for nobody until something reaches main.
**Where:** `.github/workflows/frontend-ci.yml`.
**Implication:** A broken build can ride a feature branch indefinitely and surface only at merge. The gates are correct and complete; only the trigger is unreachable. Proposed and not yet done: add `feature/**` to the push trigger.
**From:** repairing the merged branch's build (2026-07-17)

## Quirk: a dead vite leaves a fully working app in the tab

**Quirk:** A tab loaded from one worktree's dev server keeps working after that server dies — React lives in memory, so clicking through modals is pure client state and needs no network. API calls still succeed (the backend is a separate process), so the app looks healthy while rendering a bundle from another branch entirely.
**Where:** Cost a full diagnostic round. Symptom: the user saw `Создание документа` with a "скоро" pill on Ручной режим — copy that exists on `feature/07-authorization-frontend` and **in no revision of this branch**, while the backend log showed their logins and generations succeeding.
**Implication:** When a reported UI contradicts the code, grep the reported *strings* against the tree before theorising about caches. A string that exists in no revision of your branch identifies the other worktree immediately. `git log -S "<their string>" --all` is the decisive command.
**From:** the first live-build hand-off (2026-07-17)

## Quirk: Windows shell mangles Cyrillic and appends \r — three near-miss bug reports

**Quirk:** Three separate false backend defects were nearly filed, all shell artifacts: (1) `python -c "print(...)"` appends `\r`, so a verification code piped through it reaches the API as `120358\r` → `INVALID_OR_EXPIRED_CODE`; (2) Cyrillic in a `curl -d '...'` argument is mangled → 400 "error parsing the body"; (3) `python -m json.tool` reads stdin as cp1251, rendering a correct UTF-8 `доклад` as `РґРѕРєР»Р°Рґ`.
**Where:** Every curl probe against the live stack from Git Bash on Windows.
**Implication:** Send non-ASCII bodies from a **file** (`--data-binary "@file.json"` written via Python's `.encode('utf-8')`), pipe through `tr -d '\r'`, and check raw bytes with `od -c` before believing an encoding bug. All three read exactly like backend defects.
**From:** docking to the live backend (2026-07-17)

## Quirk: sessionStorage is per-tab — a new tab is an anonymous visitor

**Quirk:** The session lives in `sessionStorage` (a recorded 2026-07-16 decision: a stolen token dies with the tab). The cost is that opening the app in a **new tab** signs you out — no "Мои работы", and the CTA routes to `/register`.
**Where:** `features/auth/utils/authSession.ts`.
**Implication:** Not a bug, but the first thing to check when someone reports "the signed-in UI is missing". Anyone handed a link must log in **in that tab**. Revisit if the sign-in friction outweighs the token-lifetime argument — that trade is the product owner's, not the code's.
**From:** the first live-build hand-off (2026-07-17)

## Quirk: a green suite is not evidence — the measured examples

**Quirk:** Three times this story a fully green suite coexisted with the live defect it was supposed to guard. (1) The minimal green for the docking work passed **93/93** with both defects shipping, because the contract tests supply the idempotency key themselves and nothing constrained the caller. (2) With that fixed, replacing the key ref with an inline `crypto.randomUUID()` still passed **190/190** — the required parameter closes the keyless call structurally but cannot stop a fresh key at the call site. (3) `jsdom` reports every CSS rule as working; it has no layout engine.
**Where:** `useDocumentInit.strictMode.test.tsx` exists solely to close (2), and kills that mutant with `expected 2 to be 1`.
**Implication:** For anything with a live surface, the order is: mutate the fix and watch the tests fail, then drive the real thing. Neither step is ceremony. Both caught defects here that the suite could not.
**From:** docking + history + mobile (2026-07-17)

## Codebase Quirk: jsdom needs a geometry polyfill for editor pointer events
**Quirk:** ProseMirror's mousedown coordinate math throws in jsdom (no `elementFromPoint`/`getClientRects`); any test dispatching a real pointer event into the editor DOM depends on the zero-geometry stub in `src/test/setup.ts`.
**Where:** `frontend/src/test/setup.ts`.
**Implication:** Stub is suite-global — a future test asserting real layout gets a silent zero-rect false-green, not a throw; scope per-file if layout matters. Correlates with an intermittent cross-file `act()` state leak at `ManualEditor.tsx:50`.
**From:** scenario 7.9 (link-active-toolbar)

## Decision: `\p{C}` reject coverage is bounded per-sub-category, not per-codepoint
**Decision:** The link-URL control-char reject tests pin one representative per security-relevant C sub-category (Cf, Cc), not every member; the live `/\p{C}/u` screen is the real guard and already rejects unpinned siblings.
**Where applied:** `normalizeHref.ts:50` + `ManualEditor.link.urlShapes.output.test.tsx` GROUPs 5-6; a hard bidi guarantee needs a structural range screen, not more member fixtures.
**From:** scenario 7.9 (link-active-toolbar)

## Quirk: a seeded token is not enough for API-calling screens; mint a real session
**Quirk:** A seeded sessionStorage token reaches the type/mode modals (no request can reject it) but any screen that calls the API on mount/submit 401s on it — `createDocument`, the generation POST — after which the client clears the session and the app collapses to the landing.
**Where:** `acceptance/statements/frontend/live_auth_session.py` (`issue_live_session`: register→verify→login over HTTP, code from the register response body) + `base_frontend_statements.py`'s `live_session` flag threaded through `navigate_to_doklad_type_modal`.
**Implication:** every future Selenium flow that lands on an API-calling screen must pass `live_session=True`; the cheap seeded path is valid only up to the last purely-client screen.
**From:** scenario 1.2 (manual-editor-opens)

## Quirk: the empty-editor placeholder renders nowhere (open real defect)
**Quirk:** A freshly created manual document shows no placeholder at all — the content area is exactly `<br class="ProseMirror-trailingBreak">`, with no `.me-placeholder` element and no `data-placeholder` attribute.
**Where:** `ManualEditor.tsx` (`Placeholder.configure(...)` over a `Document.extend({ content: 'inline*' })` schema); `.me-placeholder` lives only in `ManualEditor.css` and nothing renders it.
**Implication:** Tiptap's `Placeholder` decorates an empty NODE and the inline-only schema has no paragraph node to carry it, so it silently no-ops. Scenario 2.1's `green-selenium` is skipped on this; fixing it needs a node the decoration can attach to (or a different placeholder mechanism). No jsdom test asserts the placeholder, so the suite is green over the gap.
**From:** scenario 2.1 (empty-editor)

## Quirk: a WebDriver click re-places the caret in the contenteditable
**Quirk:** `send_keys` after a `click()` on the editor types at the pointer's landing position, not at the logical end of prior input — so a click between keystrokes moves the caret and the continuation lands in the wrong place (`foobar<br>` instead of `foo<br>bar`).
**Where:** `acceptance/statements/frontend/generation/manual_editor_line_break_statements.py` (`continue_typing_in_editor` types with no click; `type_text_in_editor` clicks to focus).
**Implication:** a multi-keystroke Selenium sequence must click ONCE to focus, then keep typing without re-clicking; jsdom line-break tests also cannot be trusted for trailing-Enter counts (jsdom collapses consecutive trailing Enters that a real browser keeps).
**From:** scenario 3.3 (line-break)
