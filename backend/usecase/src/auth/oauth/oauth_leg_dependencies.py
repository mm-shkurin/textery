"""The port preamble shared by the two OAuth legs.

`StartOAuth` and `CompleteOAuthCallback` are separate top-level usecases -- neither
calls the other -- but both legs of one redirect dance need the same registry, the
same state store, the same clock, the same transaction boundary and the same rate
guard, and both must default the optional three identically or leg 2 validates a
state leg 1 minted against a different clock. This base is NOT a usecase: it has
no `execute` and declares no behaviour, only the wiring, in the same layer.
"""

from analytics.oauth_attribution_parking import (
    NullOAuthAttributionParking,
    OAuthAttributionParking,
)
from auth.oauth.oauth_state_repository import OAuthStateRepository
from auth.oauth.provider_registry import ProviderRegistry
from auth.oauth.rate_limiter import OAuthRateGuard
from shared.clock import Clock, SystemClock
from shared.unit_of_work import NullUnitOfWork, UnitOfWork


class OAuthLegDependencies:
    """Holds the collaborators both OAuth legs share."""

    def __init__(
        self,
        provider_registry: ProviderRegistry,
        state_repository: OAuthStateRepository,
        clock: Clock | None = None,
        unit_of_work: UnitOfWork | None = None,
        rate_guard: OAuthRateGuard | None = None,
        attribution_parking: OAuthAttributionParking | None = None,
    ) -> None:
        self._provider_registry = provider_registry
        self._state_repository = state_repository
        self._clock = clock or SystemClock()
        self._unit_of_work = unit_of_work or NullUnitOfWork()
        self._rate_guard = rate_guard or OAuthRateGuard()
        # On the base rather than on each leg, for the reason this base exists: leg
        # 1 parks against the state value and leg 2 takes it back by that same
        # value, so the two must default identically or the campaign is written by
        # one and invisible to the other.
        self._attribution_parking = attribution_parking or NullOAuthAttributionParking()
