# Manual mode — what the editor actually does today

A feature-level read of Story 5's frontend on `features/story-5-frontend`, rewritten 2026-07-28
against the source. Complement to [`progress-frontend.md`](progress-frontend.md): that file tracks
*which work units ran*, this one describes *what a visitor can do* and what looks finished but is
not. Where the two disagree, the code wins.

## Кратко по-русски: что готово, чего нет

**Готово и работает** (28 из 38 фронтовых сценариев, 74%):

- Ручной режим на равных с AI-генерацией: обе карточки в модалке живые, выбор создаёт документ
  (`POST`) и сразу открывает редактор — без skeleton, с плейсхолдером и полным тулбаром.
- Редактор на Tiptap с **полноценной блочной схемой** (миграция 2026-07-26): абзацы, заголовки
  H1–H3, маркированные и нумерованные списки, цитаты, блоки кода, горизонтальная линия — это
  настоящие узлы StarterKit, а не самодельные марки, как было раньше.
- Форматирование: жирный, курсив, зачёркнутый, подчёркнутый, инлайн-код, выравнивание по центру,
  ссылки (поповер для ввода URL, с нормализацией и отсевом опасных схем), undo/redo с реактивным
  disabled.
- Тулбар подсвечивает состояние **в точке курсора**, а не по документу целиком.
- **Автосохранение** с дебаунсом — правки уходят на сервер без нажатия «Сохранить». Плюс ручная
  кнопка. Статус: «Создание документа…» / «Черновик, ещё не сохранён» / «Сохранение…» /
  «Сохранено».
- Конкурентность решена структурно: в полёте всегда один запрос, правка во время запроса ставит
  флаг «сохранить ещё раз», который срабатывает после ответа с актуальным контентом и версией.
  Устаревший ответ не может перезаписать свежий — гонки просто не возникает.
- OCC по версии: конфликт (409) не затирает чужую запись молча — идёт перечитывание и повтор.
- Ошибки классифицируются по типу: transient (таймаут, 5xx) — повтор с backoff 1с/2с/4с, до 4
  попыток; истёкшая сессия — не ретраится; остальное — баннер `role="alert"` под тулбаром,
  контент при этом не трогается.
- Защита от потери правок при закрытии вкладки: `beforeunload` включается, пока документ грязный,
  и снимается после успешного сохранения.
- Повторное открытие сохранённого документа компонентом умеет работать (GET + версия).

**Не сделано** (10 сценариев открыты):

- **Заголовок документа** — ни ввода, ни сохранения, ни проверки длины (E4.1, E4.2, E4.3/H9.1).
- **Санитизация вставки** на клиенте — вставка форматированного текста из Word/веба не чистится
  на фронте (E5.1).
- **Счётчик слов и символов** (E7.1).
- **Таблицы** (E8.1).
- **Undo/redo поверх блочной структуры** — базовый undo есть, поведение на блоках не закреплено
  (E6.1).
- **Legacy-документы** (созданные в старой inline-схеме) — цикл load-edit-save без потери
  контента не проверен (H10.1).
- **Уход со страницы внутри приложения** — `beforeunload` ловит только закрытие вкладки; кнопка
  «Назад» просто размонтирует редактор, роняя незасинканную правку (H10.3).
