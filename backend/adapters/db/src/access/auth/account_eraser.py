from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from model.auth.account_model import AccountModel
from model.auth.handoff_code_model import HandoffCodeModel
from model.auth.oauth_identity_model import OAuthIdentityModel
from model.auth.verification_code_model import VerificationCodeModel
from model.document.document_model import DocumentModel


class SqlAlchemyAccountEraser:
    """Deletes an account and every row that belongs to it, children first.

    THE ORDER IS NOT COSMETIC. Three of the child tables reference `accounts.id`
    with no `ondelete`, which is `NO ACTION`: `verification_codes`,
    `oauth_identities` and `oauth_handoff_codes`. Every verified account has a
    verification-code row, so a bare `DELETE FROM accounts` raises IntegrityError
    on essentially every real account.

    `documents.owner_id` carries NO foreign key at all. Nothing cascades from it
    and nothing ever will unless someone adds one, so the only thing that removes
    a deleted user's documents is the explicit statement below. Without it their
    text stays in the database forever, unreachable by any route and owned by
    nobody -- which is the opposite of what the user asked for.

    `generations.owner_id` is the one FK with `ondelete="CASCADE"`, so those rows
    go with the account and are deliberately absent from this method. (Their
    self-reference `source_generation_id` is `ON DELETE SET NULL`, which Postgres
    resolves within the same cascade.)

    `analytics_events.user_id` is the one FK with `ondelete="SET NULL"`, and it is
    absent from this method ON PURPOSE. Analytics rows SURVIVE account erasure with
    the account detached -- Postgres nulls the column as part of the delete below.
    That is a retention decision, not an oversight: Story 15's cohort figures need
    the rows (`stories/14-analytics-event-tracking/decisions/analytics-ingest-shape-decision.md`).
    It is also a deliberate departure from the convention this docstring describes,
    and it makes `DeleteAccount`'s "removes an account and everything that belongs
    to it" partially false -- the rows that remain belong to nobody and name nobody.

    `oauth_states` and `oauth_rate_limits` are NOT here and that is checked, not
    assumed: the first is keyed by the state value, the second by
    `(bucket_key, window_start)`. Neither carries an account id in any form, so
    neither has rows to remove.

    NO MIGRATION was added to give the three FKs `ON DELETE CASCADE`. Explicit
    deletes solve the problem without altering constraints on three tables of a
    populated database, and `documents` would need every existing row validated
    against `accounts` before it could take a foreign key at all -- a data-repair
    job, on the eve of a deadline, for an operation this method already performs
    correctly. If a later migration does add the constraints, the statements here
    become redundant rather than wrong.

    No commit: the caller owns the transaction, and it must be ONE transaction.
    A partial deletion is the worst available outcome -- an account whose
    documents are gone, or documents belonging to an account that no longer
    exists.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def erase(self, account_id: UUID) -> None:
        # 1. Children with no FK at all -- invisible to the database, visible only
        #    here.
        await self._session.execute(
            delete(DocumentModel).where(DocumentModel.owner_id == account_id)
        )
        # 2. Children whose FK is NO ACTION: they must be gone before the parent
        #    row can be, or Postgres refuses the delete.
        await self._session.execute(
            delete(VerificationCodeModel).where(VerificationCodeModel.account_id == account_id)
        )
        await self._session.execute(
            delete(OAuthIdentityModel).where(OAuthIdentityModel.account_id == account_id)
        )
        await self._session.execute(
            delete(HandoffCodeModel).where(HandoffCodeModel.account_id == account_id)
        )
        # 3. The account itself. `generations` follow by cascade.
        await self._session.execute(delete(AccountModel).where(AccountModel.id == account_id))
