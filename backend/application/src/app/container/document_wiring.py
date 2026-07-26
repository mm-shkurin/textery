from sqlalchemy.ext.asyncio import AsyncSession

from access.document.document_storage import SqlAlchemyDocumentStorage
from container.runtime import request_scoped
from document.create_document import CreateDocument
from document.export_document import ExportDocument
from document.get_document import GetDocument
from document.list_documents import ListDocuments
from document.save_document import SaveDocument
from sanitization.nh3_html_sanitizer import Nh3HtmlSanitizer
from session import SqlAlchemyUnitOfWork
from shared.clock import SystemClock


@request_scoped
def create_create_document(session: AsyncSession) -> CreateDocument:
    return CreateDocument(
        document_repository=SqlAlchemyDocumentStorage(session),
        clock=SystemClock(),
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )


@request_scoped
def create_get_document(session: AsyncSession) -> GetDocument:
    return GetDocument(document_repository=SqlAlchemyDocumentStorage(session))


@request_scoped
def create_export_document(session: AsyncSession) -> ExportDocument:
    # Deferred import: WeasyPrintPdfRenderer imports weasyprint at module load,
    # which needs native Pango/cairo libs absent on the dev host. Importing it
    # here rather than at module top keeps this wiring module (and every host
    # test that imports it) loadable without those libs; only a real export
    # request, served in-container, constructs the renderer.
    from rendering.weasyprint_pdf_renderer import WeasyPrintPdfRenderer

    return ExportDocument(
        document_repository=SqlAlchemyDocumentStorage(session),
        document_renderer=WeasyPrintPdfRenderer(),
    )


@request_scoped
def create_list_documents(session: AsyncSession) -> ListDocuments:
    return ListDocuments(document_repository=SqlAlchemyDocumentStorage(session))


@request_scoped
def create_save_document(session: AsyncSession) -> SaveDocument:
    return SaveDocument(
        document_repository=SqlAlchemyDocumentStorage(session),
        html_sanitizer=Nh3HtmlSanitizer(),
        clock=SystemClock(),
        # One session across the repository and the unit of work, so the usecase's
        # commit is what makes the CAS durable.
        unit_of_work=SqlAlchemyUnitOfWork(session),
    )
