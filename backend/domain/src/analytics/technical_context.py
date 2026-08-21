"""What the server itself observed about the caller that created an account.

Five values, every one of them derived on the server from the request
(`14_AnalyticsEventTracking.md` §4). None of them is ever accepted from a body or
a query string -- a client that could set its own country or device type could
fabricate the segmentation the business is measured by (`03_Security_Tests.md`
§2.2), and there would be nothing in the data to reveal it.

`country` is the one value this module cannot derive on its own: it comes from a
geolocation port the adapters implement. It is a parameter here rather than a
lookup, so the domain stays free of the dependency and an outage of it is the
caller's problem to swallow rather than this module's to hide.
"""

from dataclasses import dataclass

from analytics.device import device_type_of, operating_system_of
from analytics.language_tag import language_tag_of

FIELD_NAMES = (
    "registration_ip",
    "registration_country",
    "device_type",
    "operating_system",
    "device_language",
)

# `text` columns, but bounded before they are stored: an IPv6 address with a
# zone id is the longest legitimate value by a wide margin, and an unbounded
# caller-controlled string is a write amplification rather than a fact.
MAX_IP_LENGTH = 64


@dataclass(frozen=True)
class TechnicalContext:
    """The server's own observations, ready to be stored on the account."""

    registration_ip: str | None = None
    registration_country: str | None = None
    device_type: str | None = None
    operating_system: str | None = None
    device_language: str | None = None

    @classmethod
    def observed(
        cls,
        client_ip: str | None,
        country: str | None,
        user_agent: str | None,
        accept_language: str | None,
    ) -> "TechnicalContext":
        return cls(
            registration_ip=_bounded_ip(client_ip),
            registration_country=country,
            device_type=device_type_of(user_agent),
            operating_system=operating_system_of(user_agent),
            device_language=language_tag_of(accept_language),
        )

    def as_columns(self) -> dict[str, str | None]:
        return {name: getattr(self, name) for name in FIELD_NAMES}


def _bounded_ip(client_ip: str | None) -> str | None:
    if not client_ip or len(client_ip) > MAX_IP_LENGTH:
        return None
    return client_ip
