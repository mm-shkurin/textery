from auth.oauth.oauth_leg_dependencies import OAuthLegDependencies
from auth.oauth_state import OAuthState


class StartOAuth(OAuthLegDependencies):
    """Leg 1: turn a click on the provider button into a redirect to that provider.

    Mints a server-side CSRF state, persists it, and hands back the provider's
    authorization URL carrying that state. The client never sees or supplies the
    state; only a value this server minted and stored will validate on the callback.
    """

    async def execute(self, provider_name: str, source: str = "") -> str:
        now = self._clock.now()
        await self._rate_guard.check("start", source, now)
        provider = self._provider_registry.get(provider_name)
        state = OAuthState.generate(provider_name, now)
        await self._state_repository.save(state)
        await self._unit_of_work.commit()
        return provider.authorization_url(state.value)
