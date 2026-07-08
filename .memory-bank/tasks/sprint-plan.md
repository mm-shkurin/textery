# Sprint Plan — Лаборатория, Сезон 2026

Source of truth for scoring rules: `.memory-bank/sprint.txt`. This file is the working
plan derived from it, kept in sync with `ProductSpecification/stories.md`.

## Working copies (2026-07-07)

Backend and frontend sessions were sharing one working directory (`textery/`), which
risked one session's uncommitted edits landing in the other's commits. Fixed with a
git worktree: `C:\Users\trape\OneDrive\Desktop\textery-frontend` is an isolated
checkout on branch `features/story-1-frontend` (forked from
`features/story-1-auto-generate-doklad` at the point backend reached `red-usecase` for
scenario 1.1). Both feature branches PR into `dev` independently — no need to merge
one into the other first. Frontend session should be pointed at the worktree path,
not the main `textery/` folder, from now on.

## Progress log

### 2026-07-07 (sprint 1, day 2, TDD loop underway) — P0-1 design done; backend session rotating out (context limit)

Backend session ran real TDD work on `features/story-1-auto-generate-doklad` (branched
off `dev` per the earlier call — one branch for the whole P0 push):
- **red-acceptance** (scenario 1.1, "reject missing topic"): predicted-vs-actual failure
  matched exactly (400 expected, 501 actual — placeholder backend). Self-corrected a
  wrong 422 prediction mid-unit, traced it to a stale line in the story spec, fixed the
  spec too, not just the test.
- **design** (scenario 1.1): domain-level validation architecture —
  `Generation.create(...)` factory + `ValidationException` + two centralized FastAPI
  exception handlers (400 for validation, generic 500 catch-all, never leaks internals).
  Rejected per-controller imperative checks (would duplicate trim/length/emptiness logic
  per field as 1.2/1.3/1.4 land). **Declared the pattern for 1.2/1.3/1.4 and stories
  #2-4** — now recorded in `tech-details/backend.md`'s "Decided" section, full ADR at
  `ProductSpecification/stories/01-auto-generate-doklad/decisions/request-validation-architecture-decision.md`.
  Hazard-scanned the design itself (not just the spec) — 4 groups clean/out-of-altitude,
  4 found real gaps, all folded in: trim-before-emptiness-check, 300-char topic max,
  omitted/null/empty-string all producing the identical 400, the catch-all handler
  requirement.
