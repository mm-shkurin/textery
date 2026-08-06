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

## Функциональное состояние на 2026-08-06

Срез по **возможностям**, а не по шагам. Пошаговое состояние — в `progress-backend.md`;
здесь только то, что уже работает на живом эндпоинте, и то, что ещё нет.

### Работает end-to-end

**Лента проектов отдаётся по HTTP.** `GET /api/v1/projects` смонтирован в `main.py`,
провайдер переопределён на реальный `SqlAlchemyProjectFeedRepository` — маршрут живой на
каждом аутентифицированном вызове, не заглушка. Путь целиком: роутер → `ListProjects` →
порт `ProjectFeedRepository` → SQL по таблице `documents` → доменный `ProjectPage` →
`ProjectPageDto` на проводе.

**Чужое не видно.** `owner_id` берётся из Bearer-токена как предикат запроса, а не как
параметр — сузить или расширить выборку query-строкой нельзя по построению. Запрос без
токена не доходит до порта: зависимость падает раньше тела обработчика. Отказ при
неразрешённом владельце сделан явным (`MISSING_OWNER_REFUSAL`), чтобы `None` не
превращался в «корректный пустой 200» для того, чью личность так и не установили.

**Строка ленты несёт весь контракт.** Девять полей — `kind`, `id`, `title`, `preview`,
`document_type`, `status`, `retryable`, `created_at`, `updated_at` — проецируются из
`documents` колоночным `SELECT` (не ORM-сущностью: кортеж `Row` нельзя ответить из
identity map, это сильнее, чем `expire_all()`, и держит форму под будущий `UNION ALL`).
Ни у одного поля нет значения по умолчанию — рефлексивный тест над `dataclasses.fields`
запрещает их вернуть, иначе «пустая строка» снова стала бы законной.

**`title` различает пустоту и отсутствие.** `str | None` сквозь все слои: NULL не
схлопывается в `''`. Это то, на чём стоит сортировка 3.3 («без названия — в конец»).

**Время на проводе — всегда UTC.** Валидатор отвергает naive-значение (`astimezone` его
не отвергает — молча читает как локальное время хоста и выдаёт правильно выглядящую
строку с неправильным моментом), затем конвертирует в UTC. Смещение `+07:00` уходит
клиенту как `Z`, а не эхом.

**Неизвестный статус не роняет страницу.** Значение вне enum контракта отображается в
`unknown` (`before`-валидатор, не отказ). Отказ ушёл бы в catch-all `main.py` и обнулил
бы **всю** ленту 500-й ошибкой из-за одной строки — правило «проблема строки не должна
становиться проблемой страницы» закреплено тестом на двухстрочной странице.

**Лента не кэшируется на общем прокси.** `Cache-Control: no-store` на 200 — и это теперь
закреплено тестом: удаление строки из роутера раньше оставляло весь rest-набор зелёным.

**Проводка проверена отдельно.** `test_project_feed_wiring.py` собирает реальный
`ListProjects` над реальным репозиторием и пиннит, что переопределение провайдера
установлено.

### Ещё не работает — и это ожидаемо

- **Пагинация.** `page`, `limit`, `total` не эмитятся; `ProjectPageRequest` принимается и
  игнорируется. Ни `LIMIT`, ни `OFFSET` в запросе нет.
- **Сортировка и поиск.** `sort`/`q` не существуют. Дефолтного `ORDER BY` тоже нет —
  порядок строк в Postgres произволен, и до пагинации это обязано быть закрыто, иначе
  строка может показаться на двух страницах или ни на одной.
- **Ветка генераций.** Лента читает только `documents`. `kind` — литерал `document`,
  `retryable` — литерал `False`. Дедупликация «генерация, ставшая документом»,
  `recovering` по порогу устаревания, повторы — всё это сценарии 1.2–1.9.
- **Обрезка `preview`.** Контракт требует ограниченный префикс (200 code points, без
  разметки), а сейчас `preview = content` целиком, и `SELECT` не ограничен. Полный текст
  каждого документа уходит на list-эндпоинт — это и вес страницы, и вопрос
  конфиденциальности. Владельца у этого ограничения пока нет ни на одном слое; шаги
  заведены.
- **Приёмочный тест 1.1 всё ещё под skip.** Он парсит конверт целиком, поэтому ждёт
  `page`/`limit`/`total`. Снимется, когда счётчики конверта доедут до провода.
- **Лог-сигнал на ветке `unknown`.** Контракт требует записи с id и нераспознанным
  значением; сейчас ветка молчит. Fail-closed без сигнала — это fail-silent.
- **`ProjectStatus`/`ProjectKind` живут в REST-слое**, хотя ADR помещает их в домен.
  Тестового давления на перенос пока нет.
