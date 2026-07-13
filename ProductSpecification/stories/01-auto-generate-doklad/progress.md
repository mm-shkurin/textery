# Story 1: Auto-generate: доклад — Progress

**Split 2026-07-13** (Phase 6 of `_project_audit/CLEANUP_PLAN.md`, two people working
this story in parallel): the per-scenario checklists moved out to
`progress-backend.md` (Backend + Integration + Security + Load + Infrastructure
Scenarios, acceptance steps included inline) and `progress-frontend.md` (Frontend
Scenarios). This file keeps the story-level narrative, decisions, and the Spec
checklist — the shared context that doesn't belong to one person's file.
`ProductSpecification/stories.md` remains the single cross-file progress rollup.

## Priority for Sprint 1 (decided 2026-07-07 — see .memory-bank/tasks/sprint-plan.md)

67 scenarios / 424 steps is far more than fits before Friday's deploy deadline. Work
these **P0** scenarios first, in this order — they're the walking skeleton that makes
the product actually work end-to-end and unblocks frontend integration. Branch:
`features/story-1-auto-generate-doklad`, PR into `dev` once P0 is green and deployed.

- [x] **P0-1** — Backend 1.1: Reject request with missing topic (all steps done through `green-acceptance`, see `decisions/request-validation-architecture-decision.md`)
- [x] **P0-2** — Backend 1.2: Reject request with out-of-range volume
- [x] **P0-3** — Backend 2.1: Valid request is accepted and queued without waiting on the LLM call — originally built off-framework (`evening-demo-backend-plan.md` + known-debt #10), fully backfilled 2026-07-10: usecase (pre-existing), DB storage adapter, REST adapter (with a real DTO-shape fix — `GenerationCreatedDto` was missing the echoed fields the original red-acceptance test expected), and green-acceptance (real backend, 4/4 passing). Queue adapter stays `[S]` — `NoOpGenerationQueue` is a deliberate known-debt no-op, nothing to test.
- [x] **P0-4** — Backend 4.1: A pending generation reports its status without document content — usecase-layer coverage backfilled 2026-07-10 (`test_generation_lifecycle_usecase.py`), verified genuinely red against a `NotImplementedError` stub first
- [x] **P0-5** — Backend 4.2: A completed generation includes the document content — same backfill pass, same file
- [S] **P0-6** — Integration 1.1: A successful provider call produces a completed document — verified manually end-to-end against real GigaChat, no automated integration test
- [ ] **P0-7** — Integration 1.2: The requested volume converts to a pinned, tested prompt budget for Cyrillic text

## Evening-demo backend slice (2026-07-09) — result

Built end-to-end per `evening-demo-backend-plan.md`, all 13 steps done, no TDD ceremony
(known-debt #10). Manually verified live: `POST /api/v1/generations` → 201 pending →
background task calls real `GigaChatProvider` (creds in `backend/.env`, gitignored) →
`GET /api/v1/generations/{id}` polls to `completed` with generated Cyrillic doklad text;
unknown id → 404. Fixed along the way: alembic was never wired (`migrations/env.py`,
`script.py.mako`, hand-written `generations` table migration — no live DB for
autogenerate at write time); GigaChat needs the Russian Minsvyaz trust-CA
(`generation_provider/certs/russiantrustedca.pem`, bundled) and a 30s httpx timeout
(default 5s times out against it). Known gap: `SqlAlchemyGenerationStorage` sessions
from `container.py` factories are never explicitly closed — SAWarning in logs, not
blocking, not fixed in this slice.

## Frontend framework-skip decision (decided 2026-07-09 — speed measure)

Sprint velocity is too slow for the deadline (1/74 scenarios after the full 8-step
frontend cycle on the landing hero alone). To compress: **Frontend Scenarios 1.2, 2.1,
2.2, 3.1, 3.2 (the CTA→modal trigger, the document-type modal, and the mode modal) are
built WITHOUT the TDD framework** — no red-selenium/red-frontend/green-frontend/
red-frontend-api/green-frontend-api/align-design/green-selenium/demo cycle. Write the
components directly as code, verify by eye in the browser once, mark all 8 checkboxes
`[S]` with this note as the reason. 1.2 was folded in after starting the modal work —
it is one line of glue (CTA onClick opens the type modal) with no logic of its own
separate from the modal it opens; testing the trigger in isolation from its
destination added no value.

**Why:** both modals are near-static UI (pick doc type, pick mode) with the framework's
per-scenario ceremony costing far more than the risk it buys here. The one piece of
real logic in this pair — "only one option enabled, rest disabled" (доклад-only,
Автоматический-only) — has no automated regression coverage after this decision; any
future change nearby must be re-verified by hand in the browser, not caught by a test
suite.

**Scope of the exception — do NOT extend it further without a new decision:**
Frontend Scenarios 4.1 onward (generation form → chat/progress/result flow, i.e. the
"chat") keep the full framework unchanged. That is where the real risk lives (field
validation, double-submit race in 6.2, three progress states, back-navigation) and
where a bug reaching demo actually costs the product working. If sprint pressure later
tempts skipping framework there too, that requires a fresh explicit decision, not a
silent extension of this one.

**Additional ceremony trim for 4.1 onward (still full framework, lighter steps):**
`demo` is skipped (`[S]`) for every remaining frontend scenario — visual-only, non-gating,
catches nothing green-selenium didn't already catch. `align-design` targets "matches the
mockup", not pixel-perfect — full design-review rigor stays only where visual precision
actually matters (already done for the landing hero).

**Layout deviation for 4.1 onward (decided 2026-07-09):** the standalone generation-form
page (mockup 04, spec section 4) is skipped entirely — see `.memory-bank/tasks/known-debt.md`
#8 for the full mapping and what it invalidates (scenario 7.2 in particular). Instead,
after the mode modal the visitor lands on a single doc-left/chat-right screen (mockups
05-07 layout, columns flipped: document wide on the left, chat panel narrow on the
right). The initial request is one free-text chat input (messenger-style), not four
discrete fields — mapped to `topic`; `volume_pages` sent as a fixed default (5);
`requirements`/`extra_wishes` sent empty. Read known-debt #8 before touching Scenarios
4.1-9.2 in a future session — the checkbox/scenario text below still describes the
original 4-field form and has not been rewritten.

**Logic/view split (decided 2026-07-09):** every component from Scenario 4.1 onward
splits into a presentational component (markup/CSS only, props in) and a `use*` hook
(state, validation, API calls, submit logic) that owns everything else. `align-design`
then only ever touches the presentational half — the hook, and any red/green-frontend
coverage of it, stays untouched when the design gets reskinned later. E.g. `useGenerationForm`
(state/validation/submit) + `GenerationForm` (renders from the hook's return value).

**Everything else below (60 scenarios) is explicitly deferred past this Friday** —
retry policy, reconciliation sweep, load, most security/infra hardening. Do not work
them before P0-1..7 are green and deployed, no matter what order `/continue` would
otherwise pick.

**Ceremony cut for P0-1..7 only (decided 2026-07-09) — forced measure, sprint deadline
pressure, NOT a permanent process change:** after scenario 1.2's green-usecase work
unit took ~10 background agent dispatches for one step, we're dropping process weight
that doesn't gate correctness, to fit the remaining P0 scenarios before Friday:
- **Skip** the two pre-commit review passes (`agent-review-agent` + `premortem-agent`) —
  they're non-gating/advisory only, findings are a nice-to-have, not required for P0.
- **Skip** the full `/refactor` detector fan-out (3 concurrent cluster agents) — only
  refactor inline if a duplication/smell is obvious on sight; don't dispatch the fan-out
  for small diffs.
- **Do NOT skip**: red/green TDD cycle, `/test-review` (assertion strictness),
  `/test-coverage`. These are the actual correctness signal — cutting them would mean
  shipping P0 to prod unverified, which is worse than missing ceremony.
Revert this once P0-1..7 are green and deployed — resume full `/continue` ceremony
(review passes + refactor fan-out) for everything after.

## Ad-hoc Figma design-alignment pass (2026-07-10) — landing, modals, chat, mobile

Done outside the formal per-scenario framework (same spirit as the 1.2-3.2 framework-skip
above — near-static visual work) at the user's direct request, driven by a real Figma
file (`https://www.figma.com/design/rA86oLSfshnx9CYlAtSfqr/...`, frames "Main screen 2.0",
"Generation screen", "Generation screen 2") plus `.memory-bank/figma/` exports. Design
tokens (Inter font sizes, dark-surface color scale, radius scale) were pulled via the
Figma REST API (`GET /v1/files/{key}/nodes`) using a user-supplied personal access token
— token was pasted in chat and not persisted anywhere in the repo; user was told to
rotate it in Figma settings after the session.

**What changed (all in `frontend/src/`):**
- `index.css` — `:root` tokens replaced with the real Figma palette/radius scale
  (`--bg-page`, `--bg-header`, `--bg-card`, `--radius-sm/md/lg/pill`, etc.), old
  `--accent-*` vars kept alongside (still used by `ChatWorkspace`/`ChatWorkspaceDoc` CSS).
- `features/landing/components/Header.tsx` (new) + `Header.css` (new) — nav bar with
  logo, "Вход" ghost button, primary CTA (`data-testid="header-primary-cta-button"`).
- `features/landing/components/LandingPage.tsx`/`.css` — added hero image collage
  (`frontend/public/hero-collage.svg`, built from `.memory-bank/figma/Разметка.svg`
  geometry, cropped to drop the vector-glyph pill text and duplicate blur layers), a
  real-DOM trust-row pill (accessible text, not the SVG's baked-in glyphs), a features
  section (4 cards + big placeholder), and a big "Textery AI" footer wordmark. A
  fade-out grid background (`.hero-collage-wrap::before`, CSS linear-gradients +
  radial-gradient mask) was added behind the collage to match a later `Разметка.png`
  revision that added a grid backdrop.
- `shared/components/PlaceholderImage.tsx` (new) — reusable inline-SVG placeholder icon
  (frame + circle + "mountain"), used across the landing features section and both
  generation modals.
- `features/generation/components/TypeModal.tsx`/`ModeModal.tsx`/`Modal.css` — cards
  restyled to match the Figma modal frames (top image placeholder + name + separate
  "+" button below, not an overlaid "скоро" badge); `ModeModal` card order flipped to
  Ручной-first/Автоматический-second to match the mockup; back control changed from a
  text row to an icon-only arrow button.
- `public/logo.svg` (added by user) — swapped in as the real logo everywhere a
  hand-built "T" mark existed: `Header.tsx` (landing) and
  `features/generation/components/ChatWorkspace.tsx` (chat header).
- `features/generation/components/ChatWorkspace.tsx`/`.css` — **layout swap**: the
  `cw-layout` grid was `320px 1fr` (chat left, doc right); now `1fr 320px` with
  `.chat-panel { order: 2 }` / `.doc-area { order: 1 }`, so the document is on the left
  and the chat/composer panel is on the right (doc-testids unchanged — `chat-panel`/
  `doc-area` still identify the same regions, just repositioned via CSS `order`, no
  test assumed a left/right position so nothing broke).
- **Markdown rendering** — `doc-body` used to render GigaChat's raw string via
  `{content}` (`white-space: pre-wrap`); now renders `<ReactMarkdown>{content ?? ''}</ReactMarkdown>`
  (added `react-markdown` as a real dependency — reuse over hand-rolling a parser) with
  a `.markdown-body` stylesheet block in `ChatWorkspaceDoc.css` (headings, lists, bold,
  links, blockquote, code/pre) matching the existing dark theme.
- `frontend/src/features/landing/__tests__/LandingPage.test.tsx` — updated after the
  user removed the hero subheading/CTA button from `LandingPage.tsx` directly (their
  own edit, not this session's); the vitest assertion was narrowed to just the hero
  heading so the suite reflects what's actually rendered.

**Mobile-responsive pass — the one piece done through real red/green tests:**
User asked to "prescribe the phone design through tests" and confirmed Selenium
(window-resize + real rendered layout) over a jsdom `matchMedia` mock. Added:
- `acceptance/conftest.py` — `mobile_webdriver` fixture (headless Chrome,
  `--window-size=390,844`, iPhone 12/13-class viewport).
- `acceptance/statements/frontend/responsive_statements.py` (new) —
  `assert_no_horizontal_overflow(driver, label)`, comparing
  `document.documentElement.scrollWidth` to `window.innerWidth`.
- `acceptance/tests/frontend/landing/test_landing_page_mobile_acceptance.py` (new) —
  two scenarios: landing page and the (header-CTA-opened) type modal must not
  horizontally overflow at 390px width.
- **RED** (before the CSS fix): both failed — `scrollWidth` 533px vs a 390-504px
  viewport, caused by the decorative fade-grid `::before` bleeding via negative
  `inset` past the container edge, and by the modals' hardcoded `width: 760px`/`640px`.
- **GREEN**: `.landing { overflow-x: hidden }` (clips the decorative bleed only — the
  grid already fades to transparent before the container edge, so nothing visible is
  lost), `.modal { max-width: calc(100vw - 32px) }`, and `@media (max-width: 640px)`
  blocks in `LandingPage.css` (smaller hero/heading type, features grid to 1 column,
  hides the big placeholder image, wraps the trust row), `Header.css` (hides the
  "Вход" ghost button, shrinks padding), and `Modal.css` (`type-grid` → 2 columns,
  `mode-grid` → 1 column, smaller card icons). Both scenarios pass.
- **Not covered**: `ChatWorkspace`'s `cw-layout` grid (`1fr 320px`, hardcoded) has the
  same class of bug on a phone viewport and was not given a red/green cycle in this
  session — flagged here so a future pass doesn't have to rediscover it.

**Verification run each iteration:** `npx tsc --noEmit`, `npx vite build`,
`npx vitest run --pool=threads` (default `--pool=forks` hung/timed out in this Windows
environment — always pass `--pool=threads` here), and for the mobile scenarios
`FRONTEND_PORT=80 python -m pytest tests/frontend/landing/test_landing_page_mobile_acceptance.py`
from `acceptance/`. The `infra-frontend-1` Docker container (built via
`infra/docker-compose.yml`) was rebuilt (`docker compose build frontend && docker compose
up -d --no-deps frontend`) after every change so the user could review in the browser at
`http://localhost:80`.

## Frontend audit remediation (2026-07-10)

Direct fixes against an external code-quality grading audit, outside the TDD
scenario ceremony — see `frontend-audit-remediation.md` for what changed (polling
cap, error surfacing, dedup, file-size-cap splits, new test coverage, README) and
what's still deferred (CI, oxlint rules, git-config typo).

## Spec
- [x] interview
- [x] story
- [x] mockups
- [x] api-spec
- [x] test-spec

