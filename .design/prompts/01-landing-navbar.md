# Сессия 1 — Главная страница (Desktop) + Navbar авторизованного пользователя

Сначала прочитай `.design/prompts/_common.md` и `.design/cache/MANIFEST.md`.

## Источники
- `.design/cache/nodes/landing-desktop.json` — фрейм `Desktop` (node `90:880`), главная страница.
- `.design/cache/nodes/navbar-variant5.json` — компонент `Navbar/Variant5` (node `1086:4929`),
  состояние навбара, когда пользователь **авторизован**.
- Ассеты: `.design/cache/assets/icon-*.svg` — 37 иконок 24px (в т.ч. `icon-profile`,
  `icon-settings`, `icon-logout`, `icon-plus`, `icon-home`, `icon-search`).
- Токены: `.design/cache/tokens.json` — шрифт Inter, акцент `#004EE0`, текст
  `#1F1F1F` / `#6B7280` / `#464551`, радиусы 8/12/16, тень `0 4 12 #00000017`.

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
