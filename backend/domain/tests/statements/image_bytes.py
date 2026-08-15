"""Real file headers, built byte by byte, for the avatar format parser.

Hand-assembled rather than loaded from fixture files on purpose: every field the
parser reads is written here as an expression, so a test that asserts 320x200 can
be traced to the exact offsets that carry 320 and 200. Fixture binaries would
hide precisely the thing under test.

Only headers. Nothing here contains real compressed image data -- the parser
under test never looks past the header, and giving it one would only make the
fixtures unreadable.
"""

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
RIFF = b"RIFF"
WEBP = b"WEBP"

SOF0 = 0xC0
SOF2 = 0xC2
SOF9 = 0xC9
DHT = 0xC4


def png(width: int = 256, height: int = 256, chunk_type: bytes = b"IHDR") -> bytes:
    """A PNG signature plus the IHDR chunk, which is where the size lives."""
    return (
        PNG_SIGNATURE
        + _be32(13)
        + chunk_type
        + _be32(width)
        + _be32(height)
        + b"\x08\x06\x00\x00\x00"
    )


def jpeg(width: int = 256, height: int = 256, sof_marker: int = SOF0) -> bytes:
    """SOI, one APP0 segment to be walked over, then the frame header."""
    return b"\xff\xd8" + _app0() + _sof(sof_marker, width, height)


def jpeg_without_frame_header() -> bytes:
    """A file whose marker chain ends without ever reaching a SOFn segment."""
    return b"\xff\xd8" + _app0() + _segment(DHT, b"\x00" * 8)


def jpeg_with_standalone_markers(width: int = 256, height: int = 256) -> bytes:
    """Restart markers before the frame header -- two bytes each, no length field."""
    return b"\xff\xd8" + b"\xff\xd0" + b"\xff\xd1" + _sof(SOF0, width, height)


def jpeg_with_declared_segment_length(segment_length: int) -> bytes:
    """A segment that declares its own length, used to feed the parser a bad one."""
    return b"\xff\xd8\xff\xe0" + _be16(segment_length) + b"\x00" * 8


def jpeg_with_broken_marker_chain() -> bytes:
    """A segment length that lands the walk on a byte which is not 0xFF.

    Where the next marker must begin there is padding instead, so the chain the
    parser is following stops being a chain.
    """
    return b"\xff\xd8" + b"\xff\xe0\x00\x04\x00\x00" + b"\x00" * 8


def webp_lossy(width: int = 256, height: int = 256) -> bytes:
    """VP8: the 14-bit width and height that follow the three-byte sync code."""
    body = b"\x00\x00\x00" + b"\x9d\x01\x2a" + _le16(width) + _le16(height)
    return _riff(b"VP8 ", body)


def webp_lossless(width: int = 256, height: int = 256) -> bytes:
    """VP8L: width-1 and height-1 in 14 bits each, packed little-endian."""
    packed = (width - 1) | ((height - 1) << 14)
    return _riff(b"VP8L", b"\x2f" + packed.to_bytes(4, "little"))


def webp_extended(width: int = 256, height: int = 256) -> bytes:
    """VP8X: the canvas size, as two three-byte minus-one values."""
    # One flags byte plus three reserved, then the canvas size.
    body = b"\x00" * 4 + _le24(width - 1) + _le24(height - 1)
    return _riff(b"VP8X", body)


def webp_with_chunk(chunk: bytes, body: bytes = b"") -> bytes:
    """A RIFF/WEBP container carrying a chunk the parser does not know."""
    return _riff(chunk, body)


def webp_lossy_with_sync_code(sync_code: bytes) -> bytes:
    """VP8 whose three-byte sync code is not the one the format requires."""
    return _riff(b"VP8 ", b"\x00\x00\x00" + sync_code + _le16(256) + _le16(256))


def webp_lossless_with_signature_byte(signature: int) -> bytes:
    """VP8L whose leading signature byte is not 0x2F."""
    return _riff(b"VP8L", bytes([signature]) + b"\x00" * 4)


def riff_that_is_not_webp(fourcc: bytes = b"WAVE") -> bytes:
    """A RIFF container of some other kind -- the fourcc at offset 8 decides."""
    return RIFF + _le32(4) + fourcc


def svg() -> bytes:
    return b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


def svg_with_xml_declaration() -> bytes:
    return b'<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg"/>'


def gif() -> bytes:
    return b"GIF89a" + b"\x00" * 26


def pdf() -> bytes:
    return b"%PDF-1.7\n" + b"\x00" * 24


def bmp() -> bytes:
    return b"BM" + b"\x00" * 30


def _app0() -> bytes:
    return _segment(0xE0, b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00")


def _sof(marker: int, width: int, height: int) -> bytes:
    return _segment(marker, b"\x08" + _be16(height) + _be16(width) + b"\x03")


def _segment(marker: int, payload: bytes) -> bytes:
    return bytes([0xFF, marker]) + _be16(len(payload) + 2) + payload


def _riff(chunk: bytes, body: bytes) -> bytes:
    return RIFF + _le32(4 + 8 + len(body)) + WEBP + chunk + _le32(len(body)) + body


def _be16(value: int) -> bytes:
    return value.to_bytes(2, "big")


def _be32(value: int) -> bytes:
    return value.to_bytes(4, "big")


def _le16(value: int) -> bytes:
    return value.to_bytes(2, "little")


def _le24(value: int) -> bytes:
    return value.to_bytes(3, "little")


def _le32(value: int) -> bytes:
    return value.to_bytes(4, "little")
