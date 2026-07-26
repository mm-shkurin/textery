from enum import Enum

from shared.exceptions import ValidationException

INVALID_FORMAT_MESSAGE = "The format must be pdf or docx."


class ExportFormat(Enum):
    """The target format for a document export.

    Parsing is exact and case-sensitive -- only the lowercase tokens "pdf" and
    "docx" are accepted, mirroring DocumentType: these are fixed protocol values
    the client picks from an enum, not free text. Deliberately no .lower()/.strip()
    normalization, so "PDF" and " pdf " are refused rather than silently widened.
    A violation surfaces as this project's {error_code, message} shape via
    ValidationException, matching PageRequest's INVALID_LIMIT pattern.
    """

    PDF = "pdf"
    DOCX = "docx"

    @classmethod
    def parse(cls, value: str | None) -> "ExportFormat":
        if not isinstance(value, str):
            raise ValidationException(
                error_code="INVALID_FORMAT", message=INVALID_FORMAT_MESSAGE
            )
        try:
            return cls(value)
        except ValueError as error:
            raise ValidationException(
                error_code="INVALID_FORMAT", message=INVALID_FORMAT_MESSAGE
            ) from error
