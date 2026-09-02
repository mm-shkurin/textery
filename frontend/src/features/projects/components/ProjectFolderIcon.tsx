import { useId } from 'react'

interface ProjectFolderIconProps {
  className?: string
}

// The card thumbnail's folder glyph. The path data is copied verbatim from the mockup's
// `<symbol id="folder">` (mockups/desktop/01-projects-grid.html), not drawn by hand — the ban on
// inline SVG exists because generated path data is unreliable, and this is transcribed geometry.
// The project has no icon package installed (see package.json), and adding a dependency is not a
// styling change; `PlaceholderImage` is the existing precedent for a transcribed inline glyph.
//
// Both paths paint with `currentColor`, so a document type is a colour token on the parent and
// never a second copy of the geometry.
export function ProjectFolderIcon({ className }: ProjectFolderIconProps) {
  // Один id на экземпляр. Общий id схлопывается в первый градиент документа, и вся лента
  // красится цветом первой карточки — ровно это и случилось в моке, пока id был константой.
  const gradientId = useId()
  return (
    <svg className={className} viewBox="0 0 52 64" aria-hidden="true">
      {/* Лист залит градиентом того же цвета типа: два стопа `currentColor` с разной
          прозрачностью, поэтому тип остаётся ОДНИМ цветовым токеном, а не своей картинкой. */}
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="currentColor" stopOpacity=".78" />
          <stop offset="1" stopColor="currentColor" stopOpacity="1" />
        </linearGradient>
      </defs>
      <path
        fill={`url(#${gradientId})`}
        d="M4 8a6 6 0 0 1 6-6h20l18 18v36a6 6 0 0 1-6 6H10a6 6 0 0 1-6-6V8z"
      />
      {/* The FOLD is the lighter of the two, not the sheet. The card shipped with the opacities
          the other way round, which drained the glyph to a pale outline with one solid corner —
          in frame 484:1104 the sheet is the type's full colour and the turned corner is a wash
          of it. */}
      <path fill="currentColor" opacity=".55" d="M30 2l18 18H36a6 6 0 0 1-6-6V2z" />
    </svg>
  )
}