- **H9.4 (частота сохранений)** — основное сделано, остаётся хвост follow-up'ов.
- **Точки входа в список документов нет** — компонент умеет открыть существующий документ, но в
  приложении нет UI, который бы это вызвал (история #12).

Ниже — то же самое подробнее, с оговорками о том, что именно НЕ проверено.

## Getting into the editor

Manual mode is offered alongside AI generation on the mode modal — both cards live, no "скоро"
badge. Choosing it creates a document immediately (`POST`) and drops the visitor into an empty
editor: placeholder, full toolbar, a breadcrumb carrying the document type, and a status line.
No intermediate skeleton — the editor is built unconditionally.

"Назад" returns to the mode modal with the document type still scoped, not to the landing page.

## Writing and formatting

**The inline-only schema is gone.** Until 2026-07-26 the document was `Document.extend({ content:
'inline*' })`, which made every block-level Tiptap extension structurally unreachable and forced
blockquote / code block / H3 / centre-alignment to be re-implemented as Marks. The block-schema
migration (see `decisions/`) replaced all of that with StarterKit's standard node model: the
document is `block+`, and paragraph, heading (1–3), bullet and ordered lists, blockquote, code
block, horizontal rule and hard break are real nodes. Alignment is now a block attribute
(`style="text-align: …"`) rather than a wrapping mark.

Toolbar (13 controls): H3, bold, italic, strike, underline, inline code, blockquote, bullet list,
ordered list, horizontal rule, centre-align, link, undo, redo. State follows the **cursor**, not
the document — a button lights up (`aria-pressed`) only while the caret sits in text carrying that
mark. Undo/redo are the only controls with a disabled rather than an active state.

Link ships inside StarterKit and is configured, not re-registered: `openOnClick: false`,
`autolink: false`, `linkOnPaste: false`. The last two fire outside explicit user intent — autolink
runs on any `docChanged`, so a server-returned bare host would silently gain an href nobody typed,
and the next save would persist it.

## Saving

**Autosave is live**, debounced, alongside the manual button. The status line moves between
*Создание документа…*, *Черновик, ещё не сохранён*, *Сохранение…* and *Сохранено*.

Concurrency is made structurally impossible rather than reconciled after the fact: only one save
is ever in flight, and a save requested during one sets a flag the in-flight save consumes when it
settles, firing a fresh save with the then-current content and the version the server just
returned. There is no out-of-order response to compare — the race cannot happen. Stronger than the
Gherkin asks for, and it also means two genuinely concurrent requests are never exercised.

Failures are classified rather than lumped together (H9.3): a request timeout or a 5xx retries on
a capped backoff — 1s, 2s, 4s, four attempts total — while a session expiry or a 4xx does not,
because waiting cannot heal it. A version conflict (409) refetches and retries rather than
overwriting. Anything that exhausts the ladder raises the inline banner; content is never touched.

A dirty-content guard (H9.4) suppresses a redundant PUT when the editor holds exactly what the
server confirmed — the memory is recorded only when the editor still holds what was sent, and
dropped whenever a failure leaves the server's content unknown.

`beforeunload` is armed while the document is dirty and detached on clean/unmount, so a tab close
or refresh raises the browser's native prompt. It does **not** cover in-app navigation.

## Reopening a saved document

`ManualEditor` accepts an optional `existingDocumentId`: it fetches the document, populates the
editor, and adopts the returned version so the next save targets the right base. Tested and
working — **and still with no entry point.** `App.tsx` never passes it; there is no document list
or history UI in this story (that is story #12). The capability stops at the component boundary.

## What is honestly not verified

Worth stating plainly, because a green suite invites the opposite conclusion.

The **client/server round-trip is thinly tested**. `*.parseHTML` tests assert that Tiptap re-parses
markup Tiptap itself rendered, inside one jsdom process. `editor.getHTML()` is API surface, so the
markup these scenarios produce is a contract mostly checked on one side only. The autosave suites
do exercise a sanitizing server (the adopted-content path), but not through the real backend.

**Nothing persists unsaved work locally.** No `localStorage`/`IndexedDB` anywhere in
`frontend/src`; content lives only in Tiptap's in-memory state. The save-error banner still tells
the visitor their text is "сохранён локально в редакторе" — false, recorded as an open BLOCK in
[`carryover.md`](carryover.md) since scenario 5.2.

**In-app navigation drops a dirty document.** `beforeunload` guards browser unload only;
`flow.backFromEditor` unmounts, the `[]`-scoped cleanup clears the pending timer, and a pending
write is dropped with nothing beyond a `console.error` (H10.3, open).

**The 503 premise is load-bearing and only partly gated.** The autosave treats a 503 as proof the
write never landed and can suppress it on that answer. `npm run check:ingress` now scans both the
container nginx conf and `backend/` on every build, but the hops with no IaC source — WAF, TLS
terminator, host/prod-copy proxy — have no gate at all; see `infra/architecture.md` Deploy notes.

**Coverage numbers are not evidence of round-trips**, twice demonstrated. A mark whose `parseHTML`
returns a bare tag rule is declarative data, so its "100%" is schema-build time. A factory-extracted
toggle shares source lines across marks, so one test paints several green. Both are in
`carryover.md` with their scars.

**CI is red at HEAD for unrelated reasons**: `npm run lint` (9 `react(only-export-components)`
warnings under `--max-warnings=0`) and `npm run format:check` (13 files under
`src/features/generation`). Pre-existing, not from the H9.4 work.

## Where the state of play lives

- [`status-ru.md`](status-ru.md) — the same picture as prose in Russian: what works, what does not, what to know before calling it done.
- [`progress-frontend.md`](progress-frontend.md) — per-scenario work-unit state, the source of truth for what runs next.
- [`progress.md`](progress.md) — story-level narrative, the Spec checklist, and items owed to the backend layer.
- [`decisions/`](decisions/) — the block-schema migration and the 7.9 URL-input ADRs.
- [`carryover.md`](carryover.md) — quirks and scars a future scenario will hit.
- [`tests/02_UI_Tests.md`](tests/02_UI_Tests.md) — the Gherkin these scenarios implement.
