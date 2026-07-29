"""The seven story-19 AI-edit routes as vocabulary — no app, no client, no mocks.

Paths are verbatim from `ProductSpecification/stories/19-ai-chat-editing/endpoints.md`
and mirror the acceptance client (`acceptance/clients/application/document_edit_client.py`)
so the two layers cannot drift into probing different URLs while both look green.

The edit and revision identifiers are deliberately well-formed but unrelated to any
real row: per the ADR the document scope must be resolved before the child identifier
is ever looked at, so a probe that used a real child id would let a guard that checks
the child first pass for the wrong reason.
"""

from dataclasses import dataclass, field
from uuid import UUID

DOCUMENTS_PATH = "/api/v1/documents"

PROBE_EDIT_ID = UUID("3f1a5c26-0f0f-4a3b-9a5b-1c2d3e4f5a6b")
PROBE_REVISION_NUMBER = 1
PROBE_INSTRUCTION = "Сократи введение до одного абзаца."
PROBE_BASE_VERSION = 1
IDEMPOTENCY_HEADERS = {"Idempotency-Key": "story-19-scope-guard-probe"}

# The one body all seven routes must answer with. A literal, deliberately not rebuilt
# from `exception_handlers.NOT_FOUND_MESSAGE`: a test that derives its expectation from
# the code it guards moves with that code and stops being an anchor. If the product
# text ever changes, this line must be changed by hand and reviewed.
CANONICAL_REFUSAL_BODY = {
    "error_code": "NOT_FOUND",
    "message": "The requested resource was not found.",
}

# The same answer at the level the scenario actually claims: "byte-identical". Parsing
# to a dict first would let key order and separator whitespace vary while the test still
# passed, so the literal is spelled in bytes, exactly as `JSONResponse` serialises it.
CANONICAL_REFUSAL_BYTES = (
    b'{"error_code":"NOT_FOUND","message":"The requested resource was not found."}'
)

# Exact, not a `startswith` prefix: `application/json-seq` and `application/jsonlines`
# both satisfy a prefix check and both are streaming media types — precisely what the
# stream route must not answer with.
CANONICAL_CONTENT_TYPE = "application/json"

# Stands in for a scope argument the route never passed. A literal rather than `None`,
# so "the route omitted document_id" and "the route passed document_id=None" fail with
# different, readable diffs instead of collapsing into the same one.
MISSING_KWARG = "<not passed by the route>"


@dataclass(frozen=True)
class AiEditRoute:
    name: str
    method: str
    path_suffix: str
    provider_name: str
    json_body: dict | None = None
    headers: dict = field(default_factory=dict)
    # The child identifier this route's usecase must also receive, already typed. Per
    # the ADR the path document id is authoritative and the child lookup carries it, so
    # the child id reaching the usecase is part of *this* scenario, not a later one.
    child_kwargs: dict = field(default_factory=dict)

    def path(self, document_id) -> str:
        return f"{DOCUMENTS_PATH}/{document_id}{self.path_suffix}"

    def expected_scope_kwargs(self, document_id: UUID, owner_id: UUID) -> dict:
        """Every scope argument the usecase must be awaited with, exactly and typed.

        Deliberately the scope arguments only — not `message` / `base_version`. Pinning
        the queue route's request payload here would spec the edit-submission contract,
        which scenario 2.x owns; scenario 1.1 owns who and what is being resolved.
        """
        return {"document_id": document_id, "owner_id": owner_id, **self.child_kwargs}


QUEUE_EDIT = AiEditRoute(
    name="they submit an instruction",
    method="POST",
    path_suffix="/ai-edits",
    provider_name="get_queue_ai_edit_usecase",
    json_body={"message": PROBE_INSTRUCTION, "base_version": PROBE_BASE_VERSION},
    headers=IDEMPOTENCY_HEADERS,
)
STREAM_EDIT = AiEditRoute(
    name="they read the edit's event stream",
    method="GET",
    path_suffix=f"/ai-edits/{PROBE_EDIT_ID}/stream",
    provider_name="get_stream_ai_edit_usecase",
    child_kwargs={"edit_id": PROBE_EDIT_ID},
)
GET_EDIT = AiEditRoute(
    name="the edit state endpoint",
    method="GET",
    path_suffix=f"/ai-edits/{PROBE_EDIT_ID}",
    provider_name="get_get_ai_edit_usecase",
    child_kwargs={"edit_id": PROBE_EDIT_ID},
)
CANCEL_EDIT = AiEditRoute(
    name="they cancel the edit",
    method="POST",
    path_suffix=f"/ai-edits/{PROBE_EDIT_ID}/cancel",
    provider_name="get_cancel_ai_edit_usecase",
    child_kwargs={"edit_id": PROBE_EDIT_ID},
)
LIST_MESSAGES = AiEditRoute(
    name="they read its messages",
    method="GET",
    path_suffix="/messages",
    provider_name="get_list_messages_usecase",
)
LIST_REVISIONS = AiEditRoute(
    name="they read its revisions",
    method="GET",
    path_suffix="/revisions",
    provider_name="get_list_revisions_usecase",
)
RESTORE_REVISION = AiEditRoute(
    name="they restore a revision",
    method="POST",
    path_suffix=f"/revisions/{PROBE_REVISION_NUMBER}/restore",
    provider_name="get_restore_revision_usecase",
    child_kwargs={"revision_number": PROBE_REVISION_NUMBER},
)

ALL_ROUTES = (
    QUEUE_EDIT,
    STREAM_EDIT,
    GET_EDIT,
    CANCEL_EDIT,
    LIST_MESSAGES,
    LIST_REVISIONS,
    RESTORE_REVISION,
)

ROUTE_IDS = tuple(route.provider_name.removeprefix("get_") for route in ALL_ROUTES)

# Every route that carries a request body, and so every route that could declare a
# validated model FastAPI answers 422 from before the guard is ever reached. Probing
# only the queue route would leave the same hole open on the other two.
BODY_VALIDATING_ROUTES = (QUEUE_EDIT, CANCEL_EDIT, RESTORE_REVISION)
BODY_VALIDATING_ROUTE_IDS = tuple(
    route.provider_name.removeprefix("get_") for route in BODY_VALIDATING_ROUTES
)

# One code point over any plausible instruction ceiling. Scenario 2.4 owns the exact
# limit; this only has to be long enough that a route which validated length before
# resolving would answer 400/422 instead of the refusal.
OVER_LONG_INSTRUCTION = "я" * 10_000

# Bodies that would each earn their own non-404 answer if the route validated, or
# compared versions, before resolving the document. Per the ADR every one of them
# must be indistinguishable from the plain refusal.
DISCLOSING_BODIES = {
    "non-integer-base-version": {"message": PROBE_INSTRUCTION, "base_version": "not-an-integer"},
    "blank-instruction": {"message": "   ", "base_version": PROBE_BASE_VERSION},
    "over-long-instruction": {"message": OVER_LONG_INSTRUCTION, "base_version": PROBE_BASE_VERSION},
    "correct-looking-base-version": {"message": PROBE_INSTRUCTION, "base_version": 1},
    "missing-message": {"base_version": PROBE_BASE_VERSION},
}
