# UI Conventions — Textery

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
