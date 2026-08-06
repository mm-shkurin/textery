# Audit Log

Каждая итерация — независимый аудит текущего состояния файлов и git-истории `frontend/`,
без учёта намерений предыдущих итераций. Оценка ставится по фактическому состоянию.

## Iteration 2 - Score: 2.5 / 3.0

Аудит на коммите `cf112e9c`. Все восемь гейтов, которые выполняет CI, зелёные:
`ci:parity`, `check:ingress`, `audit`, `lint`, `format:check`, `typecheck`,
`test:coverage` (763 теста, 96.69 / 92.17 / 98.78 / 98.35, пофайловый пол пройден
на 140 файлах), `build`.

### Fixed Issues:

- `format:check` — 5 файлов приведены к prettier (`1031d71f`).
- `lint` — 4 предупреждения устранены заменой ролей на настоящие элементы
  (`1c9d78ea`): карточка проекта стала `<button>` со stretched `::after` вместо
  `<div role="button">` с рукописными Enter/Space, `<form role="search">` →
  `<search><form>`, `<div role="group">` → `<fieldset>`, `projectKey` вынесен из
  файла компонента.
- `test:coverage` — 90 новых тестов на `features/projects` (`1229a229`): жизненный
  цикл ключа идемпотентности, `queryStringOf`, тулбар, пагинатор, оба пустых
  состояния, URL как источник истины, обе catch-ветки `useProjectView`.
  Покрытие 92.37 → 96.69 statements, 86 → 92.17 branches, 94.16 → 98.78 functions,
  94.55 → 98.35 lines. Порог branches подтянут 90 → 91.
- Doc-комментарий `useRetryGeneration` приведён в соответствие с кодом.
- Карточка без `title` и `preview` больше не отдаёт кнопку без доступного имени.
- `.env` теперь игнорируется и в `frontend/.gitignore` — то есть в обеих формах
  репозитория, а не только в монорепо (`cf112e9c`).
- README описывает `src/features/projects`.

### Outstanding Blockers:

- `git shortlog -s -n`: 1605 коммитов у одного автора против 14 у второго. Фактор
  автобуса равен единице, и ревью-поверхность — только сообщения коммитов: PR/MR
  в проекте не используются по решению `.claude/rules/workflow.md`, `CODEOWNERS`
  нет. Ни одно изменение в `frontend/` не проходило чужих глаз.
- Две открытые moderate-уязвимости `react-router` (GHSA-wrjc-x8rr-h8h6 open
  redirect, GHSA-337j-9hxr-rhxg) остаются нерешёнными: `npm run audit` намеренно
  поднимает порог до `high`, поэтому гейт их не видит. Фикс — мажорный апгрейд до
  react-router-dom 7.
- `index.html` тянет шрифт Inter с `fonts.googleapis.com` — сторонний CDN на
  критическом пути рендера и внешняя точка отказа; `preconnect` объявлен только к
  `googleapis.com`, но не к `fonts.gstatic.com`, откуда приходят сами файлы шрифта.
- Три теста стоят на `it.skip` в suite'ах автосохранения `ManualEditor`
  (`ManualEditor.autosaveAbandonFalseRecord`, `...AbandonRecord`) — задокументированные
  RED-строки, но пока незакрытое поведение.
- Два файла CI (`frontend/.github/workflows/ci.yml` и корневой `frontend-ci.yml`)
  синхронизируются вручную. `ci:parity` сравнивает только НАБОР npm-скриптов —
  расхождение в версии Node, в `paths:`-фильтре или в порядке шагов гейт не увидит.
- Токены доступа лежат в `sessionStorage` (`authSession.ts`) — задокументированный
  принятый риск, а не упущение, но XSS-поверхность ненулевая; настоящее решение —
  httpOnly-куки со стороны бэкенда.

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
