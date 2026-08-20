"""The stylesheet an exported document carries with it.

The editor draws its tables with `ManualEditor.css` — a stylesheet that lives in
the frontend bundle and stops at the browser. The stored document is a bare HTML
fragment with no styling of its own, so an export rendered from it gets the
renderer's defaults: HTML's default table has NO borders, and a table without
borders is a grid the reader cannot see. The cells were all present in the PDF;
the lines between them were not.

So the export path has to carry its own copy of the rules that make a table
legible. Deliberately a SEPARATE, much smaller sheet rather than the editor's:
`ManualEditor.css` is written for an editing surface (selection highlights,
placeholder text, resize handles) and none of that belongs in a document someone
prints.

DOCX cannot use this — OOXML has no cascading stylesheet — so `HtmlDocxRenderer`
expresses the same intent through a named table style. The two must be kept in
step by hand; there is no shared source that both a CSS engine and python-docx
could read.
"""

# Kept in step with `frontend/src/features/generation/components/ManualEditor.css`
# (the `.ProseMirror table` block) and with `HtmlDocxRenderer`'s table style: the
# same table should not look like three different tables depending on where it is
# read.
EXPORT_CSS = """
table {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
}

th, td {
    border: 1px solid #444;
    padding: 6px 8px;
    vertical-align: top;
    /* A long unbroken token in a cell would otherwise widen the column past the
       page box, and a table wider than the page is clipped, not scrolled. */
    word-wrap: break-word;
}

th {
    background: #eee;
    font-weight: bold;
    text-align: left;
}
"""
