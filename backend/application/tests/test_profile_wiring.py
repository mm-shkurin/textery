"""Every `/auth/me` write must be handed a REAL UnitOfWork on the repository's session.

The defect this pins has no symptom. `NullUnitOfWork.commit()` returns `None`
without touching the transaction, so a usecase constructed without a UnitOfWork
answers 200 -- with the new name, the fresh avatar timestamp, or a 204 for a
deletion -- while `request_scoped` closes the session and discards every
statement. No exception, no log, and no failing usecase test, because the fakes
commit nothing either.

Session identity alone cannot catch it: a `NullUnitOfWork` never touches a
session, so the concrete TYPE has to be asserted too. Both halves are below, per
factory. `test_login_wiring.py` exists because this already happened once.
"""

import pytest
from wiring_support import wired_on_one_session

from container.auth_wiring import (
    create_delete_account,
    create_delete_avatar,
    create_get_avatar,
    create_get_profile,
    create_rename_account,
    create_update_avatar,
)
from session import SqlAlchemyUnitOfWork

_WRITE_FACTORIES = [
    pytest.param(create_rename_account, ["account_repository"], id="rename_account"),
    pytest.param(
        create_update_avatar, ["account_repository", "avatar_repository"], id="update_avatar"
    ),
    pytest.param(
        create_delete_avatar, ["account_repository", "avatar_repository"], id="delete_avatar"
    ),
    pytest.param(
        create_delete_account, ["account_repository", "account_eraser"], id="delete_account"
    ),
]


class TestEveryProfileWriteCommitsForReal:
    @pytest.mark.parametrize(("factory", "collaborators"), _WRITE_FACTORIES)
    async def test_should_wire_a_real_unit_of_work(self, factory, collaborators):  # noqa: ARG002 -- port shape
        async with wired_on_one_session(factory) as (usecase, _):
            assert isinstance(usecase.unit_of_work, SqlAlchemyUnitOfWork), (
                f"expected {factory.__name__} to wire a real SqlAlchemyUnitOfWork so the "
                f"write is committed rather than silently discarded, got "
                f"{usecase.unit_of_work!r}"
            )

    @pytest.mark.parametrize(("factory", "collaborators"), _WRITE_FACTORIES)
    async def test_should_put_the_unit_of_work_on_the_same_session_as_every_collaborator(
        self, factory, collaborators
    ):
        async with wired_on_one_session(factory) as (usecase, sentinel_session):
            assert usecase.unit_of_work._session is sentinel_session, (
                "expected the UnitOfWork to share the wiring's single session so the "
                "write and its commit are one transaction"
            )
            for name in collaborators:
                collaborator_session = getattr(usecase, name)._session
                assert collaborator_session is sentinel_session, (
                    f"expected {name} to be backed by the wiring's single session, got "
                    f"a different object {collaborator_session!r}"
                )


class TestTheReadsShareTheirSessionToo:
    async def test_get_profile_reads_through_the_wirings_session(self):
        async with wired_on_one_session(create_get_profile) as (usecase, sentinel_session):
            assert usecase.account_repository._session is sentinel_session

    async def test_get_avatar_reads_through_the_wirings_session(self):
        # No UnitOfWork on this one, and that is correct: it only reads.
        async with wired_on_one_session(create_get_avatar) as (usecase, sentinel_session):
            assert usecase.avatar_repository._session is sentinel_session
            assert not hasattr(usecase, "unit_of_work")
