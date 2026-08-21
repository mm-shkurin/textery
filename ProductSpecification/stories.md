# In Progress

<!-- Track story progress across phases. Update as work proceeds. -->

| #  | Story                         | Spec | Back | Intg | Front | Sec | Load | Infra | Tests | %  |
|----|-------------------------------|------|------|------|-----|-------|------|-------|-------|----|
| 1  | Auto-generate: доклад          | ✅   | 🔧   | —    | 🔧   | —     | —    | —     | 12/74 | 16% |
| 5  | Manual input mode (non-AI document creation) | ✅ | 🔧 | — | 🔧 | 🔧 | — | — | 28/58 | 48% |
| 7  | Authorization (email+password w/ mocked code, Yandex ID, VK ID) | ✅ | 🔧 | — | ✅ | 🔧     | —    | —     | 35/63 | 56% |
| 16 | OAuth sign-in: VK ID + Yandex ID (frontend-first, backend reduced-TDD) | ✅ | 🔧 | — | ✅ | 🔧 | n/a | — | 14/14 | 100% |
| 17 | Export document to PDF / DOCX | ✅ | 🔧 | — | ✅ | — | — | — | 14/45 | 31% |
| 18 | Generate → edit (unify generate + manual, drop mode modal) | ✅ | — | — | 🔧 | — | — | — | 2/13 | 15% |
| 2  | Auto-generate: эссе                       | 🔧   | 🔧   | —    | 🔧   | —     | —    | —     | 0/0   | 0% |
| 3  | Auto-generate: сочинение                  | 🔧   | 🔧   | —    | 🔧   | —     | —    | —     | 0/0   | 0% |
| 4  | Auto-generate: реферат                    | ✅   | 🔧   | —    | 🔧   | —     | n/a  | n/a   | 4/27  | 15% |
| 10 | Editor pages (pagination, page setup, headers/footers) | ✅ | 🔧 | — | — | — | — | — | 0/70 | 0% |
| 12 | Мои проекты (list/search/sort, grid + list view) | ✅ | 🔧 | — | 🔧 | — | — | — | 1/177 | 1% |
| 13 | Profile management                     | ✅   | 🔧   | —    | 🔧  | —     | —    | —     | n/t   | n/t |
| 14 | Analytics Event Tracking (server-emitted events + browser ingest) | ✅ | 🔧 | — | — | — | — | — | 1/171 | 1% |

**Легенда `Tests`/`%`.** `n/t` — «not tracked»: код фазы существует и смержен, но
per-scenario чеклист под него не заводился, поэтому знаменатель из тест-спеки не
применим. Это честнее нуля, который читается как «работы не было».

**Note on #14 (Analytics Event Tracking).** Promoted from Backlog on 2026-08-19 —
spec phase complete (interview, story, api-spec, test-spec; `mockups` `[S]`, the story adds
no new UI surface). `1/171` is not work done: the one counted scenario is
`03_Load_Tests.md` §3.1, marked `[S]` out of scope because it would require bounding
`GenerationStorage.list_stale` and this story changes no existing behaviour — carried as
`tasks/7-refactoring-bound-stale-generation-sweep/`. Backend starts at API §1.1.

**Note on #16 (OAuth sign-in).** До 15.08 строка стояла в `·` («папки истории нет»)
по всем backend-фазам — это было просто неверно: папка `stories/16-oauth-signin/` есть,
`progress-backend.md` в ней есть, backend OAuth реализован (адаптер `oauth_provider`,
9 usecase-файлов, маршруты `/api/v1/auth/oauth/{provider}/start|callback` и
`/exchange`). Backend и Security идут в **reduced-TDD** — per-scenario red/green
свёрнуты, каждый такой шаг помечен `[S] reduced-TDD`, добор — в
`tasks/6-refactoring-oauth-tdd-backfill/`. Отсюда `🔧`, а не `✅`. `14/14` относится
к frontend-сценариям, которые история и считала своим скоупом.

**Note on #5 (Manual input mode).** `Back`/`Sec` = 🔧 опережают отслеживаемое
состояние: `progress-backend.md` для истории не заведён (см. врезку в её
`progress.md`), backend-чеклист не бутстрапнут из `tests/01_API_Tests.md`,
`tests/05_Security_Tests.md`, `tests/06_Integration_Tests.md`. `28/58` — фронтовые
сценарии. Замечено 20.07, всё ещё открыто на 15.08.

