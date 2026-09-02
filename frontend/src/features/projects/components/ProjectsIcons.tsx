// The one class this file reaches for: the sort glyph's quiet arrow is a colour, and colours live
// in the stylesheet. Imported rather than passed in — every caller would otherwise have to know it.
import controlStyles from './ProjectsToolbarControls.module.css'

const idleArrowClass = controlStyles['projects-sort-arrow-idle']

// The glyphs «Мои проекты» needs that are not the folder on a card. Same justification as
// `ProjectFolderIcon`: the project has no icon package installed (see package.json), adding a
// dependency is not a styling change, and every shape below is primitive geometry — circles,
// rectangles and straight lines — rather than transcribed path data that could come out wrong.
//
// All of them are `aria-hidden`: each one sits inside a control that carries its own accessible
// name, so announcing the decoration too would name the same button twice.

interface IconProps {
  className?: string
}

// The magnifier inside the search field.
export function SearchIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
      <path d="M16.5 16.5 21 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

// Four tiles — the grid view.
export function GridIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <rect x="3" y="3" width="8" height="8" rx="2" />
      <rect x="13" y="3" width="8" height="8" rx="2" />
      <rect x="3" y="13" width="8" height="8" rx="2" />
      <rect x="13" y="13" width="8" height="8" rx="2" />
    </svg>
  )
}

// Three rows, each a bullet and a line — the list view.
export function ListIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <circle cx="5" cy="6" r="1.6" />
      <circle cx="5" cy="12" r="1.6" />
      <circle cx="5" cy="18" r="1.6" />
      <rect x="9" y="5" width="12" height="2" rx="1" />
      <rect x="9" y="11" width="12" height="2" rx="1" />
      <rect x="9" y="17" width="12" height="2" rx="1" />
    </svg>
  )
}

// The four-point star on «Создать проект» — one big and one small, as in the Figma button.
export function SparkleIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M10 2.5 11.9 8.1 17.5 10 11.9 11.9 10 17.5 8.1 11.9 2.5 10 8.1 8.1Z" />
      <path d="M18 14.5 18.9 17.1 21.5 18 18.9 18.9 18 21.5 17.1 18.9 14.5 18 17.1 17.1Z" />
    </svg>
  )
}

// The funnel on the toolbar's filter button.
export function FilterIcon({ className }: IconProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4.5 6.2h15a1 1 0 0 1 .74 1.67l-5.1 5.6a1.5 1.5 0 0 0-.39 1v3.2a1 1 0 0 1-.55.9l-2.4 1.2a1 1 0 0 1-1.45-.9v-4.4a1.5 1.5 0 0 0-.39-1l-5.1-5.6A1 1 0 0 1 4.5 6.2Z" />
    </svg>
  )
}

// The two arrows on the sort control. The DOWN arrow is drawn in the border colour and the up one
// in the glyph colour: the pair states a direction, and two equal arrows would state nothing.
export function SortIcon({ className }: IconProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path
        className={idleArrowClass}
        stroke="currentColor"
        d="M8 4.5v14m0 0-3.2-3.2M8 18.5l3.2-3.2"
      />
      <path stroke="currentColor" d="M16 19.5v-14m0 0-3.2 3.2M16 5.5l3.2 3.2" />
    </svg>
  )
}

// The card's overflow control. Horizontal, as drawn in `Icons/More 24px horizontal`.
export function MoreIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <circle cx="5" cy="12" r="2" />
      <circle cx="12" cy="12" r="2" />
      <circle cx="19" cy="12" r="2" />
    </svg>
  )
}
