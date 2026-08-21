"""What a completed OAuth sign-in reports, once the sign-in itself is committed.

Extracted from `CompleteOAuthCallback` because it is a different job: the usecase
turns a provider redirect into a handoff code, and everything here happens after
that has already succeeded and may not affect it. Kept out of
`RecordRegistrationContext` for the rule's sake -- a usecase may not call another
usecase -- and out of the callback for the reader's: the callback's flow is now
readable without the analytics tail in the middle of it.
"""

from uuid import UUID

from analytics.analytics_recorder import AnalyticsRecorder, occurrence_of
from analytics.event_names import LOGIN_SUCCESS, REGISTRATION_COMPLETED
from analytics.oauth_attribution_parking import OAuthAttributionParking
from analytics.registration_context_recorder import RegistrationContextRecorder


class SignInAnalytics:
    def __init__(
        self,
        recorder: AnalyticsRecorder,
        registration_context: RegistrationContextRecorder,
        attribution_parking: OAuthAttributionParking,
    ) -> None:
        self._recorder = recorder
        self._registration_context = registration_context
        self._attribution_parking = attribution_parking

    async def record(
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
            await self._recorder.record(
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
        await self._recorder.record(event_name=LOGIN_SUCCESS, visitor_id=None, user_id=account_id)
