"""Drives a brand-new account over its daily AI-edit quota, over HTTP, for UI scenario 0.2.

**THE CONTRACT GAP THIS FILE AND ITS TEST SPECIFY.** The scenario's Given is a state no
endpoint reports: `endpoints.md`'s seven endpoints return no quota fields, and
`documents_ai_edits_create.yaml` carries `resets_at` in exactly one place — the `429` body of
`POST /ai-edits`, i.e. only in answer to an edit already sent. So "they open a document -> the
chat input is disabled" has, today, no data source at all. Written to the spec's Gherkin anyway,
on the 0.1 precedent. **What green owes: a quota-state read the editor route can issue on
open**, carrying the exhausted flag and the same `resets_at` instant. Its shape is green's call;
skipping it is not, and the alternative Gherkin (disable only *after* a 429) is a different
scenario this one deliberately does not become.

**How the Given is reached.** The only documented mechanism that moves the counter is spending
it, so the setup spends and takes the server's own 429 as proof rather than assuming a count:
the daily number is env-configured (`19_AiChatEditing_Criteria.md`, "Quota, revisions &
history") and no literal for it is declared anywhere in the repo, so no constant here could be
trusted. ONE document serves every probe — the account must own exactly one, or the documents
list this test clicks through would show indistinguishable rows and the click could open the
wrong one. That costs a wait per edit, which makes `MAX_QUOTA_PROBES` a cost ceiling as much as
a safety one: **the acceptance environment must configure the daily quota low**, or
green-selenium pays for a full day of real LLM edits per run.

**Every probe must reach `done`, not merely a terminal state.** Only a completed edit
demonstrably charges the counter — the criteria commit to "refund on infrastructure failure and
on CAS miss" — so an environment failing every edit would refund every charge, sail through all
probes, and be reported as a quota configured too high: a misdiagnosis of the opposite
problem. `error` and `cancelled` therefore fail loudly here.

HTTP lives in `DocumentEditClient`, not here (`tdd-rules.md`, "Acceptance Test Client Layer"):
this file owns only the quota-spending POLICY — how many probes, what proves the counter moved,
what the 429 must carry.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from clients.application.document_edit_client import DocumentEditClient
from clients.application.dto.document.raw_response_dto import RawResponseDto
from statements.frontend.live_auth_session import LiveAuthSession, issue_live_session

DOCUMENT_TYPE = "доклад"
QUOTA_PROBE_INSTRUCTION = "Сократи введение."
FIRST_VERSION = 1

CREATED_STATUS = 201
ACCEPTED_STATUS = 202
OK_STATUS = 200
OVER_QUOTA_STATUS = 429

QUEUED_EDIT_STATUS = "queued"
COMPLETED_EDIT_STATUS = "done"
NON_TERMINAL_EDIT_STATUSES = frozenset({QUEUED_EDIT_STATUS, "streaming"})

# Ceiling on how many edits the setup will spend before declaring the environment
# misconfigured. Also the cost ceiling — see the module docstring.
MAX_QUOTA_PROBES = 25
EDIT_POLL_ATTEMPTS = 60
EDIT_POLL_INTERVAL_SECONDS = 1

# `resets_at` is "start of the next quota day in the server's canonical zone" (QuotaError).
# No literal can pin the instant, but it is fully BOUNDED: strictly future, never more than one
# quota day out. Slack absorbs clock skew between this runner and the server.
QUOTA_DAY_MAX_HOURS = 24
CLOCK_SLACK_SECONDS = 120


@dataclass(frozen=True)
class OverQuotaAccount:
    """A verified account with no quota left, and the single document it owns."""

    access_token: str
    refresh_token: str
    document_id: str
    resets_at: str


def issue_account_over_its_daily_quota() -> OverQuotaAccount:
    session = issue_live_session()
    return asyncio.run(_drive_the_account_over_its_quota(session))


async def _drive_the_account_over_its_quota(session: LiveAuthSession) -> OverQuotaAccount:
    client = DocumentEditClient()
    try:
        document_id = await _create_document(client, session.access_token)
        resets_at = await _spend_the_daily_quota(client, session.access_token, document_id)
    finally:
        await client.close()
    return OverQuotaAccount(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        document_id=document_id,
        resets_at=resets_at,
    )


async def _create_document(client: DocumentEditClient, token: str) -> str:
    response = await client.create_document(
        token, DOCUMENT_TYPE, f"over-quota-setup-{time.time_ns()}"
    )
    _assert_status(response, CREATED_STATUS, "creating the document")
    body = _body_of(response)
    # `version` is asserted, not assumed: every probe submits `base_version=FIRST_VERSION`, and
    # a document created at another version would meet a 409 that charges no quota.
    assert (body["document_type"], body["version"]) == (DOCUMENT_TYPE, FIRST_VERSION), (
        f"over-quota setup: expected the new document to be a "
        f"'{DOCUMENT_TYPE}' at version {FIRST_VERSION}, got {response.text}"
    )
    return str(body["document_id"])


async def _spend_the_daily_quota(
    client: DocumentEditClient, token: str, document_id: str
) -> str:
    """Submit edits until the server refuses one as over quota; return its `resets_at`."""
    for probe in range(MAX_QUOTA_PROBES):
        response = await client.queue_edit(
            token,
            document_id,
            {"message": QUOTA_PROBE_INSTRUCTION, "base_version": FIRST_VERSION},
            f"over-quota-probe-{probe}-{time.time_ns()}",
        )
        if response.status_code == OVER_QUOTA_STATUS:
            return _resets_at_of(response)
        _assert_status(response, ACCEPTED_STATUS, f"probe {probe}, which was not a {OVER_QUOTA_STATUS},")
        body = _body_of(response)
        # Each probe carries a fresh Idempotency-Key, so each is a FIRST submission, whose
        # status the contract server-sets to exactly `queued`; a replay charged nothing.
        assert body["status"] == QUEUED_EDIT_STATUS, (
            f"over-quota setup: probe {probe} was accepted with status "
            f"'{body['status']}', expected a first submission's '{QUEUED_EDIT_STATUS}'"
        )
        await _wait_for_edit_to_complete(client, token, document_id, str(body["edit_id"]))
    raise AssertionError(
        f"over-quota setup: {MAX_QUOTA_PROBES} edits completed without a "
        f"{OVER_QUOTA_STATUS}; configure the daily AI-edit quota below {MAX_QUOTA_PROBES} "
        "in the acceptance environment"
    )


def _resets_at_of(response: RawResponseDto) -> str:
    """Bound the 429's `resets_at` and return it in the server's own wire form — the RAW
    string, not the parsed instant, because the hint's `data-resets-at` must equal byte for
    byte what the API answered."""
    raw = _body_of(response).get("resets_at")
    assert isinstance(raw, str), (
        f"over-quota setup: the {OVER_QUOTA_STATUS} body must carry a string resets_at "
        f"(documents_ai_edits_create.yaml QuotaError), got {response.text}"
    )
    instant = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    assert instant.tzinfo is not None, (
        f"over-quota setup: resets_at must be an offset-aware date-time, got '{raw}'"
    )
    now = datetime.now(timezone.utc)
    latest = now + timedelta(hours=QUOTA_DAY_MAX_HOURS, seconds=CLOCK_SLACK_SECONDS)
    assert now < instant <= latest, (
        f"over-quota setup: resets_at must be the start of the NEXT quota day — after "
        f"'{now.isoformat()}' and no later than '{latest.isoformat()}' — got '{raw}'"
    )
    return raw


async def _wait_for_edit_to_complete(
    client: DocumentEditClient, token: str, document_id: str, edit_id: str
) -> None:
    """Poll the edit until it reaches `done` — terminal-but-failed is not good enough (see the
    module docstring). Polling at all is required because the next probe would otherwise meet
    the 409 that one active edit per document produces, which charges no quota."""
    for _ in range(EDIT_POLL_ATTEMPTS):
        response = await client.get_edit(token, document_id, edit_id)
        _assert_status(response, OK_STATUS, f"reading edit {edit_id}")
        status = _body_of(response)["status"]
        if status not in NON_TERMINAL_EDIT_STATUSES:
            assert status == COMPLETED_EDIT_STATUS, (
                f"over-quota setup: edit {edit_id} terminalized as '{status}', not "
                f"'{COMPLETED_EDIT_STATUS}'. Only a completed edit demonstrably charges the "
                f"quota — a refunded one would loop to {MAX_QUOTA_PROBES}: {response.text}"
            )
            return
        await asyncio.sleep(EDIT_POLL_INTERVAL_SECONDS)
    raise AssertionError(
        f"over-quota setup: edit {edit_id} was still non-terminal after "
        f"{EDIT_POLL_ATTEMPTS * EDIT_POLL_INTERVAL_SECONDS}s"
    )


def _assert_status(response: RawResponseDto, expected: int, what: str) -> None:
    assert response.status_code == expected, (
        f"over-quota setup: {what} expected {expected}, "
        f"got {response.status_code}: {response.text}"
    )


def _body_of(response: RawResponseDto) -> dict:
    assert response.body is not None, (
        f"over-quota setup: expected a JSON object body, got {response.text}"
    )
    return response.body
