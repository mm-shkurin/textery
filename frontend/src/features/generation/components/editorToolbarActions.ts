import type { Editor } from '@tiptap/react'

export type ToolbarActionKey =
  | 'heading1'
  | 'heading2'
  | 'paragraph'
  | 'bulletList'
  | 'orderedList'
  | 'bold'
  | 'italic'
  | 'strike'
  | 'blockquote'

export interface ToolbarAction {
  key: ToolbarActionKey
  label: string
  ariaLabel: string
  testId?: string
  run: (editor: Editor) => void
  isActive: (editor: Editor) => boolean
}

export const TOOLBAR_DIVIDER_BEFORE: Set<ToolbarActionKey> = new Set(['bulletList', 'bold'])

function toggleBlockquote(editor: Editor): void {
  const { selection } = editor.state
  if (selection.empty) {
    const { $from } = selection
    editor.chain().focus().setTextSelection({ from: $from.start(), to: $from.end() }).toggleMark('blockquote').run()
    return
  }
  editor.chain().focus().toggleMark('blockquote').run()
}

export const TOOLBAR_ACTIONS: ToolbarAction[] = [
  {
    key: 'heading1',
    label: 'H1',
    ariaLabel: 'Заголовок 1',
    run: (editor) => editor.chain().focus().toggleHeading({ level: 1 }).run(),
    isActive: (editor) => editor.isActive('heading', { level: 1 }),
  },
  {
    key: 'heading2',
    label: 'H2',
    ariaLabel: 'Заголовок 2',
    run: (editor) => editor.chain().focus().toggleHeading({ level: 2 }).run(),
    isActive: (editor) => editor.isActive('heading', { level: 2 }),
  },
  {
    key: 'paragraph',
    label: '¶',
    ariaLabel: 'Абзац',
    run: (editor) => editor.chain().focus().setParagraph().run(),
    isActive: (editor) => editor.isActive('paragraph'),
  },
  {
    key: 'bulletList',
    label: '•',
    ariaLabel: 'Маркированный список',
    run: (editor) => editor.chain().focus().toggleBulletList().run(),
    isActive: (editor) => editor.isActive('bulletList'),
  },
  {
    key: 'orderedList',
    label: '1.',
    ariaLabel: 'Нумерованный список',
    run: (editor) => editor.chain().focus().toggleOrderedList().run(),
    isActive: (editor) => editor.isActive('orderedList'),
  },
  {
    key: 'bold',
    label: 'B',
    ariaLabel: 'Жирный',
    testId: 'toolbar-bold',
    run: (editor) => editor.chain().focus().toggleBold().run(),
    isActive: (editor) => editor.isActive('bold'),
  },
  {
    key: 'italic',
    label: 'I',
    ariaLabel: 'Курсив',
    run: (editor) => editor.chain().focus().toggleItalic().run(),
    isActive: (editor) => editor.isActive('italic'),
  },
  {
    key: 'strike',
    label: 'S',
    ariaLabel: 'Зачёркнутый',
    testId: 'toolbar-strike',
    run: (editor) => editor.chain().focus().toggleStrike().run(),
    isActive: (editor) => editor.isActive('strike'),
  },
  {
    key: 'blockquote',
    label: '"',
    ariaLabel: 'Цитата',
    testId: 'toolbar-blockquote',
    run: (editor) => toggleBlockquote(editor),
    isActive: (editor) => editor.isActive('blockquote'),
  },
]
