## red-selenium (2026-07-14)

**Quirk:** The `.soon-pill` CSS selector used to assert "no card shows a coming-soon badge" is not scoped to a single modal — it matches page-wide.
**Where:** `SelectableCard.tsx` (renders `.soon-pill` on any unavailable card), asserted from `mode_modal_statements.py`.
**Implication:** Safe only because `TypeModal` and `ModeModal` are mutually exclusive in `App.tsx` (`step === 'type'` vs `step === 'mode'`) — only one is ever mounted. Any future scenario that could render both modals' DOM at once (e.g. a transition-animation overlap) must scope this selector to the active modal's container, not assert page-wide.
