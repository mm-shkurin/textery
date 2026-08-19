# Сессия 1 — Главная страница (Desktop) + Navbar авторизованного пользователя

Сначала прочитай `.design/prompts/_common.md` и `.design/cache/MANIFEST.md`.

## Источники
- `.design/cache/nodes/landing-desktop.json` — фрейм `Desktop`, главная страница.
- `.design/cache/nodes/navbar-variant5.json` — фрейм `Navbar/Variant5`,
  состояние навбара, когда пользователь **авторизован**.
- Ассеты: `.design/cache/assets/` (иконки svg, иллюстрации png@2x).

## Область (только эти пути)
- `frontend/src/features/landing/**`
- `frontend/src/shared/components/navbar/**`, `frontend/src/shared/components/AppHeader.tsx`
- `frontend/src/shared/theme/**`, `frontend/src/styles/**` (только добавление токенов;
  существующие значения не переименовывать — их читают чужие сессии)
- `frontend/src/features/landing/__tests__/**`, тесты навбара

## Задачи
1. Выровнять `LandingPage`/`Header` по фрейму `Desktop`: сетка, ширина контейнера,
   вертикальные ритмы, типографика, кнопки, состояния hover/focus.
2. Навбар: сделать вариант для авторизованного пользователя строго по
   `Navbar/Variant5` — состав элементов, аватар/меню, порядок, отступы, активный пункт.
   Неавторизованный вариант оставить рабочим — оба состояния должны существовать.
3. Ассеты положить в `frontend/src/assets/` (или туда, где они уже лежат по проекту),
   svg подключать как компоненты, png — с `srcset`/2x.
4. Токены, которых не хватает, добавить в тему; в отчёте перечислить добавленные имена —
   остальные сессии на них опираются.

## Отчёт
Список правок, добавленные токены, недостающие ноды/ассеты (node id), результат `/test-frontend`.
