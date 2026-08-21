"""The two reported values that have to be read before an event can exist.

They were private methods on `RecordAnalyticsEvent` and used no state of it --
which is what made the usecase's own file the wrong place for them. Read here,
the refusals they raise are testable without building a usecase and its four
collaborators.
"""

from uuid import UUID

from analytics.analytics_error_codes import UNKNOWN_EVENT_NAME, UNKNOWN_EVENT_NAME_MESSAGE
from analytics.event_names import BROWSER_ORIGIN_EVENT_NAMES
from shared.exceptions import ValidationException


def accepted_name(event_name: object) -> str:
    """One of the three names a browser legitimately produces, or a refusal.

    The catalogue has twelve and the column's CHECK constraint lists all
    twelve, so a later story can emit the subscription names without a
    migration. The ROUTE accepts three: on a tokenless endpoint, "no client
    is allowed to send the others" is not a rule unless something refuses
    them.
    """
    if event_name not in BROWSER_ORIGIN_EVENT_NAMES:
        raise ValidationException(message=UNKNOWN_EVENT_NAME_MESSAGE, error_code=UNKNOWN_EVENT_NAME)
    return str(event_name)


def identifier(raw: object, error_code: str, message: str) -> UUID:
    """Parse one wire identifier, refusing anything that is not a UUID.

    `isinstance` FIRST: `uuid.UUID(3)` raises `AttributeError`, and
    `uuid.UUID(None)` a `TypeError` -- neither is a `ValueError`, so a
    `except ValueError` alone would let a JSON number out of here as a 500 on
    the one route that has no token in front of it.
    """
    if not isinstance(raw, str):
        raise ValidationException(message=message, error_code=error_code)
    try:
        return UUID(raw)
    except ValueError as error:
        raise ValidationException(message=message, error_code=error_code) from error
