"""The registration route's entry point for storing attribution.

A one-method usecase over `RegistrationContextRecorder`, which is where the work
actually is. It exists as a usecase because the register ROUTE needs something to
depend on and a controller depends on usecases; the recorder exists separately
because the OAuth callback needs the same behaviour and a usecase may not call
another usecase.

Never raises. See `registration_context_recorder.py` for why that is the whole
point rather than a convenience.
"""

from collections.abc import Mapping
from uuid import UUID

from analytics.registration_context import Geolocation, RegistrationContextWriter
from analytics.registration_context_recorder import RegistrationContextRecorder


class RecordRegistrationContext:
    def __init__(
        self,
        context_writer: RegistrationContextWriter | None = None,
        geolocation: Geolocation | None = None,
    ) -> None:
        self._recorder = RegistrationContextRecorder(context_writer, geolocation)

    async def execute(
        self,
        account_id: UUID,
        campaign_parameters: Mapping[str, object],
        client_ip: str | None,
        user_agent: str | None,
        accept_language: str | None,
    ) -> None:
        await self._recorder.record(
            account_id, campaign_parameters, client_ip, user_agent, accept_language
        )
