import styles from './GenerationPending.module.css'
import { generatingTitle, writingProgressMessage } from '../../../shared/copy/documentTypeCopy'
import type { DocumentType } from '../../../shared/domain/documentTypes'

interface GenerationPendingProps {
  documentType: DocumentType
}

/**
 * Что видит пользователь, пока идёт генерация.
 *
 * По фрейму: пустой экран, по центру диск с искрой, строка состояния и три точки. Всё
 * остальное с экрана уходит — ни формы, ни сводки: делать здесь нечего, а форма, оставленная
 * на месте, приглашала бы править то, что уже отправлено.
 *
 * Строка состояния — `role="status"`: она появляется вместо формы, и без живой области
 * скринридер не сообщил бы, что экран сменился. Точки декоративны.
 */
export function GenerationPending({ documentType }: GenerationPendingProps) {
  return (
    <div className={styles.genpend} data-testid="generation-generating">
      <span className={styles['genpend-disc']} aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="currentColor">
          <path d="M10 2.5 11.9 8.1 17.5 10 11.9 11.9 10 17.5 8.1 11.9 2.5 10 8.1 8.1Z" />
          <path d="M18 14.5 18.9 17.1 21.5 18 18.9 18.9 18 21.5 17.1 18.9 14.5 18 17.1 17.1Z" />
        </svg>
      </span>
      {/* Живая область — ОБЁРТКА, а не сам заголовок: роль вытесняет собственную роль
          элемента, и h2 с role="status" перестаёт быть заголовком, то есть экран лишается
          структуры. <output> вместо div с role: элемент несёт эту роль нативно. */}
      <output>
        <h2 className={styles['genpend-title']}>{generatingTitle(documentType)}</h2>
      </output>
      {/* Две вещи в одной строке, и обе нужны: ЧТО происходит («ИИ пишет доклад») и СКОЛЬКО
          это займёт. Первая половина вынесена в свой span, потому что она склоняется по типу
          документа и её же по равенству читает Selenium (generating_state_locators.py). */}
      <p className={styles['genpend-text']}>
        <span>{writingProgressMessage(documentType)}</span> — обычно 1–2 минуты, страница обновится
        автоматически
      </p>
      <span className={styles['genpend-dots']} aria-hidden="true">
        <span className={styles['genpend-dot']} />
        <span className={styles['genpend-dot']} />
        <span className={styles['genpend-dot']} />
      </span>
    </div>
  )
}
