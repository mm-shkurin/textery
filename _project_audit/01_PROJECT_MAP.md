# Карта проекта Textery

> Это read-only аудит. Ничего в проекте не менялось. Все выводы ниже — по состоянию на 2026-07-13, ветка `dev`.

Textery — сервис автогенерации студенческих работ (докладов, эссе, сочинений, рефератов) через AI. Сейчас в разработке только первая история — "Auto-generate: доклад".

## Как устроен репозиторий: два независимых слоя

Репозиторий одновременно содержит:
1. **Само приложение** — backend (Python/FastAPI) + frontend (TypeScript/React) + acceptance-тесты (чёрный ящик, Python/Selenium).
2. **Агентный фреймворк Claude Code** — набор правил, скиллов и агентов, которые управляют тем, *как* пишется код (строгий TDD-цикл через специализированных саб-агентов).

Ниже — назначение каждой корневой директории.

## Директории верхнего уровня

| Директория | Что это (простыми словами) | Статус |
|---|---|---|
| `backend/` | Само приложение-сервер на Python/FastAPI. Разбито на 5 под-модулей (domain/usecase/adapters×3/application) по принципу Clean Architecture — см. `.claude/rules/coding-rules.md`. | Активно используется, реальный код |
| `frontend/` | Само веб-приложение на React/TypeScript (Vite). | Активно используется, реальный код |
| `acceptance/` | Чёрные ящик-тесты: гоняют реальный HTTP API и реальный браузер (Selenium) снаружи, не видя внутренностей backend/frontend. | Активно используется, 8 реальных тестовых сценариев |
| `ProductSpecification/` | Спецификации продукта: что строим, зачем, как выглядит экран, какие тесты нужны, какие технологии выбраны. Это "источник истины" о требованиях. | Активно ведётся |
| `.claude/` | **Корневой** агентный фреймворк — правила и инструменты, которыми Claude Code пользуется, чтобы вести TDD-разработку. Подробно — в `02_FRAMEWORK_GUIDE.md`. | Активно используется, ежедневный инструмент |
| `.agents/` | Сторонний, не связанный с Textery набор скиллов `caveman*`/`cavecrew` — личный плагин пользователя для сжатого стиля общения с Claude (установлен из внешнего GitHub-репозитория, см. `skills-lock.json`). Никак не участвует в разработке продукта. | Не относится к продукту, но используется как личный инструмент |
| `.memory-bank/` | **Более старая** система планирования (Figma-скриншоты, `sprint.txt`, `tz.md`, `known-debt.md`, `steerings/development-conventions.md`) — судя по всему, предшествовала появлению `ProductSpecification/` и текущего `.claude/`-фреймворка. Частично устарела, частично всё ещё читается (`known-debt.md` явно цитируется из `technology.md`). | Смешанный статус — не выбрасывать, но не единственный источник истины |
| `infra/` | **Реальная** инфраструктура: Docker Compose, Dockerfile'ы backend/frontend, nginx-конфиг, плюс **собственный отдельный** мини-фреймворк `infra/.claude/` для deployment-задач ("Mini Dev-Loop Harness"). | Активно используется |
| `infrastructure/` | Пустая директория (0 файлов). На неё ссылается весь `.claude/rules/infrastructure.md` и связанные guidelines/skills — но реальная инфраструктура физически лежит в `infra/` (см. выше). Это ключевое расхождение проекта. | **Пустая, но на неё ссылается документация** — не мусор в смысле "случайный файл", аadres несуществующего назначения |
| `.github/` | GitHub Actions CI: `backend-ci.yml`, `frontend-ci.yml`. См. также дублирующиеся копии внутри `backend/.github/` и `frontend/.github/` (ниже). | Активно используется, но дублирован и разошёлся |
| `.idea/` | Служебные файлы IDE (IntelliJ/PyCharm). Стандартный артефакт редактора, не имеет отношения к логике проекта. | Служебное, игнорируется в `.gitignore`? — фактически не в `.gitignore` (см. `05_CLEANUP_CANDIDATES.md`) |
| `qodana.yaml` (файл в корне) | Черновой конфиг статического анализатора JetBrains Qodana. **Untracked** (не закоммичен), 0 упоминаний в git-истории, линтер указан как `jetbrains/qodana-jvm-community` — это анализатор для Java/Kotlin, тогда как проект на Python+TypeScript. Похоже на не доведённый до конца эксперимент. | Черновик, не внедрён |
| `skills-lock.json` (файл в корне) | Файл блокировки версий для скилл-плагинов, установленных из внешних источников (сейчас — только `caveman*`/`cavecrew` из GitHub). | Служебный, относится к `.agents/`, не к продукту |
| `CLAUDE.md` (файл в корне) | Главная точка входа фреймворка — объясняет архитектуру и указывает, какой guideline читать перед той или иной работой. | Активно используется |

