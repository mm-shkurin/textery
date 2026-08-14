"""Image fixtures built byte by byte, and the two files that must never be accepted.

Constructed rather than checked in as binaries: an assertion about magic bytes and
header-declared dimensions should be readable next to the bytes it is about, and a
committed `.webp` would make "why is this 400" a question answered with a hex
editor.

None of these are complete, renderable images -- they carry a valid header and
nothing behind it. That is exactly the surface the server inspects: it reads the
header and stores the bytes, and never decodes.
"""

import struct
import zlib

WEBP = "image/webp"
PNG = "image/png"


def webp(width: int = 256, height: int = 256) -> bytes:
    """A RIFF/WEBP container with a VP8X chunk declaring the canvas size.

    VP8X stores width-1 and height-1 as 3-byte little-endian values -- the
    minus-one is the trap this fixture exists to keep honest, since an off-by-one
    in the parser puts the boundary one pixel from where the contract says.
    """
    chunk = b"VP8X" + struct.pack("<I", 10) + b"\x00\x00\x00\x00"
    chunk += (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
    return b"RIFF" + struct.pack("<I", 4 + len(chunk)) + b"WEBP" + chunk


def png(width: int = 256, height: int = 256) -> bytes:
    """An 8-byte signature followed by a well-formed IHDR chunk."""
    header = struct.pack(">II", width, height) + b"\x08\x06\x00\x00\x00"
    chunk = b"IHDR" + header
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", len(header))
        + chunk
        + struct.pack(">I", zlib.crc32(chunk))
    )


# An SVG. Refused because it is a DOCUMENT, not an image: it can carry <script>,
# and this origin serving one back means stored XSS against the whole
# application -- session, editor content, everything the app can reach. There is
# no sanitising branch to add later; the answer is the refusal.
SVG = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"

# A PDF. Not dangerous in the same way, and refused by the same mechanism: the
# check asks "is this one of our three formats", so every other format is refused
# without anyone having had to think of it in advance. That is the property the
# SVG case depends on.
PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
