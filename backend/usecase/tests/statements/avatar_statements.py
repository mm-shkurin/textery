from auth.avatar_format import JPEG, PNG
from auth.delete_avatar import DeleteAvatar
from auth.get_avatar import GetAvatar
from auth.update_avatar import UpdateAvatar
from fake.auth.fake_avatar_repository import FakeAvatarRepository
from shared.exceptions import NotFoundException, ValidationException
from statements.image_bytes import jpeg, png, svg
from statements.profile_base import ProfileStatementsBase


class AvatarStatements(ProfileStatementsBase):
    """The three avatar usecases: upload, remove, serve.

    One class rather than three because they share a store: "upload then read it
    back" and "remove then read nothing" are the assertions that prove the
    round trip, and they need one repository between them.
    """

    UNSUPPORTED_TYPE_CODE = "AVATAR_UNSUPPORTED_TYPE"

    def __init__(self) -> None:
        super().__init__()
        self.avatar_repository = FakeAvatarRepository()
        self.write_failure = RuntimeError("the avatar write failed")
        self.served_avatar = None
        self.uploaded_bytes = b""

    async def given_a_stored_avatar(self) -> None:
        await self.avatar_repository.update_avatar(
            account_id=self.account_id,
            data=png(),
            media_type=PNG,
            updated_at=self.FIXED_CLOCK_NOW,
        )

    def given_the_avatar_write_fails(self) -> None:
        self.avatar_repository.raise_on_update = self.write_failure

    def given_the_avatar_clear_fails(self) -> None:
        self.avatar_repository.raise_on_clear = self.write_failure

    async def upload_a_png(self) -> None:
        await self._upload(png(64, 64))

    async def upload_a_jpeg(self) -> None:
        await self._upload(jpeg(64, 64))

    async def upload_an_svg(self) -> None:
        await self._upload(svg())

    async def upload_an_empty_body(self) -> None:
        await self._upload(b"")

    async def remove_the_avatar(self) -> None:
        self.returned_account = await self._capture(
            DeleteAvatar(
                account_repository=self.account_repository,
                avatar_repository=self.avatar_repository,
                unit_of_work=self.unit_of_work,
            ).execute(self.account_id)
        )

    async def serve_the_avatar(self) -> None:
        self.served_avatar = await self._capture(
            GetAvatar(avatar_repository=self.avatar_repository).execute(self.account_id)
        )

    async def _upload(self, data: bytes) -> None:
        self.uploaded_bytes = data
        self.returned_account = await self._capture(
            UpdateAvatar(
                account_repository=self.account_repository,
                avatar_repository=self.avatar_repository,
                clock=self.clock,
                unit_of_work=self.unit_of_work,
            ).execute(self.account_id, data)
        )

    def assert_the_stored_bytes_are_exactly_what_was_uploaded(self) -> None:
        stored = self.avatar_repository.stored[self.account_id]
        assert stored.data == self.uploaded_bytes, (
            "expected the bytes to be stored unchanged -- no decode, no re-encode"
        )

    def assert_the_stored_media_type_is(self, expected: str) -> None:
        stored = self.avatar_repository.stored[self.account_id]
        assert stored.media_type == expected, (
            f"expected the type read from the magic bytes, {expected!r}, got {stored.media_type!r}"
        )

    def assert_the_stored_media_type_is_jpeg(self) -> None:
        self.assert_the_stored_media_type_is(JPEG)

    def assert_the_returned_profile_reports_the_upload_instant(self) -> None:
        assert self.profile.avatar_updated_at == self.FIXED_CLOCK_NOW, (
            "expected the response to carry the instant this upload was stamped with, got "
            f"{self.profile.avatar_updated_at!r}"
        )

    def assert_the_returned_profile_reports_no_avatar(self) -> None:
        assert self.profile.avatar_updated_at is None

    def assert_the_stored_timestamp_matches_the_returned_one(self) -> None:
        stored = self.avatar_repository.stored[self.account_id]
        assert stored.updated_at == self.profile.avatar_updated_at, (
            "expected the timestamp written to storage to be the one the client was "
            f"told, got {stored.updated_at!r} against {self.profile.avatar_updated_at!r}"
        )

    def assert_no_avatar_is_stored(self) -> None:
        assert self.account_id not in self.avatar_repository.stored, (
            "expected storage to hold no avatar for this account"
        )

    def assert_nothing_reached_storage(self) -> None:
        assert self.avatar_repository.update_avatar_calls == [], (
            "expected a refused upload to never reach the repository, got "
            f"{self.avatar_repository.update_avatar_calls!r}"
        )

    def assert_the_avatar_was_cleared_once(self) -> None:
        assert self.avatar_repository.clear_avatar_calls == [self.account_id]

    def assert_refused_as_an_unsupported_type(self) -> None:
        assert isinstance(self.thrown_exception, ValidationException), (
            f"expected a ValidationException, got {self.thrown_exception!r}"
        )
        assert self.thrown_exception.error_code == self.UNSUPPORTED_TYPE_CODE

    def assert_refused_as_not_found(self) -> None:
        assert isinstance(self.thrown_exception, NotFoundException), (
            f"expected a NotFoundException, got {self.thrown_exception!r}"
        )

    def assert_the_served_bytes_and_type_are_the_stored_ones(self) -> None:
        stored = self.avatar_repository.stored[self.account_id]
        assert self.served_avatar is not None, "expected an avatar to have been served"
        assert (self.served_avatar.data, self.served_avatar.media_type) == (
            stored.data,
            stored.media_type,
        )

    def assert_the_write_failure_reached_the_caller(self) -> None:
        assert self.thrown_exception is self.write_failure, (
            f"expected the original failure to propagate, got {self.thrown_exception!r}"
        )

    def assert_the_work_was_rolled_back(self) -> None:
        assert self.unit_of_work.rollback_call_count == 1, (
            f"expected exactly one rollback, got {self.unit_of_work.rollback_call_count}"
        )
