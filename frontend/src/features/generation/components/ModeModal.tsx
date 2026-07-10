import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'
import './Modal.css'

export type GenerationMode = 'auto' | 'manual'

const MODES: Array<{ id: GenerationMode; name: string; desc: string; available: boolean }> = [
  { id: 'manual', name: 'Ручной режим', desc: 'Создайте документ самостоятельно, без ИИ', available: false },
  { id: 'auto', name: 'Автоматический режим', desc: 'ИИ сгенерирует текст по вашей теме и требованиям', available: true },
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
        <div className="modal-header">
          <button type="button" className="back-btn" onClick={onBack} aria-label={`Назад к типу документа: ${documentTypeLabel}`}>
            ←
          </button>
          <h1>Создание документа</h1>
          <button type="button" className="close-btn" onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </div>
        <p className="modal-subtitle">Выберите тип работы который вы будете использовать</p>
        <div className="mode-grid">
          {MODES.map((mode) => (
            <div key={mode.id} className="card-slot">
              <button
                type="button"
                className={`mode-card${mode.available ? '' : ' disabled'}`}
                disabled={!mode.available}
                data-testid={`mode-card-${mode.id}`}
                onClick={() => mode.available && onSelect(mode.id)}
              >
                {!mode.available && <span className="soon-pill">скоро</span>}
                <PlaceholderImage className="card-icon" />
                <span className="mode-name">{mode.name}</span>
              </button>
              <button
                type="button"
                className="add-btn"
                disabled={!mode.available}
                aria-label={`Выбрать ${mode.name}`}
                onClick={() => mode.available && onSelect(mode.id)}
              >
                +
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
