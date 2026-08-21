from datetime import datetime
from uuid import UUID, uuid4

from analytics.analytics_recorder import AnalyticsRecorder, NullAnalyticsRecorder, occurrence_of
from analytics.event_names import LOGIN_SUCCESS, REGISTRATION_COMPLETED
from analytics.oauth_attribution_parking import OAuthAttributionParking
from analytics.registration_context_recorder import RegistrationContextRecorder
from auth.account import Account
from auth.account_repository import AccountRepository
from auth.email import Email
from auth.handoff_code import HandoffCode
from auth.oauth.handoff_code_repository import HandoffCodeRepository
from auth.oauth.oauth_error_codes import OAuthCallbackError
from auth.oauth.oauth_identity_repository import OAuthIdentityRepository
from auth.oauth.oauth_leg_dependencies import OAuthLegDependencies
from auth.oauth.oauth_provider import OAuthProvider, OAuthProviderError, ProviderIdentity
from auth.oauth.oauth_state_repository import OAuthStateRepository
from auth.oauth.provider_registry import ProviderRegistry
from auth.oauth.rate_limiter import OAuthRateGuard
from auth.oauth_identity import OAuthIdentity
from auth.oauth_state import OAuthState
from shared.clock import Clock
from shared.unit_of_work import UnitOfWork


class CompleteOAuthCallback(OAuthLegDependencies):
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
        rate_guard: OAuthRateGuard | None = None,
        attribution_parking: OAuthAttributionParking | None = None,
        analytics_recorder: AnalyticsRecorder | None = None,
        registration_context: RegistrationContextRecorder | None = None,
    ) -> None:
        super().__init__(
            provider_registry,
            state_repository,
            clock,
            unit_of_work,
            rate_guard,
            attribution_parking,
        )
        self._identity_repository = identity_repository
        self._account_repository = account_repository
        self._handoff_code_repository = handoff_code_repository
        self._handoff_ttl_seconds = handoff_ttl_seconds
        self._analytics_recorder = analytics_recorder or NullAnalyticsRecorder()
        # A collaborator, NOT the `RecordRegistrationContext` usecase: a usecase may
        # not call another usecase, and this leg genuinely needs the same behaviour
        # the register route does -- it is the only other place an account is born.
        self._registration_context = registration_context or RegistrationContextRecorder()

    async def execute(
        self,
        provider_name: str,
        code: str,
        state: str,
        source: str = "",
        client_ip: str | None = None,
        user_agent: str | None = None,
        accept_language: str | None = None,
    ) -> str:
        """The three request facts are parameters because `/callback` is itself a
        browser request: IP, User-Agent and `Accept-Language` are present here
        exactly as they are at `/register`, so a provider-created account carries
        the same technical context as a registered one. They are never accepted
        from a query parameter -- the provider drives this redirect, and a value a
        client could set is a value it could fabricate.
        """
        now = self._clock.now()
        await self._rate_guard.check("callback", source, now)
        provider = self._provider_registry.get(provider_name)
        self._validate_state(await self._state_repository.consume(state), provider_name, now)
        identity = await self._fetch_identity(provider, code)
        email = self._normalize_email(identity.email)
        existing = await self._identity_repository.find(provider_name, identity.subject)
        account_id = (
            existing.account_id
            if existing is not None
            else await self._auto_create(provider_name, identity.subject, email, now)
        )
        handoff = HandoffCode.generate(account_id, now, self._handoff_ttl_seconds)
        await self._handoff_code_repository.save(handoff)
        await self._unit_of_work.commit()
        await self._record_sign_in(
            account_id,
            is_new_account=existing is None,
            state_value=state,
            client_ip=client_ip,
            user_agent=user_agent,
            accept_language=accept_language,
        )
        return handoff.value

    async def _record_sign_in(
        self,
        account_id: UUID,
        is_new_account: bool,
        state_value: str,
        client_ip: str | None,
        user_agent: str | None,
        accept_language: str | None,
    ) -> None:
        """A FIRST sign-in through a provider is two events; a later one is one.

        Both are emitted after the commit, so neither can name an account the
        transaction went on to roll back. The registration's occurrence key is
        derived from the account, so two callbacks racing the same first sign-in
        still record one registration.

        The technical context and the parked campaign are stored only for a new
        account: rewriting them on every sign-in would move an existing account's
        first-touch attribution to whichever link its owner happened to click last,
        which is the exact opposite of what a first-touch model means.
        """
        if is_new_account:
            await self._analytics_recorder.record(
                event_name=REGISTRATION_COMPLETED,
                visitor_id=None,
                user_id=account_id,
                occurrence_key=occurrence_of(REGISTRATION_COMPLETED, account_id),
            )
            await self._registration_context.record(
                account_id,
                await self._attribution_parking.take(state_value),
                client_ip,
                user_agent,
                accept_language,
            )
        await self._analytics_recorder.record(
            event_name=LOGIN_SUCCESS, visitor_id=None, user_id=account_id
        )

    def _validate_state(self, state: OAuthState | None, provider_name: str, now: datetime) -> None:
        # A None state covers all three of forged, missing and replayed: none of them
        # match a row this server minted and has not yet consumed.
        if state is None or not state.belongs_to(provider_name) or state.is_expired_at(now):
            raise OAuthCallbackError("the OAuth state did not validate")

    async def _fetch_identity(self, provider: OAuthProvider, code: str) -> ProviderIdentity:
        try:
            return await provider.fetch_identity(code)
        except OAuthProviderError as error:
            raise OAuthCallbackError("the provider exchange failed") from error

    def _normalize_email(self, raw_email: str) -> str:
        try:
            return Email(raw_email).value
        except ValueError as error:
            raise OAuthCallbackError("the provider asserted an unusable email") from error

    async def _auto_create(
        self, provider_name: str, subject: str, email: str, now: datetime
    ) -> UUID:
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
