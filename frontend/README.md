# Textery — фронтенд

Приложение на React + TypeScript + Vite для Textery: пользователь выбирает тип
документа, описывает тему, и наблюдает, как сгенерированный ИИ документ
появляется по мере создания.

## Структура

- `src/app` — сборка приложения: роутинг и навигация по флоу (`useFlowNavigation`).
- `src/features/landing` — маркетинговая посадочная страница.
- `src/features/auth` — регистрация, подтверждение кода, вход, сессия.
- `src/features/generation` — процесс генерации документа: модалки выбора
  типа/режима, чат-подобное рабочее пространство, ручной редактор (`ManualEditor`
  на Tiptap), хук поллинга (`useGeneration`) и HTTP-клиенты.
- `src/features/history` — «Мои работы»: два списка с keyset-пагинацией.
- `src/shared` — то, что принадлежит не одной фиче: транспорт (`api/`),
  словарь типов документов (`documentTypes.ts`), общие компоненты.

### Слои HTTP

```
shared/api/httpClient  — транспорт; про авторизацию не знает ничего
features/auth/api/authorizedRequest — токен, обновление сессии, повтор запроса
shared/api/send        — httpClient + сессия + читаемый текст ошибки
features/*/api/*Api    — конкретные эндпоинты, перевод wire ⇄ приложение
```

`httpClient` намеренно не знает про токены: клиент, добавляющий токен, импортировал бы
сессию, а клиент `/auth/refresh` тогда импортировал бы клиент, который обновляет токен —
цикл. Поэтому авторизация живёт ровно на слой выше. `auth` здесь не «соседняя фича», а
слой сессии: `generation`, `history` и `documents` стоят на нём, обратных импортов нет.

## Установка и запуск

```bash
npm install
npm run dev           # запуск dev-сервера (проксирует /api на бэкенд)
npm run build         # проверка типов + production-сборка
npm run lint          # oxlint
npm run format        # prettier --write
npm run format:check  # prettier --check (этот шаг выполняется в CI)
npm run test          # разовый запуск тестов
npm run test:watch
```

## CI

Пайплайн описан в `.github/workflows/frontend-ci.yml` **в корне репозитория** — GitHub
читает workflow-файлы только оттуда. Раньше рядом лежала копия в `frontend/.github/`,
которая не запускалась никогда и успела разойтись с настоящей: выглядела как источник
правды, но ни на что не влияла. Копия удалена; правьте корневой файл.

CI выполняет: `lint` → `format:check` → `typecheck` → `test` → `build`, затем сборку
docker-образа.

## Переменные окружения

- `VITE_API_BASE_URL` — базовый URL для API генерации. По умолчанию `''`,
  что направляет запросы через прокси `/api` dev-сервера Vite
  (см. `vite.config.ts`, целевой адрес задаётся `VITE_API_PROXY_TARGET`).
- `FRONTEND_PORT` — порт, на котором слушает dev-сервер (по умолчанию `5173`).

## Тестирование

Тесты используют Vitest + Testing Library (`src/test/setup.ts`). Перед
коммитом запускайте `npm run test`; `npm run build` также проверяет типы
через `tsc -b`.
