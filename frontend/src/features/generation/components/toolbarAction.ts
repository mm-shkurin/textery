import type { Editor } from '@tiptap/react'

export type ToolbarActionKey =
  | 'heading1'
  | 'heading2'
  | 'heading3'
  | 'paragraph'
  | 'bulletList'
  | 'orderedList'
  | 'bold'
  | 'italic'
  | 'strike'
  | 'underline'
  | 'code'
  | 'blockquote'
  | 'horizontalRule'
  | 'codeBlock'
  | 'alignCenter'
  | 'link'
  | 'undo'
  | 'redo'

interface ToolbarActionBase {
  key: ToolbarActionKey
  label: string
  ariaLabel: string
  testId?: string
  isActive: (editor: Editor) => boolean
  disabled?: (editor: Editor) => boolean
}

// The click-only shape: 17 of 18 actions. Clicking runs a command outright.
export interface ToolbarRunAction extends ToolbarActionBase {
  run: (editor: Editor) => void
  ui?: undefined
}

// The opt-in UI channel: clicking opens a panel that collects input before any
// command runs. Following the `disabled?(editor)` precedent from 7.5 — extend
// the contract rather than special-case the renderer. `run` is absent by type,
// so a UI action cannot silently carry a dead click handler.
export interface ToolbarUiAction extends ToolbarActionBase {
  ui: 'link-popover'
  run?: undefined
}

export type ToolbarAction = ToolbarRunAction | ToolbarUiAction
