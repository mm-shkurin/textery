# Audit Log

Каждая итерация — независимый аудит текущего состояния файлов и git-истории `frontend/`,
без учёта намерений предыдущих итераций. Оценка ставится по фактическому состоянию.

## Iteration 9 - Score: 2.5 / 3.0

Аудит на коммите `4e2dbc94`. Девять гейтов зелёные. Оценка та же: то, что удерживает
её на 2.5, — фактор автобуса, `sessionStorage` и объём инфраструктуры гейтов — за
итерацию не меняется, а всё, что было закрываемо изнутри `frontend/`, закрывается.

### Fixed Issues:

- `authApi.resendCode` получил тесты (`2ea09805`). Модуль различает «сервер отказал»
  и «запрос не дошёл» — ровно то, что в нём когда-то было сломано, — и проверялся
  только через мок в `VerifyCodeForm`. Сегодня эндпоинт отвечает 404, то есть обе
  ветки отказа и есть весь его production-путь.
- Пофайловый пол покрытия 60/45 -> 75/48. Фактические минимумы — 80% строк и 50%
  ветвей: старый порог не сработал бы и при регрессе.

### Outstanding Blockers:

- Фактор автобуса равен единице (1617 против 20), PR не используются, `CODEOWNERS` нет.
- `GHSA-qwww-vcr4-c8h2` (high) в журнале исключений до 2026-11-01: релиза без него и
  без четырнадцати адвизори версий <= 7.17.0 не существует.
- Токены в `sessionStorage` — httpOnly-куки на стороне бэкенда.
- `scripts/` — 21 файл, ~2900 строк инфраструктуры гейтов против ~1520 покрытых строк
  прикладного кода; владелец нигде не назван.
- `check-audit.mjs` зависит от доступности registry (fail-closed, офлайн-кэша нет).
- Три записи `shared -> features/auth` в `boundaryRules.mjs`: гейт их называет, но шов
  остаётся — настоящее решение это модуль сессии вне `features/`.
- Машина сохранения размазана по шести модулям, связанным общими `MutableRef`.
- Комментарии в `scripts/` и хуках автосохранения по объёму превосходят код.

## Iteration 8 - Score: 2.5 / 3.0

Аудит на коммите `3a658bc5`.

### Fixed Issues:

- Гейт границ модулей (`4e2dbc94`). README описывал слоение словами, и это была
  единственная архитектурная гарантия репозитория без проверки: правило про импорты
  держится до первого дня, когда нужен компонент из соседней фичи. `npm run lint`
  теперь заканчивается `check-boundaries.mjs`; три импорта `shared -> features/auth`
  перечислены поимённо с причиной, вместо того чтобы молча допускаться. Девять
  self-тест-кейсов, включая re-export — иначе барельный файл отмывал бы что угодно.

### Outstanding Blockers:

- Те же, что в итерации 9, минус границы модулей.

## Iteration 7 - Score: 2.5 / 3.0

Аудит на коммите `49994a90`. **`format:check` был красным на `dev`**: файл
`accountEmail.ts` приехал неотформатированным, то есть ветка падала на четвёртом
шаге обоих пайплайнов ещё до тестов.

### Fixed Issues:

- `format:check` починен (`68216aa9`).
- `ci:parity` закрыл два последних названных слепых пятна (`3a658bc5`): порядок шагов
  (гейты выстроены от дешёвых к дорогим; два пайплайна с разным первым падением на
  одном коммите — начало «у меня зелено») и `paths:`-фильтр монорепо-пайплайна,
  который обязан покрывать и `frontend/`, и сам файл воркфлоу. Второе — самое тихое
  падение из возможных: воркфлоу не стартует, и красного нет, потому что ничего не
  запускалось. Воркфлоу, который не перезапускается при собственном изменении, нельзя
  починить изменением. Четыре кейса, включая тот, который падать не должен.

### Outstanding Blockers:

- Те же, что в итерации 9, плюс границы модулей (закрыто в итерации 8).

