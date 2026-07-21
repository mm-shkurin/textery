from auth.verification_code import VerificationCode
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_verification_code_repository import FakeVerificationCodeRepository
from shared.exceptions import ValidationException


class ResendCodeAssertions:
    """Assertion half of ResendCodeStatements (split out to stay under the 200-line cap).

    A mixin: every attribute it reads is initialised by ResendCodeStatements.__init__.
    Kept beside the arrange half so the DSL still reads as one Statements object.
    """

    COOLDOWN_ERROR_CODE = "RESEND_COOLDOWN_ACTIVE"
    COOLDOWN_MESSAGE = "A verification code was recently sent. Please wait before requesting another."
    INVALID_OR_EXPIRED_CODE = "INVALID_OR_EXPIRED_CODE"
    INVALID_OR_EXPIRED_MESSAGE = "The verification code is invalid or has expired."

    verification_code_repository: FakeVerificationCodeRepository
    account_repository: FakeAccountRepository
    codes_before_resend: int
    thrown_exception: Exception | None
    old_code: str | None
    new_code: str | None
    old_code_entity: VerificationCode | None
    old_code_verify_exception: Exception | None
    new_code_verify_exception: Exception | None

    def assert_rejected_as_cooldown_active_with_no_new_code(self) -> None:
        self._assert_validation_exception(
            self.thrown_exception, self.COOLDOWN_ERROR_CODE, self.COOLDOWN_MESSAGE
        )
        assert len(self.verification_code_repository.saved_codes) == self.codes_before_resend, (
            f"expected an in-cooldown resend to issue NO new code, saved_codes went from "
            f"{self.codes_before_resend} to {len(self.verification_code_repository.saved_codes)}"
        )

    def assert_new_code_issued_and_supersedes_the_old_one(self) -> None:
        self._assert_fresh_code_issued()
        self._assert_is_invalid_or_expired(self.old_code_verify_exception)
        assert self.new_code_verify_exception is None, (
            f"expected the NEW code to verify the account, got "
            f"{type(self.new_code_verify_exception).__name__}: {self.new_code_verify_exception}"
        )
        assert self.account_repository.saved_accounts[-1].is_verified is True, (
            "expected the account to be verified by the NEW code after supersession"
        )

    def assert_reissued_code_timestamp_is_strictly_greater(self) -> None:
        # The real find_active_by_account_id runs ORDER BY created_at DESC, so
        # supersession only holds if the reissued code carries a strictly-greater
        # timestamp. The Fake's insertion-order lookup would mask a green that
        # persists an equal/earlier timestamp; this pins monotonicity directly.
        # expires_at is the only monotonic field the entity exposes (= created_at
        # + fixed expiry), so it tracks created_at ordering.
        self._assert_fresh_code_issued()
        new_entity = self.verification_code_repository.saved_codes[-1]
        assert self.old_code_entity is not None and (
            new_entity.expires_at > self.old_code_entity.expires_at
        ), (
            f"expected the reissued code's timestamp to be strictly greater than the "
            f"superseded code's, got new={new_entity.expires_at} "
            f"old={self.old_code_entity.expires_at if self.old_code_entity else None}"
        )

    def assert_a_new_code_was_issued_at_the_boundary(self) -> None:
        # The boundary's intent (resend AT exactly 60s must SUCCEED, per the ADR's
        # `now - max(created_at) >= 60s`) lives in the test method's docstring; the
        # observable outcome is identical to any successful resend, so it shares the
        # same fresh-code assertion.
        self._assert_fresh_code_issued()

    def _assert_fresh_code_issued(self) -> None:
        assert self.thrown_exception is None, (
            f"expected the resend to succeed, got "
            f"{type(self.thrown_exception).__name__}: {self.thrown_exception}"
        )
        assert len(self.verification_code_repository.saved_codes) == self.codes_before_resend + 1, (
            f"expected exactly one NEW code to be persisted by the resend, saved_codes went from "
            f"{self.codes_before_resend} to {len(self.verification_code_repository.saved_codes)}"
        )
        assert self.new_code is not None and len(self.new_code) == 6 and self.new_code.isdigit(), (
            f"expected a fresh 6-digit code, got {self.new_code!r}"
        )
        assert self.new_code != self.old_code, (
            f"expected the reissued code to differ from the superseded one, both were "
            f"{self.new_code!r}"
        )

    def _assert_is_invalid_or_expired(self, exc: Exception | None) -> None:
        self._assert_validation_exception(
            exc, self.INVALID_OR_EXPIRED_CODE, self.INVALID_OR_EXPIRED_MESSAGE
        )

    def _assert_validation_exception(
        self, exc: Exception | None, expected_error_code: str, expected_message: str
    ) -> None:
        assert isinstance(exc, ValidationException), (
            f"expected ValidationException('{expected_error_code}'), got "
            f"{type(exc).__name__ if exc else None}: {exc}"
        )
        actual = (exc.error_code, exc.message)
        expected = (expected_error_code, expected_message)
        assert actual == expected, f"expected {expected}, got {actual}"
