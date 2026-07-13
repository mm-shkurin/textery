# План чистки и структуризации документации (по итогам аудита 13.07.2026)

Источник: `_project_audit/00-05_*.md`. Статусы: `[ ]` не начато, `[~]` в процессе, `[x]` готово, `[S]` пропущено (с причиной).

## Фаза 0 — гигиена (без риска)

- [x] Перенести `tasks/1-refactoring-generation-error-handling` → `tasks/done/`
- [x] Перенести `tasks/2-refactoring-generation-hardening` → `tasks/done/`
- [x] `qodana.yaml` удалён (untracked черновик, линтер `jetbrains/qodana-jvm-community` под JVM, стек — Python+TypeScript, `projectJDK: "26"` не подходил проекту)

## Фаза 1 — синхронизация прогресса

- [x] `stories/01-auto-generate-doklad/progress.md`: сценарии 4.1/4.2 `[~]`→`[x]` (Task 3 Step 6 добавил реальный top-level acceptance-тест `test_generation_lifecycle_acceptance.py`, зелёный). 4.3 (not-found) оставлен `[~]` — этот кейс НЕ покрыт lifecycle-тестом, аудит ошибочно включил его в "закрыто"
- [x] Пересчитан `ProductSpecification/stories.md` — Story 1 Tests: 6/74 (8%) → 12/74 (16%), точный подсчёт по чекбоксам (backend 1.1/1.2/2.1/4.1/4.2 + frontend 1.1/1.2/2.1/2.2/3.1/3.2/4.1 = 12 полностью закрытых сценариев)
- [x] Причина найдена, не баг: `.claude/skills/continue/SKILL.md` (строки 143-163) корректно обновляет `stories.md` в одном коммите с `progress.md`. Дрейф вызван работой ВНЕ `/continue` (evening-demo спринт 2026-07-09, Task 1/2/3 backfill — явно помечены "built off-framework"/"no TDD ceremony" в самом progress.md), из-за чего шаг 10 просто не запускался. Ничего в skill'е менять не нужно — процессный риск, а не дефект инструмента.

## Фаза 2 — провайдер/технологии (правда против документации)

- [x] `ProductSpecification/technology.md`: OpenRouter/`openai` → GigaChat; `arq`+Redis → `BackgroundTasks`+DB-sweep; MSW → `vi.mock()`; добавлен `oxlint`; заполнен "Browser Testing" (ссылка на `.claude/guidelines/frontend-rules.md`)
- [x] `ProductSpecification/BriefProductDescription.md`, `ExpectedLoad.md` — провайдер GigaChat
- [x] `.memory-bank/tech-details/backend.md` помечен "замороженный снимок 2026-07-08"; `infra/.memory-bank/index.md` обновлён на GigaChat env vars
- [x] `infra/.memory-bank/open-questions.md` — "CI/CD platform: not chosen yet" закрыт (CI существует с 2026-07-10)

## Фаза 3 — API-спеки под факт

- [x] `stories/01-.../endpoints.md`: Idempotency-Key и `GET /generations` (список) → "planned, not yet implemented", со ссылкой на нереализованные сценарии 3.1/6.1-6.4
- [x] `api-specs/generations_get.yaml`: убрана вложенность `document.content` → плоские top-level `content`/`error_message`, сверено с реальным `GenerationDetailDto` (`backend/adapters/rest/src/dto/generation/generation_response_dto.py`)

## Фаза 4 — архитектурное решение

Решено пользователем: (б) переписать ссылки `infrastructure/` → `infra/` во всех правилах/guidelines/skills, не переносить файлы физически.

