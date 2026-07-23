from datetime import datetime
from uuid import UUID


class OAuthIdentity:
    """A provider-asserted identity bound to exactly one local account.

    Identity is `(provider, subject)`, never the email. The email a provider
    returns can change (a user renames their mailbox) and can be reused by the
    provider for a different person; the subject cannot. Keying on the email
    would silently hand one person's account to another after a rename.
    """

    def __init__(
        self,
        id: UUID,
        provider: str,
        subject: str,
        account_id: UUID,
        created_at: datetime,
    ) -> None:
        if not provider or not subject:
            raise ValueError("An OAuth identity needs both a provider and a subject.")
        self.id = id
        self.provider = provider
        self.subject = subject
        self.account_id = account_id
        self.created_at = created_at

    @classmethod
    def create(
        cls,
        id: UUID,
        provider: str,
        subject: str,
        account_id: UUID,
        created_at: datetime,
    ) -> "OAuthIdentity":
        return cls(
            id=id,
            provider=provider,
            subject=subject,
            account_id=account_id,
            created_at=created_at,
        )
