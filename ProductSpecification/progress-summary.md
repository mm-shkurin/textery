# Текущий прогресс проекта Textery — функциональная сводка

Обновлено: 2026-08-15 (аудит документации, `_project_audit/07_DOC_AUDIT_2026-08-15.md`).
Источники: `ProductSpecification/stories.md`, progress-файлы историй и **прямая сверка
с кодом** — маршруты `backend/adapters/rest/src/router/`, модули
`frontend/src/features/`, сценарии `acceptance/tests/`.

> Предыдущая редакция (2026-07-15) описывала только истории 1 и 7 как «единственные в
> работе» и месяц читалась как текущее состояние. Раздел «Что было в редакции 15.07»
> ниже сохраняет её выводы как исторический срез.

## Что доступно по API (маршруты, проверено 2026-08-15)

| Область | Эндпоинты |
|---|---|
| Аутентификация | `POST /api/v1/auth/register`, `/verify`, `/resend-code`, `/login`, `/refresh` |
| OAuth | `GET /api/v1/auth/oauth/{provider}/start`, `/{provider}/callback`, `POST /api/v1/auth/oauth/exchange` — Yandex ID доведён до конца, VK ID в контракте есть, учётных данных нет и он отвечает именованной ошибкой |
| Профиль | `GET`/`PATCH /api/v1/auth/me`; аватар — `PUT`/`GET`/`DELETE /api/v1/auth/me/avatar`; удаление аккаунта — `POST /api/v1/auth/me/deletion` |
| Генерация | `POST /api/v1/generations`, `GET /api/v1/generations`, `GET /{id}`, `POST /{id}/retry` |
| Документы | `POST /api/v1/documents`, `POST /from-generation`, `GET`, `GET /{id}`, `PUT /{id}`, `GET /{id}/export` |
| Лента проектов | `GET /api/v1/projects` — offset-пагинация, поиск, 4 порядка сортировки, объединённая лента |
| Служебное | `GET /health` |

Генерация идёт через GigaChat (прямой `httpx`-клиент), inline в ASGI-процессе на
`BackgroundTasks`, с периодическим DB-sweep для зависших задач. Отдельного воркера нет.

## Что есть на фронтенде

Фич-модули `frontend/src/features/`: `landing`, `auth`, `generation`, `history`,
`projects`, `profile`. Тёмная тема, редактор на TipTap, автосохранение, экспорт.
Selenium-сценарии — `acceptance/tests/frontend/{auth,generation,landing,profile}`,
backend-сценарии — `acceptance/tests/backend/{authorization,auto_generate_doklad,documents,oauth,profile,projects}`.
Всего 71 acceptance-файл.

## Где проходит граница «работает» / «не отслеживается»

Роллап фаз — `stories.md`. Три места, где код опережает отслеживание, и это не
оценка, а факт из аудита:

- **Story 13 (профиль)** — код смержен 14.08 вне per-scenario цикла;
  `progress-backend.md`/`progress-frontend.md` не заведены, 130 сценариев тест-спеки
  не размечены. В `stories.md` стоит `n/t`, не `0%`.
- **Story 16 (OAuth)** — backend в reduced-TDD, добор в
  `tasks/6-refactoring-oauth-tdd-backfill/`.
- **Story 5 (ручной ввод)** — `progress-backend.md` не заведён с 20.07,
  backend-чеклист не бутстрапнут из тест-спек.

## Чего в продукте нет

Истории 6 (выбор модели по тарифу), 8 (биллинг), 9 (лендинг и маркетинг),
11 (переименование/удаление/дублирование документов), 14 (аналитика), 15 (отчёты и
CSV) — только названия в бэклоге. Истории 2 и 3 (эссе, сочинение) имеют папку с
`interview.md` и `progress.md`, но своей спеки и сценариев ещё нет: типы работают за
счёт общего слайса генерации.

## Что было в редакции 15.07 (исторический срез)

На тот момент end-to-end работали: регистрация с валидацией email/пароля,
защита от дублей и гонок на уровне БД, регистронезависимая и Unicode-нормализованная
уникальность адреса (ADR `decisions/unicode-email-normalization-decision.md`), приём
запроса на генерацию доклада и отслеживание статуса через API, а на фронтенде — путь
от лендинга до формы генерации включительно. Подтверждение по коду, логин, refresh,
сама генерация текста и все остальные истории тогда числились не начатыми — с тех пор
закрыты аутентификация целиком, OAuth, генерация, редактор, экспорт, лента проектов и
профиль.
