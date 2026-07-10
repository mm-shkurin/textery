import type { ReactNode } from 'react'
import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'

interface SelectableCardProps {
  available: boolean
  name: string
  cardClassName: string
  nameClassName: string
  testId: string
  onSelect: () => void
}

export function SelectableCard({
  available,
  name,
  cardClassName,
  nameClassName,
  testId,
  onSelect,
}: SelectableCardProps): ReactNode {
  return (
    <div className="card-slot">
      <button
        type="button"
        className={`${cardClassName}${available ? '' : ' disabled'}`}
        disabled={!available}
        data-testid={testId}
        onClick={() => available && onSelect()}
      >
        {!available && <span className="soon-pill">скоро</span>}
        <PlaceholderImage className="card-icon" />
        <span className={nameClassName}>{name}</span>
      </button>
      <button
        type="button"
        className="add-btn"
        disabled={!available}
        aria-label={`Выбрать ${name}`}
        onClick={() => available && onSelect()}
      >
        +
      </button>
    </div>
  )
}
