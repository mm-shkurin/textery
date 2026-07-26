import type { ToolbarAction, ToolbarActionKey, ToolbarRunAction } from './toolbarAction'

export type {
  ToolbarAction,
  ToolbarActionKey,
  ToolbarRunAction,
  ToolbarUiAction,
} from './toolbarAction'

export const TOOLBAR_DIVIDER_BEFORE: Set<ToolbarActionKey> = new Set(['bold'])

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

// Block-schema toolbar (migration ADR, 2026-07-26): heading/blockquote/codeBlock
// are real block nodes now, so their toggles call the StarterKit node commands
// and `isActive` reads node/attr names. H3 toggles the level-3 heading node;
// alignment is a `textAlign` block attribute, not a wrapping mark.
export const TOOLBAR_ACTIONS: ToolbarAction[] = [
  {
    key: 'heading3',
    label: 'H3',
    ariaLabel: 'Заголовок 3',
    testId: 'toolbar-h3',
    run: (editor) => editor.chain().focus().toggleHeading({ level: 3 }).run(),
    isActive: (editor) => editor.isActive('heading', { level: 3 }),
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
    run: (editor) => editor.chain().focus().toggleBlockquote().run(),
    isActive: (editor) => editor.isActive('blockquote'),
  },
  {
    key: 'bulletList',
    label: '•',
    ariaLabel: 'Маркированный список',
    testId: 'toolbar-bullet-list',
    run: (editor) => editor.chain().focus().toggleBulletList().run(),
    isActive: (editor) => editor.isActive('bulletList'),
  },
  {
    key: 'orderedList',
    label: '1.',
    ariaLabel: 'Нумерованный список',
    testId: 'toolbar-ordered-list',
    run: (editor) => editor.chain().focus().toggleOrderedList().run(),
    isActive: (editor) => editor.isActive('orderedList'),
  },
  {
    key: 'horizontalRule',
    label: '―',
    ariaLabel: 'Горизонтальная линия',
    testId: 'toolbar-horizontal-rule',
    run: (editor) => editor.chain().focus().setHorizontalRule().run(),
    isActive: () => false,
  },
  {
    key: 'codeBlock',
    label: '{}',
    ariaLabel: 'Блок кода',
    testId: 'toolbar-code-block',
    run: (editor) => editor.chain().focus().toggleCodeBlock().run(),
    isActive: (editor) => editor.isActive('codeBlock'),
  },
  {
    key: 'alignCenter',
    label: '↔',
    ariaLabel: 'Выравнивание по центру',
    testId: 'toolbar-align-center',
    run: (editor) => editor.chain().focus().setTextAlign('center').run(),
    isActive: (editor) => editor.isActive({ textAlign: 'center' }),
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
