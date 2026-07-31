"""Static shape guards for the AI-edit storage adapter (Scenario 1.2).

Split out of `ai_edit_storage_statements` because none of this touches a session,
a row, or the database: it is introspection over two production symbols. Keeping
it here lets its tests take a fixture that opens no connection, and leaves the
storage DSL to the behaviour it actually seeds and reads.
"""

import inspect
from inspect import Parameter

from document_edit.ai_edit_repository import AiEditRepository

from access.document_edit.ai_edit_storage import SqlAlchemyAiEditStorage

FINDER_NAME = "find_scope_by_id_and_document"

# The finder's signature in full, hand-written, positionally exact -- not a lookup
# of the two names this scenario cares about. Checking only `edit_id`/`document_id`
# widens with the module it guards: an adapter that grew a third same-typed UUID
# parameter positionally would still pass a per-name kind check, which is the very
# transposition hazard the keyword-only rule exists to close. Same lesson as 1.1's
# `dataclasses.fields(DocumentScope)`. Read off the unbound function, hence `self`.
EXPECTED_FINDER_SIGNATURE = [
    ("self", Parameter.POSITIONAL_OR_KEYWORD),
    ("edit_id", Parameter.KEYWORD_ONLY),
    ("document_id", Parameter.KEYWORD_ONLY),
]


def _signature_shape(function) -> list[tuple[str, object]]:
    """The function's parameters as `(name, kind)` pairs, in declaration order.

    The comparable form of `EXPECTED_FINDER_SIGNATURE` above -- order included,
    because position is half of what the keyword-only rule is pinning.
    """
    return [
        (name, parameter.kind)
        for name, parameter in inspect.signature(function).parameters.items()
    ]


class AiEditPortShapeStatements:
    """DSL for the adapter's structural obligations to `AiEditRepository`."""

    def assert_the_scoping_ids_are_keyword_only(self) -> None:
        """Both same-typed UUIDs, on the port *and* on the shipped adapter.

        Two UUIDs in a row transpose silently: a positional adapter that binds the
        pair the other way round type-checks, returns `None` for every owner's own
        edit, and leaves the usecase suite green because it runs against the fake.
        The rule has to hold at the boundary it guards, not one frame short of it.
        """
        for owner, function in (
            ("AiEditRepository", getattr(AiEditRepository, FINDER_NAME)),
            (
                SqlAlchemyAiEditStorage.__name__,
                getattr(SqlAlchemyAiEditStorage, FINDER_NAME),
            ),
        ):
            actual = _signature_shape(function)
            assert actual == EXPECTED_FINDER_SIGNATURE, (
                f"{owner}.{FINDER_NAME} must declare exactly "
                f"{EXPECTED_FINDER_SIGNATURE} -- both scoping ids keyword-only "
                f"(a leading `*`) and no other parameter -- got {actual}"
            )

    def assert_the_storage_satisfies_the_port_structurally(self) -> None:
        """The `raise NotImplementedError` body can never fire for this adapter.

        `SqlAlchemyDocumentStorage` satisfies `DocumentRepository` structurally,
        and this one will too -- so the port's raising bodies, which exist to make
        a forgotten method loud, protect nothing here. What actually has to be
        true is that the method is defined *on this class*, not inherited.
        """
        name = SqlAlchemyAiEditStorage.__name__
        assert AiEditRepository not in SqlAlchemyAiEditStorage.__mro__, (
            f"{name} must satisfy AiEditRepository structurally, as "
            "SqlAlchemyDocumentStorage does -- inheriting the Protocol makes every "
            "unimplemented method a concrete body this suite would never notice."
        )
        assert FINDER_NAME in vars(SqlAlchemyAiEditStorage), (
            f"{name} must define {FINDER_NAME} itself; nothing else in "
            "this codebase makes a missing implementation visible at runtime."
        )
        assert inspect.iscoroutinefunction(getattr(SqlAlchemyAiEditStorage, FINDER_NAME)), (
            f"{name}.{FINDER_NAME} must be `async def` -- the port is "
            "awaited, and a plain `def` returning a value would await it as a non-awaitable."
        )
