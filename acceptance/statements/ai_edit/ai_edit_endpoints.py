"""The seven AI-edit endpoints, named exactly as the spec's DSL names them.

Vocabulary only — no client, no HTTP, no probe identifiers. A test class may bind
to this module to parametrize over the endpoint family without importing test
infrastructure; `ai_edit_endpoint_probes` imports the same names to dispatch them.

Names are verbatim from the DSL Technical Reference of
ProductSpecification/stories/19-ai-chat-editing/tests/01_API_Tests.md.
"""

SUBMIT_AN_INSTRUCTION = "they submit an instruction"
READ_THE_EVENT_STREAM = "they read the edit's event stream"
THE_EDIT_STATE_ENDPOINT = "the edit state endpoint"
CANCEL_THE_EDIT = "they cancel the edit"
READ_ITS_MESSAGES = "they read its messages"
READ_ITS_REVISIONS = "they read its revisions"
RESTORE_A_REVISION = "they restore a revision"

ALL_ENDPOINTS = (
    SUBMIT_AN_INSTRUCTION,
    READ_THE_EVENT_STREAM,
    THE_EDIT_STATE_ENDPOINT,
    CANCEL_THE_EDIT,
    READ_ITS_MESSAGES,
    READ_ITS_REVISIONS,
    RESTORE_A_REVISION,
)
