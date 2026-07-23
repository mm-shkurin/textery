# Scenario 3.3 — Line break in Ручной режим (journey summary)

## red-frontend-line-break (2026-07-20)

**Expected:** save payload collapses to `line oneline two` (the `<br>` dropped, adjacent text joined).
**Actual:** `line one line two` — the dropped `<br>` is replaced by a single space, not by nothing.
**Why:** ProseMirror's schema-driven reconciliation of the DOM (via the forced `domObserver.flush()`) treats the unknown `<br>` as a whitespace boundary when hardBreak is not in the schema, not as a zero-width join.
**Resolution:** None needed — failure type/status/assertion identical; only the received string literal in the prediction was corrected.

## green-frontend-line-break (2026-07-20)

**Mistake:** The ADR's first plan — an `appendTransaction` that deletes a trailing `hardBreak` node — was implemented and OOM-crashed the test worker.
**Why wrong:** The delete re-renders ProseMirror's trailing-break cursor helper, and the same synchronous `domObserver.flush()` reparses that helper into a fresh trailing hardBreak inside the *same* dispatch — an unbreakable strip↔reparse loop; a meta-flag re-entry guard did not stop it (each flush emits a fresh unflagged transaction).
**Correct location/approach:** Remove both stray-`<br>` *sources* instead of the symptom — a required `marker` attr disqualifies hardBreak from the `inline*` schema's `ContentMatch.defaultType` (kills the ghost filler) and a parse rule ignores `br.ProseMirror-trailingBreak` (kills the helper reparse). See `hardBreakNode.ts`.

## green-frontend-line-break (2026-07-20)

**Quirk:** In this `inline*` Document a plain `hardBreak` (no required attrs) is eligible as the schema's `defaultType`, so ProseMirror auto-injects a trailing `<br>` on reconciliation with no keystroke; and plain **Enter** does nothing (the default keymap has no block to split), so a line break needs an explicit Enter→hardBreak keymap.
**Where:** `frontend/src/features/generation/components/hardBreakNode.ts`, `hardBreakKeymap.ts` (same ghost-filler class already handled in `horizontalRuleNode.ts`).
**Implication:** Any future inline-node addition to this editor must give the node a required attr (or otherwise disqualify it from `defaultType`) or it will ghost-fill, and any block-splitting gesture must be bound explicitly.

## green-selenium (2026-07-22)

**Expected:** both live-browser tests pass on the first run — characterization of already-shipped behavior, pre-probed live before writing.
**Actual:** both FAILED — `foobar<br>` instead of `foo<br>bar`.
**Why:** the fault was the test, not the product: `type_text_in_editor` focuses by clicking, and a WebDriver click re-places the caret where the pointer landed (the previous line), so the continuation typed *before* the break.
**Resolution:** added `continue_typing_in_editor` (send_keys with no click, typing at the current caret); a multi-keystroke Selenium sequence must click once to focus, then keep typing.

## green-selenium (2026-07-22)

**Surprise:** two consecutive Enters at end-of-content keep BOTH breaks in a real browser (`foo<br><br>baz`), where jsdom collapsed them to zero — the premortem had rated the collapse a CREDIBLE possible multi-trailing bug.
**Why:** the jsdom collapse was a fake-caret artifact (the 2nd synthetic keyDown does not reposition the caret); a real contenteditable advances it.
**Impact:** the behavior is correct and now pinned; the jsdom line-break tests cannot be trusted for trailing-Enter counts — only the live Selenium run can.
