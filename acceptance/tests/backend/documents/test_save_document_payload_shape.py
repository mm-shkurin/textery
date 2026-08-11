import pytest


@pytest.mark.backend
class TestSaveDocumentPayloadShape:
    """Scenario 2.1's premise, made executable: the client OMITS `title`, not nulls it.

    Given the acceptance client's save call
    When it is made with no title intent (`title=None`)
    Then the request body carries exactly {"content", "version"} -- no `title` key
    And when it is made with a real title
    Then the request body carries `title` as well
    And when it is made with a blank title (`title=""`)
    Then the request body carries `title` as an empty string, not as a missing key
    And when it is made with a whitespace-only title (`title="   "`)
    Then the request body carries `title` with its spaces intact, unstripped
    And in every case the save is dispatched as an authorized PUT to the document.

    Why this row exists at all. The whole of scenario 2.1 is the ABSENT-key row: the
    content-only autosave must leave the stored title alone, and it must do so through
    the wire shape a real frontend autosave produces -- the key missing, not the key
    sent as null. `SaveDocumentRequestDto.title_update()` distinguishes the two by
    reading `model_fields_set`, so they are genuinely different requests. But the
    absent shape is manufactured entirely by three lines of shared client code
    (`clients/application/application_client.py`, the `if title is not None` around the
    payload), and until this file nothing anywhere asserted the body they produce.
    Three Statements call that method; all three inherited the shape on trust.

    The regression this forecloses is a plausible tidy-up, not a hypothetical. Writing
    the payload as one literal --

        payload = {"content": content, "version": version, "title": title}

    -- reads as a simplification, passes review, and sends `"title": null` for the
    row whose entire identity is that the key is absent. TODAY that mutation changes
    NOTHING observable: `clear()` is unmapped in storage (`document_storage.py`, the
    `carries_a_value()` branch), so preserve and clear are the same value end to end
    and every existing row stays green. The failure surfaces only once
    `adapters-discovery (b)` maps the erasure arm -- at which point the red points at
    the erasure work that just shipped, not at the client that drifted weeks earlier.
    That delay is the cost this row removes.

    NOT skipped, and no class-level marker. All five assertions hold against the client
    as it stands, so a marker would park live mutation-killing guards for a red period
    that buys nothing -- and this scenario has a recorded defect (progress-backend.md,
    "guard the RED markers themselves") of markers outliving their work unit unnoticed.
    Same call `test_wire_shape_key_fence_leg_guard_preemption.py` makes and argues at
    its line 51. The RED evidence is therefore a MEASURED mutation rather than a
    failing run: with the payload rewritten as the literal above, the omission row
    fails on the whole-body equality, with the null shape named in the message, while
    the titled row is untouched and still green -- exactly the asymmetry that makes the
    mutation invisible everywhere else.

    Marked `backend` though it needs no running backend. The subject is a request body,
    caught by a recording transport before it reaches a server, so nothing is dispatched.
    The marker is what makes `pytest acceptance/ -m backend` -- the command this suite is
    actually run with -- collect the row; leaving it unmarked would keep it out of every
    standard run, which is the same silent non-execution a skip marker causes.

    Five methods, not one, and all are load-bearing. The omission assertion alone is
    satisfied by a client that drops `title` unconditionally; the titled assertion is
    what pins the omission as CONDITIONAL. The blank-title assertion pins WHERE that
    condition sits: on `is not None`, not on truthiness. The first two rows both survive
    a tidy-up to `if title:` -- None is still omitted, a Cyrillic title is still sent --
    while `title=""` silently drops from `{"title": ""}` to key-absent. That is the
    empty half of the two blank values scenario 3.2 is parametrised over
    (`["", "   "]`, test_export_document_acceptance.py:142; forwarded to the client at
    `document_blank_title_save_statements.py:74-80`). Under that edit 3.2's empty_title
    request becomes byte-identical to 2.1's and 3.2 stays green while testing 2.1's
    premise instead of its own. One row, not two, is correct for THAT mutation: `"   "`
    is truthy and survives `if title:`, so a whitespace row would be green for a reason
    the guard did not earn.

    The fourth row covers the strip-normalising family, which the first three do not.
    Two mutations, both measured rather than argued. `if title and title.strip()` drops
    `"   "` to key-absent, so 3.2's OTHER parametrization, `whitespace_title`, becomes
    byte-identical to 2.1's request and goes green for 2.1's reason -- same failure
    class as the blank row's, one value over. That one reds the blank row as well
    (`""` is falsy), so it does not by itself justify a fourth row. What does is
    `payload["title"] = title.strip()`: the key stays, the value becomes `""`, and the
    blank row is blind to it because `"".strip()` is `""`. Measured: 1 failed, 4
    passed, and the failure is this row alone. It is also the layering claim --
    stripping decides what a title MEANS, and `model_fields_set` is where that decision
    is read, so a client that strips has answered the DTO's question before the DTO is
    built. Split across separate test methods rather than one so a failure names which
    direction broke -- which is also why the fifth row exists. The request line and the
    Authorization header were asserted inside the shared accessor the four body rows
    call, so a dropped header reddened all four with an auth message and the "which
    title direction broke" split it names above was unreadable. That envelope is now
    one row of its own.
    """

    async def test_a_save_with_no_title_intent_omits_the_title_key(
        self, document_save_payload_statements
    ):
        statements = document_save_payload_statements

        await statements.given_a_save_carrying_no_title_intent()

        statements.assert_the_title_key_was_omitted_entirely()

    async def test_a_save_carrying_a_title_sends_the_title_key(
        self, document_save_payload_statements
    ):
        statements = document_save_payload_statements

        await statements.given_a_save_carrying_an_explicit_title()

        statements.assert_the_title_key_was_sent()

    async def test_a_save_carrying_a_blank_title_sends_the_title_key(
        self, document_save_payload_statements
    ):
        statements = document_save_payload_statements

        await statements.given_a_save_carrying_a_blank_title()

        statements.assert_the_blank_title_key_was_sent()

    async def test_a_save_carrying_a_whitespace_title_sends_the_title_key(
        self, document_save_payload_statements
    ):
        statements = document_save_payload_statements

        await statements.given_a_save_carrying_a_whitespace_title()

        statements.assert_the_whitespace_title_key_was_sent()

    async def test_a_save_is_dispatched_as_an_authorized_put(
        self, document_save_payload_statements
    ):
        statements = document_save_payload_statements

        await statements.given_a_save_carrying_an_explicit_title()

        statements.assert_the_save_was_dispatched_as_an_authorized_put()
