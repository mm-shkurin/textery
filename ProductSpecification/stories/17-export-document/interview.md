# Interview — Story 17: Export document to PDF / DOCX

## Scope

Авторизованный пользователь открывает документ (сгенерированный+отредактированный из
story 18 или ручной из story 5) и скачивает его как **PDF** или **DOCX**. Файл
формируется бэкендом на лету из сохранённого HTML-контента и стримится в ответ.

В скоуп:

- `GET /api/v1/documents/{id}/export?format=pdf|docx` — owner-scoped, отдаёт бинарный
  файл с `Content-Disposition: attachment`.
- Оба формата: PDF и DOCX.
- Кнопка/меню экспорта в редакторе (frontend), скачивание blob с серверным именем файла.

Вне скоупа (явно):

- Хранение файлов на диске/в объектном сторадже — файл генерится в памяти на запрос,
  нигде не сохраняется (многоинстансное правило `coding-rules`).
- Стилевые темы/шаблоны оформления экспорта — базовый рендер HTML → PDF/DOCX. Богатое
  оформление (обложки, колонтитулы, стили по типу документа) — будущее.
- Асинхронный экспорт/очередь — синхронный request/response (документы малы, ≤200k
  символов).

## Key Architectural Decisions

- DECISION: рендер **на бэкенде** (выбрано с пользователем 2026-07-25). DOCX — через
  python-docx / htmldocx; PDF — через WeasyPrint (или аналог с чистым pip-audit). Единый
  результат, не зависит от браузера.
- DECISION: файл **не хранится** — генерится на лету, стримится, ничего не пишется на
  диск инстанса.
- DECISION: источник — сохранённый **санитайзнутый HTML** документа (тот же
  `Document.content`). Экспорт не запускает генерацию и не меняет документ.
- DECISION: имя файла выводится из `title` документа (story-5-extension добавляет поле
  `title`); кодируется по RFC 5987 для кириллицы, экранируется от header-injection.

## Business Rules & Constraints

- Owner-scoped: документ должен принадлежать вызывающему (Bearer). Чужой/отсутствующий →
  404, никогда 403.
- `format` валидируется: не `pdf`/`docx` → 422.
- Пустой документ экспортируется в валидный (почти пустой) файл, не ошибка.
- **SSRF-защита:** рендерер PDF не должен ходить в сеть. Отключить `url_fetcher`
  (WeasyPrint) — `<img src="http://...">` в контенте не должен инициировать исходящий
  запрос. Внешние ресурсы игнорируются/блокируются.
- **Стоимость/DoS:** контент ограничен теми же 200k символов (story 5); время рендера
  ограничено, чтобы патологический документ не вешал воркер.
- Content-Type строго: `application/pdf` / `application/vnd.openxmlformats-
  officedocument.wordprocessingml.document`.
- Новые зависимости (WeasyPrint, python-docx/htmldocx) должны пройти CI `audit` гейт.
  ACTION: проверить, что WeasyPrint и его системные зависимости ставятся в
  backend.Dockerfile (нужны libpango/cairo и пр.).

## Already Implemented (REUSE)

- `Document` + `GET /documents/{id}` (owner-scope, версии) — story 5.
- `Document.content` санитайзнутый HTML — источник экспорта.
- Bearer/owner-scope — story 7.

## NOT Yet Implemented (Gaps)

- `GET /documents/{id}/export` endpoint + usecase (backend).
- HTML → PDF (WeasyPrint, network off) и HTML → DOCX (python-docx/htmldocx) адаптеры.
- `title` поле на `Document` (общее со story-5-extension; кто первый — тот добавляет).
- Кнопка экспорта + скачивание blob + состояния загрузки/ошибки (frontend).
- Системные зависимости WeasyPrint в backend.Dockerfile.

## Cross-Story Dependencies

- **Story 5 / 18** — экспорт работает поверх редактируемого `Document`; не блокирует, но
  осмыслен только когда документ есть и правится.
- **Story-5-extension** — поле `title` (имя файла). Согласовать, кто добавляет колонку.
- **Story 7** — Bearer/owner-scope.

## Testing Considerations

- Экспорт бинарный — тест проверяет Content-Type, Content-Disposition, непустое тело и
  сигнатуру формата (PDF `%PDF`, DOCX = zip `PK`).
- Selenium: скачивание в headless Chrome капризно — настроить download dir, проверять
  факт файла, не рендер. ACTION: заложить время на headless-download конфиг.
- SSRF: контент с `<img src>` на локальный/внешний адрес — assert рендерер не делает
  запрос (fake/observed network).

## Performance / Rate Limits

- Профиль Throughput: экспорт добавляет CPU-нагрузку (рендер). Нагрузочный сценарий —
  устойчивая частота экспортов, ceiling по времени рендера.
