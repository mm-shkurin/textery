from auth.oauth.oauth_state_repository import OAuthStateRepository
from auth.oauth.provider_registry import ProviderRegistry
from auth.oauth_state import OAuthState
from shared.clock import Clock, SystemClock
from shared.unit_of_work import NullUnitOfWork, UnitOfWork


class StartOAuth:
    """Leg 1: turn a click on the provider button into a redirect to that provider.

    Mints a server-side CSRF state, persists it, and hands back the provider's
    authorization URL carrying that state. The client never sees or supplies the
    state; only a value this server minted and stored will validate on the callback.
    """

    def __init__(
        self,
        provider_registry: ProviderRegistry,
        state_repository: OAuthStateRepository,
        clock: Clock | None = None,
        unit_of_work: UnitOfWork | None = None,
    ) -> None:
        self._provider_registry = provider_registry
        self._state_repository = state_repository
        self._clock = clock or SystemClock()
        self._unit_of_work = unit_of_work or NullUnitOfWork()

    async def execute(self, provider_name: str) -> str:
        provider = self._provider_registry.get(provider_name)
        state = OAuthState.generate(provider_name, self._clock.now())
        await self._state_repository.save(state)
        await self._unit_of_work.commit()
        return provider.authorization_url(state.value)
