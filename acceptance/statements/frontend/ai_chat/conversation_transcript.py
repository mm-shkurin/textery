"""What scenario 1.2's setup submits, and what it demands the server hold afterwards.

Split from `conversation_history_session.py` at the 200-line limit, and at a real seam rather
than an arbitrary one: that module SPENDS edits, this one states what those edits must have
recorded. The instructions live here, beside the assertion that reads them back, because the
two are one statement — "these three texts, in this order, are the conversation" — and keeping
them apart is how a seed and its expectation drift.

The shared response helpers live here too, so both halves of the setup prefix their diagnostics
with the same `CONTEXT` and a failure never has to be traced to which half raised it.
"""

from datetime import datetime
from typing import Any

from clients.application.document_edit_client import DocumentEditClient
from clients.application.dto.document.raw_response_dto import RawResponseDto

CONTEXT = "restored-conversation setup"
OK_STATUS = 200

USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"
MESSAGE_FIELDS = ("message_id", "role", "text", "created_at")
MESSAGE_ROLES = ("user", "assistant")

# Three edits, not thirty. Each one is a real model call charged against the daily quota, and
# `over_quota_session.py`'s module docstring requires the acceptance environment to configure
# that quota LOW so scenario 0.2 can exhaust it cheaply. Those two requirements pull in opposite
# directions, and this count is the compromise: high enough that "in order" has more than one
# possible wrong answer, low enough to sit under a deliberately small quota.
#
# The instructions are LONG on purpose. Scenario 1.2's second Then is only a real assertion on a
# conversation TALLER than the panel, and bubble height is free while each extra bubble costs a
# quota unit and a model round trip — so the overflow is bought with the length of each turn
# rather than with the number of turns.
#
# They are also DISTINCT. Three copies of one sentence would render three identical rows, and an
# ordering assertion over identical values passes under any permutation — the one failure this
# scenario exists to catch.
SEED_INSTRUCTIONS = (
    "Перепиши введение так, чтобы оно начиналось с постановки проблемы, затем коротко "
    "называло цель работы и заканчивалось перечислением задач, которые предстоит решить.",
    "Добавь ко введению абзац о практической значимости темы: где результаты применимы, "
    "кому они полезны и какой эффект от них ожидается в реальной работе.",
    "Смягчи формулировки во всём тексте: убери категоричные утверждения, замени их "
    "осторожными оценками и добавь ссылки на то, что вопрос остаётся дискуссионным.",
)


async def read_the_transcript_back(
    client: DocumentEditClient, token: str, document_id: str
) -> tuple[str, ...]:
    """Read `GET /messages` — the same endpoint the editor route reads — and pin its order.

    Every instruction submitted must come back as a `user` message, in submission order. That is
    stronger than a count and weaker than a hard total: nothing in `endpoints.md` promises how
    many rows one edit records, so a total would be inventing a contract, while the instructions
    are texts this setup chose and can therefore demand back verbatim.

    Reading back at all is what lets the browser layer compare rendered rows to the server's own
    texts — the assistant's replies are model-generated and unknowable at seed time — and it
    pins the contract's ordering claim (`documents_messages_list.yaml`: "One page of messages,
    oldest first") at the source, so a Then that finds the rows out of order accuses the VIEW
    rather than leaving the server a live suspect.
    """
    response = await client.list_messages(token, document_id)
    assert_status(response, OK_STATUS, "reading the seeded chat history")
    body = body_of(response)
    items = body.get("items")
    assert isinstance(items, list) and items, (
        f"{CONTEXT}: expected GET /documents/{document_id}/messages — the read the editor "
        f"route itself issues — to return a non-empty items array, got {response.text}"
    )
    _assert_the_page_is_the_whole_conversation(body)
    for row in items:
        _assert_the_message_is_well_formed(row)
    _assert_the_instructions_are_in_submission_order(items)
    _assert_the_page_is_ordered_oldest_first(items)
    _assert_both_sides_of_every_turn_are_recorded(items)
    return tuple(str(row["text"]) for row in items)


def _assert_both_sides_of_every_turn_are_recorded(items: list) -> None:
    """Without this the Given is SELF-FULFILLING on the one fact it exists to establish.

    Everything above anchors only the `user` rows — texts this setup chose. Nothing demanded an
    `assistant` row. If the server records the instruction and drops the reply (an async write
    after `status: done` is exactly that shape, and `wait_for_edit_to_complete` returns when the
    status flips, without reading the reply back), `transcript_texts` becomes the three
    instructions, the browser Then compares the panel against those three, and it PASSES —
    certifying a panel that restores half a conversation, from the scenario whose whole premise
    is that a real one exists. Counted per instruction, not merely non-zero: one reply for three
    edits is the same defect wearing a smaller number.
    """
    replies = [row for row in items if row["role"] == ASSISTANT_ROLE]
    assert len(replies) == len(SEED_INSTRUCTIONS), (
        f"{CONTEXT}: expected one {ASSISTANT_ROLE} message per submitted instruction — this "
        f"scenario's Given is that BOTH sides of each turn are stored — got "
        f"{len(replies)} for {len(SEED_INSTRUCTIONS)} instructions. The edits reached `done`, "
        f"so the edit ran; what is missing is the reply write."
    )


