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
| `adapters/oauth_provider` | Вход через Yandex ID и фейковый провайдер. | `usecase` |
| `adapters/rendering` | Экспорт документа: PDF (WeasyPrint), DOCX, Markdown→HTML. | `usecase` |
| `application` | Точка входа и composition root — связывает всё вместе. | все модули |

Внутренний слой никогда не импортирует внешний: `domain` не знает ни про
FastAPI, ни про SQLAlchemy, `usecase` объявляет порты, а реализуют их адаптеры.

## Установка и запуск

```bash
pip install -r requirements.txt          # только то, что нужно приложению
alembic -c adapters/db/alembic.ini upgrade head        # применить миграции
uvicorn main:app --app-dir application/src/app --reload
```

Для разработки нужен второй файл — он подтягивает первый и добавляет
инструментарий (pytest, ruff, mypy):

```bash
pip install -r requirements-dev.txt
```

Разделение не косметическое: `infra/docker/backend.Dockerfile` ставит именно
`requirements.txt`, и пока файл был один, в production-образ уезжали pytest,
ruff и mypy. По той же причине джоб `audit` в CI проверяет уязвимости только по
runtime-файлу — он отвечает на вопрос «уязвимо ли то, что мы деплоим».

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
| `POST /api/v1/auth/resend-code` | Повторная отправка кода подтверждения (с кулдауном). | нет |
| `GET /api/v1/auth/oauth/{provider}/start` | Шаг 1: редирект к провайдеру. | нет |
| `GET /api/v1/auth/oauth/{provider}/callback` | Шаг 2: редирект обратно с одноразовым кодом передачи. | нет |
| `POST /api/v1/auth/oauth/exchange` | Шаг 3: обмен кода передачи на пару токенов. | нет |
| `POST /api/v1/generations` | Запустить генерацию документа. | да |
| `GET /api/v1/generations` | История своих генераций (keyset-пагинация). | да |
| `GET /api/v1/generations/{id}` | Статус и содержимое генерации. | да |
| `POST /api/v1/documents` | Создать документ (идемпотентно по `Idempotency-Key`). | да |
| `GET /api/v1/documents` | История своих документов. | да |
| `GET /api/v1/documents/{id}` | Прочитать документ. | да |
| `GET /api/v1/documents/{id}/export` | Выгрузить документ файлом (`?format=pdf` или `docx`). | да |
| `PUT /api/v1/documents/{id}` | Сохранить содержимое (оптимистичная блокировка по `version`). | да |
| `GET /health` | Готовность экземпляра: `200` — БД отвечает, `503` — нет. | нет |

`GET /health` намеренно лежит вне `/api/v1` и не требует токена: его вызывает
оркестратор, у которого токена нет, а версионировать инфраструктурный пробник
означало бы привязать перезапуск контейнера к версии клиентского API. Он
проверяет БД и только её — сбой GigaChat выводит из строя один эндпоинт, и
объявлять из-за него весь экземпляр нездоровым значило бы гасить контейнеры,
которые исправно обслуживают вход, историю и редактор.

Токен передаётся заголовком `Authorization: Bearer <access_token>`. Все данные
привязаны к владельцу: чужой ресурс отвечает `404`, а не `403` — `403` подтвердил
бы, что он существует.

## Переменные окружения

Полный список с комментариями — в `.env.example`; скопируйте его в `.env`.