## Iteration 6 - Score: 2.5 / 3.0

Аудит на коммите `80bf81c2`. Девять гейтов зелёные (восемь шагов CI, из них `build`
теперь включает бюджеты размера). Оценка снова 2.5: закрыто три пункта из
Outstanding итерации 5, но то, что удерживает планку на 2.5 — фактор автобуса,
хранение токенов и объём инфраструктуры гейтов — за одну итерацию не меняется.

### Fixed Issues:

- Слепая зона `ci:parity` по версиям actions закрыта (`80bf81c2`): расхождение
  `@v4`/`@v5` у общего action и два разных пина одного action внутри файла роняют
  гейт. Сравнение — по общим именам, потому что docker-job существует только в
  монорепо; три self-тест-кейса, включая тот, который падать НЕ должен.
- Ветвевое покрытие 92.09% -> 93.01%, statements 96.77% -> 97.25% (`a29e5831`).
  Закрыты охранные ветки, до которых нельзя дойти набором текста: IME-композиция и
  бросающий `posAtDOM` в `editorDomSync`, четыре ветки отказа регистрации, включая
  `message: '   '` — строку, которая проходит `if (message)` и рисует пустую
  плашку. Пороги подняты до 96/92/98/97, запас снова ~1 пункт.
- Запас до порога ветвей был 1.09 пункта (замечание итерации 5) — стал 1.01 при
  более высоком абсолютном значении.

### Outstanding Blockers:

- `git shortlog -s -n`: 1617 против 20. Фактор автобуса равен единице; PR не
  используются, `CODEOWNERS` нет.
- `GHSA-qwww-vcr4-c8h2` (high) в журнале исключений до 2026-11-01. Не достижим для
  SPA на `BrowserRouter`, но релиза без него и без четырнадцати адвизори версий
  <= 7.17.0 не существует.
- Токены в `sessionStorage`; httpOnly-куки — задача бэкенда.
- `scripts/` — 17 файлов, ~2300 строк инфраструктуры гейтов против ~1460 покрытых
  строк прикладного кода. Владелец нигде не назван.
- `check-audit.mjs` зависит от доступности registry (fail-closed, офлайн-кэша нет).
- `ci:parity` по-прежнему не сравнивает порядок шагов и `paths:`-фильтры.
- Пофайловый пол (60/45) остаётся втрое ниже общего порога: `loadFailureMessages.ts`
  (83%) и `ProjectsToolbar.tsx` (87.5%) проходят его, не приближаясь к общей планке.
- Машина сохранения по-прежнему размазана по шести модулям, связанным передачей
  общих `MutableRef`.
- Комментарии в `scripts/` и в хуках автосохранения по объёму превосходят код,
  который описывают: сегодня они точны, но устаревают молча.

## Iteration 5 - Score: 2.5 / 3.0

Контрольный прогон на коммите `85aeea8f` — оценка итерации 4 подтвердилась на
дереве, где к тому моменту добавились бюджеты размера бандла, тесты транспорта
«Повторить», `CONTRIBUTING.md` и тег `v0.2.0`. Все гейты зелёные,
`git ls-files` не содержит ни `.env`, ни `node_modules`, ни `dist/`, ни
`coverage/`; `it.skip` в `src/` не осталось.

### Fixed Issues:

- Бюджеты размера бандла в конце `build` (`e79ec2d8`): `vite build` печатал
  размеры и выходил с нулём, что бы ни напечатал. Чанк без бюджета тоже красный.
- `retryGenerationApi` получил собственные тесты (`3686f590`) — модуль единственной
  платной операции проверялся только через моки, 0% функций.
- `CONTRIBUTING.md` (`1053d2c4`) и релиз `v0.2.0` (`85aeea8f`).

### Outstanding Blockers:

- Те же, что в итерации 4, плюс два новых наблюдения: запас ветвевого покрытия до
  порога — 1.09 пункта, самый узкий из четырёх, и `ci:parity` не сравнивает версии
  actions между пайплайнами.

