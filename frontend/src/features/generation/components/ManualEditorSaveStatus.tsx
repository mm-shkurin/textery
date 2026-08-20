import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'
import styles from './ManualEditorSaveStatus.module.css'

interface ManualEditorSaveStatusProps {
  documentId: string | null
  hasUnsavedChanges: boolean
  // True while an autosave attempt has failed and the capped backoff has another one scheduled.
  // Without it the ~7 seconds the ladder can burn look exactly like the instant before the first
  // attempt was ever sent — the user reads «Черновик…» and has no way to tell a save was tried
  // and refused. Ranked ABOVE hasUnsavedChanges below: both are true in that window, and the
  // strictly more informative one has to win.
  isRetryPending?: boolean
  // True once init has failed. Without it, "Создание документа…" is indistinguishable from a
  // creation that gave up a minute ago and will never finish — a progress message sitting next
  // to a Save button that cannot work, which is the most reassuring possible way to say "broken".
  hasFailedToInitialize?: boolean
}

export function ManualEditorSaveStatus({
  documentId,
  hasUnsavedChanges,
  isRetryPending = false,
  hasFailedToInitialize = false,
}: ManualEditorSaveStatusProps) {
  if (!documentId) {
    if (hasFailedToInitialize) {
      // <output> rather than a span with role="status": it has the role implicitly, and this
      // line replaces "Создание документа…" in place, so it must be announced when it swaps in.
      return (
        <output className={`${styles['me-save-status']} ${styles['me-save-status--failed']}`}>
          Документ не создан
        </output>
      )
    }
    return <span className={styles['me-save-status']}>Создание документа…</span>
  }

  if (isRetryPending) {
    // <output> rather than a span, for the same reason the --failed branch above is one: this line
    // swaps in over «Черновик…» with no focus change and nothing else moving on screen, so a
    // screen-reader user hears that a save failed only if the element announces itself.
    return (
      <output className={`${styles['me-save-status']} ${styles['me-save-status--retrying']}`}>
        Не удалось сохранить, повторяем…
      </output>
    )
  }

  if (hasUnsavedChanges) {
    return (
      <span className={`${styles['me-save-status']} ${styles['me-save-status--dirty']}`}>
        Черновик, ещё не сохранён
      </span>
    )
  }

  return (
    <span className={`${styles['me-save-status']} ${styles['me-save-status--saved']}`}>
      <PlaceholderImage />
      Сохранено
    </span>
  )
}
