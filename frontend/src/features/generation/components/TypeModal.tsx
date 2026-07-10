import { SelectableCard } from './SelectableCard'
import { DOCUMENT_TYPES, type DocumentType } from '../documentTypes'
import './Modal.css'

export type { DocumentType }

interface TypeModalProps {
  onSelect: (type: DocumentType) => void
  onClose: () => void
}

export function TypeModal({ onSelect, onClose }: TypeModalProps) {
  return (
    <div className="modal-backdrop">
      <div className="modal" data-testid="type-modal">
        <div className="modal-header">
          <h1>Создание документа</h1>
          <button type="button" className="close-btn" onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </div>
        <p className="modal-subtitle">Выберите тип документа с которым будете работать</p>
        <div className="type-grid">
          {DOCUMENT_TYPES.map((type) => (
            <SelectableCard
              key={type.id}
              available={type.available}
              name={type.name}
              cardClassName="type-card"
              nameClassName="type-name"
              testId={`type-card-${type.id}`}
              onSelect={() => onSelect(type.id)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
