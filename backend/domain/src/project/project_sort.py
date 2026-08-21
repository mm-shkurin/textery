from dataclasses import dataclass
from enum import StrEnum

from shared.error_codes import ErrorCode
from shared.exceptions import ValidationException


class SortKey(StrEnum):
    """The five orders the contract allows, and nothing else.

    A `StrEnum` rather than a set of strings so the storage adapter can branch on
    a member instead of re-parsing text: the value never reaches SQL as a
    string, which is what keeps `sort` off the interpolation path entirely.
    """

    CREATED_DESC = "created_desc"
    CREATED_ASC = "created_asc"
    UPDATED_DESC = "updated_desc"
    TITLE_ASC = "title_asc"
    TYPE_ASC = "type_asc"


@dataclass(frozen=True)
class ProjectSort:
    """A validated sort order.

    An unrecognised value is a refusal, never a silent fall back to the default:
    a client that misspells `updated_desc` must not be told that
    `created_desc` is the order it asked for.
    """

    key: SortKey

    @classmethod
    def default(cls) -> "ProjectSort":
        return cls(key=SortKey.CREATED_DESC)

    @classmethod
    def parse(cls, raw: str | None) -> "ProjectSort":
        """The order named by `raw`, or the default when it is absent.

        Absent and empty are not the same: an omitted `sort` means "no preference"
        and gets the default, while `?sort=` is a client that sent the parameter
        and named nothing, which is a malformed request rather than a preference.
        """
        if raw is None:
            return cls.default()
        try:
            return cls(key=SortKey(raw))
        except ValueError:
            raise ValidationException(
                message="sort must be one of: " + ", ".join(k.value for k in SortKey) + ".",
                error_code=ErrorCode.INVALID_SORT,
            ) from None
