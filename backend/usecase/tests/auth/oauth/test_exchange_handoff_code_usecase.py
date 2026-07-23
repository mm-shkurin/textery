from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from auth.account import Account
from auth.handoff_code import MAX_HANDOFF_CODE_LENGTH, HandoffCode
from auth.oauth.exchange_handoff_code import ExchangeHandoffCode
from fake.auth.fake_account_repository import FakeAccountRepository
from fake.auth.fake_clock import FakeClock
from fake.auth.fake_token_service import FakeTokenService
from fake.auth.fake_unit_of_work import FakeUnitOfWork
from fake.auth.oauth.fake_handoff_code_repository import FakeHandoffCodeRepository
from shared.exceptions import ValidationException

_NOW = datetime(2026, 7, 23, 12, 0, 0, tzinfo=UTC)
_TTL = 300
_ERROR = "INVALID_OR_EXPIRED_OAUTH_CODE"


class _Fixture:
    def __init__(self) -> None:
        self.handoffs = FakeHandoffCodeRepository()
        self.accounts = FakeAccountRepository()
        self.tokens = FakeTokenService()
        self.uow = FakeUnitOfWork()
        self.usecase = ExchangeHandoffCode(
            handoff_code_repository=self.handoffs,
            account_repository=self.accounts,
            token_service=self.tokens,
            clock=FakeClock(_NOW),
            unit_of_work=self.uow,
        )

    async def given_account_with_code(self, created_at: datetime = _NOW) -> tuple[Account, str]:
        account = Account.create(uuid4(), "user@yandex.ru", password_hash="", created_at=_NOW)
        await self.accounts.save(account)
        code = HandoffCode.generate(account.id, created_at, _TTL)
        await self.handoffs.save(code)
        return account, code.value


class TestExchangeSuccess:
    async def test_issues_a_token_pair_for_the_codes_account(self):
        f = _Fixture()
        account, code = await f.given_account_with_code()

        pair = await f.usecase.execute(code)

        assert f.tokens.issued_for == [(account.id, account.email)]
        assert pair.access_token == f"access-token-for-{account.id}"

    async def test_burns_the_code_and_commits(self):
        f = _Fixture()
        _, code = await f.given_account_with_code()

        await f.usecase.execute(code)

        assert code not in f.handoffs._by_value
        assert f.uow.commit_call_count == 1


class TestExchangeSingleUse:
    async def test_a_second_exchange_of_one_code_is_refused(self):
        f = _Fixture()
        _, code = await f.given_account_with_code()
        await f.usecase.execute(code)

        with pytest.raises(ValidationException) as caught:
            await f.usecase.execute(code)

        assert caught.value.error_code == _ERROR


class TestExchangeRejections:
    async def test_refuses_an_empty_code_before_any_lookup(self):
        f = _Fixture()

        with pytest.raises(ValidationException) as caught:
            await f.usecase.execute("")

        assert caught.value.error_code == _ERROR
        assert f.handoffs.redeem_calls == []

    async def test_refuses_an_over_length_code_before_any_lookup(self):
        f = _Fixture()

        with pytest.raises(ValidationException) as caught:
            await f.usecase.execute("x" * (MAX_HANDOFF_CODE_LENGTH + 1))

        assert caught.value.error_code == _ERROR
        assert f.handoffs.redeem_calls == []

    async def test_refuses_an_unknown_code(self):
        f = _Fixture()

        with pytest.raises(ValidationException) as caught:
            await f.usecase.execute("never-minted")

        assert caught.value.error_code == _ERROR

    async def test_refuses_an_expired_code(self):
        f = _Fixture()
        # Minted far enough in the past that _NOW is beyond its TTL.
        _, code = await f.given_account_with_code(created_at=_NOW - timedelta(seconds=_TTL + 1))

        with pytest.raises(ValidationException) as caught:
            await f.usecase.execute(code)

        assert caught.value.error_code == _ERROR

    async def test_refuses_a_code_whose_account_is_gone(self):
        f = _Fixture()
        orphan = HandoffCode.generate(uuid4(), _NOW, _TTL)
        await f.handoffs.save(orphan)

        with pytest.raises(ValidationException) as caught:
            await f.usecase.execute(orphan.value)

        assert caught.value.error_code == _ERROR
