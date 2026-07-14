import type { Editor } from '@tiptap/react'

export interface ToolbarAction {
  key: string
  label: string
  ariaLabel: string
  testId?: string
  run: (editor: Editor) => void
  isActive: (editor: Editor) => boolean
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
]
