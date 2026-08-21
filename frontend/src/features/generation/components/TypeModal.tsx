import { TypeCard } from './TypeCard'
import { type DocumentType } from '../../../shared/domain/documentTypes'
import { DOCUMENT_TYPES } from '../../../shared/copy/documentTypeCopy'
import modalStyles from './Modal.module.css'
import styles from './TypeModal.module.css'

interface TypeModalProps {
  onSelect: (type: DocumentType) => void
  onClose: () => void
}

export function TypeModal({ onSelect, onClose }: TypeModalProps) {
  return (
    <div className={modalStyles['modal-backdrop']}>
      <div
        className={`${modalStyles.modal} ${styles['type-modal-panel']}`}
        data-testid="type-modal"
      >
        <div className={`${modalStyles['modal-header']} ${styles['modal-header']}`}>
          {/* «Создание проекта», not «Создание документа»: the screen this opens from is «Мои
              проекты», the thing being created is called a project everywhere else in the flow,
              and two names for one object is how a user starts wondering whether they are two
              objects. */}
          <h1>Создание проекта</h1>
          <button
            type="button"
            className={`${modalStyles['close-btn']} ${styles['close-btn']}`}
            onClick={onClose}
            aria-label="Закрыть"
          >
            ×
          </button>
        </div>
        {/* The accent on «тип документа» is the design's, and it is a highlight rather than a
            link — there is nowhere for it to go, so it is a <span> and not an <a> that would
            announce itself as navigation and do nothing when followed. */}
        <p className={`${modalStyles['modal-subtitle']} ${styles['modal-subtitle']}`}>
          Выберите <span className={styles['modal-subtitle-accent']}>тип документа</span>, с которым
          будете работать
        </p>
        {/* The frame groups the four cards under «Учебные» — a section label, left-aligned while
            the title and subtitle above it are centred. It is written here rather than derived
            from a `group` field on DocumentType because all four types the product has are
            учебные: a field carrying one constant value would be a data model for a distinction
            nothing yet makes. The day a деловой type is specced, this heading is what has to
            move into the data, and it will be the only thing that does. */}
        <h2 className={styles['type-group-heading']}>Учебные</h2>
        <div className={styles['type-grid']}>
          {DOCUMENT_TYPES.map((option) => (
            <TypeCard key={option.id} option={option} onSelect={onSelect} />
          ))}
        </div>
      </div>
    </div>
  )
}
