"""Scenario 2.1 at the storage seam: page settings survive the mapper, absence stays absent.

Three guards, one per hazard the design review named
(`decisions/page-settings-read-tristate-decision.md`):

(a) the mapper. `DocumentModel.to_domain` calls `Document.reconstitute` with eleven
    kwargs, and green-usecase gave `reconstitute` a `page_settings: PageSettings |
    None = None`. That default is what makes this guard necessary: a `to_domain`
    that never passes a twelfth argument is a VALID call, every configured document
    reads back unconfigured, and no existing test anywhere fails.

(b) the column. Nullable, no server default, no backfill -- because SQL NULL is the
    only way the column can say "nobody configured this", and a default would spend
    that vocabulary on every legacy row at once.

(c) the two falsy values. A stored `{}` is an empty *configured* object; SQL NULL is
    absence. They must not collapse into each other.

The usecase suite already pins that `GetDocument` resolves nothing. That is the
layer where it is *decided*; this is the layer where it is *stored*, and the two
failure modes have nothing to do with each other.
"""


class TestConfiguredPageSettingsSurviveTheMapper:
    """Guard (a): a nine-key object seeded into the column reaches the domain intact."""

    async def test_should_read_back_every_stored_page_setting(self, document_storage_statements):
        owner_id = await document_storage_statements.given_an_account()
        document = await document_storage_statements.given_a_configured_document(owner_id)
        await document_storage_statements.commit()
        # Without this the identity map hands back the instance the seed left behind
        # and the SELECT re-hydration -- the mapper, the actual subject here -- never
        # runs. Same reason `test_document_storage_title.py` expires before every read.
        document_storage_statements.expire_identity_map()

        fetched = await document_storage_statements.find_by_id_and_owner(document.id, owner_id)

        document_storage_statements.assert_page_settings_round_tripped(fetched, document)


class TestPageSettingsColumnIsNullableWithNoDefault:
    """Guard (b): the column's shape is what carries "never configured", so it is pinned.

    Applying the migration to a table that already holds rows must leave those rows
    SQL NULL. The suite runs against a database already at head, so no row it can
    create predates the migration and the property is not directly observable here.
    Three arms approach it from the two sides where it IS observable.

    The first two are the database's own account of the column: its declared type,
    nullability and default, and a document the write path never mentioned still
    sitting at SQL NULL. Between them they catch the `server_default` reflex --
    `server_default=text("'{}'::jsonb")` shows up in `information_schema` AND turns
    every unmentioned row into a configured-looking empty object.

    They do NOT catch a backfill written as data. `op.execute("UPDATE documents SET
    page_settings = '{}'::jsonb")`, or the standard Alembic two-step of adding the
    column WITH a default and dropping the default afterwards, leaves
    `column_default` NULL and `is_nullable` 'YES' and touches no row either test
    creates -- both arms stay green while every pre-existing document has been
    frozen at today's preset. An earlier version of this docstring claimed those two
    arms covered it; they do not. The third arm reads the migration script, which is
    where a data backfill is visible at all.
    """

    async def test_should_declare_the_column_jsonb_nullable_with_no_server_default(
        self, document_storage_statements
    ):
        shape = await document_storage_statements.page_settings_column_shape()

        document_storage_statements.assert_column_is_jsonb_nullable_with_no_default(shape)

    async def test_should_add_the_column_without_writing_into_existing_rows(
        self, document_storage_statements
    ):
        upgrades = document_storage_statements.page_settings_migration_upgrades()

        document_storage_statements.assert_migration_adds_the_column_without_backfilling(upgrades)

    async def test_should_leave_a_document_the_write_path_never_configured_sql_null(
        self, document_storage_statements
    ):
        owner_id = await document_storage_statements.given_an_account()
        # `save_new` is the pre-story write path: it names every column the document
        # has and says nothing about page settings, exactly as every row written
        # before the migration did.
        document = await document_storage_statements.given_a_saved_document(owner_id)
        await document_storage_statements.commit()

        stored = await document_storage_statements.stored_page_settings_column(document.id)

        document_storage_statements.assert_column_is_sql_null(stored)


class TestStoredEmptyObjectStaysDistinctFromSqlNull:
    """Guard (c): `{}` and SQL NULL must not read back the same.

    Deliberately does NOT decide what `{}` resolves to. `PageSettings` has nine
    required fields and `from_stored` -- the resolver that would give `{}` a
    meaning -- belongs to scenarios 2.3/2.4. So there is no domain value that can
    currently hold `{}`, and a test picking one would be inventing the answer to a
    question the ADR left open; raising is an equally admissible outcome today.

    "Not deciding" is not the same as "not pinning", though, and the first version
    of this guard confused the two. It asserted only that the `{}` outcome DIFFERS
    from the SQL NULL one, which excluded exactly one of the five reachable
    outcomes: a broken owner filter finding no row at all, or any exception raised
    anywhere on the read path, satisfied it just as well as a correct
    implementation. The admissible outcomes are enumerated instead -- still without
    choosing between them, so this stays true whichever way 2.3 goes, but now
    nothing else can buy a pass.
    """

    async def test_should_not_read_an_empty_stored_object_as_never_configured(
        self, document_storage_statements
    ):
        owner_id = await document_storage_statements.given_an_account()
        configured_to_nothing = (
            await document_storage_statements.given_a_document_configured_to_nothing(owner_id)
        )
        never_configured = await document_storage_statements.given_a_saved_document(owner_id)
        await document_storage_statements.commit()
        document_storage_statements.expire_identity_map()

        stored_empty = await document_storage_statements.page_settings_read_outcome(
            configured_to_nothing.id, owner_id
        )
        absent = await document_storage_statements.page_settings_read_outcome(
            never_configured.id, owner_id
        )

        document_storage_statements.assert_empty_object_is_not_read_as_never_configured(
            stored_empty=stored_empty,
            never_configured=absent,
            # The columns are re-read raw so the fixture cannot silently degrade:
            # a seed that wrote NULL would make both arms "absent" and the earlier
            # differ-only assertion would have blamed the mapper for it.
            stored_empty_column=await document_storage_statements.stored_page_settings_column(
                configured_to_nothing.id
            ),
            never_configured_column=await document_storage_statements.stored_page_settings_column(
                never_configured.id
            ),
        )
