import { Fragment, useState, type ReactNode } from 'react'
import type { Editor } from '@tiptap/react'
import styles from './ManualEditorToolbar.module.css'
import linkPopoverStyles from './LinkPopover.module.css'
import { TOOLBAR_ACTIONS, TOOLBAR_DIVIDER_BEFORE } from '../utils/editorToolbarActions'
import type { ToolbarActionKey } from '../utils/editorToolbarActions'
import { LinkPopover } from './LinkPopover'
import {
  AlignCenterIcon,
  BulletListIcon,
  CodeBlockIcon,
  ColumnAddIcon,
  LinkIcon,
  OrderedListIcon,
  QuoteIcon,
  RedoIcon,
  RowAddIcon,
  RuleIcon,
  TableDeleteIcon,
  TableIcon,
  UndoIcon,
} from './EditorIcons'

interface ManualEditorToolbarProps {
  editor: Editor | null
}

// Which glyph replaces an action's text label. Only the actions whose label was a symbol are
// listed: «⌫⊞», «+|», «―» and «⊞» meant nothing outside the file that wrote them, and the
// toolbar read as debug output because of it. B / I / U / S / </> / H3 keep their letters —
// there the letter IS the conventional sign, and an icon would be the less legible of the two.
const ICON_BY_KEY: Partial<Record<ToolbarActionKey, ReactNode>> = {
  blockquote: <QuoteIcon />,
  bulletList: <BulletListIcon />,
  orderedList: <OrderedListIcon />,
  horizontalRule: <RuleIcon />,
  codeBlock: <CodeBlockIcon />,
  alignCenter: <AlignCenterIcon />,
  table: <TableIcon />,
  tableAddRow: <RowAddIcon />,
  tableAddColumn: <ColumnAddIcon />,
  tableDelete: <TableDeleteIcon />,
  link: <LinkIcon />,
  undo: <UndoIcon />,
  redo: <RedoIcon />,
}

/**
 * Панель форматирования.
 *
 * Сохранение и его статус живут теперь в верхней полосе (`ManualEditorTopbar`): на фрейме
 * состояние документа стоит рядом с его названием, а панель — только про текст. Раньше обе
 * роли делили одну строку, и «Сохранить» соседствовала с «Удалить таблицу».
 */
export function ManualEditorToolbar({ editor }: ManualEditorToolbarProps) {
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
    <div className={styles['edf-toolbar']}>
      <div className={styles['edf-toolbar-group']}>
        {TOOLBAR_ACTIONS.map((action) => {
          const button = (
            <button
              type="button"
              className={styles['edf-tool']}
              aria-label={action.ariaLabel}
              data-testid={action.testId}
              onClick={() => handleClick(action)}
              aria-pressed={editor ? action.isActive(editor) : false}
              aria-expanded={action.ui ? openUiKey === action.key : undefined}
              disabled={editor ? (action.disabled?.(editor) ?? false) : true}
            >
              {ICON_BY_KEY[action.key] ?? action.label}
            </button>
          )
          return (
            <Fragment key={action.key}>
              {TOOLBAR_DIVIDER_BEFORE.has(action.key) && (
                <div className={styles['edf-divider']} aria-hidden="true" />
              )}
              {action.ui ? (
                <span className={linkPopoverStyles['me-link-popover-anchor']}>
                  {button}
                  {editor && action.ui === 'link-popover' && openUiKey === action.key && (
                    <LinkPopover editor={editor} onClose={() => setOpenUiKey(null)} />
                  )}
                </span>
              ) : (
                button
              )}
            </Fragment>
          )
        })}
      </div>
    </div>
  )
}