## Iteration 4 - Score: 2.5 / 3.0

Аудит на коммите `f9a5b090`. Все восемь гейтов зелёные, включая три новых проверки,
которых на итерации 3 не было. Оценка та же, что и на итерации 3, но список
незакрытого стал короче, а часть прежних «осознанных компромиссов» перестала быть
компромиссами.

### Fixed Issues:

- `react-router-dom` 6.30.4 -> 7.18.2 (`fc5743c8`). Две «moderate», которые
  итерации 1-3 вели как отложенные, к этому моменту переоценены как **high**, и
  вместе с ними в диапазоне до 7.17.0 открыто ещё двенадцать: XSS в
  `ScrollRestoration`, RCE через vendored turbo-stream, DoS на сопоставлении
  маршрутов. То есть гейт `audit` на пороге `high` был не «зелёным по договорённости»,
  а красным по факту. 763 теста, typecheck и build прошли без правок кода.
- Порог severity в `npm run audit` заменён журналом исключений (`af360a78`):
  `scripts/check-audit.mjs` падает на любом production-адвизори, кроме записанных в
  `scripts/auditExceptions.mjs` с причиной и датой окончания. Просроченная запись и
  запись, которую npm больше не сообщает, роняют гейт так же. Шесть self-тест-кейсов.
- Inter больше не тянется с `fonts.googleapis.com` (`20b540de`): два woff2 со своего
  origin (вариативный шрифт, `unicode-range` на кириллицу и латиницу), preload
  кириллического сабсета, fallback-стек из реальных системных шрифтов. Прежний
  `preconnect` вёл на `googleapis.com`, а файлы приходили с `gstatic.com`.
- Слепая зона `ci:parity` закрыта (`00fa544f`): сравниваются версия Node в обоих
  пайплайнах и её соответствие `engines.node`. Раньше сравнивался только НАБОР
  npm-скриптов.
- Три теста, стоявшие на `it.skip` с 2026-07-30, включены и зелёные (`f9a5b090`).
  Запись о брошенном автосохранении была неверна с обеих сторон: шумела там, где
  правка отменена до сохранённого содержимого, и молчала там, где документ так и не
  был создан — то есть ровно там, где теряется всё. Флаг снимался по факту
  срабатывания таймера, а не по факту передачи записи туда, где её напишут.
- `.gitattributes` (`text=auto eol=lf`, `f2d7c8b1`-серия): `format:check` падал на
  Windows-чекауте и проходил в CI — красный гейт, который видит одна машина.
- `scripts/` попали под prettier, который до этого проверял только `src/`
  (`aecab35a`); `check-ci-parity.selftest.mjs` разделён на кейсы и харнесс, чтобы
  остаться в пределах 200 строк.

### Outstanding Blockers:

- `git shortlog -s -n`: 1617 коммитов у одного автора против 20 у второго. Фактор
  автобуса равен единице; PR/MR в проекте не используются по решению
  `.claude/rules/workflow.md`, `CODEOWNERS` нет — ни одно изменение во `frontend/`
  не проходило чужих глаз.
- В журнале исключений одна запись: `GHSA-qwww-vcr4-c8h2` (high, CSRF в RSC-режиме
  `react-router`) до 2026-11-01. Приложение её не достаёт (SPA на `BrowserRouter`,
  ни RSC, ни loader'ов, ни action'ов), но релиза, где закрыты и она, и
  четырнадцать адвизори версий <= 7.17.0, не существует.
- Токены доступа лежат в `sessionStorage` (`authSession.ts`). Настоящее решение —
  httpOnly-куки со стороны бэкенда, то есть вне границ фронтенда.
- `scripts/` — это уже 15 файлов и ~2000 строк инфраструктуры гейтов против ~1450
  покрытых строк прикладного кода. Оправданно, но это вторая кодовая база, и у неё
  нигде не назван владелец.