## Внутри `backend/` — слои Clean Architecture

| Модуль | Назначение | Зависит от |
|---|---|---|
| `backend/domain` | Сущности и бизнес-правила (`Generation`, исключения валидации). Ничего не знает про базу данных, HTTP или фреймворки. | Ничего (только стандартная библиотека Python) |
| `backend/usecase` | Сценарии использования (`GenerateDocument`, `GetGeneration`, `RequestGeneration`, `RequeueStaleGenerations`) + порты (интерфейсы для БД/очереди/провайдера генерации). | `domain` |
| `backend/adapters/rest` | HTTP-контроллеры (FastAPI-роутеры), DTO, обработка ошибок. | `usecase` |
| `backend/adapters/db` | Работа с PostgreSQL через SQLAlchemy (async) + миграции Alembic. | `usecase` |
| `backend/adapters/generation_provider` | Реальный клиент AI-провайдера (GigaChat — не OpenRouter, см. `03_REAL_PROJECT_STATUS.md`) + тестовая заглушка `FakeProvider`. | `usecase` |
| `backend/application` | Точка входа (`main.py`) и composition root (`container.py`) — здесь всё связывается воедино. | Все модули |

## Внутри `ProductSpecification/` — спецификации

| Путь | Назначение |
|---|---|
| `BriefProductDescription.md` | Краткое описание продукта в целом. |
| `technology.md` | Заявленный технологический профиль (см. drift-файл — часть пунктов разошлась с реальностью). |
| `stories.md` | Таблица историй: In Progress / Backlog / Done, с прогрессом по фазам (Spec/Back/Intg/Front/Sec/Load/Infra) и счётчиком тестов. |
| `ExpectedLoad.md` | Ожидаемая нагрузка (для load-тестов). |
| `ui/ui-conventions.md` | UI-конвенции для мокапов/фронтенда. |
| `api-specs/*.yaml` | OpenAPI-спецификации трёх эндпоинтов генерации. |
| `stories/01-auto-generate-doklad/` | Вся папка первой (и единственной начатой) истории: интервью, мокапы, тесты по 6 категориям, `progress.md` (состояние), `carryover.md`, ADR (`decisions/`), several `*-fix-plan.md`/`*-audit-remediation.md`/`*-demo-plan.md` — рабочие артефакты, накопленные за ~6 дней интенсивной разработки. |
| `tasks/` | Отдельные (не story-based) задачи: `1-refactoring-generation-error-handling`, `2-refactoring-generation-hardening` (обе фактически завершены, но не перенесены в `done/`), `tasks/done/3-refactoring-backfill-generation-tdd-coverage` (перенесена корректно). |

## Где что искать

- **Приложение (продукт)** → `backend/`, `frontend/`, `acceptance/`.
- **Агентный фреймворк (как разрабатывается)** → `.claude/` (корневой, для backend/frontend/acceptance), `infra/.claude/` (отдельный, для инфраструктуры/деплоя).
- **Спецификации (что строим)** → `ProductSpecification/`.
- **Временные/устаревшие материалы** → `.memory-bank/` (предыдущая система планирования, частично актуальна), `infrastructure/` (пустая директория-призрак), `qodana.yaml` (недоделанный черновик), `.agents/` (сторонний плагин, не о продукте).

Подробности по технологиям и расхождениям — в `03_REAL_PROJECT_STATUS.md` и `04_DOCUMENTATION_DRIFT.md`. Подробности по агентному фреймворку — в `02_FRAMEWORK_GUIDE.md`.
