from uuid import UUID

from sqlalchemy import Select, String, cast, func, literal, not_, or_, select, union_all
from sqlalchemy.sql.selectable import Subquery

from model.document.document_model import DocumentModel
from model.generation.generation_model import GenerationModel
from project.project_preview import PREVIEW_SOURCE_MAX_CHARS
from project.project_query import LIKE_ESCAPE, ProjectQuery
from project.project_sort import ProjectSort, SortKey
from project.project_status import DOCUMENT_KIND, GENERATION_KIND

# The columns every arm of the union projects, in order. Named once so the two
# arms cannot drift into projecting the same values in a different order -- a
# UNION matches by position, not by label, so that mistake type-checks and
# silently swaps two columns of the answer.
_COLUMNS = (
    "kind",
    "id",
    "title",
    "preview_source",
    "document_type",
    "status",
    "created_at",
    "updated_at",
)


def _documents_arm(owner_id: UUID) -> Select:
    """Every document the caller owns.

    `content` is read as a bounded prefix, not whole: the bytes a page returns
    must not grow with stored document size, and a 200 000-character body would
    otherwise cross the wire between the database and this process on every list
    request just to be thrown away.
    """
    return select(
        literal(DOCUMENT_KIND).label("kind"),
        DocumentModel.id.label("id"),
        DocumentModel.title.label("title"),
        func.left(DocumentModel.content, PREVIEW_SOURCE_MAX_CHARS).label("preview_source"),
        DocumentModel.document_type.label("document_type"),
        DocumentModel.status.label("status"),
        DocumentModel.created_at.label("created_at"),
        DocumentModel.updated_at.label("updated_at"),
    ).where(DocumentModel.owner_id == owner_id)


def _generations_arm(owner_id: UUID) -> Select:
    """Only the generations no document links to.

    A converted generation is represented by its document, so excluding it here
    is what keeps one piece of work from appearing twice. The predicate is a
    correlated NOT EXISTS over `documents.generation_id` -- the column the
    conversion writes -- rather than an anti-join, so a document belonging to
    another account cannot suppress this owner's row.

    A generation's `title` is its topic: the two tables answer the same question
    with differently-named columns, and `title_asc` must order over one value.
    """
    linked = select(literal(1)).where(DocumentModel.generation_id == GenerationModel.id)
    return select(
        literal(GENERATION_KIND).label("kind"),
        GenerationModel.id.label("id"),
        GenerationModel.topic.label("title"),
        func.left(func.coalesce(GenerationModel.content, ""), PREVIEW_SOURCE_MAX_CHARS).label(
            "preview_source"
        ),
        GenerationModel.document_type.label("document_type"),
        GenerationModel.status.label("status"),
        GenerationModel.created_at.label("created_at"),
        GenerationModel.updated_at.label("updated_at"),
    ).where(GenerationModel.owner_id == owner_id, not_(linked.exists()))


def feed_subquery(owner_id: UUID, query: ProjectQuery) -> Subquery:
    """The merged, owner-scoped, searched feed as one subquery.

    The merge is `UNION ALL` in SQL rather than two queries stitched in Python:
    stitching reads the caller's entire history on every page request, which
    passes every correctness test and collapses on exactly the accounts that
    matter most.

    Search is applied per arm, before the union, so each arm's predicate can name
    the columns that arm actually has -- a document matches on title or body, a
    generation on its topic.
    """
    documents = _documents_arm(owner_id)
    generations = _generations_arm(owner_id)
    if query.is_present:
        pattern = query.like_pattern()
        documents = documents.where(
            or_(
                DocumentModel.title.ilike(pattern, escape=LIKE_ESCAPE),
                DocumentModel.content.ilike(pattern, escape=LIKE_ESCAPE),
            )
        )
        generations = generations.where(GenerationModel.topic.ilike(pattern, escape=LIKE_ESCAPE))
    return union_all(documents, generations).subquery("feed")


def order_by(feed: Subquery, sort: ProjectSort) -> list:
    """The ORDER BY for one sort order, always made total.

    Every order ends with `(kind, id)`. `id` alone is not a tiebreak: document
    and generation ids come from different tables and can collide, and under
    offset paging a non-total order is how a row gets served twice or skipped.

    `sort` reaches here as an enum member, never as text -- there is no path from
    the query string to a column name.
    """
    columns = feed.c
    tiebreak = [columns.kind.asc(), columns.id.asc()]
    if sort.key is SortKey.CREATED_ASC:
        leading = [columns.created_at.asc()]
    elif sort.key is SortKey.UPDATED_DESC:
        leading = [columns.updated_at.desc()]
    elif sort.key is SortKey.TITLE_ASC:
        # NULLS LAST is explicit, not inherited: Postgres puts NULLs first under
        # ASC by default, which would open the feed with every untitled document.
        leading = [columns.title.asc().nullslast()]
    elif sort.key is SortKey.TYPE_ASC:
        leading = [cast(columns.document_type, String).asc()]
    else:
        leading = [columns.created_at.desc()]
    return leading + tiebreak
