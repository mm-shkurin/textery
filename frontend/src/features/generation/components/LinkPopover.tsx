import { useState } from 'react'
import type { Editor } from '@tiptap/react'
import './LinkPopover.css'

export const LINK_INVALID_MESSAGE = 'Не удалось применить ссылку. Проверьте адрес.'

// `defaultProtocol: 'http'` does NOT normalize on the `setLink` path — it
// reaches only `isAllowedUri` and the linkify/autolink path, while `setLink`
// stores `attributes` verbatim (`extension-link/dist/index.js:365-376`). So a
// bare host must be prefixed here or it serializes as `<a href="example.com">`,
// a relative URL against our own origin, and is persisted that way forever.
const HAS_SCHEME = /^[a-zA-Z][a-zA-Z0-9+.-]*:/

const IS_EMAIL = /^[^\s@/]+@[^\s@/]+$/
// The path class is `\S*`, deliberately: a path ends at whitespace and nowhere
// else, and `apply()` trims before calling. Enumerating its characters is what
// breaks — `\w` stays ASCII-only even under `/u` (dropping `Война_и_мир`) and
// excludes `@` (dropping `/@vsauce`). That `\w`-path mutant is what guard 4 of
// `ManualEditor.link.urlShapes.guards.test.tsx` names verbatim and exists to
// kill; guard 1 caught it too, but only incidentally — its own kill target is
// the email-branch candidate. Do not re-enumerate this class: no test forbids
// it (an enumeration passes the whole suite), only this comment does.
//
// Note what this branch cannot do: everything matching HOST_SHAPE is prefixed
// `http://`, so the scheme is `http` by construction, and `isAllowedUri` — the
// one downstream validator — vets the scheme only. This branch is therefore
// unrejectable, and widening it widens what ships unvalidated.
const HOST_SHAPE = /^[\p{L}\p{N}-]+(\.[\p{L}\p{N}-]+)*(:\d+)?([/?#]\S*)?$/u
function normalizeHref(url: string): string {
  if (HOST_SHAPE.test(url)) return `http://${url}`
  if (HAS_SCHEME.test(url)) return url
  if (IS_EMAIL.test(url)) return `mailto:${url}`
  return url
}

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
