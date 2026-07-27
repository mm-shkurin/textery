# Story 17 — Carryover

Enduring quirks and decisions promoted from completed scenarios. Read on resume.

## Quirk: Selenium element.text reads whole-node subtree text
**Quirk:** Selenium `element.text` on a `data-testid` node returns the whole subtree's text, so an interactive child nested inside a message node pollutes an exact-text acceptance pin; unit-level `toHaveTextContent` matches substrings and does NOT catch it.
**Where:** ExportControl error banner; `manual_editor_export_error_statements.py` exact-text assertions.
**Implication:** Keep testid nodes that acceptance pins by exact text free of text-bearing children (put siblings in a wrapper); at unit level assert whole-node text with `.toBe(el.textContent?.trim())`, not `toHaveTextContent`.
**From:** scenario 3.2 (export-error)
