from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RevisionScope:
    """A bounded projection of a document revision, for callers that only need to
    know it exists and belongs to the document in the path.

    Deliberately not the revision row: no `content` (up to 200 000 units), no
    `source`, no `version`. The guard reads none of them, and the §7.x restore
    usecase loads the content it needs after the guard has answered -- a field no
    statement reads is a field that can only leak.

    It does carry the row `id` as well as the number. `revision_number` is
    per-document, so a content loader keyed on the number alone is globally
    ambiguous: it would copy another document's revision text into the caller's
    document, a cross-tenant leak that is also a write. The content port is
    `id`-keyed, and this is where that id comes from.

    Lives in its own module so `DocumentRevisionRepository` can name it in the
    signature of the bounded finder without importing the guard that consumes it.
    See 19-ai-chat-editing/decisions/revision-scope-guard-decision.md.
    """

    id: UUID
    revision_number: int
    document_id: UUID
