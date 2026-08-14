"""`detect_media_type` -- the line between "an image" and "bytes we will serve back".

Every case here is decided from the file's own leading bytes. Nothing in this
module passes the parser a declared `Content-Type`, because the parser has no
parameter for one: the type is read from the file, and that is the property under
test. The lying-header case (a request that says PNG over JPEG bytes) is proved
end to end in `adapters/rest/tests/router/auth/test_avatar_put_router.py`.
"""

import pytest

from auth.avatar_format import JPEG, PNG, SUPPORTED_MEDIA_TYPES, WEBP, detect_media_type
from statements import image_bytes


class TestDetectsSupportedFormats:
    def test_detects_png_from_its_eight_byte_signature(self):
        assert detect_media_type(image_bytes.png()) == PNG

    def test_detects_jpeg_from_its_start_of_image_marker(self):
        assert detect_media_type(image_bytes.jpeg()) == JPEG

    def test_detects_lossy_webp_from_the_riff_container_and_its_fourcc(self):
        assert detect_media_type(image_bytes.webp_lossy()) == WEBP

    def test_detects_lossless_webp(self):
        assert detect_media_type(image_bytes.webp_lossless()) == WEBP

    def test_detects_extended_webp(self):
        assert detect_media_type(image_bytes.webp_extended()) == WEBP

    def test_every_detected_type_is_in_the_allowlist(self):
        detected = {
            detect_media_type(image_bytes.png()),
            detect_media_type(image_bytes.jpeg()),
            detect_media_type(image_bytes.webp_lossy()),
        }

        assert detected == set(SUPPORTED_MEDIA_TYPES)


class TestRefusesEverythingElse:
    def test_refuses_svg_because_it_can_carry_script(self):
        assert detect_media_type(image_bytes.svg()) is None

    def test_refuses_svg_behind_an_xml_declaration(self):
        assert detect_media_type(image_bytes.svg_with_xml_declaration()) is None

    def test_refuses_gif(self):
        assert detect_media_type(image_bytes.gif()) is None

    def test_refuses_pdf(self):
        assert detect_media_type(image_bytes.pdf()) is None

    def test_refuses_bmp(self):
        assert detect_media_type(image_bytes.bmp()) is None

    def test_refuses_a_riff_container_that_is_not_a_webp(self):
        assert detect_media_type(image_bytes.riff_that_is_not_webp()) is None

    def test_refuses_plain_text(self):
        assert detect_media_type(b"this is not an image at all") is None


class TestRefusesTruncatedAndEmptyBodies:
    def test_refuses_an_empty_body(self):
        assert detect_media_type(b"") is None

    @pytest.mark.parametrize("length", [1, 2, 4, 7])
    def test_refuses_a_png_signature_cut_short(self, length: int):
        assert detect_media_type(image_bytes.PNG_SIGNATURE[:length]) is None

    @pytest.mark.parametrize("length", [1, 2])
    def test_refuses_a_jpeg_signature_cut_short(self, length: int):
        assert detect_media_type(b"\xff\xd8\xff"[:length]) is None

    @pytest.mark.parametrize("length", [4, 8, 11])
    def test_refuses_a_webp_header_that_stops_before_its_fourcc(self, length: int):
        assert detect_media_type(image_bytes.webp_lossy()[:length]) is None


class TestRefusesPrefixesThatDoNotContinue:
    def test_refuses_bytes_that_start_like_png_and_then_diverge(self):
        assert detect_media_type(b"\x89PNG\r\n\x1a\x00" + b"\x00" * 24) is None

    def test_refuses_bytes_that_start_like_jpeg_and_then_diverge(self):
        assert detect_media_type(b"\xff\xd8\x00" + b"\x00" * 24) is None

    def test_refuses_riff_whose_fourcc_is_one_byte_off(self):
        assert detect_media_type(image_bytes.riff_that_is_not_webp(b"WEBQ")) is None
