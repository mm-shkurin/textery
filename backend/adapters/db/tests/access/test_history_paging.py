from uuid import UUID

from statements.history_paging_statements import BASE_TIME, HistoryPagingStatements


class TestOwnerScoping:
    """History is a caller-facing read: another account's rows are not merely
    hidden in the response, they never leave the database."""

    async def test_should_never_return_another_owners_generations(
        self, history_paging_statements: HistoryPagingStatements
    ):
        mine = await history_paging_statements.given_an_account()
        theirs = await history_paging_statements.given_an_account()
        my_generation = await history_paging_statements.given_a_generation(mine)
        await history_paging_statements.given_a_generation(theirs)

        await history_paging_statements.list_generations(mine, limit=20)

        history_paging_statements.assert_page_ids(my_generation)

    async def test_should_never_return_another_owners_documents(
        self, history_paging_statements: HistoryPagingStatements
    ):
        mine = await history_paging_statements.given_an_account()
        theirs = await history_paging_statements.given_an_account()
        my_document = await history_paging_statements.given_a_document(mine)
        await history_paging_statements.given_a_document(theirs)

        await history_paging_statements.list_documents(mine, limit=20)

        history_paging_statements.assert_page_ids(my_document)

    async def test_should_return_an_empty_page_for_an_owner_with_no_history(
        self, history_paging_statements: HistoryPagingStatements
    ):
        owner = await history_paging_statements.given_an_account()
        other = await history_paging_statements.given_an_account()
        await history_paging_statements.given_a_generation(other)

        await history_paging_statements.list_generations(owner, limit=20)

        history_paging_statements.assert_page_is_empty()


class TestOrdering:
    async def test_should_return_newest_first(
        self, history_paging_statements: HistoryPagingStatements
    ):
        owner = await history_paging_statements.given_an_account()
        newest, middle, oldest = await history_paging_statements.given_generations_seconds_apart(
            owner, count=3
        )

        await history_paging_statements.list_generations(owner, limit=20)

        history_paging_statements.assert_page_ids(newest, middle, oldest)


class TestKeysetPaging:
    async def test_should_resume_exactly_where_the_previous_page_stopped(
        self, history_paging_statements: HistoryPagingStatements
    ):
        owner = await history_paging_statements.given_an_account()
        rows = await history_paging_statements.given_generations_seconds_apart(owner, count=5)

        await history_paging_statements.list_generations(owner, limit=2)
        history_paging_statements.assert_page_ids(rows[0], rows[1])
        cursor = history_paging_statements.cursor_after_last_of_page()

        await history_paging_statements.list_generations(owner, limit=2, cursor=cursor)

        # No overlap with page 1 and no gap: the cursor row itself is excluded by
        # the strict `<`, so rows[1] must not reappear and rows[2] must not be skipped.
        history_paging_statements.assert_page_ids(rows[2], rows[3])

    async def test_should_walk_the_whole_history_without_gaps_or_repeats(
        self, history_paging_statements: HistoryPagingStatements
    ):
        owner = await history_paging_statements.given_an_account()
        rows = await history_paging_statements.given_generations_seconds_apart(owner, count=7)

        seen: list[UUID] = []
        cursor = None
        for _ in range(4):
            await history_paging_statements.list_generations(owner, limit=3, cursor=cursor)
            if not history_paging_statements.page:
                break
            seen.extend(row.id for row in history_paging_statements.page)
            cursor = history_paging_statements.cursor_after_last_of_page()

        assert seen == [row.id for row in rows], (
            f"paging must reproduce the full history exactly once, in order; got {seen}"
        )

    async def test_should_break_a_same_timestamp_tie_by_id(
        self, history_paging_statements: HistoryPagingStatements
    ):
        # The reason `id` is in the key at all. Two rows sharing created_at to the
        # microsecond make the anchor ambiguous: with created_at alone, a page
        # boundary landing between them either serves one twice or never at all.
        owner = await history_paging_statements.given_an_account()
        first = await history_paging_statements.given_a_generation(owner, created_at=BASE_TIME)
        second = await history_paging_statements.given_a_generation(owner, created_at=BASE_TIME)
        newest_first = sorted([first, second], key=lambda row: row.id, reverse=True)

        await history_paging_statements.list_generations(owner, limit=1)
        history_paging_statements.assert_page_ids(newest_first[0])
        cursor = history_paging_statements.cursor_after_last_of_page()

        await history_paging_statements.list_generations(owner, limit=1, cursor=cursor)

        history_paging_statements.assert_page_ids(newest_first[1])

    async def test_should_return_an_empty_page_past_the_end(
        self, history_paging_statements: HistoryPagingStatements
    ):
        owner = await history_paging_statements.given_an_account()
        await history_paging_statements.given_generations_seconds_apart(owner, count=2)

        await history_paging_statements.list_generations(owner, limit=2)
        cursor = history_paging_statements.cursor_after_last_of_page()
        await history_paging_statements.list_generations(owner, limit=2, cursor=cursor)

        history_paging_statements.assert_page_is_empty()

    async def test_should_not_let_a_cursor_cross_owners(
        self, history_paging_statements: HistoryPagingStatements
    ):
        # A cursor is forgeable by design. Presenting one built from someone else's
        # row must not widen the window: the owner predicate is a separate AND and
        # is never read from the cursor.
        mine = await history_paging_statements.given_an_account()
        theirs = await history_paging_statements.given_an_account()
        await history_paging_statements.given_a_generation(theirs, created_at=BASE_TIME)
        await history_paging_statements.list_generations(theirs, limit=1)
        their_cursor = history_paging_statements.cursor_after_last_of_page()

        await history_paging_statements.list_generations(mine, limit=20, cursor=their_cursor)

        history_paging_statements.assert_page_is_empty()

    async def test_should_page_documents_the_same_way(
        self, history_paging_statements: HistoryPagingStatements
    ):
        owner = await history_paging_statements.given_an_account()
        older = await history_paging_statements.given_a_document(owner, created_at=BASE_TIME)
        newer = await history_paging_statements.given_a_document(
            owner, created_at=BASE_TIME.replace(hour=13)
        )

        await history_paging_statements.list_documents(owner, limit=1)
        history_paging_statements.assert_page_ids(newer)
        cursor = history_paging_statements.cursor_after_last_of_page()

        await history_paging_statements.list_documents(owner, limit=1, cursor=cursor)

        history_paging_statements.assert_page_ids(older)
