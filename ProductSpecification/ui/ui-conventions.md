# UI Conventions — Textery

> **Two design systems live in this repo. Read this first.**
>
> Everything below the "Dark system (stories 1, 5, 7, 16, 17)" heading describes the
> original dark theme. It is **historical** for any screen inside the authenticated
> product. In 2026-07-28 the customer supplied a new **light** design, adopted by story 18
> and continued by story 10; its tokens live in
> `stories/18-generate-then-edit/mockups/desktop/theme.css`. New authenticated-product
> mockups use the light system — see "Light system (current)" at the end of this file.
> The dark rules still apply to the pre-auth landing until that is redesigned too.

Single authority for all mockup design rules. Bootstrapped 2026-07-06 during story 1's
`/mockups`, from three reference images in `.memory-bank/`: `Landing.png` (Textery's own
rough landing wireframe — logo, hero, feature cards), `Тип Работы.png` and
`Тип документа.png` (a competitor, Slidy.AI — the two-step "choose mode → choose document
type" modal this product's own doc-type selector should follow visually). Dark theme
throughout; no light-mode variant is planned.

## Brand

- **Logo**: small rounded-square mark (`T` monogram) + "Textery" wordmark, set in Inter
  Bold, next to each other, left-aligned in the header.
- **Product tone**: modern AI-SaaS, calm and professional (not garish) — dark surfaces,
  a single indigo→violet gradient as the one accent, generous whitespace, rounded
  corners everywhere.

## Dark system (stories 1, 5, 7, 16, 17) — historical for in-product screens

## Color Palette (dark theme only)

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-page` | `#111214` | Page background |
| `--bg-surface` | `#1a1b1e` | Card/panel background |
| `--bg-surface-raised` | `#232428` | Nested/hover surface (inputs, secondary cards) |
| `--border-subtle` | `rgba(255,255,255,0.08)` | Card/input borders |
| `--border-strong` | `rgba(255,255,255,0.16)` | Focused/active borders |
| `--text-primary` | `#f5f5f7` | Headlines, primary text |
| `--text-secondary` | `#9a9ba3` | Supporting text, labels |
| `--text-muted` | `#6b6c74` | Placeholders, disabled |
| `--accent-start` | `#6366f1` | Gradient start (indigo) |
| `--accent-end` | `#a855f7` | Gradient end (violet) |
| `--accent-gradient` | `linear-gradient(135deg, var(--accent-start), var(--accent-end))` | Icon badges, active borders, progress rings |
| `--success` | `#22c55e` | Completed status |
| `--error` | `#ef4444` | Failed status |
| `--warning` | `#f59e0b` | Pending/attention status |

CTA buttons are **white-filled, dark text** (`background:#f5f5f7; color:#111214`) — this
matches `Landing.png`'s header/hero CTA exactly. Secondary buttons are transparent with a
`--border-subtle` outline and `--text-secondary` text.

## Typography

- Font: **Inter** (Google Fonts), `<link>` in `<head>`.
- Headlines: 700 weight, `-0.02em` letter-spacing.
- Body: 400/500 weight.
- Sizes (desktop): H1 `40px`, H2 `28px`, H3 `20px`, body `16px`, small `14px`, micro `12px`.
- Sizes (mobile): H1 `28px`, H2 `22px`, H3 `18px`, body `15px`, small `13px`.
- Language: Russian (`lang="ru"`).

## Spacing & Radius

- Spacing scale: `4/8/12/16/24/32/48/64px`.
- Card/panel radius: `16px`. Buttons/inputs/badges: `10px`. Icon badges: `12px`.
- Max content width (desktop): `1200px`, centered.

## Components

### Icon badge (replaces the reference's 3D illustrations)

No 3D render assets are available to mockups, so every place the references use a 3D
icon illustration, use instead: a `48x48` (or `64x64` for featured cards) rounded-`12px`
square with `--accent-gradient` background and a white Lucide icon centered inside
(`<i data-lucide="...">` at `24px`/`32px`, `stroke-width: 2`). This keeps the gradient
accent from the references without requiring custom artwork.

### Document-type card (from `Тип документа.png`)

A 4-up grid (desktop) / stacked list (mobile) of cards, one per document type
(доклад/эссе/сочинение/реферат). Each card: icon badge (see above) + type name (H3) +
thin border. The **enabled** type (доклад, for story 1) has an `--accent-gradient` border
and is clickable/selected by default; the other three are rendered at reduced opacity
(`0.45`) with a small "скоро" (coming soon) pill badge in the corner and are
non-interactive (`pointer-events: none`, `cursor: not-allowed` conveyed via the reduced
opacity — no literal `disabled` attribute needed since these are static mockups).

### Buttons

- Primary: white fill, dark text, `10px` radius, `14px 24px` padding, weight 600.
- Secondary: transparent, `--border-subtle` outline, `--text-secondary` text.
- Disabled: `--bg-surface-raised` fill, `--text-muted` text, no hover.

### Status badge (pending/in_progress/completed/failed)

Pill badge, `--bg-surface-raised` background, colored dot + label:
- `pending`/`in_progress` → `--warning` dot, label "В обработке".
- `completed` → `--success` dot, label "Готово".
- `failed` → `--error` dot, label "Ошибка".

### Form inputs

`--bg-surface-raised` background, `--border-subtle` border (→ `--border-strong` on
focus, no colored focus ring — this app has no light-mode glow to contrast against),
`10px` radius, `14px 16px` padding, `--text-primary` value, `--text-muted` placeholder.

## Layout

No sidebar/dashboard shell exists yet — story 1 is a fully anonymous, single-flow page
(no logged-in area). Header is a simple bar: logo left, "Вход" (secondary) + "Попробовать
бесплатно" (primary) right — reused verbatim from `Landing.png` even on the generation
flow's pages, since there's no user session yet to change the header's contents.

- **Desktop**: viewport `1400px`, centered `1200px` content column.
- **Mobile**: viewport `375px`, single column, `16px` side padding, no bottom nav yet (no
  multi-tab app shell exists until later stories add one).

## Format Rules (from `.claude/templates/ui/mockup-generation-rules.md`)

- Standalone HTML, embedded CSS, Google Fonts (Inter) + Lucide icon CDN
  (`<script src="https://unpkg.com/lucide@latest"></script>`, `lucide.createIcons()`
  before `</body>`).
- `lang="ru"`, all interface text in Russian.
- Unsplash URLs for any photographic imagery (none expected for story 1 — this story has
  no marketing/landing screens, only the generation flow).
- One file per screen state, desktop and mobile as **separate files**, not responsive
  breakpoints.

## Templates & Components

No `ProductSpecification/ui/templates/*.html` base layouts exist yet (no auth/dashboard
pages have been built) — story 1's screens don't need them (no sidebar, no auth). No
shared web components in `ProductSpecification/ui/components/` yet either, since nothing
has repeated across 2+ stories yet. Both will be extracted the first time a pattern from
this story (e.g., the header bar, the status badge) actually repeats in story #2+.

---

## Light system (current) — stories 18, 10, 12, 13

Adopted 2026-07-28 from the customer's design. Tokens are shared, not re-declared per
story: copy `theme.css` next to the mockups and `<link>` it. Story 10 adds a second
stylesheet, `pages.css`, for the paginated-editor shell.

### Tokens

| Token | Value |
|-------|-------|
| `--bg-page` / `--bg-surface` / `--bg-sunken` | `#f2f4f7` / `#ffffff` / `#f7f8fa` |
| `--border-subtle` / `--border-strong` | `#e6e8ec` / `#d3d7de` |
| `--text-primary` / `--text-secondary` / `--text-muted` | `#0f172a` / `#64748b` / `#94a3b8` |
| `--accent` / `--accent-hover` / `--accent-soft` | `#1552f0` / `#1243c8` / `#e8effe` |
| `--danger` | `#ef4444` |
| radius | `--radius-lg 16px`, `--radius-md 10px`, `--radius-sm 8px` |

Primary buttons are **accent-filled with white text** here — not the dark system's
white-on-dark. Desktop mockup width is `1400px` (story 18 used `1640px`; story 10
narrowed it so a page rail plus an A4 sheet plus a settings panel fit without stretching).

### Editor shell (story 18 → story 10)

Top bar → breadcrumb bar → format bar → three-column body → status bar. Story 18's third
column is the AI chat; story 10's is the page-setup panel. Only one right-hand column is
open at a time.

### Paginated document (new in story 10)

- **Sheet.** White card, `6px` radius, `--shadow-card`, one element per page. Desktop
  renders A4 portrait at `720px` wide (real ratio, scaled); mobile fills the viewport
  width. Padding *is* the page margin — the ГОСТ preset 20/10/20/30 mm renders as
  `73px 55px 73px 82px` at that scale.
- **Sheet gap.** Sheets are separated by page background plus a centred `— разрыв
  страницы —` caption, so a break is legible without hovering.
- **Folio.** Page number absolutely positioned at the sheet's bottom centre. Absent on
  sheet 1 by default (`skip_number_on_first_page`).
- **Running head.** Top of the sheet, muted, with a hairline rule under it.
- **Page rail.** 240px left column listing pages. It is **navigation, not authoring** —
  pages are derived from content height and cannot be created by hand. The action is
  «Вставить разрыв страницы», never «Добавить страницу» (story 18's mockup had the
  latter; it contradicts the model and was corrected here).
- **Manual break marker.** Accent dashed rule with a centred label, selectable like a
  block. Desktop shows a side popover with «Удалить разрыв»; mobile shows full-width
  action buttons beneath it (44px touch targets).

### Measuring state

The document font must be loaded before layout is measured, so a paginated editor has a
real pre-layout state: spinner, «Готовим страницы…», skeleton lines in the sheet and
skeleton chips in the rail, and **no page count** in the status bar. It must be
distinguishable from both an error and an empty document.

### Two error channels, visually distinct

- **Inline field errors** — a `--danger` border plus a red caption under the field, for
  values the server rejected at the boundary (422). The caption states the arithmetic
  («Сверху и снизу вместе — 150 мм при высоте листа 148 мм»), not just "invalid".
- **Banner** — a red block at the top of the settings panel for a save that did not reach
  the server (network / 5xx), carrying a «Повторить» action.

Never render the two the same way: one means "your values are wrong", the other means
"your values are fine but unsaved".

### Mobile adaptations

- Page rail → horizontal chip strip under the format bar.
- Settings panel → bottom sheet with a grabber, `max-height: 88vh`.
- Status bar → fixed to the bottom edge.
- All touch targets ≥ 44px.

### Shell width by page kind (new in story 13)

Shell max-width is a separate number from the mockup **viewport** (see above: 1400px since
story 10). Which shell a page gets follows from its content, not from when it was drawn: a
**feed** («Мои проекты», 1640px) spreads across the viewport, a **single-column form**
(профиль, 1240px) does not. The narrower shell keeps the header and footer cards
proportionate to one column of fields — at feed width the chrome reads as belonging to a
page much wider than the form under it. Both centre with `margin: 0 auto`.

The form column itself is left-aligned under the H1, not centred in the shell — it hangs
off the same edge as the page title, which is what makes it read as that page's content
rather than a floating dialog.

### Account avatar — three states, all distinguishable (new in story 13)

The avatar is now backed by a network call (`GET /me`), so it has three states and each must
be legible against the other two at a glance:

| State | Rendering |
|-------|-----------|
| Норма | initials on the Figma gradient `linear-gradient(135deg,#51a2ff,#4f39f6)` (`Button/Container`, node 573:4506) — **not** the flat `--accent` fill theme.css declares |
| Загрузка | sunken circle, muted user glyph, shimmer — a *defined* placeholder, never a blank that pops into initials |
| Отказ | sunken circle, **dashed** `--border-strong` border, alert glyph, static — no shimmer |

The circle radius is constant across all three: a placeholder that changes shape when the
response lands is the same pop it exists to prevent. A degraded avatar that looks healthy
reads as "account with no name", which is why the failure state is dashed rather than merely
grey. The comparison strip in `13-profile-management/mockups/desktop/08-header-degraded.html`
is the reference — it is a mockup annotation, not a screen element.

### Identity block (new in story 13)

Top of a profile-like card: large avatar (72px desktop / 56px mobile) + primary line +
secondary line + a muted `since` row with a calendar icon. The primary line is the display
name when set and the **email** otherwise, with the secondary line carrying the other value.
The user's identity therefore never renders blank, whatever is missing.

### Account menu (`ProfileMenu`, Figma `profile navbar` 1218:5171)

238px panel anchored to the trigger's right edge. First row is the identity — avatar +
name/email, divider under it — and it is **not** a menu item: it answers "whose account am I
in", so it is never focusable or activatable. Items below, in order: «Мой профиль», «Выйти».
On mobile the panel is `calc(100vw - 44px)` capped at 260px, items padded to a 44px target.
«Выйти» never depends on `/me`: if the menu's contents were gated on a successful fetch, an
outage would trap the user in a session they cannot end.

### Bounded text field with a counter (new in story 13)

`<label>` and counter share a baseline row above the input; the counter is
`font-variant-numeric: tabular-nums` so it does not jitter while typing. It must match the
server's bound on **both** axes, and each is a separate way to get it wrong:

- **Unit** — code points, not UTF-16 units. `.length` disagrees by 2× on any non-BMP name.
- **Stage** — the value *after* the same normalization the server applies (trim + NFC), not
  the raw keystrokes. A 60-character NFD name is 120 raw code points and is accepted `200`;
  a counter reading the raw value shows `120 / 60` and, if over-limit also disables submit,
  blocks a value the server would have taken.

Over the limit: counter turns `--danger` and bold, input border turns `--danger`, and a
caption below states the arithmetic («сейчас 61»), not just "invalid". This is the inline
channel from story 10 — the banner channel still means "your value is fine but did not reach
the server", and a form with a write path needs **both** drawn.

Paired action buttons: primary is «Сохранить», secondary is «Отмена», and both are disabled
while the form is pristine. «Отмена» restores the last server-confirmed value and clears the
dirty flag — it is not a navigation. The dirty comparison runs on the normalized value
against the last server-confirmed one, for the same reason the counter does: compared raw, a
trailing space or an NFD paste leaves the form permanently dirty after a successful save.
