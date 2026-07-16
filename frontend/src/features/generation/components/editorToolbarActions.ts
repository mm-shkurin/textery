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
  | 'undo'
  | 'redo'

export interface ToolbarAction {
  key: ToolbarActionKey
  label: string
  ariaLabel: string
  testId?: string
  run: (editor: Editor) => void
  isActive: (editor: Editor) => boolean
  disabled?: (editor: Editor) => boolean
}

export const TOOLBAR_DIVIDER_BEFORE: Set<ToolbarActionKey> = new Set(['bulletList', 'bold'])

// Shared by the blockquote and codeBlock toolbar actions: on an empty
// selection, toggling a mark needs an explicit line-range selection first
// (ProseMirror can't apply a mark to a collapsed selection), then the
// cursor position is restored so typing continues where the user left off.
function toggleLineMark(editor: Editor, markName: string): void {
  const { selection } = editor.state
  if (selection.empty) {
    const { $from } = selection
    const cursorPos = $from.pos
    editor
      .chain()
      .focus()
      .setTextSelection({ from: $from.start(), to: $from.end() })
      .toggleMark(markName)
      .setTextSelection({ from: cursorPos, to: cursorPos })
      .run()
    return
  }
  editor.chain().focus().toggleMark(markName).run()
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
    key: 'heading3',
    label: 'H3',
    ariaLabel: 'Заголовок 3',
    testId: 'toolbar-h3',
    run: (editor) => toggleLineMark(editor, 'heading3'),
    isActive: (editor) => editor.isActive('heading3'),
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
    key: 'underline',
    label: 'U',
    ariaLabel: 'Подчёркнутый',
    testId: 'toolbar-underline',
    run: (editor) => editor.chain().focus().toggleUnderline().run(),
    isActive: (editor) => editor.isActive('underline'),
  },
  {
    key: 'code',
    label: '<>',
    ariaLabel: 'Код',
    testId: 'toolbar-code',
    run: (editor) => editor.chain().focus().toggleCode().run(),
    isActive: (editor) => editor.isActive('code'),
  },
  {
    key: 'blockquote',
    label: '"',
    ariaLabel: 'Цитата',
    testId: 'toolbar-blockquote',
    run: (editor) => toggleLineMark(editor, 'blockquote'),
    isActive: (editor) => editor.isActive('blockquote'),
  },
  {
    key: 'horizontalRule',
    label: '―',
    ariaLabel: 'Горизонтальная линия',
    testId: 'toolbar-horizontal-rule',
    run: (editor) =>
      editor
        .chain()
        .focus()
        .insertContent({ type: 'horizontalRule', attrs: { marker: 'hr' } })
        .run(),
    isActive: () => false,
  },
  {
    key: 'codeBlock',
    label: '{}',
    ariaLabel: 'Блок кода',
    testId: 'toolbar-code-block',
    run: (editor) => toggleLineMark(editor, 'codeBlock'),
    isActive: (editor) => editor.isActive('codeBlock'),
  },
  {
    key: 'undo',
    label: '↶',
    ariaLabel: 'Отменить',
    testId: 'toolbar-undo',
    run: (editor) => editor.chain().focus().undo().run(),
    isActive: () => false,
    disabled: (editor) => !editor.can().undo(),
  },
  {
    key: 'redo',
    label: '↷',
    ariaLabel: 'Повторить',
    testId: 'toolbar-redo',
    run: (editor) => editor.chain().focus().redo().run(),
    isActive: () => false,
    disabled: (editor) => !editor.can().redo(),
  },
]
