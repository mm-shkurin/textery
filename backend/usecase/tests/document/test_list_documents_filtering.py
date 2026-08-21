"""«Поиск по истории» and «фильтровать по дате создания», at the usecase boundary."""

from uuid import uuid4

from document.document_filter import DocumentFilter
from document.list_documents import ListDocuments
from statements.document_fakes import seeded, stored_document


def _matching(page, documents):
    return [item.id for item in page.items] == [document.id for document in documents]


class TestListDocumentsFiltering:
    async def test_should_return_the_whole_history_when_no_filter_is_given(self):
        owner_id = uuid4()
        newest = stored_document(owner_id=owner_id, title="Квантовые вычисления")
        older = stored_document(owner_id=owner_id, minutes_old=10, title="Фотосинтез")
        usecase = ListDocuments(document_repository=await seeded(newest, older))

        page = await usecase.execute(owner_id=owner_id)

        assert _matching(page, [newest, older]), "the default call must narrow nothing"

    async def test_should_narrow_to_documents_whose_title_matches(self):
        owner_id = uuid4()
        wanted = stored_document(owner_id=owner_id, title="Квантовые вычисления")
        other = stored_document(owner_id=owner_id, minutes_old=10, title="Фотосинтез")
        usecase = ListDocuments(document_repository=await seeded(wanted, other))

        page = await usecase.execute(
            owner_id=owner_id, document_filter=DocumentFilter.parse(q="квантовые")
        )

        # Lowercase query against a capitalised title: the search box is not a place a user
        # capitalises carefully, and the real adapter matches with ILIKE.
        assert _matching(page, [wanted])

    async def test_should_narrow_to_documents_whose_content_matches(self):
        owner_id = uuid4()
        wanted = stored_document(
            owner_id=owner_id, title="Без названия", content="<p>Про фотосинтез</p>"
        )
        other = stored_document(
            owner_id=owner_id, minutes_old=10, title="Другое", content="<p>Х</p>"
        )
        usecase = ListDocuments(document_repository=await seeded(wanted, other))

        page = await usecase.execute(
            owner_id=owner_id, document_filter=DocumentFilter.parse(q="фотосинтез")
        )

        # The body counts, not only the heading: a user searching their history is usually looking
        # for what a work was ABOUT, and half of these rows have no title at all.
        assert _matching(page, [wanted])

    async def test_should_narrow_to_the_creation_window(self):
        owner_id = uuid4()
        # `stored_document` anchors at 2026-07-17 12:00 UTC and counts minutes backwards.
        recent = stored_document(owner_id=owner_id, minutes_old=0)
        old = stored_document(owner_id=owner_id, minutes_old=60 * 24 * 3)
        usecase = ListDocuments(document_repository=await seeded(recent, old))

        page = await usecase.execute(
            owner_id=owner_id, document_filter=DocumentFilter.parse(created_from="2026-07-17")
        )

        assert _matching(page, [recent])

    async def test_should_include_a_document_created_on_the_windows_closing_day(self):
        owner_id = uuid4()
        document = stored_document(owner_id=owner_id)
        usecase = ListDocuments(document_repository=await seeded(document))

        page = await usecase.execute(
            owner_id=owner_id, document_filter=DocumentFilter.parse(created_to="2026-07-17")
        )

        # The row was written at midday on the closing date. Reading a bare end date as that day's
        # FIRST instant would exclude it — and would make «с 17 по 17 июля» match nothing at all.
        assert _matching(page, [document])

    async def test_should_never_widen_past_the_caller(self):
        owner_id = uuid4()
        mine = stored_document(owner_id=owner_id, title="Отчёт")
        theirs = stored_document(owner_id=uuid4(), title="Отчёт")
        usecase = ListDocuments(document_repository=await seeded(mine, theirs))

        page = await usecase.execute(
            owner_id=owner_id, document_filter=DocumentFilter.parse(q="отчёт")
        )

        # The filter is ANDed with the owner predicate and can never relax it: a search matching
        # someone else's identically-titled document must not surface it.
        assert _matching(page, [mine])

    async def test_should_page_the_filtered_set_rather_than_filter_a_page(self):
        owner_id = uuid4()
        matches = [
            stored_document(owner_id=owner_id, minutes_old=index, title="Отчёт")
            for index in range(3)
        ]
        noise = [
            stored_document(owner_id=owner_id, minutes_old=100 + index, title="Другое")
            for index in range(5)
        ]
        usecase = ListDocuments(document_repository=await seeded(*matches, *noise))

        page = await usecase.execute(
            owner_id=owner_id, limit=2, document_filter=DocumentFilter.parse(q="отчёт")
        )

        # A full page of matches plus a cursor. Filtering AFTER the page was read would return one
        # row here — the noise having eaten the rest of the limit — while still reporting more to
        # come, so «показать ещё» would walk a list that was never really searched.
        assert _matching(page, matches[:2])
        assert page.next_cursor is not None

        second = await usecase.execute(
            owner_id=owner_id,
            limit=2,
            cursor=page.next_cursor,
            document_filter=DocumentFilter.parse(q="отчёт"),
        )

        assert _matching(second, matches[2:])
        assert second.next_cursor is None
