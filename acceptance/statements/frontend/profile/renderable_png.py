"""A PNG a real browser will actually DECODE, written to a temporary file.

The backend's `avatar_fixtures` are header-only on purpose -- the server reads the
header and never decodes. That is exactly why they are useless here: the client
resizes the picture through a canvas before it uploads anything, so a browser test
needs a complete image, IDAT and all, or `createImageBitmap` rejects and the
upload never happens.

Deliberately NOT a checked-in binary. Every field below is an expression, so the
picture's size -- which is the whole point of a downscaling test -- is readable
next to the assertion about it rather than in a hex editor. It also lets a test
ask for a NON-SQUARE source, which is the case a naive resize deforms.
"""

import struct
import tempfile
import zlib
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def write_png(directory: Path, name: str = "avatar.png", width: int = 600, height: int = 600) -> str:
    """Write an opaque grey RGB PNG and return its absolute path as a string.

    A string because that is what `send_keys` on a file input takes; a Path would
    be stringified by Selenium anyway, one layer further from the reader.
    """
    path = directory / name
    path.write_bytes(png_bytes(width, height))
    return str(path)


def png_bytes(width: int = 600, height: int = 600) -> bytes:
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    # One filter byte per scanline (0 = None), then three bytes per pixel. Flat grey: the test
    # asserts dimensions and byte counts, never colour.
    raw = b"".join(b"\x00" + b"\x80\x80\x80" * width for _ in range(height))
    return (
        PNG_SIGNATURE
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(raw, 6))
        + _chunk(b"IEND", b"")
    )


def temporary_directory() -> tempfile.TemporaryDirectory:
    return tempfile.TemporaryDirectory(prefix="textery-avatar-")


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )
