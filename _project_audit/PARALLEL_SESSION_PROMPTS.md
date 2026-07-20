# Параллельные сессии backfill'а — сетап и промпты

3 сессии Claude Code, каждая в своём worktree. Разделение по слоям (File Ownership,
CLAUDE.md). Читать вместе с `FRAMEWORK_BACKFILL_PLAN.md`.

## Worktree (на Рабочем столе)

| Каталог | Ветка | Роль |
|---|---|---|
| `textery-be`  | `backfill/backend`   | S1 — backend |
| `textery-fe`  | `backfill/frontend`  | S2 — frontend |
| `textery-rec` | `backfill/reconcile` | S3 — reconcile (без кода) |

Запускай Claude Code в каждом каталоге отдельно. Порты — из `infra/.env`, не хардкодь.
Процессы/контейнеры чужих сессий не трогай. Запусти **S3 первой** — она даёт S1/S2
готовые чеклисты.

---

## Промпт S1 — Backend

```
Ты backend-сессия backfill'а Textery. Рабочий каталог — этот worktree (branch backfill/backend).

ГРАНИЦЫ (File Ownership, CLAUDE.md — строго):
- Правишь ТОЛЬКО: backend/, acceptance/tests/backend/, ProductSpecification/stories/*/progress-backend.md
- Общие файлы (progress.md narrative, stories.md) — только строки своего слоя, чужие не переписываешь.
- НЕ трогаешь frontend/, acceptance/tests/frontend/, progress-frontend.md.

ЦЕЛЬ: прогнать весь backend через TDD-фреймворк по _project_audit/FRAMEWORK_BACKFILL_PLAN.md.

ЦИКЛ (повторяй, пока в твоём слое есть незакрытые сценарии):
1. Прочитай _project_audit/FRAMEWORK_BACKFILL_PLAN.md и reconcile-чеклист _project_audit/RECONCILE_*.md (если появился).
2. Следующая backend-дыра по приоритету: stale-skip acceptance (снять skip, сверить причину) → отсутствующее поведение (Story 7 rejection 3.2–3.6; Story 5 backend после бутстрапа progress-backend.md) → остаточные [ ] Story 1.
3. Если Story 5 backend не трекается — сначала забутстрапь progress-backend.md из tests/{01_API,05_Security,06_Integration}_Tests.md.
4. Полный work-unit через /continue (red-* → test-review → commit → refactor → commit). Атомарно, не стопай между суб-скиллами.
5. Off-framework код меть [S] "backfill pending", НИКОГДА [x] без red→green/acceptance. Skip-причины датируй: reason="RED 2026-07-DD: ...".
6. Commit на ветку (проект без PR). Префикс по типу работы.
7. Повтори с шага 1.

ХОСТ: порты из infra/.env. Чужие процессы/контейнеры не убивай (не по имени exe). Не блокируйся >30с (run_in_background + короткие поллы).
СТОП: все backend/integration/security сценарии активных историй закрыты, ИЛИ суб-скилл упал (report и стоп).
```

---

## Промпт S2 — Frontend

```
Ты frontend-сессия backfill'а Textery. Рабочий каталог — этот worktree (branch backfill/frontend).

ГРАНИЦЫ (File Ownership, строго):
- Правишь ТОЛЬКО: frontend/, acceptance/tests/frontend/, ProductSpecification/stories/*/progress-frontend.md
- Общие файлы (progress.md, stories.md) — только свой слой.
- НЕ трогаешь backend/, acceptance/tests/backend/, progress-backend.md.

ЦЕЛЬ: прогнать весь frontend через TDD-фреймворк по _project_audit/FRAMEWORK_BACKFILL_PLAN.md.

ЦИКЛ (повторяй, пока есть незакрытые frontend-сценарии):
1. Прочитай FRAMEWORK_BACKFILL_PLAN.md и reconcile-чеклист (если есть).
2. Следующая frontend-дыра: stale-skip Selenium (test_manual_editor_acceptance.py — снять skip, локатор под contenteditable; landing hero-subheading known-debt #12) → модалки Story 1 без red→green ([S] 1.2/2.1/2.2/3.1/3.2 — характеризационный red или оставить осознанно) → остаточные frontend Story 5.
3. Полный work-unit через /continue (red-frontend → test-review → commit → refactor → commit; для Selenium — green-selenium/demo). Атомарно.
4. Перед Selenium — /cleanup-chrome (только осиротевшие процессы, НЕ по имени exe). Чужие Chrome/chromedriver не трогай.
5. Off-framework код меть [S] "backfill pending", НИКОГДА [x] без покрытия. Skip-причины датируй.
6. Commit на ветку, префикс по типу.
7. Повтори.

ХОСТ: порты из infra/.env. Не блокируйся >30с.
СТОП: все frontend-сценарии активных историй закрыты, ИЛИ суб-скилл упал.
```

---

## Промпт S3 — Reconcile (без кода, запускать первой)

```
Ты reconcile-сессия Textery. НЕ пишешь прод-код и НЕ правишь тесты. Пишешь ТОЛЬКО новые доки в _project_audit/. Задача — кормить backend/frontend сессии точными чеклистами.

ЦЕЛЬ: Фаза A из _project_audit/FRAMEWORK_BACKFILL_PLAN.md — классификация всех пропусков.

ЦИКЛ (по историям 1, 5, 7, потом заново на верификацию):
1. Возьми историю. grep -rn "\[S\]|pytest.mark.skip" по её progress-*.md и acceptance/tests/.
2. Классифицируй КАЖДЫЙ пропуск, сверяя с реальным кодом (backend/frontend read-only):
   - legit — делать нечего (нет порта / покрыто прошлым сценарием) → не в backlog;
   - deferred — поведение отложено, не построено → в backlog;
   - stale — причина ложна СЕГОДНЯ (сверено с кодом) → в backlog как срочное.
3. Пиши в _project_audit/RECONCILE_<story>.md: таблица файл:строка | тип | причина | что делать | слой (backend/frontend). Датируй.
4. Каждый @pytest.mark.skip reason сверяй с кодом — протухшие помечай stale + доказательство (файл:строка кода, опровергающего причину).
5. НИЧЕГО в коде/тестах не меняешь. Только _project_audit/*.md.
6. Commit доков на свою ветку.
7. Следующая история; после всех — второй проход на верификацию (что закрыли code-сессии — вычёркивай).

СТОП: RECONCILE_*.md полны для всех активных историй и второй проход не находит нового.
```

---

## Слияние обратно

Ветки `backfill/*` мержить в `dev` по мере закрытия слоёв. Миграции backend
сериализуй вручную (linear Alembic chain — не давай двум сессиям плодить два head).
