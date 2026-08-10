from tests.backend.abstract_backend_test import AbstractBackendTest


class TestContentOnlySaveDoesNotWipeStoredTitle(AbstractBackendTest):
    """Scenario 2.1 guard: a content-only autosave leaves the stored title untouched.

    Given a document whose stored title was set by an earlier save
    When a later autosave submits content and version with NO title key at all
    Then the save is applied (the CAS increments, and the new content is stored)
    And the stored title survives, observed directly on the save response and
    corroborated by the export filename.

    Why this row exists when every leg is already guarded: it is the only test in the
    repo that drives the absent-title path in COMPOSITION. The router row
    (test_save_document_title_router.py:57) drives {"content","version"} against a
    mocked usecase and asserts only the port argument; the storage row
    (test_document_storage_title.py:61) hand-constructs TitleUpdate.preserve(). Nothing
    below the port runs in the first, nothing above it in the second, and
    `SaveDocumentRequestDto.title_update()` -- the single hinge between them -- has no
    honest exercise anywhere else.

    Measured worth. The mutation is TWO-legged, and that it has to be is itself the
    finding: flipping `document_dtos.py:55-56` alone (absent title -> clear() instead of
    preserve()) changes NOTHING observable -- 14 passed, 1 skipped, this row included --
    because `clear()` is currently unmapped in storage. `_update_values` asks only
    `carries_a_value()`, which is False for clear() as well as preserve(), so an erasure
    falls into the omit branch and no-ops (documented at document_storage.py:167-170,
    owned by the routed adapters-discovery (b) step). Today clear() and preserve() are
    behaviourally the same value.

    So the mutation that models the real forecast -- the day the erasure ships -- is both
    legs at once: absent-reads-as-clear in the DTO, plus the `SET title = NULL` arm
    (`if title.erases()`) in storage. Under that pair, run over the whole directory:

        baseline          14 passed, 1 skipped
        both legs mutated  1 FAILED, 13 passed, 1 skipped

    The one failure is this row, and it fails on the save response: expected the stored
    Cyrillic title, got ``'title': None``. Every other row stays green -- the
    blank-title rows, the filename rows and the default-filename row all send the key,
    so none of them can see an absent-key regression.

    Two observation channels, deliberately. The save's own response body is the DIRECT
    one: PUT /documents/{id} returns DocumentResponseDto, which carries `title`
    (document_dtos.py:108, populated at :126) -- verified at runtime, the response body
    carries all nine keys including it. The export Content-Disposition is the
    corroborating one; under the mutation it would also fail (expected the RFC
    5987-encoded title, got ``attachment; filename*=UTF-8''document.pdf``), but the
    direct pin trips first and reports the wiped title without percent-encoding in the
    way.

    An earlier draft of this row claimed the header was the ONLY black-box view of the
    stored title because "DocumentResponseDto carries no title field". That was simply
    wrong, and it was load-bearing -- it is what justified asserting the title only
    through the header. The shape with no title is GetDocumentResponseDto, the separate
    READ shape, which is why the sibling blank-title row's re-read comparison cannot
    see the title and this row's save-response comparison can.
    """

    async def test_content_only_save_does_not_wipe_the_stored_title(
        self, document_content_only_save_statements
    ):
        statements = document_content_only_save_statements

        response = await statements.given_owner_autosaves_content_only_over_a_stored_title()

        statements.assert_content_only_save_preserved_the_title()
        statements.assert_filename_rfc5987_encoded_from_title(response)
