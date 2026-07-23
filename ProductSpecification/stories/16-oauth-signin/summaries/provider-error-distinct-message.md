# Scenario 4.1 — Provider error / user-cancel returns to login with a distinct message

## green-frontend stale-banner (2026-07-23)

**Mistake:** Wrote the "banner survives the scrub" guard as an in-file `rerender` on a `MemoryRouter` whose entry state changed, expecting it to prove capture-locally beats blank-on-scrub.
**Why wrong:** `MemoryRouter` ignores changed `initialEntries` on rerender, and the file's `useNavigate` mock is a no-op, so live `location.state` is never actually cleared — a naive live-reading component passes the in-file rerender too, making it non-discriminating.
**Correct location/approach:** Put the survives-the-scrub test in a SEPARATE file with react-router left fully REAL (`OAuthErrorBanner.survivesScrub.test.tsx`), so the effect's real `navigate(...,{state:{}})` genuinely clears state mid-mount; verified it fails against a live-reading variant and passes against the captured-`useState` version.
