# Textery — бэкенд

Бэкенд Textery на FastAPI, построенный по принципам Чистой архитектуры
(Clean Architecture): зависимости направлены только внутрь.

## Структура

```
application → adapters → usecase → domain
```

| Модуль | Назначение | Зависит от |
|--------|------------|------------|
| `domain` | Сущности, объекты-значения, исключения. Без фреймворков. | — |
| `usecase` | Сценарии использования, интерфейсы портов. | `domain` |
| `adapters/rest` | HTTP-контроллеры, DTO, обработчики ошибок, разбор Bearer-токена. | `usecase` |
| `adapters/db` | Репозитории SQLAlchemy и миграции Alembic. | `usecase` |
| `adapters/security` | Хеширование паролей (bcrypt), JWT, санитизация HTML (nh3). | `usecase` |
| `adapters/generation_provider` | Интеграция с GigaChat и фейковый провайдер. | `usecase` |
| `application` | Точка входа и composition root — связывает всё вместе. | все модули |

Внутренний слой никогда не импортирует внешний: `domain` не знает ни про
FastAPI, ни про SQLAlchemy, `usecase` объявляет порты, а реализуют их адаптеры.

## Установка и запуск

```bash
pip install -r requirements.txt
alembic -c adapters/db/alembic.ini upgrade head        # применить миграции
uvicorn main:app --app-dir application/src/app --reload
```

Команды выполняются из этого каталога (`backend/`). `--app-dir` обязателен:
`main.py` — это composition root, он добавляет корни слоёв в `sys.path` при
старте, поэтому импортировать его нужно как модуль `main`.

Документация API поднимается вместе с приложением: `/docs` (Swagger UI) и
`/redoc`.

## API

Все ответы об ошибках имеют единую форму `{"error_code": ..., "message": ...}`.

| Метод и путь | Назначение | Требует токен |
|--------------|------------|---------------|
| `POST /api/v1/auth/register` | Регистрация, выдаёт код подтверждения. | нет |
| `POST /api/v1/auth/verify` | Подтверждение аккаунта кодом. | нет |
| `POST /api/v1/auth/login` | Логин, выдаёт пару access/refresh. | нет |
| `POST /api/v1/auth/refresh` | Обновление пары по refresh-токену. | нет |
| `POST /api/v1/generations` | Запустить генерацию документа. | да |
| `GET /api/v1/generations` | История своих генераций (keyset-пагинация). | да |
| `GET /api/v1/generations/{id}` | Статус и содержимое генерации. | да |
| `POST /api/v1/documents` | Создать документ (идемпотентно по `Idempotency-Key`). | да |
| `GET /api/v1/documents` | История своих документов. | да |
| `GET /api/v1/documents/{id}` | Прочитать документ. | да |
| `PUT /api/v1/documents/{id}` | Сохранить содержимое (оптимистичная блокировка по `version`). | да |

Токен передаётся заголовком `Authorization: Bearer <access_token>`. Все данные
привязаны к владельцу: чужой ресурс отвечает `404`, а не `403` — `403` подтвердил
бы, что он существует.

## Переменные окружения

Полный список с комментариями — в `.env.example`; скопируйте его в `.env`.

| Переменная | Обязательна | Назначение |
|------------|-------------|------------|
| `DATABASE_URL` | да | Подключение к PostgreSQL (`postgresql+asyncpg://user:password@host:5432/db`). |
| `JWT_SECRET` | да | Ключ подписи HS256. Минимум 32 байта — с более коротким приложение не стартует (RFC 7518 §3.2). Сгенерировать: `openssl rand -hex 32`. |
| `GENERATION_PROVIDER` | нет | `gigachat` (по умолчанию) или `fake` — запуск без реальных доступов. |
| `GIGACHAT_CREDENTIALS` | при `gigachat` | Доступы к GigaChat. |
| `GIGACHAT_CA_BUNDLE` | нет | Переопределяет вшитый корневой сертификат, если цепочка GigaChat изменится. |
| `GENERATION_STALE_AFTER_MINUTES` | нет | Через сколько минут зависшая генерация перезапускается (по умолчанию 10). |
| `TEST_DATABASE_URL` | для тестов | БД для тестов адаптера `db`. |

## Тестирование и проверки

```bash
pytest                      # весь набор
pytest domain usecase       # только быстрые тесты, без БД
ruff check .                # линтер
ruff format --check .       # форматирование
mypy                        # статическая проверка типов (конфиг в pyproject.toml)
```

Тесты каждого слоя лежат рядом с модулем (`domain/tests`, `usecase/tests`,
`adapters/*/tests`). Живой PostgreSQL нужен только тестам `adapters/db` —
остальные работают без внешних сервисов. Без поднятой БД набор `adapters/db`
целиком помечается `skipped` с указанием причины, а не падает и не зависает.

CI держит покрытие не ниже 90% (`--cov-fail-under`); фактическое — 98%.

Корни слоёв подключаются через `pythonpath` в `pyproject.toml`, поэтому `pytest`
запускается из этого каталога без настройки `PYTHONPATH`.

## История изменений

[`CHANGELOG.md`](CHANGELOG.md) — что вошло в каждую версию, включая принятые
ограничения. Версия объявлена в `pyproject.toml` и совпадает с верхним
выпущенным заголовком changelog.
