from auth.avatar_format import detect_media_type, read_dimensions
from shared import limits
from shared.exceptions import ValidationException

# 512 KiB. A 256x256 WebP is a few tens of KB; the headroom is for a client that
# sends PNG instead, not for a different kind of file.
MAX_AVATAR_BYTES = 512 * 1024

# Any side above this is refused. The client resizes to 256x256 before uploading,
# so this is not the product's size rule -- it is the ceiling that keeps a
# decompression bomb (a 100000x100000 PNG whose compressed form is a few KB) from
# being handed to every browser that later renders the image.
MAX_AVATAR_SIDE_PIXELS = limits.MAX_AVATAR_SIDE_PIXELS
# And any side below this is refused too. A header declaring 0x0 passes a ceiling
# check -- `max(0, 0)` is under any maximum -- so without a floor the one file
# that states an impossible size is the one file that gets through. It is not a
# renderable image in any browser, and the whole reason the dimensions are read at
# all is that a size no guard has checked is a size the browser will find its own
# answer for.
MIN_AVATAR_SIDE_PIXELS = 1

AVATAR_TOO_LARGE_CODE = "AVATAR_TOO_LARGE"
AVATAR_TOO_LARGE_MESSAGE = "The image is too large."
AVATAR_UNSUPPORTED_TYPE_CODE = "AVATAR_UNSUPPORTED_TYPE"
AVATAR_UNSUPPORTED_TYPE_MESSAGE = "The image format is not supported."
AVATAR_DIMENSIONS_TOO_LARGE_CODE = "AVATAR_DIMENSIONS_TOO_LARGE"
AVATAR_DIMENSIONS_TOO_LARGE_MESSAGE = "The image dimensions are too large."


class Avatar:
    """Uploaded image bytes, proven acceptable, with the media type they actually are.

    Holds the bytes UNCHANGED. The server does not decode, re-encode, resize or
    strip anything: the client uploads an already-scaled 256x256 image, and every
    transformation the server could apply would mean adding an image decoder --
    a large attack surface reached directly by untrusted input.

    `media_type` comes from the magic bytes, never from the client's
    `Content-Type`. It is what `GET .../avatar` serves the bytes back as, so
    taking the client's word for it would let an uploader pick the type its own
    bytes are returned under.

    Three refusals, in order of cost: length, then signature, then the header's
    own dimensions. Each is a slice-and-compare over a bounded prefix.
    """

    def __init__(self, data: bytes) -> None:
        if len(data) > MAX_AVATAR_BYTES:
            raise ValidationException(
                error_code=AVATAR_TOO_LARGE_CODE, message=AVATAR_TOO_LARGE_MESSAGE
            )
        media_type = detect_media_type(data)
        if media_type is None:
            # Everything that is not PNG/JPEG/WebP lands here, and `<svg` and
            # `%PDF` land here BY DEFAULT rather than by a rule that names them.
            # An allowlist cannot be defeated by a format nobody thought to
            # denylist; that is why the check is "is it one of ours", not "is it
            # one of the dangerous ones".
            raise ValidationException(
                error_code=AVATAR_UNSUPPORTED_TYPE_CODE,
                message=AVATAR_UNSUPPORTED_TYPE_MESSAGE,
            )
        dimensions = read_dimensions(media_type, data)
        if dimensions is None or not self._within_bounds(dimensions):
            # `None` -- a header this parser cannot read -- is refused, not waved
            # through. A file whose declared size cannot be found is a file whose
            # size no guard has checked, and the browser that renders it later
            # will find dimensions somewhere.
            raise ValidationException(
                error_code=AVATAR_DIMENSIONS_TOO_LARGE_CODE,
                message=AVATAR_DIMENSIONS_TOO_LARGE_MESSAGE,
            )
        self._data = data
        self._media_type = media_type
        self._width, self._height = dimensions

    @staticmethod
    def _within_bounds(dimensions: tuple[int, int]) -> bool:
        return (
            min(dimensions) >= MIN_AVATAR_SIDE_PIXELS and max(dimensions) <= MAX_AVATAR_SIDE_PIXELS
        )

    @property
    def data(self) -> bytes:
        return self._data

    @property
    def media_type(self) -> str:
        return self._media_type

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height
