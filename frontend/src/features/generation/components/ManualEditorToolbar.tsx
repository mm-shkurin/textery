import { Fragment } from 'react'
import type { Editor } from '@tiptap/react'
import { TOOLBAR_ACTIONS, TOOLBAR_DIVIDER_BEFORE } from './editorToolbarActions'
import { ManualEditorSaveStatus } from './ManualEditorSaveStatus'

interface ManualEditorToolbarProps {
  editor: Editor | null
  documentId: string | null
  hasUnsavedChanges: boolean
  isSaving: boolean
  onSave: () => void
}

export function ManualEditorToolbar({
  editor,
  documentId,
  hasUnsavedChanges,
  isSaving,
  onSave,
}: ManualEditorToolbarProps) {
  return (
    <div className="me-toolbar">
      {TOOLBAR_ACTIONS.map((action) => (
        <Fragment key={action.key}>
          {TOOLBAR_DIVIDER_BEFORE.has(action.key) && <div className="me-toolbar-divider" aria-hidden="true" />}
          <button
            type="button"
            className="me-toolbar-btn"
            aria-label={action.ariaLabel}
            data-testid={action.testId}
            onClick={() => editor && action.run(editor)}
            aria-pressed={editor ? action.isActive(editor) : false}
          >
            {action.label}
          </button>
        </Fragment>
      ))}
      <div className="me-toolbar-status">
        <ManualEditorSaveStatus documentId={documentId} hasUnsavedChanges={hasUnsavedChanges} />
        {/*
          aria-disabled (not the native disabled attribute) so the
          button keeps receiving click/keyboard events while a save is
          in flight. A natively disabled <button> never dispatches
          click at all (not a jsdom quirk — that's spec behavior), so
          a click during isSaving would be silently lost instead of
          reaching handleSave's own in-flight guard, which is what
          queues the "save again" intent.
        */}
        <button type="button" className="me-save-btn" aria-disabled={isSaving} onClick={onSave}>
          {isSaving && <span data-testid="save-spinner" className="me-save-spinner" aria-hidden="true" />}
          Сохранить
        </button>
      </div>
    </div>
  )
}
