# Story 12: Мои проекты (list/search/sort, grid + list view) — Progress

Shared story-level narrative, decisions, and Spec checklist. Per-layer scenario checklists
live in `progress-backend.md` and `progress-frontend.md`. `ProductSpecification/stories.md`
is the cross-file rollup.

## Spec
- [x] interview
- [x] story
- [x] mockups
- [x] api-spec
- [x] test-spec (hazard scan: groups 1–8; all fired-trigger GAPs folded as named
  scenarios, none dismissed — record in `tests/00_Hazard_Scan_Record.md`, and a second
  scan record in `12_MyProjects_Notes.md`)

## Decisions

- **New `GET /api/v1/projects` instead of extending the existing list endpoints.** Search +
  4 sort orders + merging failed generations into one feed all break the keyset cursor,
  whose anchor must be immutable. `GET /api/v1/generations` and `GET /api/v1/documents` get
  marked deprecated and stay working. Reasoning in `interview.md`.
- **Merge reconciliation (2026-08-06).** The backend and frontend branches were specced
  independently and disagreed. The backend contract won: the write route is
  `POST /api/v1/generations/{id}/retry` (not `/repeat`), the item field is `retryable`
  (not `can_repeat`), validation failures are 400 (not 422), and `limit` tops out at 100
  (not 50). The frontend's `projects_schemas.yaml` split is dropped —
  `projects_list.yaml` carries its schemas inline. Frontend client code still reads
  `can_repeat` and is corrected as part of bringing `dev` to a working state.

## Функциональное состояние на 2026-08-06 (после мерджа веток в dev)

Срез по **возможностям**, а не по шагам. Важно: всё ниже написано **вне TDD-цикла**, по
прямому решению пользователя («добить фичи не по фреймворку, покроем тестами после»).
Поэтому чекбоксы в `progress-backend.md` / `progress-frontend.md` **намеренно не
проставлены**: код есть, red/green-шагов за ним нет. Проставлять их задним числом —
значит соврать про то, что было проверено.

### Что работает end-to-end

**Лента.** `GET /api/v1/projects` отдаёт объединённый `UNION ALL` двух источников: все
документы владельца плюс те генерации, на которые не ссылается ни один документ. Значит
сконвертированная генерация видна ровно один раз — как документ, а завершившаяся, но так и
не ставшая документом, перестала пропадать (это и есть причина существования истории).
Слияние делается **в SQL**, не сшивается в Python.

**Пагинация, сортировка, поиск.** `page`/`limit`/`sort`/`q` разбираются в адаптере, границы
живут в домене, каждый отказ несёт свой `error_code`. Пять порядков сортировки, каждый
доведён до тотального тай-брейком `(kind, id)` — не по `id`, потому что у двух таблиц
разные пространства идентификаторов. Поиск нормализуется в NFC с обеих сторон, LIKE-мета‑
символы экранируются (иначе `q=%` — это полный скан).

**Конверт.** `items` + `page` + `limit` + `total`. `total` считается по той же подзапросной
проекции в том же снимке, никогда из `len(items)`.

**`preview`.** Читается ограниченным префиксом из БД, разметка снимается **до** обрезки,
хвост отматывается до целого символа. Полные тела документов больше не уезжают на
list-эндпоинт.

**Статусы генераций.** Незавершённая старше порога устаревания — `recovering` и **не**
retryable (её перезапускает sweep). Неизвестный статус fail-closed в `unknown`. Обе ветки
считаются от инжектированных часов.

**«Повторить».** `POST /api/v1/generations/{id}/retry` — без тела, параметры копируются со
строки-источника. Только `failed` (иначе 409), идемпотентность по `(owner_id,
Idempotency-Key)` в БД, потолок 5 повторов на источник (429). Повтор по тому же ключу
возвращает существующую строку и **ничего не ставит в очередь**. Миграция
`c1d2e3f4a5b6` добавляет `idempotency_key` и `source_generation_id`, индексы строятся
`CONCURRENTLY`.

**Экран.** Страница «Мои проекты» подключена: она заняла шаг `history` во флоу вместо
`HistoryPage` (оба показывали одни и те же строки). Поиск с debounce, пять сортировок,
переключатель плитка/список, пагинатор, два разных пустых состояния, скелетон загрузки,
ретрай ошибки с сохранением `q`/`sort`, кнопка «Повторить» на карточке. `q`/`sort`/`page`
живут в query-строке, поэтому возврат из редактора восстанавливает ту же ленту.

### Чего ещё нет

- **Ни одного теста на новый код.** Существующие 677 backend + 652 frontend зелёные, но они
  покрывают то, что было до этой работы. Новое — нет.
- **SQL не проверен против живой Postgres.** Интеграционные тесты адаптера скипаются без
  БД, Docker на машине не поднят. `UNION ALL`, `NOT EXISTS`, `func.left`, `NULLS LAST` и
  миграция с `CONCURRENTLY` проверены только чтением.
- **Сортировка по типу — по значению колонки**, без продуктового порядка типов; кириллица
  отсортируется так, как решит коллация БД. Явная коллация (`ru-RU-x-icu`) не закреплена.
- **Нет шединга поиска.** `UnlimitedSearchSlots` выдаёт разрешение всем: 429 `SEARCH_BUSY`
  из контракта не реализован, как и таймаут запроса на 3 с.
- **Нет лог-сигнала на ветке `unknown`** — fail-closed без сигнала это fail-silent.
- **`ProjectStatus`/`ProjectKind` живут в REST-слое**, хотя ADR помещает их в домен.
- Приёмочный тест 1.1 всё ещё под skip.

