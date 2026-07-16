# Task 5: Toolbar actions don't mark the document dirty, so the save status falsely reads "Сохранено" — Progress

Type: bug

## Spec
- [x] spec

## Fix: dirty flag only set by the DOM input handler, never by programmatic transactions
- [x] root cause analysis — confirmed by probe during Story 5 scenario 7.9's premortem: `setHasUnsavedChanges(true)` has one call site, `editorProps.handleDOMEvents.input` (`ManualEditor.tsx:117-118`); programmatic toolbar transactions emit no DOM `input` event. See spec.md for the probe output and the `hasUnsavedChanges` init-to-`true` trigger detail.
- [S] design — fix approach is obvious and single-option: move the flag to Tiptap's `onUpdate`, which fires on any document-changing transaction regardless of origin. No competing approach worth an ADR; the one non-obvious seam (`setContent` on reopen must NOT mark dirty) is a test-scoping detail, recorded in spec.md and pinned in the red phase, not a design decision.
- [~] steps discovery