def _assert_the_page_is_the_whole_conversation(body: dict) -> None:
    """One page must hold everything, or `transcript_texts` is a PREFIX of the conversation.

    The browser layer compares the rendered rows to this tuple with `==`. A second page left
    unread would make the expectation short, and that assertion would then fail against a panel
    rendering the history correctly — accusing the view of the setup's own truncation. The seed
    spends three edits and `limit` defaults to 50, so a cursor here means the contract changed.
    """
    cursor = body.get("next_cursor")
    assert cursor is None, (
        f"{CONTEXT}: expected the seeded conversation to fit in ONE page, but the server "
        f"returned next_cursor='{cursor}' — this setup reads a single page, so the transcript "
        f"it hands the browser layer would be only a prefix of the real conversation"
    )


def _assert_the_message_is_well_formed(row: Any) -> None:
    """Every contract field present AND carrying a usable value, not merely a key.

    Presence alone is not enough for what this transcript is used for. `text` in particular is
    handed to the browser layer as the expected row text, so an EMPTY text would put an empty
    string on both sides of that comparison and make one turn of the ordering assertion pass
    without asserting anything. The texts are model-generated and cannot be pinned exactly, so
    non-empty is the strongest available claim — `role`, by contrast, is a closed enum and IS
    pinned exactly.
    """
    missing = [field for field in MESSAGE_FIELDS if field not in row]
    assert not missing, (
        f"{CONTEXT}: a message is missing {missing} (documents_messages_list.yaml "
        f"requires {list(MESSAGE_FIELDS)}), got {row}"
    )
    assert row["role"] in MESSAGE_ROLES, (
        f"{CONTEXT}: role must be one of {list(MESSAGE_ROLES)} "
        f"(documents_messages_list.yaml enum), got '{row['role']}' in {row}"
    )
    for field in ("message_id", "text"):
        value = row[field]
        assert isinstance(value, str) and value.strip(), (
            f"{CONTEXT}: {field} must be a non-empty string — an empty one would render as a "
            f"blank chat row and make the browser layer's ordering assertion vacuous for this "
            f"turn — got {value!r} in {row}"
        )
    _parsed_instant(row)


def _assert_the_page_is_ordered_oldest_first(items: list[Any]) -> None:
    """`created_at` never decreases across the page.

    `_assert_the_instructions_are_in_submission_order` pins order for the USER rows only, by
    comparing them to texts this setup chose. The assistant replies are model-generated and have
    no such anchor, so without this they could come back in any position and the browser layer
    would faithfully expect them there — pinning the view to a server bug. This is what holds the
    contract's "One page of messages, oldest first" for the whole list.
    """
    instants = [_parsed_instant(row) for row in items]
    assert instants == sorted(instants), (
        f"{CONTEXT}: expected the page oldest first (documents_messages_list.yaml fixes the "
        f"order server-side), got created_at in this order: "
        f"{[row['created_at'] for row in items]}"
    )


def _parsed_instant(row: Any) -> datetime:
    raw = row["created_at"]
    assert isinstance(raw, str), (
        f"{CONTEXT}: created_at must be a date-time string, got {raw!r} in {row}"
    )
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise AssertionError(
            f"{CONTEXT}: created_at '{raw}' is not an ISO-8601 date-time "
            f"(documents_messages_list.yaml declares format: date-time): {error}"
        ) from error


def _assert_the_instructions_are_in_submission_order(items: list[Any]) -> None:
    submitted = [row["text"] for row in items if row["role"] == USER_ROLE]
    assert submitted == list(SEED_INSTRUCTIONS), (
        f"{CONTEXT}: expected the {USER_ROLE} messages to be exactly the instructions this "
        f"setup submitted, oldest first (documents_messages_list.yaml fixes the order "
        f"server-side), got {submitted}"
    )


def assert_status(response: RawResponseDto, expected: int, what: str) -> None:
    assert response.status_code == expected, (
        f"{CONTEXT}: {what} expected {expected}, got {response.status_code}: {response.text}"
    )


def body_of(response: RawResponseDto) -> dict:
    assert response.body is not None, (
        f"{CONTEXT}: expected a JSON object body, got {response.text}"
    )
    return response.body
