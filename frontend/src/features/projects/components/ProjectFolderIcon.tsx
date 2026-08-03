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
  return (
    <svg className={className} viewBox="0 0 52 64" aria-hidden="true">
      <path
        fill="currentColor"
        opacity=".35"
        d="M4 8a6 6 0 0 1 6-6h20l18 18v36a6 6 0 0 1-6 6H10a6 6 0 0 1-6-6V8z"
      />
      <path fill="currentColor" d="M30 2l18 18H36a6 6 0 0 1-6-6V2z" />
    </svg>
  )
}
