"""Story 19's seven AI-edit routes.

RED stub: the router and its dependency providers exist so the guard tests can wire
overrides against real symbols, but no route handler is declared yet. Every request
therefore falls through to Starlette's own 404, which renders `{"detail": ...}` —
which is precisely what the scenario has to be able to tell apart from a genuine
refusal. The handlers land in green-adapter rest.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/documents", tags=["ai-edits"])

_WIRED_BY_COMPOSITION_ROOT = "wired by the application composition root"


def get_queue_ai_edit_usecase() -> object:
    raise NotImplementedError(_WIRED_BY_COMPOSITION_ROOT)


def get_stream_ai_edit_usecase() -> object:
    raise NotImplementedError(_WIRED_BY_COMPOSITION_ROOT)


def get_get_ai_edit_usecase() -> object:
    raise NotImplementedError(_WIRED_BY_COMPOSITION_ROOT)


def get_cancel_ai_edit_usecase() -> object:
    raise NotImplementedError(_WIRED_BY_COMPOSITION_ROOT)


def get_list_messages_usecase() -> object:
    raise NotImplementedError(_WIRED_BY_COMPOSITION_ROOT)


def get_list_revisions_usecase() -> object:
    raise NotImplementedError(_WIRED_BY_COMPOSITION_ROOT)


def get_restore_revision_usecase() -> object:
    raise NotImplementedError(_WIRED_BY_COMPOSITION_ROOT)
