"""`read_dimensions` -- the size a file declares about itself, or a refusal.

`None` is never "unknown, carry on": `Avatar` turns it into a rejection. So every
unreadable header below is asserting a refusal, not a missing value.
"""

import pytest

from auth.avatar_format import JPEG, PNG, WEBP, read_dimensions
from statements import image_bytes


class TestPngDimensions:
    def test_reads_width_and_height_from_the_ihdr_chunk(self):
        assert read_dimensions(PNG, image_bytes.png(320, 200)) == (320, 200)

    def test_reads_a_size_far_above_the_products_ceiling_so_the_caller_can_refuse_it(self):
        assert read_dimensions(PNG, image_bytes.png(100000, 100000)) == (100000, 100000)

    def test_reads_a_declared_size_of_zero_rather_than_reporting_it_unreadable(self):
        assert read_dimensions(PNG, image_bytes.png(0, 0)) == (0, 0)

    def test_refuses_a_first_chunk_that_is_not_ihdr(self):
        assert read_dimensions(PNG, image_bytes.png(chunk_type=b"IDAT")) is None

    @pytest.mark.parametrize("length", [8, 16, 18, 22, 23])
    def test_refuses_a_header_that_stops_inside_the_dimension_fields(self, length: int):
        assert read_dimensions(PNG, image_bytes.png()[:length]) is None

    def test_refuses_an_empty_body(self):
        assert read_dimensions(PNG, b"") is None


class TestJpegDimensions:
    def test_reads_height_then_width_from_the_frame_header(self):
        assert read_dimensions(JPEG, image_bytes.jpeg(320, 200)) == (320, 200)

    @pytest.mark.parametrize("marker", [image_bytes.SOF0, image_bytes.SOF2, image_bytes.SOF9])
    def test_reads_the_size_from_every_frame_marker_in_the_sofn_family(self, marker: int):
        assert read_dimensions(JPEG, image_bytes.jpeg(320, 200, marker)) == (320, 200)

    def test_walks_over_standalone_markers_that_carry_no_length_field(self):
        assert read_dimensions(JPEG, image_bytes.jpeg_with_standalone_markers(64, 48)) == (64, 48)

    def test_refuses_a_file_whose_marker_chain_never_reaches_a_frame_header(self):
        assert read_dimensions(JPEG, image_bytes.jpeg_without_frame_header()) is None

    def test_refuses_a_chain_broken_where_a_marker_must_begin(self):
        assert read_dimensions(JPEG, image_bytes.jpeg_with_broken_marker_chain()) is None

    @pytest.mark.parametrize("segment_length", [0, 1])
    def test_refuses_a_segment_declaring_a_length_below_its_own_length_field(
        self, segment_length: int
    ):
        data = image_bytes.jpeg_with_declared_segment_length(segment_length)

        assert read_dimensions(JPEG, data) is None

    def test_refuses_a_frame_header_that_stops_inside_its_dimension_fields(self):
        truncated = image_bytes.jpeg()[:-4]

        assert read_dimensions(JPEG, truncated) is None

    def test_refuses_an_empty_body(self):
        assert read_dimensions(JPEG, b"") is None


class TestWebpDimensions:
    def test_reads_the_fourteen_bit_size_of_a_lossy_frame(self):
        assert read_dimensions(WEBP, image_bytes.webp_lossy(320, 200)) == (320, 200)

    def test_reads_the_minus_one_encoded_size_of_a_lossless_frame(self):
        assert read_dimensions(WEBP, image_bytes.webp_lossless(320, 200)) == (320, 200)

    def test_reads_the_canvas_size_of_an_extended_file(self):
        assert read_dimensions(WEBP, image_bytes.webp_extended(320, 200)) == (320, 200)

    def test_refuses_a_chunk_type_no_branch_knows(self):
        assert read_dimensions(WEBP, image_bytes.webp_with_chunk(b"ALPH", b"\x00" * 16)) is None

    def test_refuses_a_lossy_frame_whose_sync_code_is_wrong(self):
        assert read_dimensions(WEBP, image_bytes.webp_lossy_with_sync_code(b"\x00\x00\x00")) is None

    def test_refuses_a_lossless_frame_whose_signature_byte_is_wrong(self):
        assert read_dimensions(WEBP, image_bytes.webp_lossless_with_signature_byte(0x00)) is None

    @pytest.mark.parametrize(
        "builder",
        [image_bytes.webp_lossy, image_bytes.webp_lossless, image_bytes.webp_extended],
    )
    def test_refuses_a_header_that_stops_inside_the_dimension_fields(self, builder):
        assert read_dimensions(WEBP, builder()[:-1]) is None

    def test_refuses_an_empty_body(self):
        assert read_dimensions(WEBP, b"") is None


class TestUnsupportedMediaType:
    @pytest.mark.parametrize("media_type", ["image/svg+xml", "image/gif", "", "png"])
    def test_refuses_any_media_type_outside_the_three_it_parses(self, media_type: str):
        assert read_dimensions(media_type, image_bytes.png()) is None
