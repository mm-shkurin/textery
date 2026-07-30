from document.title_update import TitleUpdate


class TestTitlePersistence:
    """Title persistence through storage (Scenarios 3.1 and 3.2).

    Write-here-read-there: the title is persisted through the version-CAS save
    path (`save_content_if_version_matches`) and read back through the export/get
    read path (`find_by_id_and_owner`). Pins the shared additive `documents.title`
    column so the export filename can later be derived from it. 3.1 covers the
    round-trip and preserve-on-omit; 3.2 covers verbatim storage (no mapper strip).
    """

    async def test_should_round_trip_a_saved_title(self, document_storage_statements):
        owner_id = await document_storage_statements.given_an_account()
        document = await document_storage_statements.given_a_saved_document(owner_id)

        await document_storage_statements.save_content_if_version_matches(
            document.id,
            owner_id,
            "<p>текст</p>",
            expected_version=1,
            title=TitleUpdate.of("Привет"),
        )
        await document_storage_statements.commit()
        # Drop the identity map so the find is a genuine SELECT re-hydration, not the
        # cached instance the CAS RETURNING loaded -- otherwise a durability bug reads green.
        document_storage_statements.expire_identity_map()

        fetched = await document_storage_statements.find_by_id_and_owner(document.id, owner_id)
        document_storage_statements.assert_stored_state(
            fetched, document, title="Привет", content="<p>текст</p>", version=2
        )

    async def test_should_preserve_an_existing_title_on_a_content_only_save(
        self, document_storage_statements
    ):
        # The CAS is the editor autosave path: after a title is set, every later
        # content-only save must LEAVE the title intact. The mechanism is that
        # `TitleUpdate.preserve()` carries no title intent, so the column stays OUT of
        # the SET list; an unconditional .values(title=title) would SET title = NULL
        # here and silently wipe the user's title -- data loss. This pins
        # preserve-on-omit.
        owner_id = await document_storage_statements.given_an_account()
        document = await document_storage_statements.given_a_saved_document(owner_id)

        await document_storage_statements.save_content_if_version_matches(
            document.id,
            owner_id,
            "<p>первый</p>",
            expected_version=1,
            title=TitleUpdate.of("Привет"),
        )
        await document_storage_statements.commit()
        # A subsequent content-only save (no title) at the advanced version.
        await document_storage_statements.save_content_if_version_matches(
            document.id,
            owner_id,
            "<p>второй</p>",
            expected_version=2,
            title=TitleUpdate.preserve(),
        )
        await document_storage_statements.commit()
        document_storage_statements.expire_identity_map()

        # Content and version are asserted alongside the title on purpose: an
        # unchanged title is also what a CAS that matched ZERO rows leaves behind,
        # so without version=3 this guard would be satisfiable by doing nothing.
        fetched = await document_storage_statements.find_by_id_and_owner(document.id, owner_id)
        document_storage_statements.assert_stored_state(
            fetched, document, title="Привет", content="<p>второй</p>", version=3
        )

    async def test_should_round_trip_a_padded_title_byte_identically(
        self, document_storage_statements
    ):
        # Scenario 3.2 guard, and the VO-unwrap arm in one. The export filename strips
        # surrounding whitespace, but the STORED title stays verbatim
        # (blank-title-semantics-decision.md: "Stripping here affects the filename only --
        # the stored title is untouched"). Every other title in the suite is unpadded, so a
        # .strip() in DocumentModel.to_domain is the identity function there and invisible;
        # this is the only test that can see it. The padding also pins the adapter's unwrap
        # of `TitleUpdate.value` byte-identically rather than merely non-None, so a mutant
        # that drops the VO's value cannot stay green. That arm used to need its own test
        # because the port also accepted a raw `str` and every test took the str door; now
        # `TitleUpdate` is the only door, so this test IS the VO arm.
        owner_id = await document_storage_statements.given_an_account()
        document = await document_storage_statements.given_a_saved_document(owner_id)

        await document_storage_statements.save_content_if_version_matches(
            document.id,
            owner_id,
            "<p>текст</p>",
            expected_version=1,
            title=TitleUpdate.of(" Отчёт "),
        )
        await document_storage_statements.commit()
        document_storage_statements.expire_identity_map()

        fetched = await document_storage_statements.find_by_id_and_owner(document.id, owner_id)
        document_storage_statements.assert_stored_state(
            fetched, document, title=" Отчёт ", content="<p>текст</p>", version=2
        )