- Review passes (`agent-review`, `premortem`) both returned CONCERNS on the
  red-acceptance step and got acted on for P0-relevant findings (422/400 fix, a
  backwards tech-profile rule, an over-scoped assertion method rename); non-P0 findings
  explicitly deferred with reasons (DTO mass-assignment escape hatch → scenarios 1.5/1.6,
  Statements file split → later, empty-string-vs-missing equivalence class → out of
  scenario 1.1's scope).

Commits: `885e44e` (P0 triage), `a5c0ccd` (acceptance scaffold refactor + 422/400 fix),
`019faa9` (known-debt #1 close, tech-lead notes), `76d9b25` (design ADR).

**P0-1 now 2/6 steps done** (red-acceptance, design); next is **red-usecase** — first
step that actually touches `backend/` (still empty until now, correctly). **0/7 P0
scenarios fully complete yet.**

**Session rotating out at this point (context limit)** — this is exactly the scenario
continue-framework's `progress.md` persistence is designed for: a fresh backend session
can pick up from `progress.md` + this log + the ADR with nothing lost. See the handoff
prompt used to start the next backend session (not stored here — given fresh each
rotation).

### 2026-07-07 (sprint 1, day 2, later) — pace check: 67 scenarios / 424 steps, 1 done — P0 triage

Checked `ProductSpecification/stories/01-auto-generate-doklad/progress.md`: 67 hazard-
scanned scenarios × 6-8 TDD steps each = 424 total steps for story 1 alone. Only
scenario 1.1's `red-acceptance` is done (`design` in progress) — roughly 1/424. At this
granularity, finishing all 67 before Thursday is not realistic; it was never actually
required — the Friday bar is "the demo works," not "every hazard-scanned edge case is
green."

**P0 (7 scenarios — the walking skeleton, must be green + deployed by Thursday):**
Backend 1.1, 1.2, 2.1, 4.1, 4.2 + Integration 1.1, 1.2 — full list with rationale now
lives in `progress.md`'s new "Priority for Sprint 1" section at the top (source of
truth; don't duplicate scenario details here). This is the minimum that makes
submit-topic → generated-доклад actually work end-to-end through a real deployed API.

**Explicitly deferred past Friday:** the other 60 scenarios — retry policy,
reconciliation sweep, load tests, most security/infra hardening. Real engineering
value, not demo-visible, not worth the time this week.

**Branching for this:** `features/story-1-auto-generate-doklad` off `dev`, one branch
for the whole P0 push (not per-scenario — the new main/dev/features convention rewards
feature-branch evidence in the code-quality audit, but per-TDD-step branching would be
absurd overhead at this granularity), PR into `dev` once P0 is green and deployed.

**Frontend unblocked in parallel, not serially:** the REST contract (`endpoints.md` +
`ProductSpecification/api-specs/*.yaml`) is already finalized and won't change based on
whether tests are green. Frontend can build the 18a-e screens against mocked responses
matching that contract right now, and swap to the real backend once P0 lands — no need
to wait.

### 2026-07-06 (sprint 1, day 1) — spec phase for story 1 complete, zero code written yet

Two parallel sessions (backend, infra) ran the full pre-implementation pipeline. Nothing
in `backend/`, `frontend/`, or `acceptance/` exists yet — everything below is
specification and local tooling, not running product code. Day-1 tasks #6 (domain
entities) through #22 (day 4) in the breakdown above are **still ahead of us**, not done.

**Backend session — spec pipeline for story 1, all the way through `/test-spec`:**
- `.claude/tech/python-fastapi-hex/` authored (coding.md, tdd.md, infrastructure.md,
  templates/) — the ORM/DI/test-stack items that were "Proposed" are now confirmed and
  folded in; `ProductSpecification/technology.md`'s Backend/Testing sections are filled
  in from it (no more TODOs there except css/browser-testing, which stays deferred per
  `known-debt.md` #1).
- `CLAUDE.md` corrected: architecture table had a leftover `backend/adapters/h2` from the
  framework's Java/H2 default — renamed to `backend/adapters/db` to match the real
  Postgres/SQLAlchemy stack.
- Ran `/interview 1` → `/story 1` → `/mockups` → `/api-spec` → `/test-spec` for
  "Auto-generate: доклад": `ProductSpecification/stories/01-auto-generate-doklad/`
  now has `interview.md`, `01_AutoGenerateDoklad.md` (spec), `_Notes.md`, `endpoints.md`,
  desktop+mobile HTML mockups with screenshots, and `tests/` (6 categories + `extended/`).
  `ProductSpecification/api-specs/` has the 3 OpenAPI specs (create/get/list generations).
- Hazard-catalogue scan ran **twice** — once on the story spec (23 fired GAPs → 18 new
  Core Requirements + 1 new tracked debt item), once independently on the drafted test
  files themselves (~30 findings → 20 new scenarios, 5 promoted from `extended/`). Net
  effect: story 1's spec is now considerably harder-nosed than the interview draft —
  idempotency keys, atomic CAS status transitions, UUID (not sequential) generation IDs,
  keyset pagination, redaction-tested secret handling, Cyrillic-specific boundary tests,
  and more are now named Core Requirements, not just prose warnings.
- **New tracked debt** (`.memory-bank/tasks/known-debt.md` #4): the temporary unscoped
  `GET /generations` leaks every caller's data to every other caller — deliberate
  (no principal exists yet to scope it to), but **must** be removed/gated no later than
  story #7. Don't let this slide past that story.
- `ProductSpecification/ExpectedLoad.md` gained a "Load Challenge Profile" section:
  confirms the binding constraint is *request throughput* (concurrent submissions, queue
  depth, OpenRouter rate limits) — not data volume or latency SLOs. Load scenarios should
  be written against that, not generic "handles N users" language.

**Infra session — local docker-compose, validated (see `infra/architecture.md` for full detail):**
- 5-service compose topology: `frontend` (nginx, TEMP static page), `backend` (TEMP
  `python -m http.server`), `worker` (same image as backend, TEMP `tail -f /dev/null` —
  separate process because arq workers and the API have different lifecycles),
  `postgres`, `redis`. All host ports env-driven (no hardcoded/no `container_name`) so
  multiple worktrees can run this on one host without colliding.
- Validated: `docker compose config` clean, all 5 services reach healthy, Postgres
  reachable from `backend`, Redis `PONG`, a written Postgres row survives
  `down`/`up -d` (named volume persists).
- `backend/.env` (gitignored, not created by the infra task) is wired into
  `backend`/`worker` via `env_file: ... required: false` so compose still boots today
  with `backend/` empty.
- **Action item, not yet fixed:** `infra/architecture.md` line ~60 still says
  `backend/.env` holds `ANTHROPIC_API_KEY` — stale, predates the OpenRouter switch. The
  actual secret is `OPENROUTER_API_KEY` (+ `OPENROUTER_MODEL`), per `interview.md` and
  `tech-details/backend.md`. Fix this the next time the infra session touches
  `architecture.md`; harmless until then (it's a comment, not wired code).

**Housekeeping done this session:** `.gitignore` now excludes `.screenshots-temp/`
(puppeteer scaffolding from the `/screenshot` skill's mockup-screenshot pass — was
untracked, not meant to be committed).

**Where this leaves Sprint 1's task list above:** tasks #1–5 and #7 (Day 1) are
partially satisfied by the spec work (test plan can now lean on the two hazard-scan
write-ups instead of starting from scratch) but **none of #6, #8–22 (actual code,
deploy, GitVerse push) have happened yet.** Story 1's spec is unusually thorough — good
for the code-quality/test-plan scoring axes, but it also means the red/green implementation
work per Core Requirement (23+ of them) is larger than a "minimal slice" estimate would
suggest. Revisit the Day 2–4 time estimates with this in mind; the cut list (drop
`ListGenerations`, defer frontend polish) is more likely to be needed than not.

### 2026-07-07 (sprint 1, day 2) — frontend flow scope expanded: Landing + modals pulled forward

Walked through the intended UX with reference mockups (`.memory-bank/Landing.png`,
`Тип документа.png`, `Тип Работы.png`, `Автоматическая работа.png`) to make sure both
sides agree on the actual flow before building it. Result — **this Friday's demo needs
more frontend than the original "minimal form" plan**:

- Entry point is now **Landing → modal (document type) → modal (mode: Ручной/
  Автоматический) → generation form → "chat" progress/result screen**, not a standalone
  form page. A **minimal slice of story #9 (Landing)** — hero + CTA only, not the full
  marketing page — is pulled forward into sprint 1. Full Landing polish (pricing,
  feature blocks, testimonials) stays in sprint 2 as originally planned.
- Both modals follow the existing "disabled option with a скоро badge" convention
  already used in the current (now-stale) form mockup: only доклад / Автоматический are
  live, the rest visibly present but disabled.
- The "chat" screen is confirmed to be a **simplification**: a plain loading indicator
  while `pending`/`in_progress`, reveal-on-complete once `GET /generations/{id}` returns
  `completed` — not real token streaming. Backend's async contract is **unchanged**.
  Real streaming (SSE/WebSocket) is deliberately deferred — tracked as
  `known-debt.md` #5, not forgotten.
- `ProductSpecification/stories/01-auto-generate-doklad/01_AutoGenerateDoklad.md`'s
  Screen States section is updated to this flow. Mockups regenerated the same day
  (backend session, before starting `/continue`): `01-landing`, `02-type-modal`,
  `03-mode-modal`, `04-generation-form` (revised — type selector moved to the modal,
  form now shows a breadcrumb chip instead), `05/06/07-chat-{pending,completed,failed}`
  — desktop + mobile, 14 files, screenshotted. No longer stale.

**Impact on the Day 4 plan below:** task #18 ("minimal frontend: form → submit → poll →
show result", originally 2h) is now underscoped — it needs Landing + 2 modals + the
existing form + a chat-style progress/result screen. Revised below. This lands on top of
a schedule the day-1 progress log already flagged as tight; treat the cut list
(non-doklad options can stay visually "скоro" placeholders with zero wiring — that part
was always the plan) as more likely needed, not less.

## Hard constraints (violate these and the sprint scores 0, no partial credit)

- **A working, reachable link is mandatory every Friday**, including sprint 1. No link /
  link doesn't open / app doesn't run → whole sprint = 0, no criteria evaluated.
- **GitVerse only.** All code, docs, artifacts. Nothing elsewhere counts.
- Judging starts **Friday 21:00 GMT+6** — everything must be live and pushed before that,
  not "finished but not yet pushed."
- Demo itself: Friday 18:00–20:00 online, every sprint except the last (sprint 8).
- Category: **AI-assisted, single developer** — technical score's "code quality" axis
  (0–3 pts) is graded by an automated Cursor/Claude-Opus audit of the whole repo (see
  `sprint.txt` for the exact prompt) — covers architecture, code smells, formatting,
  error handling, secrets-in-git, test quality, commit hygiene, README/docs. This runs
  every sprint, not just sprint 1 — keep the repo genuinely clean throughout, not just
  demo-ready.
- **Sprint 1's testing score evaluates the TEST PLAN** (goals/approach/scenarios), not
  test execution. Sprints 2–8 evaluate actual test case completeness/quality instead.
- Work done Saturday lands *after* Friday's judging cutoff — it's a head start on the
  next sprint's score, not this one's. Real crunch window per sprint: **Mon–Thu**.

## Deploy

User has an existing server/VM — deploy `infra/docker-compose.yml` there directly
(reverse proxy / opened port for a reachable URL). No Terraform/cloud IaC needed yet;
`terraform-yandex` stays dormant until that's actually worth automating (see root
`.memory-bank/tasks/known-debt.md` #3).

## 8-sprint roadmap (dates from `sprint.txt`)

| # | Dates | Focus (stories from `ProductSpecification/stories.md`) | Demo goal |
|---|-------|----------------------------------------------------------|-----------|
| 1 | Jul 6–10  | **#1** Auto-generate: доклад (walking skeleton + deploy pipeline) + **minimal slice of #9** (hero+CTA only, pulled forward 2026-07-07 — required for the real entry flow, see progress log) | Public URL: Landing → type/mode modals → generated доклад |
| 2 | Jul 13–17 | #1 polish (real streaming, known-debt #5) + **#9** Landing full polish (pricing/feature blocks — the rest of it) + start #2 | Full landing + working generation, first real test cases |
| 3 | Jul 20–24 | **#2, #3, #4** эссе/сочинение/реферат (same pipeline, reuse #1's shape) | All 4 document types selectable and working |
| 4 | Jul 27–31 | **#5** Manual input mode + **#6** Model switching | User can bypass AI and pick a model |
| 5 | Aug 3–7   | **#7** Authorization (+ retrofit `userId`, known-debt #2) | Real accounts, login, generations tied to a user |
| 6 | Aug 10–14 | **#8** Billing (3 tariffs, mocked payment) | Subscribe flow, tariff limits enforced |
| 7 | Aug 17–21 | **#11, #12, #13** Document management, History, Profile | Full account experience, not just generation |
| 8 | Aug 24–28 (final, ×2 points, no regular demo) | **#10, #14, #15** Editor polish, Analytics, Funnels + hardening/regression | Polish pass, DemoFest prep if selected |

Ordering rationale: value-first core (1→4) first three sprints per the build-order
decision already in `tech-details/backend.md`; auth/billing (7-8) only once there's
something worth gating; layered backlog (9, 11-15) fills remaining sprints around
whichever demo needs the most "looks like a real product" boost that week.

## Sprint 1 — detailed task breakdown (Jul 6–10, ~20h real budget: Mon–Thu only)

Workstream tags: **[INFRA]** infra session, **[BACKEND]** backend session (strict TDD
via `/continue`), **[DOCS]** this session. Estimates assume nothing goes wrong — see
Risks at the bottom for what to cut if Wednesday EOD is behind schedule.

**Key sequencing decision:** deploy a trivial skeleton (health-check endpoint) to the
real server on **day 1**, before any real feature code exists — this proves the whole
deploy pipeline (server reachable, port/proxy open, containers start) *before* it's the
only thing standing between "feature done" and "0 points Friday night." Swap the real
build in on day 4; the pipeline itself is already de-risked by then.

### Day 1 — Mon Jul 6 (5h): bootstrap + deploy pipeline proof

| # | Task | Owner | Est. | Definition of Done |
|---|------|-------|------|---------------------|
| 1 | Create GitVerse repo, push full history, set as remote | you (manual signup) | 0.5h | Repo visible on GitVerse; `git remote -v` shows it; latest commit pushed |
| 2 | `.gitignore` audit — confirm `.env`/secrets excluded | [DOCS] | 0.2h | `git ls-files \| grep -i env` shows nothing but `.env.example` |
| 3 | `docker-compose up` dry run, locally | [INFRA] | 0.5h | All containers report healthy locally |
| 4 | Deploy skeleton to the real server (health-check backend + placeholder frontend), open port/reverse proxy | [INFRA] | 1.5h | Public URL returns 200 from outside your network |
| 5 | Get an OpenRouter API key, pick the model string for story 1, fill `backend/.env` | [BACKEND] | 0.5h | A manual `curl` to OpenRouter with that model returns a real completion |
| 6 | Domain: `Generation`, `Document` entities + unit tests | [BACKEND] | 1.5h | Invariants tested: `volume_pages` in [1,10], `document_type` fixed to "доклад" |
| 7 | Start the sprint-1 test plan doc | [DOCS] | 0.3h | Skeleton with sections filled from `interview.md`'s Testing Considerations |

### Day 2 — Tue Jul 7 (5h): usecases (red→green)

| # | Task | Owner | Est. | DoD |
|---|------|-------|------|-----|
| 8 | Usecase `RequestGeneration` (fake `JobQueue` port) | [BACKEND] | 1.5h | Red predicted+confirmed, green minimal, gates pass (test-review/coverage/refactor) |
| 9 | Usecase `GetGenerationStatus` | [BACKEND] | 1h | Same gate discipline |
| 10 | Usecase `ListGenerations` (temp unauth "history" stand-in) | [BACKEND] | 1h | Same gate discipline |
| 11 | Finish sprint-1 test plan doc | [DOCS] | 0.5h | Goals, approach, bug-fixing approach, key scenarios per layer — all filled |
| — | Buffer for gate rework (test-review/refactor findings) | [BACKEND] | 1h | — |

### Day 3 — Wed Jul 8 (5h): adapters

| # | Task | Owner | Est. | DoD |
|---|------|-------|------|-----|
| 12 | `adapters-discovery` (maps usecase ports → adapter steps) | [BACKEND] | 0.2h | `progress.md` rewritten with concrete adapter steps |
| 13 | DB adapter: SQLAlchemy models + Alembic migration | [BACKEND] | 2h | `alembic upgrade head` runs clean against local Postgres; adapter test green |
| 14 | REST adapter: `POST/GET /generations`, `GET /generations/{id}` | [BACKEND] | 1.5h | `httpx.AsyncClient` adapter tests green, matches interview.md's endpoint contract |
| 15 | Scheduling adapter: `arq` worker + OpenRouter client + stub server for tests | [BACKEND] | 1.3h | Adapter test green against stub; real Redis via `burst=True` per interview.md |

**Checkpoint — end of Wed:** if #13–15 aren't green yet, this is the point to cut scope
(see Risks) rather than let it slide into Thursday, which has no slack.

### Day 4 — Thu Jul 9 (5h): integrate, deploy the real thing, close out

| # | Task | Owner | Est. | DoD |
|---|------|-------|------|-----|
| 16 | Composition root wiring | [BACKEND] | 0.5h | App boots, all adapters wired to real usecase ports |
| 17 | `green-acceptance` — full E2E acceptance test | [BACKEND] | 1h | Submit → poll → real generated доклад, end to end |
| 18a | Landing (minimal: hero + CTA only) | [frontend] | 0.7h | CTA opens the type modal; no pricing/feature blocks yet |
| 18b | Modal: document type select (доклад active, others "скоро") | [frontend] | 0.5h | Selecting доклад opens the mode modal |
| 18c | Modal: mode select (Автоматический active, Ручной "скоро") | [frontend] | 0.4h | Selecting Автоматический opens the generation form |
| 18d | Generation form (existing mockup, relocated into the flow) | [frontend] | 0.5h | Submit calls `POST /generations` |
| 18e | "Chat" progress/result screen — plain loading indicator, reveal-on-complete, failed state | [frontend] | 1.5h | Polls `GET /generations/{id}`; no real streaming (known-debt #5) |
| 19 | Redeploy real build to the server (replace day-1 skeleton) | [INFRA] | 0.5h | Same public URL now serves the real feature |
| 20 | Smoke-test the public URL end to end | [INFRA] | 0.3h | A generation submitted through the public URL completes successfully |
| 21 | README (setup, run, link to live deploy) + push everything | [DOCS] | 0.4h | README on GitVerse links the live URL; all Thu work pushed before Fri 21:00 |
| 22 | 2–3 sentences of demo talking points | [DOCS] | 0.3h | Ready for Friday 18:00 |

Day 4 frontend (18a–e) alone is now ~3.6h of its 5h budget, leaving little room for
#16-17/19-22 the same day — the schedule was already tight before this expansion (see
day-1 progress log entry); treat Day 4 as the most likely day to run over.

### Risks / what to cut if behind schedule

- **Never cut:** #1 (GitVerse push), #4/#19/#20 (public URL working), #7/#11 (test plan) —
  these three map directly to "sprint scores 0" and the sprint-1 testing score. Losing
  any of these loses more points than any feature work could gain.
- **Cut first if squeezed:** #10 `ListGenerations` (it's a temporary stand-in anyway,
  not real history) → drop it and let the acceptance test only cover submit+poll+read-one.
- **Cut second:** visual polish on 18a-e — bare/unstyled screens that follow the right
  flow beat pretty ones that are half-wired. The flow (Landing→modal→modal→form→chat)
  must all be *present and clickable end to end* — that's the demo requirement — but
  colors/spacing/animation can be minimal.
- **Do NOT cut:** the flow structure itself (Landing/modals/chat screen) — that's now a
  confirmed requirement for Friday, not a nice-to-have, per the 2026-07-07 decision above.
- **Structural risk, watch for it:** OpenRouter latency or rate limits during the Thu
  smoke test — verify #5's manual curl early (day 1), don't discover API problems day 4.
- **New structural risk (2026-07-07):** the frontend scope grew mid-sprint on day 2 —
  if 18a-e aren't done by Thursday midday, consider collapsing 18a-c into one screen
  (e.g. a single page with the two choices stacked, skip true modal overlays) rather
  than cutting them entirely — the flow existing matters more than modal polish.
