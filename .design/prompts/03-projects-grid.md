# Сессия 3 — «Мои проекты», вид сетка (вариант 1, Desktop)

Сначала прочитай `.design/prompts/_common.md` и `.design/cache/MANIFEST.md`.

## Источники
- `.design/cache/nodes/projects-grid.json` — «Мои проекты - вид сетка - вариант 1 (Dekstop)» (node `484:1104`).
- `.design/cache/nodes/projects-grid-mobile.json` — Mobile рядом (node `674:2534`, ширина 360).
- Иконки: `.design/cache/assets/icon-grid.svg`, `icon-list.svg`, `icon-filter.svg`,
  `icon-sort.svg`, `icon-search.svg`, `icon-rename.svg`, `icon-dublicate.svg`,
  `icon-delete.svg`, `file-*.svg` (превью по типу документа).

## Область (только эти пути)
- `frontend/src/features/projects/**`
- `frontend/src/features/history/**` (только если список проектов рендерится оттуда —
  сперва проверь, кто реально рисует сетку)
- `frontend/src/shared/formatCardDate.ts` (только если формат даты в макете другой)
- тесты в `frontend/src/features/projects/__tests__/**`
- **Навбар и тему не править** — сессия 1. Экран создания проекта — сессия 2.

## Задачи
1. Сетка карточек по фрейму: число колонок, gap, ширина/высота карточки, радиусы,
   тени, поведение при переполнении названия.
2. Карточка проекта: превью, заголовок, дата, тип, меню действий — состав и порядок
   строго по макету. Состояния: hover, выбранная, пустой список.
3. Панель над сеткой (поиск/фильтры/переключатель вида), если он есть во фрейме.
4. Даты и названия — из данных, не из макета.

## Отчёт
Правки, параметры сетки, недостающие ноды/ассеты (node id), результат `/test-frontend`.
