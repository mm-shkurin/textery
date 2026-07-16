import { Fragment, useState } from 'react'
import type { Editor } from '@tiptap/react'
import './ManualEditorToolbar.css'
import { TOOLBAR_ACTIONS, TOOLBAR_DIVIDER_BEFORE } from './editorToolbarActions'
import type { ToolbarActionKey } from './editorToolbarActions'
import { ManualEditorSaveStatus } from './ManualEditorSaveStatus'
import { LinkPopover } from './LinkPopover'

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
  // Which UI action's panel is open, if any. Conditional mount, not a hidden
  // toggle — so the panel is absent from the DOM until asked for, and its own
  // state (the typed URL, any error) is discarded on close rather than
  // reappearing on the next open.
  const [openUiKey, setOpenUiKey] = useState<ToolbarActionKey | null>(null)

  const handleClick = (action: (typeof TOOLBAR_ACTIONS)[number]) => {
    if (!editor) return
    if (action.ui) {
      setOpenUiKey(openUiKey === action.key ? null : action.key)
      return
    }
    action.run(editor)
  }

  return (
    <div className="me-toolbar">
      {TOOLBAR_ACTIONS.map((action) => (
        <Fragment key={action.key}>
          {TOOLBAR_DIVIDER_BEFORE.has(action.key) && <div className="me-toolbar-divider" aria-hidden="true" />}
          <span className={action.ui ? 'me-link-popover-anchor' : undefined}>
            <button
              type="button"
              className="me-toolbar-btn"
              aria-label={action.ariaLabel}
              data-testid={action.testId}
              onClick={() => handleClick(action)}
              aria-pressed={editor ? action.isActive(editor) : false}
              aria-expanded={action.ui ? openUiKey === action.key : undefined}
              disabled={editor ? action.disabled?.(editor) ?? false : true}
            >
              {action.label}
            </button>
            {editor && action.ui === 'link-popover' && openUiKey === action.key && (
              <LinkPopover editor={editor} onClose={() => setOpenUiKey(null)} />
            )}
          </span>
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