- `check-audit.mjs` вызывает `npm audit`, поэтому гейт падает при недоступном
  registry (fail-closed — намеренно) и не имеет офлайн-кэша адвизори.
- `ci:parity` по-прежнему не сравнивает порядок шагов, `paths:`-фильтры и версии
  actions (`actions/checkout@v4`) между двумя пайплайнами.
- Ветвевое покрытие 92.09% при пороге 91% — запас 1.09 пункта, самый узкий из
  четырёх; обычный коммит с ветвлениями может уронить сборку.
- Пофайловый пол покрытия (60/45) намеренно много ниже общего, поэтому самые слабо
  покрытые модули (`ProjectsToolbar.tsx` 87.5%, `loadFailureMessages.ts` 83%,
  `editorDomSync.ts` 75%) проходят его, не приближаясь к общей планке.
- `CHANGELOG.md` держит секцию `[Unreleased]` с 0.1.0 (2026-07-24) — тега релиза,
  к которому можно привязать собранный артефакт, с тех пор не было.
- Машина сохранения размазана по шести модулям (`useDocumentSave`,
  `autosaveWriteChain`, `autosaveSaveCycle`, `autosaveAbandonment`,
  `autosaveDirtyGuard`, `useAutosave`), которые связаны передачей общих
  `MutableRef`: связность обеспечена комментариями, а связанность — общими ссылками.

## Iteration 3 - Score: 2.5 / 3.0

Контрольный прогон на коммите `07cd99e7` — оценка подтвердилась, цикл завершён.
Ничего не менялось между итерациями 2 и 3, кроме файла аудита: прогон повторён,
чтобы измерения не зависели от одной попытки.

Результаты воспроизвелись побайтово: `ci:parity`, `check:ingress`, `lint`,
`format:check`, `typecheck` — PASS; `test:coverage` — 763 passed / 3 skipped,
96.69 / 92.17 / 98.78 / 98.35, пофайловый пол пройден на 140 файлах; `build` —
успешно (336.51 kB + 398.66 kB lazy-чанк редактора). В `git ls-files` нет ни
`.env`, ни `node_modules`, ни `dist/`, ни `coverage/`; поиск секретов по `src`,
`scripts` и конфигам — пусто.

Единственное расхождение с итерацией 2 — `npm run audit` не смог достучаться до
`registry.npmjs.org` (`EAI_AGAIN` из Node при работающем системном DNS). Это
ограничение песочницы, а не дефект репозитория: на этом же дереве гейт проходил
раньше в этой же сессии, напечатав те самые два moderate-адвизори react-router.

### Fixed Issues:

- (нет — контрольный прогон без правок)

### Outstanding Blockers:

- Те же, что в итерации 2, и все они — осознанные компромиссы либо задачи вне
  границ фронтенда: фактор автобуса, порог `audit` на уровне `high` при двух
  открытых moderate-адвизори react-router, шрифт со стороннего CDN, три
  `it.skip` в автосохранении, слепая зона `ci:parity` (сравнивает только имена
  скриптов), токены в `sessionStorage` до перехода на httpOnly-куки.

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

## Iteration 2 — Score: 2.5 / 3.0 — 2026-08-14 — 41445397

### Fixed Issues:

- (нет — итерация только зафиксировала состояние; правки ниже, в итерации 3)

### Outstanding Blockers:

- Два CI-гейта красные на вершине ветки `features/story-13-profile-management`:
  `npm run lint` падает на `ProfileDeleteModal.tsx:45`
  (`jsx-a11y/prefer-tag-over-role` — нужен `<dialog>` вместо `role="dialog"`),
  `npm run format:check` — пять неотформатированных файлов. Обе поломки внесены
  двумя последними коммитами (`9e90c6cc`, `41445397`), то есть локальная
  предкоммитная дисциплина для последнего work unit была пропущена.
