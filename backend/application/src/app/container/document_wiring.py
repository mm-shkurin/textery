from collections.abc import AsyncIterator

from sanitization.nh3_html_sanitizer import Nh3HtmlSanitizer

from access.document.document_storage import SqlAlchemyDocumentStorage
from container.runtime import session_factory
from document.create_document import CreateDocument
from document.get_document import GetDocument
from document.list_documents import ListDocuments
from document.save_document import SaveDocument
from session import SqlAlchemyUnitOfWork
from shared.clock import SystemClock


async def create_create_document() -> AsyncIterator[CreateDocument]:
    session = session_factory()
    try:
        yield CreateDocument(
            document_repository=SqlAlchemyDocumentStorage(session),
            clock=SystemClock(),
            unit_of_work=SqlAlchemyUnitOfWork(session),
        )
    finally:
        await session.close()


async def create_get_document() -> AsyncIterator[GetDocument]:
    session = session_factory()
    try:
        yield GetDocument(document_repository=SqlAlchemyDocumentStorage(session))
    finally:
        await session.close()


async def create_list_documents() -> AsyncIterator[ListDocuments]:
    session = session_factory()
    try:
        yield ListDocuments(document_repository=SqlAlchemyDocumentStorage(session))
    finally:
        await session.close()


async def create_save_document() -> AsyncIterator[SaveDocument]:
    session = session_factory()
    try:
        yield SaveDocument(
            document_repository=SqlAlchemyDocumentStorage(session),
            html_sanitizer=Nh3HtmlSanitizer(),
            clock=SystemClock(),
            # One session across the repository and the unit of work, so the
            # usecase's commit is what makes the CAS durable.
            unit_of_work=SqlAlchemyUnitOfWork(session),
        )
    finally:
        await session.close()
