# Criterion 2 — Consistency and architectural style

The question behind every item: **does the repository read as the work of one team
with one set of decisions, and does its dependency direction hold?**

Mechanical probes: category `arch` (`probes/rules_arch.py`), plus the
`ARCH-BOUNDARY-*` probes generated from each layer's `forbidden_imports` in
`probes/config.json`. Everything else is a judgment item.

## Dependency direction

| Item | What is checked | Lane |
|---|---|---|
| Boundaries hold | Each layer's declared forbidden imports never appear — inner layers know nothing of outer ones, shared code knows nothing of features. Deferred imports inside functions count | `ARCH-BOUNDARY-*` |
| No transport leakage | Business logic does not speak the delivery protocol: no MIME types, status codes, headers, or request objects below the adapter layer | `ARCH-BOUNDARY-*` |
| No persistence leakage | The delivery layer does not own transactions or sessions; that boundary lives with the use case | `ARCH-BOUNDARY-*` |
| No peer chaining | Same-layer components do not call each other (use case → use case, controller → controller) | judgment |
| Composition root | Dependencies are wired in one place, in one style, with one naming convention | judgment |
| Packaging honest | No runtime path patching to make imports resolve — that hides a broken package setup | `ARCH-PATH-HACK` |

## One project, one style

| Item | What is checked | Lane |
|---|---|---|
| Tooling declared | A linter/formatter config is committed for the layer | `ARCH-ENTRY-CONFIG` |
| One standard | Rules are not weakened for tests or any subdirectory — no double standard between test and production code | `ARCH-TEST-DOUBLE-STANDARD` |
| Export convention | One export style across the layer | `ARCH-EXPORT-STYLE` |
| File naming | One naming convention per directory; utilities, types, and hooks live in their declared place, not loose at a slice root | judgment |
| Module cohesion | One file, one concern — a schema file holds one aggregate, not every schema in the app | judgment |
| Error handling | One centralized mapping from domain errors to responses, not a hand-rolled mapping per controller | judgment |
| File size | No file over the project's line limit | `ARCH-SIZE`, `ARCH-SIZE-STYLE` |

## State and rendering (UI layers)

| Item | What is checked | Lane |
|---|---|---|
| Deliberate state model | A shared-state or data-cache solution is chosen and declared — or the local-only decision is documented with its boundary | `ARCH-STATE-LIB` |
| State grouped | Related state is one object/reducer, not many parallel slots in one hook | `ARCH-STATE-SPREAD` |
| Render scope | Input state lives in the smallest component that needs it; list items are memoized with stable props, so typing does not repaint a screen | judgment |
| Scoped styles | Component styles cannot leak; only the entry point imports a global stylesheet | `ARCH-SCOPED-STYLES` |
| Design tokens | Colors, spacing, and typography come from tokens; literals live only where tokens are declared | `ARCH-DESIGN-TOKENS` |
| Platform access | Browser/runtime globals are reached through a guarded helper, never inline | `ARCH-ENV-ACCESS` |
| Domain vs presentation | Domain types and their human-facing labels are separate — an enum is not a translation table | judgment |

## Statelessness

| Item | What is checked | Lane |
|---|---|---|
| No instance-local state | Nothing that must be consistent across instances lives in a module global, static field, or local cache | `ARCH-GLOBAL-STATE` |

## Known instances (2026-08-07)

`sys.path.insert` in the entry point; domain-layer fakes importing from the use-case
layer; MIME strings inside a use case; mixed naming in the container directory; one
DTO file holding projects, pages, elements, and paginators; DB sessions injected into
HTTP dependencies; per-controller HTTP-code mapping; relaxed lint rules for tests;
no state manager; per-keystroke re-render of a flow container; six `useState` in one
hook; unmemoized list items; loose utils at slice root; global CSS imports; hex
literals beside declared variables; magic poll interval; document types mixed with
Russian labels; mixed default/named exports; bare `window`/`document` access.
