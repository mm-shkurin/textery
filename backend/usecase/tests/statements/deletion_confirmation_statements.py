import unicodedata
from datetime import UTC, datetime
from uuid import uuid4

from auth.account import Account
from auth.deletion_confirmation import email_confirms, has_password, password_confirms
from fake.auth.fake_password_hasher import FakePasswordHasher


class DeletionConfirmationStatements:
    """The two predicates that stand between a caller and an irreversible DELETE.

    Driven directly, without the usecase around them: `DeleteAccount` picks ONE
    branch per account, so a test that went through it could never state what the
    other branch answers for the same input. Both are asserted here.
    """

    EMAIL = "ada@example.ru"
    PASSWORD = "Str0ng!Pass"
    # Precomposed "é"; the decomposed twin is the same password to a person and a
    # different byte string to a hasher.
    ACCENTED_PASSWORD_NFC = unicodedata.normalize("NFC", "Str0ng!Passé")
    ACCENTED_PASSWORD_NFD = unicodedata.normalize("NFD", "Str0ng!Passé")
    CREATED_AT = datetime(2026, 7, 1, 9, 30, 0, tzinfo=UTC)
    # Stored the way registration stores it: NFC. The decomposed twin below is the
    # same address to its owner and a different string to `==`.
    ACCENTED_EMAIL_NFC = unicodedata.normalize("NFC", "renée@example.ru")
    ACCENTED_EMAIL_NFD = unicodedata.normalize("NFD", "renée@example.ru")

    def __init__(self) -> None:
        self.password_hasher = FakePasswordHasher()
        self.account: Account | None = None
        self.answer: bool | None = None

    def given_an_account_with_a_password(self, password: str | None = None) -> None:
        self._build(self.password_hasher.hash(self.PASSWORD if password is None else password))

    def given_an_account_with_an_accented_password_stored_precomposed(self) -> None:
        self._build(self.password_hasher.hash(self.ACCENTED_PASSWORD_NFC))

    def given_an_oauth_account(self) -> None:
        """`password_hash=""` -- what `complete_oauth_callback` actually stores."""
        self._build("")

    def given_an_oauth_account_whose_address_carries_an_accent(self) -> None:
        self._build("", email=self.ACCENTED_EMAIL_NFC)

    def confirm_with_the_decomposed_form_of_the_address(self) -> None:
        self.confirm_with_email(self.ACCENTED_EMAIL_NFD)

    def _build(self, password_hash: str, email: str | None = None) -> None:
        self.account = Account.reconstitute(
            id=uuid4(),
            email=self.EMAIL if email is None else email,
            password_hash=password_hash,
            created_at=self.CREATED_AT,
            is_verified=True,
        )

    def _the_account(self) -> Account:
        """The account a `given_...` step built, or a named failure if none did.

        The attribute starts as None because the Statement is constructed before
        any step runs. Reading it through here means a Statement that confirms
        without arranging an account fails saying so, instead of handing None to
        a function whose whole contract is about a real account.
        """
        assert self.account is not None, "no account was arranged for this statement"
        return self.account

    def confirm_with_password(self, password: object) -> None:
        self.answer = password_confirms(self._the_account(), password, self.password_hasher)

    def confirm_with_the_correct_password(self) -> None:
        self.confirm_with_password(self.PASSWORD)

    def confirm_with_the_decomposed_form_of_the_password(self) -> None:
        self.confirm_with_password(self.ACCENTED_PASSWORD_NFD)

    def confirm_with_email(self, confirm_email: object) -> None:
        self.answer = email_confirms(self._the_account(), confirm_email)

    def confirm_with_the_accounts_own_email(self) -> None:
        self.confirm_with_email(self.EMAIL)

    def ask_whether_the_account_has_a_password(self) -> None:
        self.answer = has_password(self._the_account())

    def assert_confirmed(self) -> None:
        assert self.answer is True, f"expected the confirmation to be accepted, got {self.answer!r}"

    def assert_not_confirmed(self) -> None:
        assert self.answer is False, (
            "expected the confirmation to be REFUSED -- what follows it cannot be "
            f"undone, got {self.answer!r}"
        )

    def assert_the_hasher_was_never_reached(self) -> None:
        assert self.password_hasher.verify_call_count == 0, (
            "expected the guard to answer before the hasher, so the most destructive "
            "path in the product does not depend on a library's error handling"
        )