- [x] `.claude/rules/infrastructure.md` — путь исправлен на `infra/`, упрощено под реальный набор поддиректорий (нет terraform/nginx-templates/scripts)
- [x] `.claude/guidelines/infrastructure-detail.md` — путь исправлен; **дополнительно найдено**: весь механизм per-instance port-isolation (`setup-ports.sh`, `infra/scripts/`, `infra/notes/local-dev-gotchas.md`) — generic-шаблон из фреймворка, реально не существует в этом проекте (`infra/.env` — фиксированные порты, без генератора). Задокументировано как есть, не выдумано
- [x] `.claude/skills/run-backend/SKILL.md`, `run-frontend/SKILL.md`, `stop-backend/SKILL.md` — переписаны под реальный запуск через `docker compose -f infra/docker-compose.yml up/stop <service>` (сверено с `infra/architecture.md`), т.к. `infra/scripts/*.sh` не существуют
- [x] `.claude/guidelines/agent-logging.md`, `.claude/skills/continue/SKILL.md` — путь лог-файла `infrastructure/agent-progress.log` → `infra/agent-progress.log`
- [x] `.claude/guidelines/frontend-rules.md` — путь исправлен; **дополнительно найдено**: `notes/acceptance-test-gotchas.md` тоже никогда не был написан (ни в `infrastructure/`, ни в `infra/` нет `notes/`) — помечено честно, не сочинён контент
- [x] `.claude/skills/test-acceptance/SKILL.md` — Gradle-синтаксис (`backendTest --tests`) заменён на `pytest acceptance/ -m backend/frontend -k ClassName`; несуществующий `infrastructure/scripts/test-acceptance.sh` убран; `load`-ветка — честно "не реализовано" со ссылкой на `03_Load_Tests.md` вместо выдуманного load-baseline механизма; poll-паттерн переписан под pytest-вывод (`passed`/`failed`/`error`), "compile task FAILED" → "collection error"
- [x] `.claude/skills/demo/SKILL.md` — `infrastructure/scripts/{run,stop}-backend.sh` заменены на вызов skill'ов `/run-backend`/`/stop-backend`; тестовый фильтр переписан под `pytest -k`
- [x] `.claude/skills/qa-run/SKILL.md` — `infrastructure/creds.txt` → `infra/creds.txt`; добавлена оговорка, что prod-copy окружения в проекте пока не существует (не выдуман механизм)
- [x] `/cleanup-chrome` skill: убрал `taskkill /IM chrome.exe /F` (убивало все процессы в системе, включая чужие Selenium-сессии и браузер пользователя, прямое нарушение `infrastructure.md`) — заменил на поиск осиротевших процессов по дереву (родитель мёртв) и убийство по конкретному PID
- [x] Redis в `infra/docker-compose.yml`/CI — решено оставить как задел под `arq` (known-debt #13)

## Фаза 5 — CI (исправлена трактовка аудита, не дубликат)

Аудит ошибочно назвал это "задублированным и разошедшимся CI". Реально — два CI для
двух разных репо: корневой `.github/workflows/{backend,frontend}-ci.yml` для GitHub
(`mm-shkurin/textery`), `backend/.github/`+`frontend/.github/` — станут корнем после
`git subtree split --prefix=backend/frontend` при пуше на GitVerse (конкурс засчитывает
только GitVerse, см. `.memory-bank/steerings/development-conventions.md:20-45`). Разный
подход к Postgres/Redis (service-контейнеры vs apt-get) — не рассинхрон, а следствие
разных раннеров (GitVerse-раннер без Docker socket).

- [x] Установлена причина: два репо, не один пайплайн — не требует объединения
- [x] Root `.github/workflows/backend-ci.yml` (монорепо/GitHub) актуализирован под рабочий нативный apt-get подход из `backend/.github/workflows/ci.yml` (GitVerse) — service-контейнеры заменены на нативную установку postgres/redis, пароль унифицирован на `change-me`. Frontend CI различий не имел (только paths-фильтры и docker-image job, нужные только монорепо) — не трогал.
- [x] Проверено 2026-07-13: `gitverse-backend` main отставал на 3 коммита (недостающие тесты provider/router wiring, ~180 строк) от актуального `backend/` subtree-split; `gitverse-frontend` был свежий (15=15). Пересобран `backend` subtree-split, запушен как ветка `features/story-1-auto-generate-doklad`, затем force-push в `main` (subtree split каждый раз пересчитывает хэши — обычный fast-forward невозможен даже без конфликтов в содержимом)

## Фаза 6 — разделение бек/фронт (запрос сокомандника)

Решено: 2 файла-чеклиста (не 3 — acceptance-шаги вшиты внутрь backend-сценариев,
не отделимы), плюс исходный `progress.md` остаётся нарративом/агрегатором.
`stories.md` уже играет роль "целостной картины" — отдельный третий файл не нужен.

- [x] `progress-backend.md` — Backend + Integration + Security + Load + Infrastructure Scenarios
- [x] `progress-frontend.md` — Frontend Scenarios
- [x] `progress.md` урезан до нарратива/decisions/Spec-чеклиста, добавлен указатель на новые файлы
- [x] `.claude/rules/workflow.md` — "Progress Tracking" переписан под 2-файловую+narrative схему
- [x] `.claude/skills/continue/SKILL.md` — резолюция аргумента (`/continue 1 backend`), чтение нужного файла, behavior commit только своего слоя, "Updating stories.md" под split-layout
- [x] Правило владения файлами/слоями зафиксировано в `CLAUDE.md` ("File Ownership") — backend/frontend session границы, worktree, кто что правит в общих `progress.md`/`stories.md`

## Фаза 7 — верификация живым стеком

- [x] Поднят `infra/docker-compose.yml` целиком (postgres/redis/backend/frontend, все healthy), backend временно переключён на `GENERATION_PROVIDER=fake` (чтобы не тратить реальную квоту GigaChat на тестовый прогон), после тестов откачено и стек снесён (`docker compose down`) — среда осталась чистой
- [x] `adapters/db` тесты против реального Postgres — **7/7 passed** (`TestSaveAndGet`, `TestGetUnknownId`, `TestUpdate`, `TestUpdateUnknownId`, `TestUpdateConcurrentConflict`, `TestListStale` × 2)
- [x] `acceptance/` набор целиком — **backend 5/5 passed** (create + reject + lifecycle), **frontend 4/4 passed** (chat workspace initial state, landing hero+CTA, 2× mobile no-overflow). Подтверждает вертикальный срез Story 1 реально работает end-to-end, не только на бумаге
- [x] Re-audit не проводился (отдельная методология внешнего грейдинга, не часть этой сессии) — вместо этого добавлены явные Closure-секции в оба файла: frontend закрыт на 2.5/3.0 с списком оставшихся гэпов, backend закрыт на baseline 2.0/3.0 (9/10 находок закрыто, finding 5 auth/ACL сознательно отложен) — счёт больше не выглядит "недоделанным молча"