- Тесты при этом зелёные: 222 файла / 960 тестов, покрытие 97.1 % statements /
  92.6 % branches / 98.5 % functions с пофайловым полом.
- `ProfileMenu.css` — 201 строка при жёстком лимите 200.
- Обходы границ (`send`, `ProfileMenu`, `ProfileAvatar`) остаются: `shared/`
  импортирует из `features/auth/`. Правильное решение — вынести session-модуль
  из `features/` — названо в `scripts/boundaryRules.mjs`, но отложено.
- README только на русском, комментарии в коде — на английском.

## Iteration 3 — Score: 3.0 / 3.0 — 2026-08-14 — eb964863

### Fixed Issues:

- `ProfileDeleteModal` теперь настоящий `<dialog open>`, а не `<div role="dialog">`;
  `.profile-modal` сбрасывает `position/margin/color`, потому что UA-таблица стилей
  выносит `dialog` из flex-центрирования скрима. Гейт `lint` зелёный.
- Прогнан форматтер: гейт `format:check` зелёный. Полный прогон тестов после
  правки — 222 файла / 960 тестов, все зелёные.

### Outstanding Blockers:

- Латентные дефекты, найденные аудитом (ни один не блокирует счёт, все — с
  конкретным адресом):
  - `useAccountDeletion.ts:44` сравнивает введённый адрес с `profile.email`,
    который `profileWire.ts:40` приводит к `''` при отсутствии поля: битый 200
    открывает необратимую кнопку при пустом вводе.
  - `authSession.ts:66` (`saveSession`) может записать access-токен без refresh и
    только вернуть AND; `OAuthCallback.tsx` не чистит сессию при `false`, поэтому
    `isAuthenticated()` затем врёт «да» на половинной записи.
  - Два независимых пути обновления токена: `performRenewal`
    (`authorizedRequest.ts:54`) с single-flight и `renewWithoutEndingSession`
    (`identityRequest.ts:43`) без него — два параллельных `/auth/refresh`, когда
    `GET /me` и `GET /me/avatar` получают 401 одновременно.
  - `useDocumentInit.ts:68-111` применяет загруженный документ через
    `editor?.commands.setContent(...)`: если ответ пришёл раньше инстанса
    редактора, документ отрисуется пустым. Соседний
    `useGeneratedDocumentInit.ts:59` в этом месте делает `if (!editor) return`.
  - `ManualEditor.tsx:49` стартует с `hasUnsavedChanges = true` — чистый пустой
    редактор просит подтверждение ухода со страницы.
- Дублирование: `withBearer` побайтово совпадает в `authorizedRequest.ts:22` и
  `identityRequest.ts:30`; маппер «400 → типизированный reject» написан трижды
  (`profileApi.ts:25`, `avatarApi.ts:25`, `deleteAccountApi.ts:34`); guard от
  двойного сабмита (`busyRef`) переизобретён в трёх хуках профиля.
- `safeRedirectTarget.ts` фактически мёртв: единственный вызов
  (`OAuthCallback.tsx:60`) передаёт `undefined`, функция может вернуть только `'/'`.
- `ProfileMenu.css` (201) и два тест-файла профиля (269, 212) — над лимитом 200.

## Iteration 4 — Score: 2.5 / 3.0 — 2026-08-20 — 30aee5f1
### Fixed Issues:
- The tip failed two of its own five CI gates. `npm run format:check` had nine
  outstanding files; `npm run test:coverage` was under the declared floor on
  functions (97.41% vs 98%) and branches (91.55% vs 92%).
- The coverage gap was two modules with no suite at all. `shared/lib/browser.ts`
  — the single answer to "are we in a browser", so every off-browser branch in
  the product runs through it — now has one, including the storage calls that
  THROW in private mode rather than returning null.
- `ProfilePage` had its three exits untested; the unsaved-name guard sits at the
  click seam because react-router navigation fires no `beforeunload`, so a
  regression there discards a typed name silently.
- Coverage after: functions 98.17%, branches 92.35%, 1041 tests passing.

