import { TypeCard } from './TypeCard'
import { DOCUMENT_TYPES, type DocumentType } from '../../../shared/documentTypes'
import './Modal.css'
import './TypeModal.css'

interface TypeModalProps {
  onSelect: (type: DocumentType) => void
  onClose: () => void
}

export function TypeModal({ onSelect, onClose }: TypeModalProps) {
  return (
    <div className="modal-backdrop">
      <div className="modal modal-narrow type-modal-panel" data-testid="type-modal">
        <div className="modal-header">
          {/* «Создание проекта», not «Создание документа»: the screen this opens from is «Мои
              проекты», the thing being created is called a project everywhere else in the flow,
              and two names for one object is how a user starts wondering whether they are two
              objects. */}
          <h1>Создание проекта</h1>
          <button type="button" className="close-btn" onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </div>
        {/* The accent on «тип документа» is the design's, and it is a highlight rather than a
            link — there is nowhere for it to go, so it is a <span> and not an <a> that would
            announce itself as navigation and do nothing when followed. */}
        <p className="modal-subtitle">
          Выберите <span className="modal-subtitle-accent">тип документа</span>, с которым будете
          работать
        </p>
        <div className="type-grid">
          {DOCUMENT_TYPES.map((option) => (
            <TypeCard key={option.id} option={option} onSelect={onSelect} />
          ))}
        </div>
      </div>
    </div>
  )
}
