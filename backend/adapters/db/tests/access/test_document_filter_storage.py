"""The filtered history read and the delete, in SQL.

What the in-memory fake cannot say: whether the `ILIKE` pattern is escaped, whether
the date window's ends are inclusive, and whether a DELETE that matched nothing is
distinguishable from one that matched a row.
"""

from uuid import uuid4

from statements.document_filter_storage_statements import DocumentFilterStorageStatements


class TestTextSearch:
    async def test_should_match_a_title_regardless_of_case(
        self, document_filter_storage_statements: DocumentFilterStorageStatements
    ):
        owner = await document_filter_storage_statements.given_an_account()
        wanted = await document_filter_storage_statements.given_a_document(
            owner, title="Квантовые компьютеры"
        )
        await document_filter_storage_statements.given_a_document(owner, title="Фотосинтез")

        await document_filter_storage_statements.list_filtered(owner, q="квантовые")

        document_filter_storage_statements.assert_page_ids(wanted)

    async def test_should_match_the_body_as_well_as_the_title(
        self, document_filter_storage_statements: DocumentFilterStorageStatements
    ):
        owner = await document_filter_storage_statements.given_an_account()
        wanted = await document_filter_storage_statements.given_a_document(
            owner, title="Без названия", content="<p>Про фотосинтез</p>"
        )
        await document_filter_storage_statements.given_a_document(owner, title="Другое")

        await document_filter_storage_statements.list_filtered(owner, q="фотосинтез")

        document_filter_storage_statements.assert_page_ids(wanted)

    async def test_should_treat_a_percent_in_the_query_as_text_rather_than_a_wildcard(
        self, document_filter_storage_statements: DocumentFilterStorageStatements
    ):
        owner = await document_filter_storage_statements.given_an_account()
        wanted = await document_filter_storage_statements.given_a_document(
            owner, title="Рост на 100% за год"
        )
        await document_filter_storage_statements.given_a_document(owner, title="Совсем другое")

        await document_filter_storage_statements.list_filtered(owner, q="100%")

        # Unescaped, `%` is ILIKE's "anything" and this query would return the caller's ENTIRE
        # history. The fake matches with a Python `in`, so it can never catch that.
        document_filter_storage_statements.assert_page_ids(wanted)

    async def test_should_treat_an_underscore_in_the_query_as_text(
        self, document_filter_storage_statements: DocumentFilterStorageStatements
    ):
        owner = await document_filter_storage_statements.given_an_account()
        await document_filter_storage_statements.given_a_document(owner, title="ab")

        await document_filter_storage_statements.list_filtered(owner, q="a_")

        # `_` is ILIKE's single-character wildcard, which would match "ab".
        document_filter_storage_statements.assert_page_is_empty()

    async def test_should_never_reach_past_the_caller(
        self, document_filter_storage_statements: DocumentFilterStorageStatements
    ):
        mine = await document_filter_storage_statements.given_an_account()
        theirs = await document_filter_storage_statements.given_an_account()
        my_row = await document_filter_storage_statements.given_a_document(mine, title="Отчёт")
        await document_filter_storage_statements.given_a_document(theirs, title="Отчёт")

        await document_filter_storage_statements.list_filtered(mine, q="отчёт")

        # The filter is ANDed with the owner predicate in SQL and can never relax it.
        document_filter_storage_statements.assert_page_ids(my_row)


class TestDateWindow:
    async def test_should_include_a_document_created_on_the_closing_day(
        self, document_filter_storage_statements: DocumentFilterStorageStatements
    ):
        owner = await document_filter_storage_statements.given_an_account()
        # BASE_TIME is midday on 2026-08-20.
        document = await document_filter_storage_statements.given_a_document(owner, title="Сегодня")

        await document_filter_storage_statements.list_filtered(
            owner, created_from="2026-08-20", created_to="2026-08-20"
        )

        # The single-day window, which is the one a user filtering by date is most likely to ask
        # for. Read both ends as midnight and it matches nothing.
        document_filter_storage_statements.assert_page_ids(document)

    async def test_should_exclude_documents_outside_the_window(
        self, document_filter_storage_statements: DocumentFilterStorageStatements
    ):
        owner = await document_filter_storage_statements.given_an_account()
        inside = await document_filter_storage_statements.given_a_document(owner, title="Новое")
        await document_filter_storage_statements.given_a_document(
            owner, title="Старое", days_old=10
        )

        await document_filter_storage_statements.list_filtered(owner, created_from="2026-08-19")

        document_filter_storage_statements.assert_page_ids(inside)


class TestDelete:
    async def test_should_remove_the_row_and_report_that_it_did(
        self, document_filter_storage_statements: DocumentFilterStorageStatements
    ):
        owner = await document_filter_storage_statements.given_an_account()
        document = await document_filter_storage_statements.given_a_document(owner)

        await document_filter_storage_statements.delete(document.id, owner)

        assert document_filter_storage_statements.deleted is True
        assert await document_filter_storage_statements.count_for(owner) == 0

    async def test_should_report_that_nothing_was_deleted_for_an_absent_row(
        self, document_filter_storage_statements: DocumentFilterStorageStatements
    ):
        owner = await document_filter_storage_statements.given_an_account()

        await document_filter_storage_statements.delete(uuid4(), owner)

        # The rowcount is the answer, not a preceding read: a read-then-delete would report
        # success for a row a concurrent request had already taken.
        assert document_filter_storage_statements.deleted is False

    async def test_should_leave_another_owners_document_untouched(
        self, document_filter_storage_statements: DocumentFilterStorageStatements
    ):
        mine = await document_filter_storage_statements.given_an_account()
        theirs = await document_filter_storage_statements.given_an_account()
        foreign = await document_filter_storage_statements.given_a_document(theirs)

        await document_filter_storage_statements.delete(foreign.id, mine)

        # Owner-scoped in SQL, so a foreign document falls out as "nothing deleted" — which the
        # usecase turns into the same 404 an absent one gets.
        assert document_filter_storage_statements.deleted is False
        assert await document_filter_storage_statements.count_for(theirs) == 1
