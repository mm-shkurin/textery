# Interview — Story 18: Generate → edit (unify generate + manual, drop mode modal)

## Scope

Пользователь выбирает тип документа → ИИ **сразу** генерирует (модалка выбора режима
ручной/авто убирается) → готовый текст **автоматически** открывается редактируемым в
редакторе story 5 → пользователь правит и сохраняет. Экспорт готового документа — story
17, не здесь.

В скоуп:

- Убрать `ModeModal` из флоу. После type-модалки — сразу генерация, без выбора режима.
- Конвертация завершённой генерации в `Document` (backend): `POST
  /documents/from-generation`.
- Автопереход в редактор с загруженным текстом, как только генерация завершилась.
- Пустой лист «с нуля» остаётся доступен вторичным входом — переиспользует
  manual-create story 5 (`POST /documents`). Не удаляем работу story 5.

Вне скоупа (явно):

- Экспорт PDF/DOCX — story 17.
- Апгрейд самого редактора (блочная схема, списки, автосейв, title и пр., пункты 1–8) —
  расширение story 5, отдельная сессия. Story 18 использует редактор как есть + то, что
  довезёт story-5-сессия. See `ProductSpecification/decisions/editable-generated-docs-scope.md`.
- Дообработка своего текста через ИИ (обратное направление) — будущее, не здесь.

## Key Architectural Decisions

- DECISION: генерация → **document**. Завершённая генерация конвертируется в отдельную
  сущность `Document`, которая переиспользует весь готовый пайплайн: save, версии,
  санитайзинг, а дальше и экспорт. (Выбрано с пользователем 2026-07-25.)
- DECISION: переход в редактор **автоматический** — как только текст готов, экран
  превращается в редактор с загруженным содержимым. Не по кнопке «Редактировать».
- DECISION: **фронтенд оркестрирует** конвертацию — опрос видит `completed` → фронт
  вызывает `POST /documents/from-generation` → открывает редактор. Бэкенд-флоу генерации
  не меняется, каждый usecase остаётся одной точкой входа (правило «usecase не зовёт
  usecase»). Backend НЕ создаёт документ сам внутри завершения генерации.
- DECISION: `Generation` **хранится** — до конвертации обязательно (асинхронный опрос
  читает контент из БД), после конвертации остаётся как аудит «что выдал ИИ» и оригинал
  для возможного revert-to-original. `Document` — источник правды. История (`GET
  /documents`) показывает только Document, не дубль «генерация+документ».
- DECISION: `Document` получает ссылку `generation_id` (nullable — у ручного документа с
  нуля её нет). Это добавляет колонку, которой у story 5 сознательно не было; добавление
  аддитивно и не ломает существующие пути.
- DECISION: конвертация **идемпотентна** — `POST /documents/from-generation` с тем же
  `Idempotency-Key` (или повторно по тому же `generation_id`) возвращает существующий
  `document_id`, никогда второй Document. Защита от двойного автоперехода/двойного клика.

## Business Rules & Constraints

- Конвертация допустима только для генерации в статусе `completed`. `pending`/
  `in_progress`/`failed` → 409 (или 422), не создаём документ из незавершённого.
- Owner-scoped: генерация должна принадлежать вызывающему (Bearer). Чужая/несуществующая
  → 404, никогда 403 (не подтверждаем существование id).
- Формат текста ИИ: фронт сейчас рендерит вывод как **Markdown** (`ReactMarkdown`).
  Backend при конвертации делает markdown → HTML → санитайз (allowlist, тот же порт, что
  у story 5 `SaveDocument`). ACTION: проверить реальный вывод GigaChat на стенде
  (`mmshkurin.ru`) перед фиксацией парсера — вдруг plain text без markdown-разметки.
- Новая зависимость markdown-парсера должна пройти CI `audit` (pip-audit) гейт.
- Длина сконвертированного контента подчиняется тому же лимиту `Document.content`
  (200 000 символов, story 5). Генерация длиннее лимита при конвертации → чистый 4xx на
  границе, не обрезаем молча.
- Санитайзинг конвертированного HTML обязателен даже при доверенном источнике (ИИ может
  вернуть разметку, которую нельзя рендерить как исполняемую).

## Already Implemented (REUSE)

- `Generation` домен + асинхронный флоу: `POST /generations`, фоновая задача,
  `GET /generations/{id}` опрос. `backend/domain/src/generation/`,
  `backend/adapters/rest/src/router/generation/generation_router.py`.
- `Document` домен + `POST`/`GET`/`PUT /documents`, версии, санитайзинг, owner-scope —
  story 5. `SaveDocument`, `CreateDocument`, `GetDocument` usecases.
- Редактор `ManualEditor` (Tiptap) как поверхность правки. `frontend/src/features/
  generation/components/ManualEditor.tsx`.
- Type-модалка (`TypeModal`), `ChatWorkspace`, `useGeneration` (опрос),
  `useFlowNavigation` (стейт-машина шагов) — переиспользуются, `ModeModal` вырезается.
- `HtmlSanitizer` порт (allowlist) — переиспользуется для конвертированного HTML.

## NOT Yet Implemented (Gaps)

- `POST /documents/from-generation` — endpoint + usecase (backend session A).
- markdown → sanitized HTML конвертация (backend session A). ACTION: проверить формат.
- `Document.generation_id` nullable колонка + миграция (backend session A).
- Удаление `ModeModal` из флоу; type → generate → auto-open editor (frontend session B/C).
- Загрузка сконвертированного документа в редактор по `document_id` (frontend).
- Редактор должен уметь показать многоабзацный текст — зависит от блочной схемы из
  story-5-расширения (пункт 0/1). Story 18 фронт БЛОКИРОВАН этим пунктом: в инлайн-схему
  сгенерированный текст не ложится. Порядок: story-5 блочная схема → потом story 18 фронт.

## Cross-Story Dependencies

- **Story 5 (расширение)** — блочная схема редактора (пункт 0/1) блокирует фронт story 18.
- **Story 17 (экспорт)** — работает поверх Document, созданного здесь; не блокирует, но
  экспорт осмыслен только когда документ редактируемый.
- **Story 1 (генерация)** — переиспользуем её async-флоу без изменений.
- **Story 7 (auth)** — Bearer/owner-scope уже выкачен, конвертация owner-scoped.

## Testing Considerations

- `FakeProvider` (`GENERATION_PROVIDER=fake`) даёт детерминированный контент для
  acceptance без похода в GigaChat — использовать для тестов конвертации.
- Идемпотентность конвертации и гонка двух автопереходов (double-submit) — обязательные
  сценарии (тот же класс, что hazard-group 2 у story 5/16).
- Selenium: автопереход generate → editor целиком в реальном Chrome против стенда.
