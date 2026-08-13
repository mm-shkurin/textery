"""What an image is, and how large, read from the first bytes of the file.

READING A HEADER IS NOT DECODING. Nothing here allocates a pixel buffer, walks
compressed data, or runs anything the file asks it to; every function below is a
handful of slices and integer arithmetic over a bounded prefix. That distinction
is the whole reason there is no Pillow in this project: a decoder is a large C
attack surface reached by untrusted bytes on an authenticated route, and the
server has no need for one -- the client uploads an already-resized 256x256 image
and the server stores the bytes exactly as received.

The media type is decided HERE, from the magic bytes, and never from the
`Content-Type` the client sent. The stored value is what `GET .../avatar` later
serves, so trusting the client's header would let it choose the type its own
bytes are served back as.

SVG is absent from this file and must stay absent. It is not an image format in
the sense that matters here -- it is a document that can carry `<script>`, and
serving one from this origin is stored XSS against the whole application. There
is no "safe SVG" branch to add later; the answer is the unsupported-type refusal.
"""

# Longest prefix any check below reads. Callers may hand in the whole body; the
# parsers slice, so a short or truncated file yields None rather than an
# IndexError.
HEADER_BYTES = 32

PNG = "image/png"
JPEG = "image/jpeg"
WEBP = "image/webp"

# The allowlist, in one place. A media type absent from here can neither be
# stored nor served -- `detect_media_type` returns one of these three or None.
SUPPORTED_MEDIA_TYPES = (PNG, JPEG, WEBP)

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SIGNATURE = b"\xff\xd8\xff"
_RIFF = b"RIFF"
_WEBP = b"WEBP"

# Start-of-Frame markers. The whole SOFn family, not only SOF0/SOF2: a progressive
# or arithmetic-coded JPEG carries its dimensions in exactly the same five bytes,
# and a parser that knew only the two common markers would find no frame header at
# all and report "dimensions unknown" for a perfectly ordinary file.
# 0xC4 (DHT), 0xC8 (JPG) and 0xCC (DAC) are excluded -- they are not frame headers.
_SOF_MARKERS = frozenset(
    {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
)
_STANDALONE_MARKERS = frozenset({0xD8, 0xD9, *range(0xD0, 0xD8)})


def detect_media_type(data: bytes) -> str | None:
    """The media type implied by the leading bytes, or None if it is not one of ours."""
    if data.startswith(_PNG_SIGNATURE):
        return PNG
    if data.startswith(_JPEG_SIGNATURE):
        return JPEG
    # RIFF is a container: the fourcc at offset 8 is what makes it a WebP rather
    # than a WAV, so both are checked. `<svg`, `%PDF`, `GIF8` and everything else
    # fall through to None.
    if data[:4] == _RIFF and data[8:12] == _WEBP:
        return WEBP
    return None


def read_dimensions(media_type: str, data: bytes) -> tuple[int, int] | None:
    """(width, height) from the format's own header, or None if unreadable.

    None means "this file does not state its size where the format says it
    should", which the caller treats as a refusal, not as a pass: a header the
    parser cannot read is a header a browser's decoder might read differently.
    """
    if media_type == PNG:
        return _png_dimensions(data)
    if media_type == JPEG:
        return _jpeg_dimensions(data)
    if media_type == WEBP:
        return _webp_dimensions(data)
    return None


def _png_dimensions(data: bytes) -> tuple[int, int] | None:
    # IHDR is required by the spec to be the first chunk: 8-byte signature,
    # 4-byte length, 4-byte type, then width and height as big-endian uint32.
    if len(data) < 24 or data[12:16] != b"IHDR":
        return None
    return _be(data[16:20]), _be(data[20:24])


def _jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    # Walk the marker chain to the frame header. Bounded by the length of the
    # data and by the segment lengths the file itself declares; a malformed
    # length walks off the end and returns None rather than looping.
    offset = 2
    while offset + 4 <= len(data):
        if data[offset] != 0xFF:
            return None
        marker = data[offset + 1]
        if marker in _STANDALONE_MARKERS:
            offset += 2
            continue
        segment_length = _be(data[offset + 2 : offset + 4])
        if segment_length < 2:
            return None
        if marker in _SOF_MARKERS:
            # Inside the frame header: 1 byte precision, then height, then width.
            if offset + 9 > len(data):
                return None
            return _be(data[offset + 7 : offset + 9]), _be(data[offset + 5 : offset + 7])
        offset += 2 + segment_length
    return None


def _webp_dimensions(data: bytes) -> tuple[int, int] | None:
    chunk = data[12:16]
    if chunk == b"VP8 ":
        # Lossy: 3-byte frame tag, then the 3-byte sync code, then 14-bit
        # width and height (the top two bits are the scaling hint).
        if len(data) < 30 or data[23:26] != b"\x9d\x01\x2a":
            return None
        return _le(data[26:28]) & 0x3FFF, _le(data[28:30]) & 0x3FFF
    if chunk == b"VP8L":
        # Lossless: signature byte, then 14 bits of width-1 and 14 of height-1
        # packed little-endian across four bytes.
        if len(data) < 25 or data[20] != 0x2F:
            return None
        packed = _le(data[21:25])
        return (packed & 0x3FFF) + 1, ((packed >> 14) & 0x3FFF) + 1
    if chunk == b"VP8X":
        # Extended: the CANVAS size, which is the size a browser lays out, as two
        # 3-byte little-endian minus-one values.
        if len(data) < 30:
            return None
        return _le(data[24:27]) + 1, _le(data[27:30]) + 1
    return None


def _be(raw: bytes) -> int:
    return int.from_bytes(raw, "big")


def _le(raw: bytes) -> int:
    return int.from_bytes(raw, "little")
