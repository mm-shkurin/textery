import type { ReactNode } from 'react'
import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'
import './SelectableCard.css'

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
      <span className={`add-btn${available ? '' : ' disabled'}`} aria-hidden="true">
        +
      </span>
    </div>
  )
}
