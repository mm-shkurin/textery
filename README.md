# Textery

Сервис автогенерации студенческих работ (доклад, эссе, сочинение, реферат) с
редактором и экспортом в PDF/DOCX. Монорепозиторий: backend, frontend,
приёмочные тесты и инфраструктура в одном дереве.

**Публичный деплой: https://mmshkurin.ru**

Правила сезона (`.memory-bank/sprint.txt`) обнуляют спринт за нерабочую или
отсутствующую публичную ссылку — проверять её перед каждой пятницей. Развернуть
свою копию: см. «Запуск» ниже.

## Что внутри

| Каталог | Что это | Своя документация |
|---|---|---|
| `backend/` | FastAPI, Чистая архитектура: `domain → usecase → adapters → application` | [backend/README.md](backend/README.md) |
| `frontend/` | React 18 + TypeScript + Vite, фич-модули | [frontend/README.md](frontend/README.md), [CONTRIBUTING](frontend/CONTRIBUTING.md) |
| `acceptance/` | Чёрный ящик: HTTP-сценарии и Selenium, без зависимости на внутренности backend | — |
| `infra/` | docker-compose, Dockerfile-ы, nginx | [infra/architecture.md](infra/architecture.md) |
| `ProductSpecification/` | Истории, контракты API, тест-кейсы, прогресс | [stories.md](ProductSpecification/stories.md) |
| `.claude/` | Агентный фреймворк разработки: правила, скиллы, гайдлайны | [CLAUDE.md](CLAUDE.md) |
| `_project_audit/` | Аудиты «документация против кода» | [00_INDEX.md](_project_audit/00_INDEX.md) |

`backend/` и `frontend/` дополнительно публикуются как самостоятельные
репозитории, поэтому у каждого свои `Dockerfile`, `docker-compose.yml`, README и
копия тест-кейсов в `docs/testing/` (генерируется из `ProductSpecification/`,
править надо там).

## Стек

Python 3.12 / FastAPI / SQLAlchemy 2.0 async / Alembic / PostgreSQL;
React 18 / TypeScript / Vite / Vitest / oxlint; Selenium для браузерных
сценариев; генерация — GigaChat (Sber) через прямой `httpx`-клиент, задания
исполняются inline на FastAPI `BackgroundTasks` плюс периодический DB-sweep.
Полная таблица с командами и конвенциями —
[ProductSpecification/technology.md](ProductSpecification/technology.md).

## Запуск

Весь стек в контейнерах (Postgres, Redis, backend с миграциями на старте,
frontend, собранный Vite и отданный nginx):

```bash
cp infra/.env.example infra/.env        # заполнить значения
cp backend/.env.example backend/.env    # GIGACHAT_CREDENTIALS и прочие секреты бэкенда
docker compose -f infra/docker-compose.yml up -d --build
```

Порты host-side задаются переменными из `infra/.env` (`BACKEND_PORT`,
`FRONTEND_PORT`, `POSTGRES_PORT`, `REDIS_PORT`) — хардкодить их нельзя, на одном
хосте параллельно работают несколько копий. Контракт переменных целиком — в
[infra/architecture.md](infra/architecture.md).

Локальная разработка без контейнеров: `uvicorn app.main:app --reload --port $BACKEND_PORT`
для бэкенда, `npm run dev` для фронтенда.

## Тесты

```bash
pytest backend/                       # юнит- и адаптерные тесты бэкенда
cd frontend && npx vitest run         # фронтенд
pytest acceptance/tests/backend       # приёмочные HTTP-сценарии (нужен поднятый стек)
pytest acceptance/tests/frontend      # Selenium (нужны стек и браузер)
```

## Как ведётся разработка

TDD/ATDD + Чистая архитектура, цикл red → green → refactor на сценарий, состояние
живёт в progress-файлах историй, а не в голове. Правила — в
[CLAUDE.md](CLAUDE.md) и `.claude/rules/`. Pull request-ов нет: коммиты уходят
прямо в рабочую ветку, поэтому *почему* сделано именно так пишется в сообщении
коммита.

Что реально работает на сегодня —
[ProductSpecification/progress-summary.md](ProductSpecification/progress-summary.md);
где что не доделано — [stories.md](ProductSpecification/stories.md) и
[.memory-bank/tasks/known-debt.md](.memory-bank/tasks/known-debt.md).
