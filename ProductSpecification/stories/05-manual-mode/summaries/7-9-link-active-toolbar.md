# Scenario 7.9 — Link popover / normalizeHref output (journey summary)

## red-frontend-url-shapes-3 (2026-07-21)

**Decision:** Invisible / control characters in a link URL (U+00AD, U+200B, U+202E, C0) are REJECTED, not stripped and not accepted.
**Why:** They produce well-formed-*looking* but dead or deceptive links (U+202E is a known RTL-override spoofing vector); rejection is consistent with the popover's existing security posture and is the loud-over-silent choice.
**Where applied:** `LinkPopover.tsx` `normalizeHref` — the char screen (pending in green-frontend-url-shapes-3) must sit on the OUTPUT / fallback path, not only inside HOST_SHAPE.

## red-frontend-url-shapes-3 (2026-07-21)

**Surprise:** A soft-hyphen host `exa­mple.com` (U+00AD) links today with no alert, but not via HOST_SHAPE — U+00AD is Unicode category Cf, so `HOST_SHAPE.test()` is false; it flows through the FALLBACK (`return url` bare) and `isAllowedUri`'s relative-form alternative treats the soft hyphen as a word boundary and accepts the schemeless string.
**Why:** `isAllowedUri` (the only downstream validator) vets the *scheme* only and admits a relative/schemeless remainder; `new URL()` on the bare string actually throws.
**Impact:** Green cannot close G1/G2 by tightening HOST_SHAPE alone — an unparseable-or-invisible input reaches the fallback branch, so the usability screen (`new URL()` parse + `\p{C}` reject) must cover the fallback/output, while legitimate `\p{L}`/`\p{So}` (Cyrillic hosts, emoji paths) must still pass.

## green-frontend-url-shapes-3 (2026-07-21)

**Surprise:** The `isUsable` screen (`new URL()` parse + `\p{C}` reject) is bypassed for any explicitly-schemed URL, so the schemed twins of the exact vectors it closed still link — `http://example.com:99999999999` (dead port, `new URL()` throws) and `http://exa­mple.com` (soft hyphen) both ship as live links.
**Why:** `normalizeHref` checks the known-scheme SET first and `return url` unscreened; the 7 committed reds pin only the *schemeless* forms (which go through HOST_SHAPE/fallback), so the suite is green while the property is only half-enforced.
**Impact:** A future url-shapes-4 / red-2 must run `isUsable` on the passthrough result too and pin `http://…:99999999999` + `http://exa­mple.com` as rejected. Also: `tel:` vs host `localhost:3000` are structurally identical (`word:colon:digits`) — only a known-scheme SET separates them, never a regex over the string shape.

## green-frontend-aria (2026-07-21)

**Decision:** The link toolbar button keeps BOTH `aria-pressed` (cursor is inside an existing link, `isActive('link')`) AND `aria-expanded` (popover open) — they are orthogonal states, ARIA permits both, so defect-6b's "drop aria-pressed from UI actions" was abandoned.
**Why:** `aria-pressed` encodes a Gherkin-required indicator (scenario 7.9: "button active while cursor is within a link", pinned in `ManualEditor.link.test.tsx:54/63`) that is a *separate* concern from popover-open; dropping it deletes a required signal, not a duplicate.
**Where applied:** `ManualEditorToolbar.tsx` (aria-pressed on all buttons, aria-expanded only on `action.ui`); a new `.me-toolbar-btn[aria-expanded='true']` CSS rule mirrors the aria-pressed highlight so popover-open stays visible when the cursor isn't in a link.

## green-frontend-aria (2026-07-21)

**Mistake:** The `red-frontend-aria` step baked in defect-6b ("the link/UI button must NOT carry `aria-pressed`") as a real red, and `green-frontend-aria` tried to implement it.
**Why wrong:** It contradicts the committed, previously-green `ManualEditor.link.test.tsx:54/63` (aria-pressed on the link button per 7.9's Gherkin) — no production code satisfies both; the green-agent correctly hard-stopped rather than edit an out-of-scope test.
**Correct location/approach:** Keep both attributes (orthogonal), correct the aria red into a coexistence/independence guard (opening the popover flips aria-expanded without touching aria-pressed); when a red asserts *removing* an attribute, check no other committed test pins its presence first.

## green-frontend-popover-contract (2026-07-21)

**Surprise:** The document `mousedown` click-outside handler excludes `editor.view.dom` from "outside", so clicking into the editor body to reposition the caret neither applies nor closes — the popover stays stuck open and the typed URL is silently dropped, contradicting the ADR's own click-outside row ("close AND apply the captured range").
**Why:** The exclusion was added as a premortem defensive guard (don't apply on a text-selection drag ending in the editor), but a click into the editor genuinely IS outside the popover per the ADR.
**Impact:** A follow-up red-2 must resolve the tension deliberately (apply+close vs stay-open); also the captured range is frozen ABSOLUTE positions, so an autosave `setContent` round-trip (`useDocumentSave.ts:95`) while the popover is open shifts them and the link lands on the wrong text (`setTextSelection` clamps, no throw).
