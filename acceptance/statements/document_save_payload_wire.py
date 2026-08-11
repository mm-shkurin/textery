"""The wire vocabulary the save-payload rows are written in — values and bodies.

Split out of `document_save_payload_statements.py` when the fourth row (a whitespace
title) pushed that file over the 200-line cap, for the same reason
`document_blank_title_save_statements.py` was split out of the export-filename
statements. Nothing here has behaviour: it is the request the rows send and the four
exact bodies they compare against, kept together so the ONE-key-differs invariant
between them stays visible in a single screen.
"""

# Stand-ins, never resolved by anything: no server sees these, and the subject is the
# body's shape, not any identity behind it. Values still differ from each other so a
# mixed-up argument reads as a mismatch rather than as a coincidence.
DOCUMENT_ID_ON_THE_WIRE = "00000000-0000-0000-0000-00000000d0c5"
ACCESS_TOKEN_ON_THE_WIRE = "recorded-access-token"
# The header the token must arrive in. Spelled out rather than left implicit: the token
# above is passed by every `given_*` and, until this constant existed, was asserted by
# nothing -- a save that dropped the Authorization header entirely still satisfied every
# body assertion in this file, and the comment above promising that a mixed-up argument
# "reads as a mismatch" was not true of this one.
EXPECTED_AUTHORIZATION = f"Bearer {ACCESS_TOKEN_ON_THE_WIRE}"
# Cyrillic on purpose, matching the scenario's own title fixture: the recorded body is
# read back from serialized bytes, so a JSON encoding regression is visible here too.
CONTENT_ON_THE_WIRE = "Тело, сохранённое без заголовка"
TITLE_ON_THE_WIRE = "Заголовок, отправленный явно"
VERSION_ON_THE_WIRE = 2
# Scenario 3.2's shape: a title that is PRESENT but blank. Not a third flavour of "no
# title" -- the whole premise of 3.2 is that an empty string is a title the user sent,
# and that the backend is the layer allowed to read it as no-title-intent. The client
# must therefore ship it, unchanged, as a key.
BLANK_TITLE_ON_THE_WIRE = ""
# 3.2's OTHER blank value. Its own premise is literally "blank includes whitespace-only"
# (`test_export_document_acceptance.py:142` parametrises over `["", "   "]`), so this
# string is a title the user sent exactly as much as the empty one is, and the client
# must ship it byte-for-byte. Deliberately NOT stripped or normalised anywhere on the
# client side: deciding that these spaces mean "no title" is the backend's call to make.
WHITESPACE_TITLE_ON_THE_WIRE = "   "

# The request line a save must use. Pinned so the body being asserted is provably the
# save request: the recorder answers every request, so without this the assertions
# would key off dispatch position alone.
SAVE_METHOD = "PUT"
SAVE_PATH = f"/api/v1/documents/{DOCUMENT_ID_ON_THE_WIRE}"
# One `given_*` is one `save_document` call, so one request. Asserted exactly rather
# than "at least one": a client that retried or double-dispatched would otherwise be
# invisible behind a read of the last entry.
DISPATCHES_PER_SAVE = 1

# The exact body of a save that carries NO title intent. A whole-body equality, not a
# `"title" not in body`: membership alone still passes if the client starts dropping
# `content` or mangling `version`, and this is the only row that watches the save
# payload at all.
NO_TITLE_INTENT_BODY = {"content": CONTENT_ON_THE_WIRE, "version": VERSION_ON_THE_WIRE}
# The exact body of a save that carries a title.
TITLED_BODY = {**NO_TITLE_INTENT_BODY, "title": TITLE_ON_THE_WIRE}
# The exact bodies of the two blank-title saves. Spelled as NO_TITLE_INTENT_BODY plus
# the key on purpose: the ONE difference between 2.1's request and either of 3.2's
# requests is that this key exists, and writing them any other way would let the shapes
# drift apart silently.
BLANK_TITLED_BODY = {**NO_TITLE_INTENT_BODY, "title": BLANK_TITLE_ON_THE_WIRE}
WHITESPACE_TITLED_BODY = {
    **NO_TITLE_INTENT_BODY,
    "title": WHITESPACE_TITLE_ON_THE_WIRE,
}
