from datetime import datetime, timezone
from uuid import uuid4

import pytest

from auth.account import Account


def test_account_is_verified_is_false_at_construction():
    account = Account(
        id=uuid4(),
        email="user@example.com",
        password_hash="hashed",
        created_at=datetime.now(timezone.utc),
    )

    assert account.is_verified is False


def test_account_is_verified_has_no_public_setter():
    account = Account(
        id=uuid4(),
        email="user@example.com",
        password_hash="hashed",
        created_at=datetime.now(timezone.utc),
    )

    with pytest.raises(AttributeError):
        account.is_verified = True


@pytest.mark.skip(reason="RED: Account.reconstitute is not implemented")
def test_account_reconstitute_preserves_is_verified_true():
    account = Account.reconstitute(
        id=uuid4(),
        email="user@example.com",
        password_hash="hashed",
        created_at=datetime.now(timezone.utc),
        is_verified=True,
    )

    assert account.is_verified is True


@pytest.mark.skip(reason="RED: Account.verify is not implemented")
def test_account_verify_sets_is_verified_true():
    account = Account(
        id=uuid4(),
        email="user@example.com",
        password_hash="hashed",
        created_at=datetime.now(timezone.utc),
    )

    account.verify()

    assert account.is_verified is True
