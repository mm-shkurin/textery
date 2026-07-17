## green-selenium (2026-07-14)

**Quirk:** `display: flex` on a container whose children are meant to read as one continuous line (here `.me-breadcrumb-chips` wrapping two chips + separator, and each `.me-breadcrumb-chip` wrapping an icon + label) makes the browser's innerText/Selenium `.text` insert a newline between every flex item, even though visually they render side by side.
**Where:** `ManualEditor.css` — `.me-breadcrumb-chips` and `.me-breadcrumb-chip` were `display: flex`/`inline-flex`; changed to `inline-block` + `white-space: nowrap` with `vertical-align`/`margin` for icon alignment instead of `gap`.
**Implication:** Any future breadcrumb-style or inline-badge component whose text is asserted via Selenium `.text` must avoid `flex`/`inline-flex` on the text-bearing container — use inline-block/vertical-align instead, or normalize whitespace in the Statements assertion.
