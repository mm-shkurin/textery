from datetime import datetime
from uuid import UUID, uuid4

from analytics.analytics_recorder import AnalyticsRecorder, NullAnalyticsRecorder
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
from auth.oauth.oauth_sign_in_analytics import SignInAnalytics
from auth.oauth.oauth_state_repository import OAuthStateRepository
from auth.oauth.provider_registry import ProviderRegistry
from auth.oauth.rate_limiter import OAuthRateGuard
from auth.oauth_identity import OAuthIdentity
from auth.oauth_state import OAuthState
from shared.clock import Clock
from shared.unit_of_work import UnitOfWork


def _sign_in_analytics(
    recorder: AnalyticsRecorder | None,
    registration_context: RegistrationContextRecorder | None,
    attribution_parking: OAuthAttributionParking,
) -> SignInAnalytics:
    """The analytics tail, with its two optional collaborators defaulted.

    A function rather than four more lines in an already long `__init__`: the
    defaulting is one decision (an unwired deployment records nothing rather than
    failing), and it reads better stated once than interleaved with the assignments
    that make up the rest of the constructor.
    """
    return SignInAnalytics(
        recorder=recorder or NullAnalyticsRecorder(),
        registration_context=registration_context or RegistrationContextRecorder(),
        attribution_parking=attribution_parking,
    )


class CompleteOAuthCallback(OAuthLegDependencies):
    """Leg 2: validate the provider's redirect and mint a one-time handoff code.

    Consumes the CSRF state, exchanges the provider code for an asserted identity,
    resolves or auto-creates the local account, and returns an opaque handoff code.
    Every failure raises `OAuthCallbackError`, which the controller renders as a
    single generic `?error=` — no leg's failure is distinguishable to the client.

    `SignInAnalytics` is built from collaborators rather than by calling the
    `RecordRegistrationContext` usecase: a usecase may not call another usecase,
    and this leg genuinely needs the same behaviour the register route does — it
    is the only other place an account is born.

    `execute` takes IP, User-Agent and `Accept-Language` as parameters because
    `/callback` is itself a browser request: they are present here exactly as they
    are at `/register`, so a provider-created account carries the same technical
    context as a registered one. They are never accepted from a query parameter —
    the provider drives this redirect, and a value a client could set is a value
    it could fabricate.
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
        self._sign_in_analytics = _sign_in_analytics(
            analytics_recorder, registration_context, self._attribution_parking
        )

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
        """Turn the provider's redirect into a handoff code. See the class docstring."""
        now = self._clock.now()
        await self._rate_guard.check("callback", source, now)
        provider = self._provider_registry.get(provider_name)
        self._validate_state(await self._state_repository.consume(state), provider_name, now)
        identity = await self._fetch_identity(provider, code)
        existing = await self._identity_repository.find(provider_name, identity.subject)
        account_id = await self._account_behind(existing, provider_name, identity, now)
        handoff = await self._issued_handoff(account_id, now)
        await self._sign_in_analytics.record(
            account_id,
            is_new_account=existing is None,
            state_value=state,
            client_ip=client_ip,
            user_agent=user_agent,
            accept_language=accept_language,
        )
        return handoff.value

    async def _account_behind(
        self,
        existing: OAuthIdentity | None,
        provider_name: str,
        identity: ProviderIdentity,
        now: datetime,
    ) -> UUID:
        """The account this provider identity belongs to, creating it on first sight."""
        if existing is not None:
            return existing.account_id
        return await self._auto_create(
            provider_name, identity.subject, self._normalize_email(identity.email), now
        )

    async def _issued_handoff(self, account_id: UUID, now: datetime) -> HandoffCode:
        """The one-time code the browser carries back, committed before it is answered.

        Committed here rather than at the end of `execute`: everything after this
        point is analytics, and an analytics failure must not be able to undo a
        sign-in that has already produced a code.
        """
        handoff = HandoffCode.generate(account_id, now, self._handoff_ttl_seconds)
        await self._handoff_code_repository.save(handoff)
        await self._unit_of_work.commit()
        return handoff

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
