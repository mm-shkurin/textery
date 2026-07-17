from dataclasses import dataclass

from document.document import Document


@dataclass(frozen=True)
class DocumentCreationResult:
    """What CreateDocument returns.

    `is_replay` exists because the router has to choose 201 vs 200 and a bare
    Document cannot express which happened. Mirrors RegistrationResult's shape.
    """

    document: Document
    is_replay: bool
