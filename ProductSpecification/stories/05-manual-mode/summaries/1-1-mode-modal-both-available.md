## red-selenium (2026-07-14)

**Quirk:** The `.soon-pill` CSS selector used to assert "no card shows a coming-soon badge" is not scoped to a single modal — it matches page-wide.
**Where:** `SelectableCard.tsx` (renders `.soon-pill` on any unavailable card), asserted from `mode_modal_statements.py`.
**Implication:** Safe only because `TypeModal` and `ModeModal` are mutually exclusive in `App.tsx` (`step === 'type'` vs `step === 'mode'`) — only one is ever mounted. Any future scenario that could render both modals' DOM at once (e.g. a transition-animation overlap) must scope this selector to the active modal's container, not assert page-wide.

## align-design (2026-07-14)

**Quirk:** `MODES` array in `ModeModal.tsx` orders manual before auto, but the mockup (`mockups/desktop/02-mode-modal.html`) orders auto before manual (manual is the right-hand, `.active`/recommended card).
**Where:** `ModeModal.tsx` `MODES` array (pre-existing order, not introduced by the align-design pass).
**Implication:** No test asserts card position/order (`ModeModal.test.tsx` and `mode_modal_statements.py` both key off `data-testid`/text, not DOM order), so a future align-design or visual-parity pass could "fix" this as a regression, or could silently reintroduce it if the array is ever reordered. Left as-is for scenario 1.1 since it's non-gating and out of scope for "both modes available."

**Decision:** The mockup's `.active`/check-badge highlight state (recommended-mode visual treatment) was not implemented in this pass.
**Why:** Scenario 1.1 only requires both modes to render as available/selectable; there is no "currently selected/recommended" state in this app's click-to-navigate flow, so the highlight has no behavioral trigger yet.
**Where applied:** `ModeModal.tsx` / `Modal.css` — no `.active` or `.check-badge` equivalent exists; revisit only if a future scenario introduces a persisted/hover selection state.
