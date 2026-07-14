## Quirk: flex containers break Selenium text assertions

**Quirk:** `display: flex` on a container whose children are meant to read as one continuous line makes the browser's innerText/Selenium `.text` insert a newline between every flex item, even though visually they render side by side.
**Where:** Was in `ManualEditor.css` (`.me-breadcrumb-chips`, `.me-breadcrumb-chip`); fixed by switching to `inline-block` + `white-space: nowrap` with `vertical-align`/`margin` for icon alignment instead of `gap`.
**Implication:** Any future breadcrumb-style or inline-badge component whose text is asserted via Selenium `.text` must avoid `flex`/`inline-flex` on the text-bearing container — use inline-block/vertical-align instead, or normalize whitespace in the Statements assertion.
**From:** scenario 1.2 (manual-editor-opens)
