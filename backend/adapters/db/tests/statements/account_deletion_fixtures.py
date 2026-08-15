"""Seeding and row-counting for the deletion tests.

Split from `account_deletion_statements` for the 200-line cap. The seed builds an
account with a row in EVERY table that references an account, because the point
of the deletion tests is coverage of the whole graph -- a fixture that skipped
`documents` would leave the one table with no foreign key untested, which is the
table most likely to be forgotten.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from access.auth.account_storage import SqlAlchemyAccountRepository
from auth.account import Account
from model.auth.account_model import AccountModel
from model.auth.oauth_identity_model import OAuthIdentityModel
from model.auth.verification_code_model import VerificationCodeModel
from model.document.document_model import DocumentModel
from model.generation.generation_model import GenerationModel

PASSWORD_HASH = "hashed-password-value"

# The five tables that can hold a row belonging to one account. `oauth_states` and
# `oauth_rate_limits` are absent because neither carries an account id in any form
# -- the first is keyed by the state value, the second by (bucket_key,
# window_start). Checked in the models, not assumed.
TABLES = (
    "accounts",
    "verification_codes",
    "oauth_identities",
    "generations",
    "documents",
)


def all_zero() -> dict[str, int]:
    return dict.fromkeys(TABLES, 0)


def all_one() -> dict[str, int]:
    return dict.fromkeys(TABLES, 1)


async def seed_full_account(session_factory: async_sessionmaker[AsyncSession]) -> UUID:
    """One verified account with a verification code, an OAuth identity, a
    generation and a document -- one row in every table that references it."""
    account_id = uuid4()
    now = datetime.now(UTC)
    account = Account.reconstitute(
        id=account_id,
        # Per-run-unique: uq_accounts_email would collide on a rerun against the
        # persistent test database.
        email=f"deletion-{account_id}@example.com",
        password_hash=PASSWORD_HASH,
        created_at=now,
        is_verified=True,
    )
    async with session_factory() as session:
        await SqlAlchemyAccountRepository(session).save(account)
        session.add(
            VerificationCodeModel(
                id=uuid4(),
                account_id=account_id,
                code="123456",
                created_at=now,
                expires_at=now + timedelta(minutes=15),
                consumed_at=None,
            )
        )
        session.add(
            OAuthIdentityModel(
                id=uuid4(),
                provider="yandex",
                subject=f"subject-{account_id}",
                account_id=account_id,
                created_at=now,
            )
        )
        session.add(
            GenerationModel(
                id=uuid4(),
                owner_id=account_id,
                topic="Космос",
                volume_pages=3,
                document_type="доклад",
                status="pending",
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            DocumentModel(
                id=uuid4(),
                owner_id=account_id,
                document_type="доклад",
                # Real text, because this is what the user asked to have removed.
                content="Текст пользователя",
                status="draft",
                version=1,
                idempotency_key=str(uuid4()),
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()
    return account_id


async def count_every_table(
    session_factory: async_sessionmaker[AsyncSession], account_id: UUID
) -> dict[str, int]:
    async with session_factory() as session:
        return {
            "accounts": await _count(session, AccountModel, AccountModel.id, account_id),
            "verification_codes": await _count(
                session, VerificationCodeModel, VerificationCodeModel.account_id, account_id
            ),
            "oauth_identities": await _count(
                session, OAuthIdentityModel, OAuthIdentityModel.account_id, account_id
            ),
            "generations": await _count(
                session, GenerationModel, GenerationModel.owner_id, account_id
            ),
            "documents": await _count(session, DocumentModel, DocumentModel.owner_id, account_id),
        }


async def _count(session: AsyncSession, model, column, account_id: UUID) -> int:
    result = await session.execute(
        select(func.count()).select_from(model).where(column == account_id)
    )
    return int(result.scalar_one())
