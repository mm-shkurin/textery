# Task 4: Applying inline code to bold text silently strips the bold mark

Type: bug

## Description

In the manual editor (Story 5, Scenario 7.4), selecting text that already
carries the bold mark and applying inline code removes the bold formatting
instead of nesting both marks.

## Reproduction

1. Select text, click `toolbar-bold` (bold applied).
2. With the same text still selected, click `toolbar-code` (inline code applied).
3. Observe: `<code>hello</code> world` — the `<strong>` wrapper is gone.
   Expected (if bold is meant to survive): `<strong><code>hello</code></strong> world`
   or equivalent nesting.

## Root cause (already known — confirmed during Story 5 Scenario 7.4 work)

Tiptap's stock `Code` mark extension ships with `excludes: '_'`
(`node_modules/@tiptap/extension-code/dist/index.js:42`), meaning applying
the `code` mark to a selection strips every other mark from that range by
design. Verified directly via a throwaway reproduction test — not
speculative.

## Scope note

Discovered and confirmed during `ProductSpecification/stories/05-manual-mode`
Scenario 7.4 (inline code toolbar). Out of that scenario's Gherkin acceptance
criteria (7.4 doesn't test mark combination), so it was flagged rather than
fixed inline. This task tracks the decision and fix separately.

## Open question for design phase

Is `excludes: '_'` the desired product behavior (code spans are commonly
rendered as plain, unstyled monospace in many editors, so stripping other
marks may be intentional), or should bold/italic/strike survive inside code?
Needs a product decision before `root cause analysis` can conclude — the
root cause is known, but the *fix* depends on which behavior is wanted:
- Fix A: accept current behavior, close as "working as intended", add a
  regression test asserting the strip explicitly.
- Fix B: override `Code`'s `excludes` (e.g. `Code.extend({ excludes: '' })`)
  so bold/italic/strike survive inside inline code.
