import type { DocumentType } from '../../../shared/documentTypes'
import type { DocumentTypeOption } from '../../../shared/copy/documentTypeCopy'
import styles from './TypeCard.module.css'

// Which coloured folder tile backs which type, read off the creation modal (788:5094). The
// filenames are colours rather than type names because that is what the source frame is —
// «Cards/Images color folders», a palette of eight tiles, of which the modal spends four. Written
// as a table for the same reason `ProjectCard`'s accents are: it is exhaustive on DocumentType, so
// adding a type without a tile is a compile error here, in the file that has to know.
//
// Эссе is `coral`, not `orange`: the modal's second tile averages rgb(250,191,191) and coral.png
// averages rgb(251,186,187), while orange.png is rgb(254,204,151) — a different hue entirely. The
// orange tile was never in this frame; it waits with the other three unspent colours.
const TILE_BY_TYPE: Record<DocumentType, string> = {
  referat: 'blue',
  essay: 'coral',
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
 *
 * The card is a pale panel holding a coloured tile, then the name and the description BELOW it —
 * not a full-bleed image with a frosted caption across its lower half, which is what this was
 * before the frame was measured. The art is the same either way; the layout is not.
 */
export function TypeCard({ option, onSelect }: TypeCardProps) {
  return (
    <button
      type="button"
      className={`${styles['type-card']} ${styles[`type-card-${TILE_BY_TYPE[option.id]}`]}${
        option.available ? '' : ' ' + styles.disabled
      }`}
      disabled={!option.available}
      data-testid={`type-card-${option.id}`}
      onClick={() => option.available && onSelect(option.id)}
    >
      {!option.available && <span className={styles['soon-pill']}>скоро</span>}
      {/* Decorative and empty on purpose: the art carries no information the two lines below it
          do not already carry, so it is a background rather than an <img> with alt text that
          would announce «синяя папка» to a screen reader before the type's own name. */}
      <span className={styles['type-card-tile']} />
      <span className={styles['type-card-heading']}>
        <span className={styles['type-card-name']}>{option.name}</span>
        {/* Decorative: the button is already named by the two lines beside this arrow, and a
            chevron that announced itself would name the same control twice. */}
        {/* The viewBox is cropped to the stroke's own bounds rather than left at 0 0 24 24: the
            frame's chevron is 5.25x9, and a square box around a 9:16 glyph would have to be 15px
            wide, which «Сочинение» plus a 15px box does not leave room for inside a 121.5px
            card. */}
        <svg
          className={styles['type-card-chevron']}
          viewBox="8 4 9 16"
          fill="none"
          aria-hidden="true"
        >
          <path
            d="m9 5 7 7-7 7"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      <span className={styles['type-card-description']}>{option.description}</span>
    </button>
  )
}
