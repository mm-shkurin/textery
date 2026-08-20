import { useEffect, useRef } from 'react'
import { documentTypeLabelFromWire } from '../../../shared/copy/documentTypeCopy'
import { listenToDocument } from '../../../shared/lib/browser'
import type { DocumentSummary } from '../api/historyApi'
import './HistoryDeleteModal.css'

interface HistoryDeleteModalProps {
  entry: DocumentSummary
  isDeleting: boolean
  error: string | null
  onCancel: () => void
  onConfirm: () => void
}

/**
 * The confirmation standing between a mis-clicked ✕ and work that cannot be recovered.
 *
 * No typed confirmation, unlike the account-deletion dialog: that one destroys everything the
 * account has and is worth the friction, this one destroys a single document the user is looking
 * at by name. The named title in the sentence is what makes the two distinguishable — a dialog
 * reading only «Удалить работу?» cannot tell the user which of twenty rows they hit.
 */
export function HistoryDeleteModal({
  entry,
  isDeleting,
  error,
  onCancel,
  onConfirm,
}: HistoryDeleteModalProps) {
  const cancelRef = useRef<HTMLButtonElement>(null)

  // Focus lands on «Отмена», not on the destructive button. A dialog that opens with the
  // irreversible action focused turns a stray Enter — the very keypress that may have opened it —
  // into the deletion itself.
  useEffect(() => {
    cancelRef.current?.focus()
  }, [])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      // Ignored mid-request: the DELETE is already in flight and closing would hide its answer.
      if (event.key === 'Escape' && !isDeleting) onCancel()
    }
    return listenToDocument('keydown', onKeyDown)
  }, [isDeleting, onCancel])

  const name = entry.title?.trim() || documentTypeLabelFromWire(entry.documentType)

  return (
    <div className="history-modal-scrim">
      <dialog
        className="history-modal"
        open
        aria-modal="true"
        aria-labelledby="history-delete-title"
        data-testid="history-delete-confirm"
      >
        <h3 className="history-modal-title" id="history-delete-title">
          Удалить работу?
        </h3>
        <p className="history-modal-text">
          «{name}» будет удалена безвозвратно. Восстановить её будет нельзя.
        </p>
        {error !== null && (
          <p className="history-modal-error" role="alert" data-testid="history-delete-error">
            {error}
          </p>
        )}
        <div className="history-modal-actions">
          <button
            type="button"
            ref={cancelRef}
            className="history-modal-cancel"
            data-testid="history-delete-cancel"
            onClick={onCancel}
            aria-disabled={isDeleting}
          >
            Отмена
          </button>
          <button
            type="button"
            className="history-modal-confirm"
            data-testid="history-delete-submit"
            onClick={onConfirm}
            aria-disabled={isDeleting}
          >
            {isDeleting ? 'Удаляем…' : 'Удалить'}
          </button>
        </div>
      </dialog>
    </div>
  )
}
