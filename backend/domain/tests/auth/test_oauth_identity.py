from datetime import UTC, datetime
from uuid import uuid4

import pytest

from auth.oauth_identity import OAuthIdentity

_CREATED_AT = datetime(2026, 7, 23, 12, 0, 0, tzinfo=UTC)


class TestOAuthIdentityCreate:
    def test_carries_provider_subject_and_account(self):
        account_id = uuid4()
        identity = OAuthIdentity.create(uuid4(), "yandex", "2027708195", account_id, _CREATED_AT)

        assert identity.provider == "yandex"
        assert identity.subject == "2027708195"
        assert identity.account_id == account_id

    def test_rejects_a_missing_provider(self):
        # Identity is (provider, subject); neither half may be blank or the key that
        # keeps one person's account from being handed to another collapses.
        with pytest.raises(ValueError):
            OAuthIdentity.create(uuid4(), "", "2027708195", uuid4(), _CREATED_AT)

    def test_rejects_a_missing_subject(self):
        with pytest.raises(ValueError):
            OAuthIdentity.create(uuid4(), "yandex", "", uuid4(), _CREATED_AT)
