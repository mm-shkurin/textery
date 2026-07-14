import { SelectableCard } from './SelectableCard'
import './Modal.css'

export type GenerationMode = 'auto' | 'manual'

const MODES: Array<{ id: GenerationMode; name: string; desc: string; available: boolean }> = [
  { id: 'manual', name: 'Ручной режим', desc: 'Создайте документ самостоятельно, без ИИ', available: true },
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
            <SelectableCard
              key={mode.id}
              available={mode.available}
              name={mode.name}
              cardClassName="mode-card"
              nameClassName="mode-name"
              testId={`mode-card-${mode.id}`}
              onSelect={() => onSelect(mode.id)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
