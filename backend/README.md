# Textery — бэкенд

Бэкенд Textery на FastAPI, построенный по принципам Чистой архитектуры
(Clean Architecture): зависимости направлены только внутрь.

## Структура

```
application → adapters → usecase → domain
```

- `domain` — сущности, объекты-значения, исключения. Без зависимостей от
  фреймворков.
- `usecase` — сценарии использования (application services), интерфейсы
  портов. Зависит только от `domain`.
- `adapters/rest` — веб-контроллеры, авторизация.
- `adapters/db` — репозитории и миграции базы данных.
- `adapters/generation_provider` — интеграция с провайдером генерации.
- `application` — точка входа, связывающая все модули вместе.

## Установка и запуск

```bash
pip install -r requirements.txt
alembic -c adapters/db/alembic.ini upgrade head   # применить миграции
uvicorn application.src.main:app --reload         # запуск сервера
```

## Переменные окружения

- `DATABASE_URL` — строка подключения к PostgreSQL
  (`postgresql+asyncpg://user:password@host:5432/db`).
- `REDIS_URL` — строка подключения к Redis.
- `GENERATION_PROVIDER` — используемый провайдер генерации (`fake` для
  тестов/локальной разработки).

## Тестирование

```bash
pytest --cov --cov-report=xml:coverage.xml
```

Тесты каждого слоя лежат рядом с соответствующим модулем
(`domain/tests`, `usecase/tests`, `adapters/*/tests`).
