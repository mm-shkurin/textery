"""The HTTP response that carries an avatar image, headers included.

Its own module because the headers ARE the contract here, and every one of them
is load-bearing. A route body that set them inline would invite the next endpoint
serving bytes to set three of the four.
"""

from fastapi import Response

from auth.avatar_format import SUPPORTED_MEDIA_TYPES
from auth.avatar_repository import StoredAvatar

# `private` — this image belongs to one account and the body is served from a
# path identical for every caller, so a shared cache must never reuse it.
# `no-cache` — the client MAY store it, but must revalidate before reusing it, so
# a replaced avatar is picked up rather than shown stale until some TTL expires.
CACHE_CONTROL = "private, no-cache"

# The response is exactly the bytes that were uploaded, and the type was proven
# from those bytes rather than taken from the uploader's header. `nosniff` closes
# the remaining gap: without it a browser may ignore the declared type, sniff the
# content, and decide a file we call an image is something it should execute.
NO_SNIFF = "nosniff"

FALLBACK_MEDIA_TYPE = "application/octet-stream"


def avatar_response(avatar: StoredAvatar) -> Response:
    return Response(
        content=avatar.data,
        media_type=_allowlisted(avatar.media_type),
        headers={
            "X-Content-Type-Options": NO_SNIFF,
            "Cache-Control": CACHE_CONTROL,
            **_etag(avatar),
        },
    )


def _allowlisted(media_type: str) -> str:
    """Serve a stored type only if it is still one of the three we accept.

    Belt and braces over the upload-time check, and not redundant: the stored
    value outlives the code that wrote it. A row written by an older build, a
    restored dump, or a hand-edited record would otherwise choose the
    `Content-Type` this origin answers with -- which is the whole mechanism behind
    serving an uploaded file as something executable. Anything unrecognised is
    served as an opaque download instead of being trusted.
    """
    return media_type if media_type in SUPPORTED_MEDIA_TYPES else FALLBACK_MEDIA_TYPE


def _etag(avatar: StoredAvatar) -> dict[str, str]:
    """An ETag derived from the update instant, not from the bytes.

    Hashing the image would mean reading all of it to answer a revalidation; the
    timestamp changes on every upload and every removal, which is exactly when the
    resource changes. Microsecond precision, because two uploads within the same
    second are ordinary for a user retrying.

    Omitted entirely when the instant is missing, rather than emitted as a
    constant: a stable ETag over changing bytes is worse than none at all.
    """
    if avatar.updated_at is None:
        return {}
    return {"ETag": f'"{int(avatar.updated_at.timestamp() * 1_000_000)}"'}
