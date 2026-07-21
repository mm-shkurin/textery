# Scenario 7.9 — Link popover / normalizeHref output (journey summary)

## red-frontend-url-shapes-3 (2026-07-21)

**Decision:** Invisible / control characters in a link URL (U+00AD, U+200B, U+202E, C0) are REJECTED, not stripped and not accepted.
**Why:** They produce well-formed-*looking* but dead or deceptive links (U+202E is a known RTL-override spoofing vector); rejection is consistent with the popover's existing security posture and is the loud-over-silent choice.
**Where applied:** `LinkPopover.tsx` `normalizeHref` — the char screen (pending in green-frontend-url-shapes-3) must sit on the OUTPUT / fallback path, not only inside HOST_SHAPE.

## red-frontend-url-shapes-3 (2026-07-21)

**Surprise:** A soft-hyphen host `exa­mple.com` (U+00AD) links today with no alert, but not via HOST_SHAPE — U+00AD is Unicode category Cf, so `HOST_SHAPE.test()` is false; it flows through the FALLBACK (`return url` bare) and `isAllowedUri`'s relative-form alternative treats the soft hyphen as a word boundary and accepts the schemeless string.
**Why:** `isAllowedUri` (the only downstream validator) vets the *scheme* only and admits a relative/schemeless remainder; `new URL()` on the bare string actually throws.
**Impact:** Green cannot close G1/G2 by tightening HOST_SHAPE alone — an unparseable-or-invisible input reaches the fallback branch, so the usability screen (`new URL()` parse + `\p{C}` reject) must cover the fallback/output, while legitimate `\p{L}`/`\p{So}` (Cyrillic hosts, emoji paths) must still pass.
