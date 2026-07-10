# Textery — фронтенд

Приложение на React + TypeScript + Vite для Textery: пользователь выбирает тип
документа, описывает тему, и наблюдает, как сгенерированный ИИ документ
появляется по мере создания.

## Структура

- `src/features/landing` — маркетинговая посадочная страница.
- `src/features/generation` — процесс генерации документа: модалки выбора
  типа/режима, чат-подобное рабочее пространство, хук поллинга
  (`useGeneration`) и HTTP-клиент (`generationApi`).
- `src/shared` — компоненты, общие для разных фич.

## Установка и запуск

```bash
npm install
npm run dev      # запуск dev-сервера (проксирует /api на бэкенд)
npm run build    # проверка типов + production-сборка
npm run lint      # oxlint
npm run test      # разовый запуск тестов
npm run test:watch
```

## Переменные окружения

- `VITE_API_BASE_URL` — базовый URL для API генерации. По умолчанию `''`,
  что направляет запросы через прокси `/api` dev-сервера Vite
  (см. `vite.config.ts`, целевой адрес задаётся `VITE_API_PROXY_TARGET`).
- `FRONTEND_PORT` — порт, на котором слушает dev-сервер (по умолчанию `5173`).

## Тестирование

Тесты используют Vitest + Testing Library (`src/test/setup.ts`). Перед
коммитом запускайте `npm run test`; `npm run build` также проверяет типы
через `tsc -b`.