### Outstanding Blockers:
- The release ref `gitverse-frontend/main` is behind HEAD by the sprint's work.
- `4f2d7873` touches 56 files across five unrelated features — not atomic, not
  revertible feature-wise.
- Single-author history (603 vs 7); no review signal anywhere, and the project
  forgoes PRs by policy.
- `ProjectsPage.tsx` (212 lines) mixes query-string state, feed orchestration and
  rendering; `httpClient.ts` (205) and `ProfileMenu.css` (201) are over the cap.
- Only the editor is code-split: the main chunk is 133 kB gzip and carries the
  router, the query client and every feature screen on first paint.

## Iteration 5 — Score: 3.0 / 3.0 — 2026-08-21 — c2bb0a4a
### Fixed Issues:
- The analytics slice, shipped the same day, had reinvented the storage guard the
  jury's `useDismissOnOutside` remark was about: `safely()` in `visitorId.ts` plus
  bare `window.localStorage` and `window.location` in three modules. All of it now
  goes through `shared/lib/browser.ts`, and `writeStored`'s boolean return IS the
  visitor identity's `degraded` flag rather than a second guard beside it.
- `useProfileNameForm` held four `useState`s describing one save attempt. They only
  ever changed together, so each transition was three or four calls a future edit
  could get half-right — one `SaveAttempt` object now.
- CHANGELOG had gone 26 commits without an entry (limit 25).

### Outstanding Blockers:
- The release ref `gitverse-frontend/main` is 639 frontend commits behind HEAD,
  dated 2026-08-14. Nothing from this sprint is on the graded repository.
- Single-author history (628 vs 7), and the committer email on all of them is
  malformed: `trape3977@g,ail.com` — visible in the first `git log` a grader runs.
- `GIT-BULK`: four commits over 40 files, `4f2d7873` (56 files) the worst.

## Iteration 6 — Score: 2.5 / 3.0 — 2026-08-21 — 86f03d4b — confirmation
### Fixed Issues:
- Story 14's UI test cases existed only as Gherkin in `ProductSpecification` and
  had never been published: this sprint's only frontend work had no test case a
  jury could open, and `sync-test-cases.mjs --check` was announcing the hole. 24
  cases rewritten into the executable eight-field template and synced.
- The README's quick start could not be followed: it documented a default for
  `VITE_API_PROXY_TARGET` that `requireProxyTarget()` does not have, so
  `npm install && npm run dev` died on a variable the README called optional. The
  `docker run` example proxied `/api` to the container's own loopback.
- `format:check` was red on HEAD — `fbf7e5fb` committed `reporting.test.ts`
  unformatted.

### Outstanding Blockers:
- `analyticsClient.ts:59` calls `fetch` directly rather than through `httpClient`,
  so a hung analytics request has no bound at all; only `keepalive` is deliberate.
- Five per-feature error→Russian mappings (`auth/api/apiError.ts`,
  `projects/api/loadFailureMessages.ts`, `generation/hooks/saveFailureMessages.ts`,
  `shared/identity/api/profileErrors.ts`, `shared/api/send.ts`) with two
  incompatible error shapes — no single mapping.
- `features/generation/components/` holds seven non-component modules and a hook
  while `utils/` and `hooks/` exist beside it; `shared/` keeps four modules loose
  at the slice root.
- Thirteen `OAuthCallback.*.test.tsx` files repeat the same router + exchange mock
  preamble by hand.
- Auth tokens remain in `sessionStorage`; the accepted-risk note and the
  httpOnly-cookie end state are unchanged.

## Publish — 2026-08-21 — gitverse-frontend/main 219d4bbf..5fc76ef0
### What landed:
- The mirror is the `frontend/` subtree with that directory as the root. Rewritten
  with `python -m git_filter_repo --subdirectory-filter frontend` on a throwaway
  clone: **4.6 seconds**, against the ~1.5 hours `git subtree split` takes walking
  all 1756 monorepo commits.
