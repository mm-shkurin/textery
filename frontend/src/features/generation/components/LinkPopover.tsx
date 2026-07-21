import { useState } from 'react'
import type { Editor } from '@tiptap/react'
import { normalizeHref } from './normalizeHref'
import './LinkPopover.css'

export const LINK_INVALID_MESSAGE = 'Не удалось применить ссылку. Проверьте адрес.'

interface LinkPopoverProps {
  editor: Editor
  onClose: () => void
}

export function LinkPopover({ editor, onClose }: LinkPopoverProps) {
  const [url, setUrl] = useState('')
  const [error, setError] = useState<string | null>(null)

  const apply = () => {
    const trimmed = url.trim()
    // Whitespace-only trims to empty and is treated as "remove the link"
    // rather than reaching `isAllowedUri`, which strips unicode whitespace and
    // then *rejects* the empty remainder — a rejection message for pressing
    // space (ADR edge-case table).
    if (!trimmed) {
      editor.chain().focus().extendMarkRange('link').unsetLink().run()
      onClose()
      return
    }
    // `extendMarkRange('link')` first, not bare `setLink`: with a collapsed
    // cursor inside an existing link, bare setLink writes a stored mark instead
    // of changing the href (old URL ships, next typed character becomes a
    // second link); with a partial selection it splits the anchor into three.
    const applied = editor
      .chain()
      .focus()
      .extendMarkRange('link')
      .setLink({ href: normalizeHref(trimmed) })
      .run()
    if (!applied) {
      setError(LINK_INVALID_MESSAGE)
      return
    }
    onClose()
  }

  return (
    <div className="me-link-popover" data-testid="link-popover">
      <input
        type="text"
        className="me-link-input"
        data-testid="link-url-input"
        aria-label="Адрес ссылки"
        placeholder="https://example.com"
        value={url}
        onChange={(event) => {
          setUrl(event.target.value)
          setError(null)
        }}
      />
      <div className="me-link-actions">
        <button type="button" className="me-link-apply" data-testid="link-apply" onClick={apply}>
          Применить
        </button>
        <button
          type="button"
          className="me-link-cancel"
          data-testid="link-cancel"
          onClick={onClose}
        >
          Отмена
        </button>
      </div>
      {error && (
        <div className="me-link-error" role="alert">
          {error}
        </div>
      )}
    </div>
  )
}