**Note on #13 (Profile management).** Спека закрыта 13.08, код смержен 14.08
(`b1ba584c merge(story-13): profile management into dev`) — **вне per-scenario цикла**,
как и story 16. Что реально в `dev`:

- backend: `GET`/`PATCH /api/v1/auth/me` (`router/auth/profile_router.py`),
  аватар — `PUT`/`GET`/`DELETE /api/v1/auth/me/avatar` (`avatar_router.py`),
  удаление аккаунта — `POST /api/v1/auth/me/deletion` (`deletion_router.py`);
  13 usecase-файлов, domain `avatar.py`/`avatar_format.py`/`account_name.py`;
- frontend: `frontend/src/features/profile/` (18 файлов), тёмная тема,
  `profileStub` удалён;
- acceptance: 5 Selenium-сценариев в `acceptance/tests/frontend/profile/`.

`progress-backend.md` и `progress-frontend.md` для истории **не заведены** — 130
сценариев тест-спеки не размечены по факту реализации. Пока это так, `Tests` держим
`n/t`; чтобы вернуть числа, нужно бутстрапнуть оба файла из `tests/` и разметить
существующий код. Скоуп при этом уехал за интервью (аватар, удаление аккаунта, тема —
интервью явно выносило их за скоуп), это тоже надо свести при бутстрапе.

# Backlog — Core sequence (build order, decided 2026-07-06)

Value-first order: prove the generation slice end-to-end for one document type before
anything else, then widen. **#1 must ship first.** #2–#4 (the other three document
types) may run in any order relative to each other and may interleave with #5–#8 (e.g.
#7 auth can land between #1 and #2) — the only hard constraint is #1 before all of them.

| #  | Story                                    | Spec | Back | Intg | Front | Sec | Load | Infra | Tests | %  |
|----|-------------------------------------------|------|------|------|-----|-------|------|-------|-------|----|
| 6  | Model switching (per-tariff AI model choice) |      |      |      |     |       |      |       |       |    |
| 8  | Billing (tariffs + mocked subscription payment) |      |      |      |     |       |      |       |       |    |

# Backlog — layered on top later (not yet ordered)

<!-- Remaining scope from .memory-bank/комплект продуктовой архитектуры.txt not covered
     by the 8 core stories above. -->

| #  | Story                                | Spec | Back | Intg | Front | Sec | Load | Infra | Tests | %  |
|----|----------------------------------------|------|------|------|-----|-------|------|-------|-------|----|
| 9  | Landing & Marketing                    |      |      |      |     |       |      |       |       |    |
| 11 | Document Management (rename/delete/duplicate) |      |      |      |     |       |      |       |       |    |
| 15 | Funnels & Reports (CSV export)          |      |      |      |     |       |      |       |       |    |

**Note on #12 (Мои проекты).** Promoted to In Progress on 2026-08-01 — `/interview` ran,
`interview.md` and `mockups/` exist, so Spec is 🔧. Part of its backend already existed
before the story started, shipped 2026-07-17 outside the story lifecycle at the user's
direction (`feat: owner-scoped history for generations and documents`):

- `GET /api/v1/generations` and `GET /api/v1/documents` — the caller's own history,
  Bearer-required, owner-scoped in SQL, keyset-paginated, summary projection (no
  content). Contracts: `api-specs/generations_list.yaml`, `api-specs/documents_list.yaml`.
- Covered by unit, adapter and DB-level tests, and verified end to end against the
  running container. Not covered by an acceptance test — see the same gap named in
  `tasks/done/4-bug-generations-auth/progress.md`.

The interview decided **not** to extend those two: search plus four sort orders plus
merging failed generations into one feed all break the keyset cursor, whose anchor must
be immutable. #12 owns a new `GET /api/v1/projects` (offset-paginated, search, 4 sorts,
merged feed); the two existing list endpoints get marked deprecated and stay working.
Details and the reasoning in `stories/12-my-projects/interview.md`.

# Done

| #  | Story                         | Spec | Back | Intg | Front | Sec | Load | Infra | Tests | %       |
|----|-------------------------------|------|------|------|-----|-------|------|-------|---------|---------|
