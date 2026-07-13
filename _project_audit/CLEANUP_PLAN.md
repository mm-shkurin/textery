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

- [ ] `ProductSpecification/technology.md`: OpenRouter/`openai` → GigaChat; `arq`+Redis → `BackgroundTasks`+DB-sweep; MSW → `vi.mock()`; добавить `oxlint`; заполнить "Browser Testing" (ссылка на `.claude/guidelines/frontend-rules.md`)
- [ ] `ProductSpecification/BriefProductDescription.md`, `ExpectedLoad.md` — провайдер GigaChat
- [ ] `.memory-bank/tech-details/backend.md`, `infra/.memory-bank/index.md` — обновить или пометить "замороженный снимок на дату X"
- [ ] `infra/.memory-bank/open-questions.md` — убрать "CI/CD platform: not chosen yet"

## Фаза 3 — API-спеки под факт

- [ ] `stories/01-.../endpoints.md`: Idempotency-Key и `GET /generations` (список) → будущее время
- [ ] `api-specs/generations_get.yaml`: убрать вложенность `document.content`, привести к плоской форме

## Фаза 4 — архитектурное решение (обсудить перед правкой)

- [ ] **`infrastructure/` vs `infra/`** — решить: (а) создать `infrastructure/`, перенести `infra/*`, или (б) переписать ссылки в `.claude/rules/infrastructure.md` + guidelines + skills (`/run-backend`, `/stop-backend`, `/test-acceptance`, `/demo`, `agent-logging.md`) на `infra/`
- [ ] `/cleanup-chrome` skill: убрать `taskkill /IM chrome.exe /F`, заменить на убийство только процессов текущей сессии
- [ ] Redis в `infra/docker-compose.yml`/CI — оставить как задел под `arq` или убрать

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
- [ ] Проверить, что `git subtree split` реально гоняется перед каждым дедлайном (документ сам называет процесс "currently manual") — если забыли прогнать перед сдачей, GitVerse-репо с CI отстанет от кода вопреки грейдингу

## Фаза 6 — разделение бек/фронт (запрос сокомандника)

- [ ] Разбить `progress.md` истории на `progress-backend.md`/`progress-frontend.md`/`progress-acceptance.md`
- [ ] Обновить `workflow.md`/`workflow-detail.md` под новую структуру progress-файлов
- [ ] Зафиксировать правило владения файлами/слоями между двумя разработчиками в `CLAUDE.md`

## Фаза 7 — верификация живым стеком (опционально, требует Postgres/браузер)

- [ ] Прогнать `adapters/db` тесты против реального Postgres
- [ ] Прогнать `acceptance/` набор целиком (backend+frontend+Chrome)
- [ ] Финальный re-audit `backend-audit-remediation.md`/`frontend-audit-remediation.md` — провести или явно закрыть с текущим счётом
