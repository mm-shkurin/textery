from tests.backend.abstract_backend_test import AbstractBackendTest


class TestRemovingAnAvatarIsIdempotent(AbstractBackendTest):
    """DELETE answers 200 whether or not there is an avatar, and clears all of it.

    The second DELETE is the claim: a client retrying after a dropped response
    asked for "no avatar" and has it, so a 404 would report failure for a request
    that succeeded. Afterwards all three stored columns are gone, observed through
    two separate requests — the profile reports avatar_updated_at null, and the
    image route answers 404, which it does only when the bytes and their media
    type are both NULL. Each request runs on its own server-side session, so this
    is evidence about the database rather than about an identity map."""

    async def test_should_answer_200_twice_and_leave_nothing_stored(self, avatar_statements):
        outcome = await avatar_statements.upload_then_delete_twice()

        avatar_statements.assert_removal_is_idempotent_and_complete(outcome)


class TestDocumentsAreNeverAcceptedAsImages(AbstractBackendTest):
    """An SVG and a PDF are refused with AVATAR_UNSUPPORTED_TYPE, and nothing is stored.

    Both are uploaded with `Content-Type: image/png`, so a server that believed
    the header instead of the magic bytes would store them — and an SVG served
    back from this origin is stored XSS against the whole application, since an
    SVG is a document that can carry <script>. The "nothing stored" half is
    asserted separately because a refusal that answers 400 after writing the row
    is not a refusal."""

    async def test_should_refuse_svg_and_pdf_and_store_neither(self, avatar_statements):
        refusals = await avatar_statements.upload_a_document_pretending_to_be_an_image()

        avatar_statements.assert_every_document_was_refused_and_nothing_stored(refusals)


class TestTheImageIsServedSafely(AbstractBackendTest):
    """The stored image comes back with nosniff and the type read from its own bytes.

    Uploaded as a PNG while the request declared `image/webp`. The response must
    say `image/png` — the type the server proved from the magic bytes — because
    serving bytes as whatever their uploader claimed is how a file uploaded to one
    origin gets executed by it. `nosniff` closes the rest of that gap: without it
    a browser may disregard the declared type and decide for itself."""

    async def test_should_send_nosniff_and_the_type_derived_from_the_bytes(
        self, avatar_statements
    ):
        avatar = await avatar_statements.upload_a_png_and_fetch_it()

        avatar_statements.assert_the_image_is_served_safely(avatar)