| Переменная | Обязательна | Назначение |
|------------|-------------|------------|
| `DATABASE_URL` | да | Подключение к PostgreSQL (`postgresql+asyncpg://user:password@host:5432/db`). |
| `JWT_SECRET` | да | Ключ подписи HS256. Минимум 32 байта — с более коротким приложение не стартует (RFC 7518 §3.2). Сгенерировать: `openssl rand -hex 32`. |
| `YANDEX_CLIENT_ID` | да | Идентификатор приложения Yandex ID. Проверяется на импорте — **без него приложение не стартует**, независимо от `OAUTH_PROVIDER`. |
| `YANDEX_CLIENT_SECRET` | да | Секрет приложения Yandex ID. Такая же проверка на старте. |
| `YANDEX_REDIRECT_URI` | нет | Куда Yandex возвращает браузер. По умолчанию — адрес callback-страницы фронтенда. |
| `OAUTH_PROVIDER` | нет | `yandex` (по умолчанию) или `fake` — вход без реального провайдера. Выбор `fake` меняет только способ получения личности и **не отменяет** проверку `YANDEX_*` выше. |
| `OAUTH_FRONTEND_CALLBACK_URL` | нет | Страница фронтенда, куда уходит одноразовый код передачи. |
| `OAUTH_HANDOFF_CODE_TTL_SECONDS` | нет | Срок жизни одноразового кода передачи. |
| `OAUTH_RATE_LIMIT_MAX_REQUESTS` | нет | Потолок запросов на источник в окне (грубое ограничение злоупотреблений, не граница авторизации). |
| `OAUTH_RATE_LIMIT_WINDOW_SECONDS` | нет | Длина этого окна. |
| `GENERATION_PROVIDER` | нет | `gigachat` (по умолчанию) или `fake` — запуск без реальных доступов. |
| `GIGACHAT_CREDENTIALS` | при `gigachat` | Доступы к GigaChat. |
| `GIGACHAT_CA_BUNDLE` | нет | Переопределяет вшитый корневой сертификат, если цепочка GigaChat изменится. |
| `GENERATION_STALE_AFTER_MINUTES` | нет | Через сколько минут зависшая генерация перезапускается (по умолчанию 10). |
| `LOG_LEVEL` | нет | Уровень корневого логгера (`INFO` по умолчанию). Нераспознанное значение не роняет старт — приложение возвращается к `INFO`. |
| `TEST_DATABASE_URL` | для тестов | БД для тестов адаптера `db`. |

## Тестирование и проверки

```bash
pytest                      # весь набор
pytest domain usecase       # только быстрые тесты, без БД
ruff check .                # линтер
ruff format --check .       # форматирование
mypy                        # статическая проверка типов (конфиг в pyproject.toml)
mypy --disallow-incomplete-defs domain/src usecase/src adapters/*/src application/src
                            # то же по production-коду, но с запретом частично
                            # аннотированных сигнатур (см. джоб `types` в CI)
python scripts/check_file_size.py   # лимит 200 строк на файл
pip-audit -r requirements.txt   # уязвимости в том, что деплоится
```

Это ровно те проверки, которые гоняет CI (`.github/workflows/ci.yml`), и все они
блокирующие. Прогнать их локально до коммита дешевле, чем узнать о красном
`lint` из отчёта.

Тесты каждого слоя лежат рядом с модулем (`domain/tests`, `usecase/tests`,
`adapters/*/tests`). Живой PostgreSQL нужен только тестам `adapters/db` —
остальные работают без внешних сервисов. Без поднятой БД набор `adapters/db`
целиком помечается `skipped` с указанием причины, а не падает и не зависает.

### База для тестов `adapters/db`

На свежем checkout эти ~70 тестов пропускаются: базы, которую они ждут, ещё нет.
Чтобы они начали выполняться:

```bash
createdb textery_test                    # или: psql -c "CREATE DATABASE textery_test"
export TEST_DATABASE_URL=postgresql://textery:change-me@localhost:5432/textery_test
pytest adapters/db
```

`TEST_DATABASE_URL` можно не задавать — значение по умолчанию именно такое
(`adapters/db/tests/statements/database_url.py`). Задавать его нужно, только
если у вас другой хост, порт или пользователь.

**Имя базы обязано содержать `test`.** Набор делает `TRUNCATE` всех таблиц между
фикстурами, поэтому `resolve_test_database_url()` отказывается работать с базой,
чьё имя этого не подтверждает. Проверка появилась не из осторожности: 2026-08-06
значением по умолчанию была рабочая база `textery`, полный прогон `pytest`
стёр данные локального стенда, и первым симптомом стал 401 на пароле, который
минуту назад работал.

CI держит покрытие не ниже 90% (`--cov-fail-under`); фактическое — 98%.

Корни слоёв подключаются через `pythonpath` в `pyproject.toml`, поэтому `pytest`
запускается из этого каталога без настройки `PYTHONPATH`.

## История изменений

[`CHANGELOG.md`](CHANGELOG.md) — что вошло в каждую версию, включая принятые
ограничения. Версия объявлена в `pyproject.toml` и совпадает с верхним
выпущенным заголовком changelog.
