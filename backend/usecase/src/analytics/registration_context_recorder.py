"""Store what a new account's registration was worth to marketing.

Ten values on the account row: the five campaign parameters the link carried and
the five things the server itself observed. Called AFTER the registration has
already succeeded, and it cannot undo it -- there is no path out of `record` that
raises.

**A collaborator, not a usecase**, and deliberately so: two top-level operations
need it -- `POST /auth/register` through `RecordRegistrationContext`, and the
OAuth callback, which creates its account two redirects away from anything a
client can put in a body. A usecase may not call another usecase, so the shared
part is a plain object in this layer, the same shape `OAuthRateGuard` already
uses. It orchestrates no user-visible operation of its own.

That is the governing decision of this story made concrete: analytics adapts to
the application, the application is not changed for analytics. `RegisterUser` is
untouched by this file. A visitor who clicks a marketing link with a malformed
parameter, from a browser we cannot classify, behind a geolocation service that
is down, registers exactly as they would have before Story 14 existed.
"""

import logging
from collections.abc import Mapping
from uuid import UUID

from analytics.attribution import Attribution
from analytics.registration_context import (
    Geolocation,
    NullGeolocation,
    NullRegistrationContextWriter,
    RegistrationContextWriter,
)
from analytics.technical_context import TechnicalContext

logger = logging.getLogger(__name__)


class RegistrationContextRecorder:
    def __init__(
        self,
        context_writer: RegistrationContextWriter | None = None,
        geolocation: Geolocation | None = None,
    ) -> None:
        self._context_writer = context_writer or NullRegistrationContextWriter()
        self._geolocation = geolocation or NullGeolocation()

    async def record(
        self,
        account_id: UUID,
        campaign_parameters: Mapping[str, object],
        client_ip: str | None,
        user_agent: str | None,
        accept_language: str | None,
    ) -> None:
        """Never raises. See the module docstring."""
        try:
            await self._store(
                account_id, campaign_parameters, client_ip, user_agent, accept_language
            )
        except Exception as error:
            logger.warning("registration context was not recorded: %s", type(error).__name__)

    async def _store(
        self,
        account_id: UUID,
        campaign_parameters: Mapping[str, object],
        client_ip: str | None,
        user_agent: str | None,
        accept_language: str | None,
    ) -> None:
        attribution = Attribution.of(campaign_parameters)
        if attribution.is_empty and any(campaign_parameters.values()):
            # Not silent to US, only to the user. Without this line, an escaping
            # bug in a campaign builder would zero out attribution for a whole
            # channel with nothing to see. It names the outcome and no value:
            # the parameters are caller-controlled text, and a log is not a
            # place to widen who can read them (`03_Security_Tests.md` §3.5).
            logger.info("campaign parameters were discarded as a set; nothing stored")
        context = TechnicalContext.observed(
            client_ip=client_ip,
            country=await self._geolocation.country_of(client_ip),
            user_agent=user_agent,
            accept_language=accept_language,
        )
        await self._context_writer.record(
            account_id, {**attribution.as_columns(), **context.as_columns()}
        )
