# Story 13: Profile management — Progress

Shared story-level narrative, decisions, and Spec checklist. Per-layer scenario checklists
will live in `progress-backend.md` and `progress-frontend.md` once `/test-spec` produces
scenarios. `ProductSpecification/stories.md` is the cross-file rollup.

Promoted from Backlog to In Progress on 2026-08-13. The story folder was empty — no spec
artifacts existed, so the Spec checklist below starts from scratch at `interview`.

## Spec
- [x] interview
- [x] story (hazard scan: groups 1–8, all dispatched; 35 GAPs, all folded as named
  requirements or guards, none dismissed — record in `tests/00_Hazard_Scan_Record.md`)
- [~] mockups
- [ ] api-spec
- [ ] test-spec

## Decisions

Полный разбор — в `interview.md`. Кратко, чтобы не открывать файл ради состояния:

- **Скоуп: только просмотр профиля + смена имени.** Тариф, смена пароля, удаление
  аккаунта, unlink OAuth, настройка вида ленты и загрузка фото — вне скоупа, каждое с
  причиной и ссылкой на историю-источник.
- **`name` — nullable, изначально NULL.** Регистрация и OAuth не трогаются; пока имени
  нет, везде показывается email.
- **`GET /me` отдаёт `email`, `name`, `created_at`** — без `is_verified`: войти может
  только подтверждённый аккаунт, значит поле всегда `true` и ничего не сообщает.
- **Шапка переезжает на `/me`**, декодирование JWT из `accountEmail.ts` удаляется. Оно
  было заявлено обходом отсутствующего `/me` — причина обхода исчезает вместе с историей.
- **Имя: trim + NFC, 1–60 code points; пустая строка — валидное «снять имя»** (200, NULL),
  а не ошибка.

**Незакрытое требование ТЗ §3** (IP / страна / устройство / ОС / язык / UTM при
регистрации) на сегодня ничьё — ни одна история его не забрала. Сюда не берём: ТЗ
называет их данными для продуктовой аналитики. Забрать в story 14 при её промоушене.

**Ревизия после hazard-скана (2026-08-13, шаг `story`).** Скан пересмотрел два решения
интервью, и это записано, а не проведено молча:

- **Load-сценарий всё-таки в скоупе.** Интервью отказалось от него, потому что история не
  добавляет ни очереди, ни внешнего API, ни сканов таблиц. Это верно и не про то: профиль
  нагрузки проекта — Throughput, где связывающее ограничение — частота запросов, а история
  делает `/me` самым частым эндпоинтом продукта.
- **Пустота имени определяется по прецеденту домена.** `Generation._is_blank_topic` уже
  стрипает пробелы и категорию `Cf`; переиспользуем это определение, иначе `"​"`
  проходит как имя длиной 1 и рендерится пустой строкой идентичности.
- **Конкурентные переименования — last-write-wins по решению**, не по умолчанию: версии
  и 409 нет, и это записано, чтобы не выглядело упущенным.
