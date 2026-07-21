import { useEffect, useRef, useState } from 'react'
import type { Editor } from '@tiptap/react'
import { normalizeHref } from './normalizeHref'
import './LinkPopover.css'

export const LINK_INVALID_MESSAGE = 'Не удалось применить ссылку. Проверьте адрес.'

interface LinkPopoverProps {
  editor: Editor
  onClose: () => void
}

export function LinkPopover({ editor, onClose }: LinkPopoverProps) {
  const popoverRef = useRef<HTMLDivElement>(null)
  // The range the caret spanned when the popover opened. Every apply path
  // (button, Enter, click-outside) restores this range before touching the
  // document — a caret that drifts while the popover is open (a click
  // elsewhere, a moved selection) must not steal the target. Captured once via
  // the useState initializer so a rejected retry keeps aiming at the original
  // text rather than re-reading the live (drifted) selection.
  const [capturedRange] = useState(() => {
    const { from, to } = editor.state.selection
    return { from, to }
  })
  // Prefill from the anchor under the caret so opening inside an existing link
  // shows its href and Применить replaces it in place, rather than opening
  // empty and destroying the link on apply.
  const [url, setUrl] = useState<string>(() => editor.getAttributes('link').href ?? '')
  const [error, setError] = useState<string | null>(null)

  const apply = () => {
    const trimmed = url.trim()
    // Whitespace-only trims to empty and is treated as "remove the link"
    // rather than reaching `isAllowedUri`, which strips unicode whitespace and
    // then *rejects* the empty remainder — a rejection message for pressing
    // space (ADR edge-case table).
    if (!trimmed) {
      editor
        .chain()
        .focus()
        .setTextSelection(capturedRange)
        .extendMarkRange('link')
        .unsetLink()
        .run()
      onClose()
      return
    }
    // `extendMarkRange('link')` first, not bare `setLink`: with a collapsed
    // cursor inside an existing link, bare setLink writes a stored mark instead
    // of changing the href (old URL ships, next typed character becomes a
    // second link); with a partial selection it splits the anchor into three.
    // `setTextSelection(capturedRange)` first so the mark lands on the range
    // captured at open, not wherever the caret drifted to.
    const applied = editor
      .chain()
      .focus()
      .setTextSelection(capturedRange)
      .extendMarkRange('link')
      .setLink({ href: normalizeHref(trimmed) })
      .run()
    if (!applied) {
      setError(LINK_INVALID_MESSAGE)
      return
    }
    onClose()
  }

  const cancel = () => {
    // Restore editor focus (the popover <input> blurred the contenteditable);
    // leave the document untouched — an existing link survives.
    editor.chain().focus().run()
    onClose()
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    // IME composition: Enter confirms the candidate, it must not apply.
    if (event.nativeEvent.isComposing || event.keyCode === 229) return
    if (event.key === 'Enter') {
      event.preventDefault()
      apply()
    } else if (event.key === 'Escape') {
      event.preventDefault()
      cancel()
    }
  }

  // Click-outside: apply the captured range and close on success; on a rejected
  // href keep the popover open so the inline alert stays visible (ADR tension 2,
  // leaning (b)). Clicks on the toolbar (the link button is a SIBLING of the
  // popover) or inside the editor content are NOT "outside" — they must not
  // trigger an apply-and-close.
  useEffect(() => {
    const handleMouseDown = (event: MouseEvent) => {
      const popover = popoverRef.current
      if (!popover) return
      const target = event.target as Node
      const toolbar = popover.closest('.me-toolbar')
      const editorDom = editor.view.dom
      if (
        popover.contains(target) ||
        toolbar?.contains(target) ||
        editorDom.contains(target)
      ) {
        return
      }
      apply()
    }
    document.addEventListener('mousedown', handleMouseDown)
    return () => document.removeEventListener('mousedown', handleMouseDown)
    // apply reads current url/capturedRange via closure; re-bind when url changes
    // so click-outside applies the latest typed value.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url])

  return (
    <div className="me-link-popover" data-testid="link-popover" ref={popoverRef}>
      <input
        type="text"
        className="me-link-input"
        data-testid="link-url-input"
        aria-label="Адрес ссылки"
        placeholder="https://example.com"
        value={url}
        onKeyDown={handleKeyDown}
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
