import type { Editor } from '@tiptap/react'
import type { ToolbarAction, ToolbarActionKey, ToolbarRunAction } from './toolbarAction'

export type {
  ToolbarAction,
  ToolbarActionKey,
  ToolbarRunAction,
  ToolbarUiAction,
} from './toolbarAction'

export const TOOLBAR_DIVIDER_BEFORE: Set<ToolbarActionKey> = new Set(['bold'])

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

// Shared by bold/italic/strike/underline/code: each is a plain mark toggle
// with no special selection handling, differing only in the mark name,
// label, aria label and test id.
function simpleMarkToggle(
  key: ToolbarActionKey,
  markName: string,
  label: string,
  ariaLabel: string,
  testId?: string,
): ToolbarRunAction {
  return {
    key,
    label,
    ariaLabel,
    testId,
    run: (editor) => editor.chain().focus().toggleMark(markName).run(),
    isActive: (editor) => editor.isActive(markName),
  }
}

// H1/H2, paragraph, and both list toggles were mockup-era stubs calling Tiptap block-node
// commands (toggleHeading / setParagraph / toggleBulletList / toggleOrderedList). The document
// schema is Document.extend({ content: 'inline*' }) — it has no block nodes — so those commands
// are inert: the controls rendered but did nothing. Removed so the toolbar reflects real
// capability. Restoring them requires migrating the schema to block content (a separate story).
export const TOOLBAR_ACTIONS: ToolbarAction[] = [
  {
    key: 'heading3',
    label: 'H3',
    ariaLabel: 'Заголовок 3',
    testId: 'toolbar-h3',
    run: (editor) => toggleLineMark(editor, 'heading3'),
    isActive: (editor) => editor.isActive('heading3'),
  },
  simpleMarkToggle('bold', 'bold', 'B', 'Жирный', 'toolbar-bold'),
  simpleMarkToggle('italic', 'italic', 'I', 'Курсив'),
  simpleMarkToggle('strike', 'strike', 'S', 'Зачёркнутый', 'toolbar-strike'),
  simpleMarkToggle('underline', 'underline', 'U', 'Подчёркнутый', 'toolbar-underline'),
  simpleMarkToggle('code', 'code', '<>', 'Код', 'toolbar-code'),
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
    key: 'alignCenter',
    label: '↔',
    ariaLabel: 'Выравнивание по центру',
    testId: 'toolbar-align-center',
    run: (editor) => toggleLineMark(editor, 'alignCenter'),
    isActive: (editor) => editor.isActive('alignCenter'),
  },
  {
    key: 'link',
    label: '🔗',
    ariaLabel: 'Ссылка',
    testId: 'toolbar-link',
    ui: 'link-popover',
    isActive: (editor) => editor.isActive('link'),
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
