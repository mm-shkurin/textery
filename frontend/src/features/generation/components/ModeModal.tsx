import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'
import './Modal.css'
import './SelectableCard.css'
import './ModeModal.css'

export type GenerationMode = 'auto' | 'manual'

const MODES: Array<{ id: GenerationMode; name: string; desc: string; available: boolean }> = [
  {
    id: 'manual',
    name: 'Ручной режим',
    desc: 'Создайте документ самостоятельно, без ИИ',
    available: true,
  },
  {
    id: 'auto',
    name: 'Автоматический режим',
    desc: 'ИИ сгенерирует текст по вашей теме и требованиям',
    available: true,
  },
]

interface ModeModalProps {
  documentTypeLabel: string
  onSelect: (mode: GenerationMode) => void
  onBack: () => void
  onClose: () => void
}

export function ModeModal({ documentTypeLabel, onSelect, onBack, onClose }: ModeModalProps) {
  return (
    <div className="modal-backdrop">
      <div className="modal modal-narrow" data-testid="mode-modal">
        <button
          type="button"
          className="back-row"
          onClick={onBack}
          aria-label={`Назад к типу документа: ${documentTypeLabel}`}
        >
          <span aria-hidden="true">←</span>
          Тип документа: {documentTypeLabel}
        </button>
        <div className="modal-header">
          <h1>Как создаём?</h1>
          <button type="button" className="close-btn" onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </div>
        <p className="modal-subtitle">Выберите режим работы с документом</p>
        <div className="mode-grid">
          {MODES.map((mode) => (
            <button
              key={mode.id}
              type="button"
              className={`mode-card${mode.available ? '' : ' disabled'}`}
              disabled={!mode.available}
              data-testid={`mode-card-${mode.id}`}
              onClick={() => mode.available && onSelect(mode.id)}
            >
              <span className="icon-badge">
                <PlaceholderImage className="mode-icon" />
              </span>
              <span className="mode-name">{mode.name}</span>
              <span className="mode-desc">{mode.desc}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
