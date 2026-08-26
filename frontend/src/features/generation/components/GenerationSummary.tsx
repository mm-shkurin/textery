import styles from './GenerationSummary.module.css'
import { DOCUMENT_TYPE_ACCUSATIVE } from '../../../shared/copy/documentTypeCopy'
import type { DocumentType } from '../../../shared/domain/documentTypes'

interface GenerationSummaryProps {
  documentType: DocumentType
  documentTypeLabel: string
}

/**
 * «Что будет в документе?» — карточка справа от формы.
 *
 * На фрейме её пункты — рыба («Заголовок / Описание»), и подставить туда план документа
 * нельзя: плана до генерации не существует, модель строит структуру сама. Поэтому карточка
 * говорит то, что экран ЗНАЕТ: структуру задаёт выбранный тип, а объём и регистр — поля
 * слева. Обещать конкретные разделы значило бы называть то, чего никто не гарантировал.
 */
export function GenerationSummary({ documentType, documentTypeLabel }: GenerationSummaryProps) {
  return (
    <>
      <div className={styles['genform-side-type']}>
        <span className={styles['genform-side-tile']} aria-hidden="true">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M6 3h8l4 4v14H6z" />
            <path d="M9 12h6M9 16h6M9 8h3" />
          </svg>
        </span>
        <div>
          <div className={styles['genform-side-caption']}>Тип документа</div>
          <div className={styles['genform-side-name']} data-testid="generation-summary-type">
            {documentTypeLabel}
          </div>
        </div>
      </div>

      <h2 className={styles['genform-side-heading']}>Что будет в документе?</h2>
      <ul className={styles['genform-side-list']}>
        <li className={styles['genform-side-item']}>
          <span className={styles['genform-side-dot']} aria-hidden="true" />
          <span>
            <span className={styles['genform-side-item-title']}>Структура по типу</span>
            <span className={styles['genform-side-item-text']}>
              Разделы и порядок изложения — как требует «{documentTypeLabel}»
            </span>
          </span>
        </li>
        <li className={styles['genform-side-item']}>
          <span className={styles['genform-side-dot']} aria-hidden="true" />
          <span>
            <span className={styles['genform-side-item-title']}>Объём и стиль из формы</span>
            <span className={styles['genform-side-item-text']}>
              ИИ напишет {DOCUMENT_TYPE_ACCUSATIVE[documentType]} по теме и параметрам слева
            </span>
          </span>
        </li>
      </ul>

      {/* Не украшение: следующий экран после генерации — редактор, и пользователь должен
          знать это до отправки, иначе результат читается как окончательный. */}
      <p className={styles['genform-side-note']}>
        Сгенерированный документ можно будет отредактировать
      </p>
    </>
  )
}
