"""Polling an AI edit to `done`, shared by every UI setup that must spend a real edit.

Extracted when scenario 1.2 needed the identical poll scenario 0.2 already had. Copying it
would have left two files that must stay in agreement about which statuses are non-terminal,
how long to wait, and — the load-bearing one — that `done` is the ONLY acceptable terminal
state. A setup that accepted `error` or `cancelled` would look like it had seeded something.

Only the MECHANICS live here. The two diagnostic strings each caller passes carry the policy:
`context` names the setup, `consequence` says what a non-`done` terminal state would have
done to that scenario. Both are diagnostics — nothing here asserts differently on their
value — which is why they are strings rather than the behavior-switching flag `/test-review`
rejected on this story once already.
"""

import asyncio

from clients.application.document_edit_client import DocumentEditClient

OK_STATUS = 200

COMPLETED_EDIT_STATUS = "done"
NON_TERMINAL_EDIT_STATUSES = frozenset({"queued", "streaming"})

EDIT_POLL_ATTEMPTS = 60
EDIT_POLL_INTERVAL_SECONDS = 1


async def wait_for_edit_to_complete(
    client: DocumentEditClient,
    token: str,
    document_id: str,
    edit_id: str,
    context: str,
    consequence: str,
) -> None:
    """Poll the edit until it reaches `done` — terminal-but-failed is not good enough.

    Polling at all is required because a second submission on the same document would
    otherwise meet the 409 that one-active-edit-per-document produces.
    """
    for _ in range(EDIT_POLL_ATTEMPTS):
        response = await client.get_edit(token, document_id, edit_id)
        assert response.status_code == OK_STATUS, (
            f"{context}: reading edit {edit_id} expected {OK_STATUS}, "
            f"got {response.status_code}: {response.text}"
        )
        assert response.body is not None, (
            f"{context}: expected a JSON object body reading edit {edit_id}, "
            f"got {response.text}"
        )
        status = response.body["status"]
        if status not in NON_TERMINAL_EDIT_STATUSES:
            assert status == COMPLETED_EDIT_STATUS, (
                f"{context}: edit {edit_id} terminalized as '{status}', not "
                f"'{COMPLETED_EDIT_STATUS}'. {consequence}: {response.text}"
            )
            return
        await asyncio.sleep(EDIT_POLL_INTERVAL_SECONDS)
    raise AssertionError(
        f"{context}: edit {edit_id} was still non-terminal after "
        f"{EDIT_POLL_ATTEMPTS * EDIT_POLL_INTERVAL_SECONDS}s"
    )
