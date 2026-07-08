# Frontend Scenario 1.1: The landing page displays the hero and primary CTA — Journey Summary

## red-selenium (2026-07-08)

**Surprise:** `localhost` (and `::1`) was unreachable in this Windows dev environment even via native `Test-NetConnection`, though `127.0.0.1` worked fine.
**Why:** IPv6 loopback resolution is broken on this host, and Vite's default dev-server bind resolves `localhost` to `::1` first.
**Impact:** Vite's `server.host` and the Selenium `app_url` fixture both bind/target `127.0.0.1` explicitly, never `localhost`.

## red-selenium (2026-07-08)

**Mistake:** `conftest.py`'s `app_url` fixture defaulted `FRONTEND_PORT` to `5175` (an arbitrary local choice) instead of matching `vite.config.ts`'s default of `5173`.
**Why wrong:** The two independent hardcoded fallbacks diverged, so an unset `FRONTEND_PORT` would make tests silently connect to whatever unrelated server happened to be running on 5175 instead of the one just started.
**Correct location/approach:** Both default to `5173`, matching the documented `5173 + REPO_INDEX` port convention.

## red-selenium (2026-07-08)

**Decision:** The hero CTA button's locator is `data-testid="hero-primary-cta-button"`, not a generic `primary-cta-button`.
**Why:** The Figma export shows three identical "Создать генерацию" buttons (header, hero, footer); a shared testid would let Selenium's first-DOM-match resolution silently bind to the wrong one.
**Where applied:** `acceptance/statements/frontend/landing_page_statements.py`'s `PRIMARY_CTA_BUTTON` locator — the green-frontend hero CTA component must render this exact testid.

## red-frontend (2026-07-08)

**Quirk:** `npm run build` (`tsc -b && vite build`) fails as soon as a RED-phase test file exists, because `frontend/tsconfig.app.json`'s `include: ["src"]` has no exclude for `__tests__`/`*.test.tsx`, so `tsc -b` type-checks tests importing not-yet-created components.
**Where:** `frontend/tsconfig.app.json`.
**Implication:** Every future `red-frontend` step will break `npm run build` until this is fixed with an exclude or a separate build-only tsconfig; `vitest run` (the actual RED gate) is unaffected.

## red-frontend (2026-07-08)

**Quirk:** `vite.config.ts` sets `test.globals: true` but `tsconfig.app.json`'s `types` array omits `vitest/globals`, so bare-global test code (`describe`/`it`/`expect` with no import) passes `vitest run` but fails `tsc -b`.
**Where:** `frontend/vite.config.ts` / `frontend/tsconfig.app.json`.
**Implication:** Future test files relying on the `globals: true` config (rather than explicit `vitest` imports, as this scenario's test uses) will break `npm run build` even though they pass the test suite.
