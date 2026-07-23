from auth.oauth_state import OAuthState


class FakeOAuthStateRepository:
    """In-memory `OAuthStateRepository`. `consume` is remove-on-read, mirroring the
    real DELETE ... RETURNING, so a replayed state finds nothing the second time.
    """

    def __init__(self) -> None:
        self._by_value: dict[str, OAuthState] = {}
        self.consume_calls: list[str] = []

    async def save(self, state: OAuthState) -> None:
        self._by_value[state.value] = state

    async def consume(self, value: str) -> OAuthState | None:
        self.consume_calls.append(value)
        return self._by_value.pop(value, None)
