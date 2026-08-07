import type { DocumentType, DocumentTypeOption } from '../../../shared/documentTypes'
import './TypeCard.css'

// Which coloured folder tile backs which type, read off the creation modal (788:5094). The
// filenames are colours rather than type names because that is what the source frame is —
// «Cards/Images color folders», a palette of eight tiles, of which the modal spends four. Written
// as a table for the same reason `ProjectCard`'s accents are: it is exhaustive on DocumentType, so
// adding a type without a tile is a compile error here, in the file that has to know.
const TILE_BY_TYPE: Record<DocumentType, string> = {
  referat: 'blue',
  essay: 'orange',
  doklad: 'violet',
  sochinenie: 'teal',
}

interface TypeCardProps {
  option: DocumentTypeOption
  onSelect: (type: DocumentType) => void
}

/**
 * One document type on the creation modal.
 *
 * The whole tile is the button — the Figma card has no separate action control, and the earlier
 * split (a card plus a «+» affordance beside it) gave the user two targets for one choice.
 */
export function TypeCard({ option, onSelect }: TypeCardProps) {
  return (
    <button
      type="button"
      className={`type-card type-card-${TILE_BY_TYPE[option.id]}${
        option.available ? '' : ' disabled'
      }`}
      disabled={!option.available}
      data-testid={`type-card-${option.id}`}
      onClick={() => option.available && onSelect(option.id)}
    >
      {!option.available && <span className="soon-pill">скоро</span>}
      {/* The frosted panel the design puts over the bottom of the tile. It carries every word on
          the card, so the tile above it can stay purely decorative. */}
      <span className="type-card-panel">
        <span className="type-card-heading">
          <span className="type-card-name">{option.name}</span>
          {/* Decorative: the button is already named by the two lines beside this arrow, and a
              chevron that announced itself would name the same control twice. */}
          <svg className="type-card-chevron" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="m9 5 7 7-7 7"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        <span className="type-card-description">{option.description}</span>
      </span>
    </button>
  )
}