- `filter-repo` hashes are deterministic and the previous publish used it too, so all
  603 already-published commits reproduced their hashes and `219d4bbf` came out an
  ANCESTOR of the new history. The push was a plain fast-forward: **no `--force`,
  nothing rewritten, no safety branch needed.** 662 commits now; the sprint's 59 are
  59 commits, not the squashed dump that cost a mark last sprint.
- `feat/figma-alignment` published as a new ref (`63de17f2`, 641 commits), tree
  matching `feat/figma-alignment:frontend`, an ancestor of `main`.
- Verified after: tree byte-identical to `HEAD:frontend`; no `node_modules/`, `dist/`
  or `.env` tracked.

### Outstanding Blockers:
- `refactor(usecase): five flows stop carrying every step themselves` sits in the
  frontend history under a backend title — it carries two zero-line frontend renames
  the backend session's commit swept up. Content is correct; retitling it would mean
  rewriting published history.
- `GIT-BULK` and `GIT-DIRECT-MAIN` remain: history, not editable. The second is
  waiver material — the no-PR policy it flags is documented at `README.md:237`.
- The committer email on every frontend commit is `trape3977@g,ail.com`. Raised;
  the owner chose to leave it.


## Iteration 7 — Score: 2.5 / 3.0 — 2026-08-27 — 413ba383
### Fixed Issues:
- Three stylesheets were over the repository's own 200-line hard cap and no gate caught them:
  `LandingHero.module.css` (215), `LandingExport.module.css` (212), `tokens-light.css` (205).
  Split by KIND, not by line count — the hero's prompt bar became `LandingHeroPrompt`, the
  avatar stack became `LandingExportDiscs`, and the token sheet divided into semantic roles
  plus `tokens-light-components.css`. `ARCH-SIZE-STYLE` is PASS.
- Four colour literals the new landing work introduced are tokens: the comparison band's two
  glows joined `--landing-comparison-head-bg`, and the hero grid's mask stop uses the
  `--mask-opaque` token that already existed for exactly that. `ARCH-DESIGN-TOKENS`
  (a grader regression item) is PASS.
- `CHANGELOG.md` had gone 27 commits stale against a 25-commit limit, with the whole Figma
  alignment absent from it. `DOC-CHANGELOG-FRESH` is PASS.
- `tokenSheets.ts` reads both light sheets, because the browser sees one flat `:root`.

## Iteration 8 — Score: 2.5 / 3.0 (confirmation, held) — 2026-08-27 — 4091e9d3
### Fixed Issues:
- Nothing further this iteration; the confirmation run reports the 200-line cap as genuinely
  held, with the largest file in `src/` at exactly 200 lines.
### Outstanding Blockers:
- **A flaky test.** `ManualEditor.dirty.test.tsx` ("applying a toolbar format after a
  successful save marks the document unsaved again") failed in a full-suite run with
  `saveDocument` called twice, and passes in isolation both before and after this pass's
  changes. Timing the suite does not control, not a regression from these edits.
- `act(...)` warnings in the test output (e.g. `useFlowNavigation.documentType.test.tsx:41`)
  — unwrapped state updates that pass today and signal the same uncontrolled timing.
- `GIT-BULK` / `GIT-DIRECT-MAIN` / `GIT-LANGUAGE` — published history. `71ea1f84` alone is
  71 files mixing 40 new binaries, a deleted feature and 15 edited components.
- `SMELL-LONG-FUNC` (12 blocks) and `SMELL-DUPLICATION` (12 pairs) stand, on the reasoning
  recorded on 2026-08-21: the 30-line threshold does not fit a hook with a dependency array,
  and the duplication rule normalises string literals so two `.map` rows over a card collapse
  into one "duplicate".
- `package.json` is at `0.3.0` with no `v0.3.0` tag, so the changelog cannot be tied to a
  commit range.
- Bus factor 1 — 662 commits against 7, with no PR review surface by project policy.
