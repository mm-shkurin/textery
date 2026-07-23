from uuid import UUID, uuid4

from auth.account import Account
from auth.account_repository import AccountRepository
from auth.email import Email
from auth.handoff_code import HandoffCode
from auth.oauth.handoff_code_repository import HandoffCodeRepository
from auth.oauth.oauth_error_codes import OAuthCallbackError
from auth.oauth.oauth_identity_repository import OAuthIdentityRepository
from auth.oauth.oauth_provider import OAuthProviderError
from auth.oauth.oauth_state_repository import OAuthStateRepository
from auth.oauth.provider_registry import ProviderRegistry
from auth.oauth_identity import OAuthIdentity
from shared.clock import Clock, SystemClock
from shared.unit_of_work import NullUnitOfWork, UnitOfWork


class CompleteOAuthCallback:
    """Leg 2: validate the provider's redirect and mint a one-time handoff code.

    Consumes the CSRF state, exchanges the provider code for an asserted identity,
    resolves or auto-creates the local account, and returns an opaque handoff code.
    Every failure raises `OAuthCallbackError`, which the controller renders as a
    single generic `?error=` — no leg's failure is distinguishable to the client.
    """

    def __init__(
        self,
        provider_registry: ProviderRegistry,
        state_repository: OAuthStateRepository,
        identity_repository: OAuthIdentityRepository,
        account_repository: AccountRepository,
        handoff_code_repository: HandoffCodeRepository,
        handoff_ttl_seconds: int,
        clock: Clock | None = None,
        unit_of_work: UnitOfWork | None = None,
    ) -> None:
        self._provider_registry = provider_registry
        self._state_repository = state_repository
        self._identity_repository = identity_repository
        self._account_repository = account_repository
        self._handoff_code_repository = handoff_code_repository
        self._handoff_ttl_seconds = handoff_ttl_seconds
        self._clock = clock or SystemClock()
        self._unit_of_work = unit_of_work or NullUnitOfWork()

    async def execute(self, provider_name: str, code: str, state: str) -> str:
        provider = self._provider_registry.get(provider_name)
        now = self._clock.now()
        self._validate_state(await self._state_repository.consume(state), provider_name, now)
        identity = await self._fetch_identity(provider, code)
        email = self._normalize_email(identity.email)
        account_id = await self._resolve_account(provider_name, identity.subject, email, now)
        handoff = HandoffCode.generate(account_id, now, self._handoff_ttl_seconds)
        await self._handoff_code_repository.save(handoff)
        await self._unit_of_work.commit()
        return handoff.value

    def _validate_state(self, state, provider_name, now) -> None:
        # A None state covers all three of forged, missing and replayed: none of them
        # match a row this server minted and has not yet consumed.
        if state is None or not state.belongs_to(provider_name) or state.is_expired_at(now):
            raise OAuthCallbackError("the OAuth state did not validate")

    async def _fetch_identity(self, provider, code):
        try:
            return await provider.fetch_identity(code)
        except OAuthProviderError as error:
            raise OAuthCallbackError("the provider exchange failed") from error

    def _normalize_email(self, raw_email: str) -> str:
        try:
            return Email(raw_email).value
        except ValueError as error:
            raise OAuthCallbackError("the provider asserted an unusable email") from error

    async def _resolve_account(self, provider_name, subject, email, now) -> UUID:
        existing = await self._identity_repository.find(provider_name, subject)
        if existing is not None:
            return existing.account_id
        return await self._auto_create(provider_name, subject, email, now)

    async def _auto_create(self, provider_name, subject, email, now) -> UUID:
        # An email already owned by a password account is a hard stop, not a link: an
        # attacker who registered a victim's email as a password account must not have
        # an OAuth sign-in silently adopt it, and the reverse would let an OAuth login
        # hijack a real password account (invariant I8).
        if await self._account_repository.find_by_email(email) is not None:
            raise OAuthCallbackError("the email already belongs to a password account")
        account = Account.create(uuid4(), email, password_hash="", created_at=now)
        # The provider asserts the email, so the account is verified on creation —
        # there is no code to send and nothing for the user to confirm.
        account.verify()
        await self._account_repository.save(account)
        await self._identity_repository.save(
            OAuthIdentity.create(uuid4(), provider_name, subject, account.id, now)
        )
        return account.id
