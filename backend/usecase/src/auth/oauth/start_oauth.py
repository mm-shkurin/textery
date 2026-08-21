from auth.oauth.oauth_leg_dependencies import OAuthLegDependencies
from auth.oauth_state import OAuthState


class StartOAuth(OAuthLegDependencies):
    """Leg 1: turn a click on the provider button into a redirect to that provider.

    Mints a server-side CSRF state, persists it, and hands back the provider's
    authorization URL carrying that state. The client never sees or supplies the
    state; only a value this server minted and stored will validate on the callback.
    """

    async def execute(
        self,
        provider_name: str,
        source: str = "",
        campaign_parameters: dict[str, str | None] | None = None,
    ) -> str:
        """`campaign_parameters` ride along and change NOTHING about the answer.

        This route answers 302/404/500 and has no 400 at all; Story 14 does not
        give it one. Parking cannot raise, an unusable parameter is dropped rather
        than refused, and the visitor is redirected to the provider exactly as they
        would have been. A broken marketing link must never end at a broken sign-in.

        The parameters are parked, never forwarded: the provider is handed the
        state value and nothing else.
        """
        now = self._clock.now()
        await self._rate_guard.check("start", source, now)
        provider = self._provider_registry.get(provider_name)
        state = OAuthState.generate(provider_name, now)
        await self._state_repository.save(state)
        await self._unit_of_work.commit()
        # AFTER the commit: the parked campaign is keyed on a state value that has
        # to exist first, and a row parked against a state whose transaction then
        # rolled back would outlive the handshake it belongs to.
        await self._attribution_parking.park(state.value, campaign_parameters or {})
        return provider.authorization_url(state.value)
