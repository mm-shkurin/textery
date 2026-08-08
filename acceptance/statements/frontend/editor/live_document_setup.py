"""Seeds a real, owner-scoped document for a brand-new account.

Direct sibling of `live_auth_session.py` and written to the same pattern for the same reason:
a browser test's PRECONDITION is not the thing under test, so it is established over HTTP against
the running backend rather than by driving twenty clicks. `live_auth_session` mints the account;
this mints the account's first document, because the two are inseparable — a document belongs to
an owner, and the browser session must be that owner or the history list comes back empty.

Why any of this is needed for scenario 1.1's "a document is opened": the editor has exactly one
reachable entry today. `useFlowNavigation.selectType` puts the create path on `mode='auto'`
(story 18 dropped the mode modal), so the only branch of `DocumentGenerationFlow` that mounts
`ManualEditor` with an existing document is `openDocumentFromHistory` — Мои работы, then a row.
That path needs a document to already exist, and this is what puts one there.

A new account per call, inherited from `live_auth_session`: it keeps the history list a
single-row list, so "click the row" is unambiguous without the test knowing an id.
"""

import uuid
from dataclasses import dataclass

import httpx

# The backend origin and the HTTP timeout are taken from `live_auth_session` rather than
# re-declared: this module seeds a document FOR the account that module mints, over the same
# backend, so a second copy of the port lookup could only ever drift away from the one that
# matters. Same import-don't-copy shape `manual_editor_conflict_reconcile_statements` uses.
from statements.frontend.live_auth_session import (
    _REQUEST_TIMEOUT_SECONDS,
    LiveAuthSession,
    _backend_base_url,
    issue_live_session,
)

# The document the scenario opens. Content is present but deliberately unremarkable: 1.1 asserts
# nothing about layout, only about the state shown BEFORE layout can happen. An empty document
# would be the wrong fixture — scenario 2.3's blank-sheet state is one of the two states this
# scenario must be distinguishable from, and seeding an empty document would make a wrong
# implementation (render the empty state while measuring) harder to catch, not easier.
SEEDED_DOCUMENT_TYPE = "доклад"
SEEDED_DOCUMENT_TITLE = "История ИИ"
SEEDED_DOCUMENT_CONTENT = (
    "Введение\n\nДанный доклад рассматривает развитие искусственного интеллекта.\n\n"
    "Основная часть\n\nМатериал изложен последовательно и снабжён примерами.\n\n"
    "Заключение\n\nСделаны выводы о значимости темы."
)


@dataclass(frozen=True)
class SeededDocument:
    """One saved document and the session of the account that owns it.

    The document's id is deliberately NOT carried here. It is used inside `seed_saved_document`
    to address the save, and nothing downstream can act on it: the editor is reached by clicking a
    history row, not by an id, so a field holding one would be an unused attractive nuisance —
    the next scenario would be tempted to navigate by id and break the UI-only rule.
    """

    session: LiveAuthSession
    title: str


def seed_saved_document() -> SeededDocument:
    """Register a fresh account, create a document for it, and save content into it."""
    session = issue_live_session()
    headers = {"Authorization": f"Bearer {session.access_token}"}
    with httpx.Client(base_url=_backend_base_url(), timeout=_REQUEST_TIMEOUT_SECONDS) as client:
        created = client.post(
            "/api/v1/documents",
            json={"document_type": SEEDED_DOCUMENT_TYPE},
            headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
        )
        assert created.status_code == 201, (
            f"document setup: create expected 201, got {created.status_code}: {created.text}"
        )
        body = created.json()
        document_id, version = body["document_id"], body["version"]

        saved = client.put(
            f"/api/v1/documents/{document_id}",
            json={
                "content": SEEDED_DOCUMENT_CONTENT,
                "version": version,
                "title": SEEDED_DOCUMENT_TITLE,
            },
            headers=headers,
        )
        assert saved.status_code == 200, (
            f"document setup: save expected 200, got {saved.status_code}: {saved.text}"
        )

    return SeededDocument(session=session, title=SEEDED_DOCUMENT_TITLE)
