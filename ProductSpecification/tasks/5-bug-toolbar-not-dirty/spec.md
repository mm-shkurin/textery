# Task 5: Toolbar actions don't mark the document dirty, so the save status falsely reads "Сохранено"

Type: bug

## Description

In the manual editor (Story 5), applying any formatting via the toolbar after a
successful save leaves the document changed on screen while the save status line
still reads **Сохранено**. The visitor is told their work is persisted when it is
not. Closing the tab at that point loses the change silently — there is no
`beforeunload` guard anywhere in `frontend/src`, so nothing else intervenes.

Affects all 17 entries in `TOOLBAR_ACTIONS`, not one control.

## Reproduction

1. Open the manual editor, type text, click Сохранить, wait for **Сохранено**.
2. Select the text, click any formatting button (e.g. `toolbar-bold`).
3. Observe: the content changes (`<strong>hello</strong> world`), the status line
   still reads **Сохранено**.
   Expected: **Черновик, ещё не сохранён**.

Confirmed by a throwaway probe during scenario 7.9's premortem pass (probe removed,
`git status` clean at the time). Both content assertions passed before the status
assertion failed, which rules out a stored-marks false positive — the document
genuinely diverged from the server:

```
expect(contentArea.innerHTML).toBe('<strong>hello</strong> world')          // PASSED
expect(screen.queryByText('Черновик, ещё не сохранён')).toBeInTheDocument() // FAILED — received null
```

## Root cause (already known — confirmed by probe, not speculative)

`setHasUnsavedChanges(true)` has exactly one call site: the ProseMirror DOM `input`
handler at `frontend/src/features/generation/components/ManualEditor.tsx:117-118`
(`editorProps.handleDOMEvents.input`).

Toolbar actions dispatch ProseMirror transactions programmatically
(`editor.chain().focus().toggleMark(...).run()`). A programmatic transaction changes
the document but emits no DOM `input` event — that event only fires for direct user
input into the contenteditable. So the flag never flips for any toolbar-driven edit.

The trigger is precise: `hasUnsavedChanges` initialises to `true`
(`ManualEditor.tsx:39`), so the bug only manifests **after the first successful
save** resets it to `false` — exactly the state a visitor is in when they go back
over their text to format it.

## Scope

Pre-existing across all 17 toolbar actions since the dirty-flag was introduced in
scenario 5.1. Not introduced by any single scenario. Surfaced during 7.9's design
work unit and deliberately not fixed inline there: that unit was a design/spec step
with no production code, and this defect belongs to none of 7.9's Gherkin.

Related, NOT in this task's scope:
- The save-error banner separately claims content is "сохранён локально в редакторе"
  when no local persistence exists — an open BLOCK recorded in
  `ProductSpecification/stories/05-manual-mode/carryover.md` since scenario 5.2.
  Same family (the UI lying about persistence), different defect.
- The absence of any `beforeunload`/navigation guard. That is what makes this bug
  lose data rather than merely mislead, but adding an exit guard is its own change.

## Fix approach

Tiptap's `useEditor` exposes an `onUpdate` callback that fires on any transaction
that changes the document, regardless of whether it originated from a DOM event or
a programmatic chain. Moving the flag from `handleDOMEvents.input` to `onUpdate` is
the minimal fix and covers every action at once.

Care needed at one seam: `useDocumentInit` populates the editor via
`editor.commands.setContent(result.content)` when reopening a saved document
(`useDocumentInit.ts:27`). That is a document-changing transaction too, so a naive
`onUpdate` would mark a freshly-loaded, untouched document as dirty. The RED phase
must pin both directions — toolbar edit marks dirty, programmatic load does not.
