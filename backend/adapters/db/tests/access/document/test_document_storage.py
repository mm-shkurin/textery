from uuid import uuid4

import pytest

from shared.exceptions import ConflictException


class TestSaveNewAndRead:
    """Scenarios 2.1 / 4.1: a created document round-trips through storage."""

    async def test_should_round_trip_a_saved_document(self, document_storage_statements):
        owner_id = await document_storage_statements.given_an_account()
        document = await document_storage_statements.given_a_saved_document(owner_id)

        fetched = await document_storage_statements.find_by_id_and_owner(document.id, owner_id)

        document_storage_statements.assert_documents_match(fetched, document)


class TestOwnerScoping:
    """Scenario 9.2 / Security 7.1: a foreign document is indistinguishable from a missing one.

    The filter must be in SQL, not a post-read `if`. This test cannot tell the two
    apart on its own -- that is what the query-shape test below is for -- but it
    pins the observable contract either way.
    """

    async def test_should_not_return_a_document_belonging_to_another_owner(
        self, document_storage_statements
    ):
        owner_id = await document_storage_statements.given_an_account()
        other_owner_id = await document_storage_statements.given_an_account()
        document = await document_storage_statements.given_a_saved_document(owner_id)

        fetched = await document_storage_statements.find_by_id_and_owner(
            document.id, other_owner_id
        )

        assert fetched is None, "another owner's document must read as absent, never returned"

    async def test_should_return_none_for_an_unknown_id(self, document_storage_statements):
        owner_id = await document_storage_statements.given_an_account()

        assert await document_storage_statements.find_by_id_and_owner(uuid4(), owner_id) is None


class TestIdempotencyKeyUniqueness:
    """Scenario 3.1: replaying a key must not create a second document.

    The guard is the DB constraint, not a check-then-insert -- so this asserts the
    IntegrityError is mapped, which is what lets the usecase recover the original.
    """

    async def test_should_raise_conflict_when_the_same_owner_reuses_a_key(
        self, document_storage_statements
    ):
        owner_id = await document_storage_statements.given_an_account()
        await document_storage_statements.given_a_saved_document(owner_id, idempotency_key="key-1")

        with pytest.raises(ConflictException):
            await document_storage_statements.given_a_saved_document(
                owner_id, idempotency_key="key-1"
            )

    async def test_should_allow_two_owners_to_use_the_same_key(self, document_storage_statements):
        # Security 7.3: the key is scoped per owner. A global namespace would let one
        # account's key collide with another's -- and the replay path would then hand
        # over someone else's document.
        first_owner = await document_storage_statements.given_an_account()
        second_owner = await document_storage_statements.given_an_account()

        first = await document_storage_statements.given_a_saved_document(first_owner, "shared-key")
        second = await document_storage_statements.given_a_saved_document(
            second_owner, "shared-key"
        )

        assert first.id != second.id, "the same key from two owners must yield two documents"

    async def test_should_find_a_document_by_its_owner_and_key(self, document_storage_statements):
        owner_id = await document_storage_statements.given_an_account()
        document = await document_storage_statements.given_a_saved_document(owner_id, "key-lookup")

        found = await document_storage_statements.find_by_idempotency_key(owner_id, "key-lookup")

        document_storage_statements.assert_documents_match(found, document)


class TestSaveContentCompareAndSwap:
    """Scenarios 6.1 / 6.3: the version is the lost-update guard."""

    async def test_should_write_content_and_advance_the_version_on_a_matching_version(
        self, document_storage_statements
    ):
        owner_id = await document_storage_statements.given_an_account()
        document = await document_storage_statements.given_a_saved_document(owner_id)

        saved = await document_storage_statements.save_content_if_version_matches(
            document.id, owner_id, "<p>текст</p>", expected_version=1
        )

        assert saved is not None, "a matching version must be accepted"
        assert saved.content == "<p>текст</p>"
        assert saved.version == 2, "a successful save advances the version by exactly one"

    async def test_should_refuse_a_stale_version_and_leave_content_untouched(
        self, document_storage_statements
    ):
        owner_id = await document_storage_statements.given_an_account()
        document = await document_storage_statements.given_a_saved_document(owner_id)
        await document_storage_statements.save_content_if_version_matches(
            document.id, owner_id, "<p>first</p>", expected_version=1
        )
        await document_storage_statements.commit()

        refused = await document_storage_statements.save_content_if_version_matches(
            document.id, owner_id, "<p>second</p>", expected_version=1
        )

        assert refused is None, "a stale version must not write"
        current = await document_storage_statements.find_by_id_and_owner(document.id, owner_id)
        assert current.content == "<p>first</p>", "the first save's content must survive"
        assert current.version == 2, "a refused save must not advance the version"

    async def test_should_refuse_a_save_against_another_owners_document(
        self, document_storage_statements
    ):
        # Owner and version are one indivisible predicate: a foreign document must
        # never reach the version comparison, or a correct-version guess would be
        # distinguishable from a wrong one and disclose that the id exists.
        owner_id = await document_storage_statements.given_an_account()
        other_owner_id = await document_storage_statements.given_an_account()
        document = await document_storage_statements.given_a_saved_document(owner_id)

        refused = await document_storage_statements.save_content_if_version_matches(
            document.id, other_owner_id, "<p>hijack</p>", expected_version=1
        )

        assert refused is None, (
            "a foreign document must not be writable even with a correct version"
        )
        current = await document_storage_statements.find_by_id_and_owner(document.id, owner_id)
        assert current.content == "", "the owner's content must be untouched"
