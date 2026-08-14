"""`Avatar` -- the three refusals, in the order they cost.

The parser's own cases live in `test_avatar_format_detection` and
`test_avatar_format_dimensions`. What is asserted here is which refusal a given
body earns, because the error code is the contract the client switches on.
"""

import pytest

from auth.avatar import (
    AVATAR_DIMENSIONS_TOO_LARGE_CODE,
    AVATAR_TOO_LARGE_CODE,
    AVATAR_UNSUPPORTED_TYPE_CODE,
    MAX_AVATAR_BYTES,
    MAX_AVATAR_SIDE_PIXELS,
    MIN_AVATAR_SIDE_PIXELS,
    Avatar,
)
from auth.avatar_format import JPEG, PNG, WEBP
from shared.exceptions import ValidationException
from statements import image_bytes


class TestAcceptsSupportedImages:
    def test_keeps_the_bytes_exactly_as_received(self):
        data = image_bytes.png(256, 256)

        assert Avatar(data).data == data

    @pytest.mark.parametrize(
        ("builder", "expected_media_type"),
        [
            (image_bytes.png, PNG),
            (image_bytes.jpeg, JPEG),
            (image_bytes.webp_lossy, WEBP),
            (image_bytes.webp_lossless, WEBP),
            (image_bytes.webp_extended, WEBP),
        ],
    )
    def test_reports_the_media_type_the_bytes_actually_are(self, builder, expected_media_type):
        assert Avatar(builder()).media_type == expected_media_type

    def test_exposes_the_dimensions_it_read(self):
        avatar = Avatar(image_bytes.png(320, 200))

        assert (avatar.width, avatar.height) == (320, 200)

    def test_accepts_an_image_exactly_on_the_side_ceiling(self):
        avatar = Avatar(image_bytes.png(MAX_AVATAR_SIDE_PIXELS, MAX_AVATAR_SIDE_PIXELS))

        assert avatar.width == MAX_AVATAR_SIDE_PIXELS

    def test_accepts_a_body_exactly_on_the_byte_ceiling(self):
        data = image_bytes.png() + b"\x00" * (MAX_AVATAR_BYTES - len(image_bytes.png()))

        assert len(Avatar(data).data) == MAX_AVATAR_BYTES


class TestRefusals:
    def test_refuses_a_body_one_byte_over_the_cap_before_looking_at_it(self):
        with pytest.raises(ValidationException) as refusal:
            Avatar(b"\x00" * (MAX_AVATAR_BYTES + 1))

        assert refusal.value.error_code == AVATAR_TOO_LARGE_CODE

    @pytest.mark.parametrize(
        "builder",
        [image_bytes.svg, image_bytes.svg_with_xml_declaration, image_bytes.gif, image_bytes.pdf],
    )
    def test_refuses_a_format_outside_the_allowlist(self, builder):
        with pytest.raises(ValidationException) as refusal:
            Avatar(builder())

        assert refusal.value.error_code == AVATAR_UNSUPPORTED_TYPE_CODE

    def test_refuses_an_empty_body_as_an_unsupported_type(self):
        with pytest.raises(ValidationException) as refusal:
            Avatar(b"")

        assert refusal.value.error_code == AVATAR_UNSUPPORTED_TYPE_CODE

    def test_refuses_a_side_one_pixel_over_the_ceiling(self):
        with pytest.raises(ValidationException) as refusal:
            Avatar(image_bytes.png(MAX_AVATAR_SIDE_PIXELS + 1, 8))

        assert refusal.value.error_code == AVATAR_DIMENSIONS_TOO_LARGE_CODE

    def test_refuses_a_decompression_bomb_by_its_declared_size(self):
        with pytest.raises(ValidationException) as refusal:
            Avatar(image_bytes.png(100000, 100000))

        assert refusal.value.error_code == AVATAR_DIMENSIONS_TOO_LARGE_CODE

    def test_refuses_a_recognised_format_whose_header_states_no_size(self):
        with pytest.raises(ValidationException) as refusal:
            Avatar(image_bytes.jpeg_without_frame_header())

        assert refusal.value.error_code == AVATAR_DIMENSIONS_TOO_LARGE_CODE

    @pytest.mark.parametrize(("width", "height"), [(0, 0), (0, 64), (64, 0)])
    def test_refuses_an_image_that_declares_a_side_of_zero(self, width: int, height: int):
        """A 0-pixel side is a size no browser can render and no guard has cleared.

        The ceiling check alone lets it through -- `max(0, 0)` is under any
        maximum -- so the floor is stated here explicitly.
        """
        with pytest.raises(ValidationException) as refusal:
            Avatar(image_bytes.png(width, height))

        assert refusal.value.error_code == AVATAR_DIMENSIONS_TOO_LARGE_CODE

    def test_accepts_an_image_exactly_on_the_floor(self):
        avatar = Avatar(image_bytes.png(MIN_AVATAR_SIDE_PIXELS, MIN_AVATAR_SIDE_PIXELS))

        assert (avatar.width, avatar.height) == (
            MIN_AVATAR_SIDE_PIXELS,
            MIN_AVATAR_SIDE_PIXELS,
        )
