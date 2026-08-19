# Сессия 2 — Экран генерации («Мои проекты — Создать проект») + мобилка + карточки типов

Сначала прочитай `.design/prompts/_common.md` и `.design/cache/MANIFEST.md`.

## Источники
- `.design/cache/nodes/create-project.json` — desktop-фрейм «Мои проекты - Создать проект» (node `788:5094`).
- `.design/cache/nodes/create-project-mobile.json` — мобильный фрейм рядом (node `1227:9974`, ширина 360).
- `.design/cache/nodes/cards-images.json` — `Cards/Images color folders` (node `788:6243`),
  8 вариантов: Referat, Resume, Doklad, Sochinenia, Essay, Buisness plan, Summary, Letter.
- Иконки типов файлов: `.design/cache/assets/file-*.svg` (referat, resume, doklad,
  sochinenie, essay, buisness-plan, summary, letter) + `icon-*.svg`.
- **`card-*.png` в кэше пока нет** — их экспорт упёрся в 429. Верстай карточки
  на `file-*.svg`, место под картинку зарезервируй по геометрии из `cards-images.json`
  и вынеси путь к ассету в маппинг, чтобы подмена на png была однострочной.
  Сам за png в Figma НЕ ходи — это сделает сессия 0.

## Область (только эти пути)
- `frontend/src/features/generation/**`
- `frontend/src/app/DocumentGenerationFlow.tsx`, `frontend/src/app/FlowLanding.tsx`
- `frontend/src/shared/documentTypes.ts` (только маппинг тип → картинка)
- тесты в `frontend/src/features/generation/__tests__/**`
- **Навбар и тему не править** — они за сессией 1. Нужный токен отсутствует —
  временно локальная константа + пункт в отчёте.

## Задачи
1. Desktop-раскладка экрана создания проекта строго по фрейму: сетка, карточки
   типов, форма, кнопки, порядок шагов, состояния (disabled / загрузка / ошибка).
2. Мобильная раскладка по фрейму `Mobile`: брейкпоинт брать из разницы ширин
   фреймов, а не выдумывать. Проверить, что между брейкпоинтами ничего не рвётся.
3. Карточки типов генерации: подключить изображения из `Cards/Images color folders`,
   маппинг «тип документа → ассет» вынести в одно место, без хардкода внутри JSX.
4. Плейсхолдерные тексты из макета не переносить — данные идут из API/пропсов.

## Отчёт
Правки, использованный брейкпоинт, маппинг типов, недостающие ноды/ассеты (node id),
результат `/test-frontend`.
