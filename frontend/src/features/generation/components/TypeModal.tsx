import './Modal.css'

export type DocumentType = 'doklad' | 'essay' | 'sochinenie' | 'referat'

const TYPES: Array<{ id: DocumentType; name: string; available: boolean }> = [
  { id: 'doklad', name: 'Доклад', available: true },
  { id: 'essay', name: 'Эссе', available: false },
  { id: 'sochinenie', name: 'Сочинение', available: false },
  { id: 'referat', name: 'Реферат', available: false },
]

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
        <p className="modal-subtitle">Выберите тип работы, который будете создавать</p>
        <div className="type-grid">
          {TYPES.map((type) => (
            <button
              key={type.id}
              type="button"
              className={`type-card${type.available ? '' : ' disabled'}`}
              disabled={!type.available}
              data-testid={`type-card-${type.id}`}
              onClick={() => type.available && onSelect(type.id)}
            >
              {!type.available && <span className="soon-pill">скоро</span>}
              <span className="type-name">{type.name}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
