# Audit Log

Каждая итерация — независимый аудит текущего состояния файлов и git-истории `frontend/`,
без учёта намерений предыдущих итераций. Оценка ставится по фактическому состоянию.

## Iteration 1 - Score: 2.0 / 3.0

Аудит на коммите `b0339e80`.

### Fixed Issues:

- (нет — первая итерация)

### Outstanding Blockers:

- Три из восьми гейтов CI красные на вершине рабочей ветки `dev`. Оба пайплайна
  (`.github/workflows/ci.yml` и корневой `frontend-ci.yml`) выполняют их подряд, значит
  сборка на `dev` не проходит:
  - `npm run lint` — 4 предупреждения при `--max-warnings=0`
    (`ProjectCard.tsx:26` `react/only-export-components`, `ProjectCard.tsx:63`
    `jsx-a11y/no-static-element-interactions`, `ProjectsToolbar.tsx:37,74`
    `jsx-a11y/prefer-tag-over-role`).
  - `npm run format:check` — 5 файлов не отформатированы
    (`generationParameters.ts`, `loadFailureMessages.ts`, `ProjectCard.tsx`,
    `ProjectsPage.tsx`, `useProjectsFeed.ts`).
  - `npm run test:coverage` — все четыре глобальных порога не выполнены:
    statements 92.37 % (порог 95), branches 86 % (90), functions 94.16 % (98),
    lines 94.55 % (97). Дополнительно падает пофайловый пол
    (`scripts/check-per-file-coverage.mjs`) на шести модулях.
- Вся фича `src/features/projects/` (story-12, самая свежая) поставлена практически без
  тестов: `useRetryGeneration.ts` — 25 % statements / 0 % branches, `ProjectsToolbar.tsx`
  — 37.5 %, `ProjectsPager.tsx` — 50 %, `projectsApi.ts` — 54 % (весь `queryStringOf`
  не выполнялся ни разу), `ProjectCard.tsx` — 57 %, `useProjectView.ts` — 63 %.
  Непокрытым остался в том числе guard идемпотентности — единственная защита от повторной
  оплаченной генерации.
- Doc-комментарий `useRetryGeneration.ts` описывает поведение, обратное коду: заявлено
  «a fresh key is minted only after a failure», в коде ключ удаляется на успехе и
  сохраняется на ошибке.
- Карточка проекта была `<div role="button">` с рукописной обработкой Enter/Space вместо
  настоящего `<button>`; при пустых `title` и `preview` контрол оставался без доступного
  имени.
- `git shortlog -s -n`: 1605 коммитов у одного автора против 14 у второго — фактор
  автобуса равен единице; ревью-поверхность — только сообщения коммитов (PR в проекте
  не используются по решению `.claude/rules/workflow.md`).
- `index.html` подключает Google Fonts со стороннего CDN — внешний запрос на каждой
  загрузке страницы и точка отказа вне контроля проекта.
- Открытые moderate-уязвимости `react-router` (GHSA-wrjc-x8rr-h8h6,
  GHSA-337j-9hxr-rhxg) остаются: `npm run audit` намеренно поднимает порог до `high`,
  поэтому гейт зелёный, а адвизори — нет.
