import uuid
from urllib.parse import parse_qs, urlparse

# The backend under acceptance runs with OAUTH_PROVIDER=fake, so the handshake never
# leaves the host. The fake provider reads the identity it should assert straight out
# of the authorization code the test hands to /callback, in this format. The real
# Yandex adapter parses a real provider response instead — the port is what both share.
FAKE_CODE_FORMAT = "sub={subject};email={email}"

PROVIDER = "yandex"
UNCONFIGURED_PROVIDER = "vk"
FRONTEND_CALLBACK_PATH = "/auth/callback"
INVALID_CODE_ERROR = "INVALID_OR_EXPIRED_OAUTH_CODE"


def unique_email() -> str:
    return f"oauth-{uuid.uuid4()}@example.com"


def unique_subject() -> str:
    return f"subject-{uuid.uuid4()}"


def fake_authorization_code(subject: str, email: str) -> str:
    return FAKE_CODE_FORMAT.format(subject=subject, email=email)


def query_param(url: str, name: str) -> str | None:
    values = parse_qs(urlparse(url).query).get(name)
    return values[0] if values else None


def path_of(url: str) -> str:
    return urlparse(url).path
