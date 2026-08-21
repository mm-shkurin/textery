"""Builders shared by the retry-route suites, kept out of `conftest` on purpose.

`from conftest import ...` binds whichever conftest module landed on the import
path first, and this suite has three of them above it. A named sibling module
cannot be shadowed that way, and mypy can see it — `conftest.py` is excluded.
"""

from uuid import uuid4

from generation.generation import Generation

RETRY_KWARGS = {"generation_id", "owner_id", "idempotency_key", "text_style", "volume_pages"}


def a_retry(owner_id, volume_pages: int = 3, text_style: str | None = None) -> Generation:
    """A saved retry row, built through __init__ — the storage hydration path.

    Not through `retry_of`: this stands in for what the usecase RETURNS, and
    building it with the factory under test would make these assertions depend on
    the very resolution rule the domain suite owns.
    """
    seed = Generation.create(
        owner_id=owner_id,
        topic="Тема",
        volume_pages=3,
        requirements=None,
        extra_wishes=None,
        document_type="реферат",
    )
    return Generation(
        id=uuid4(),
        owner_id=owner_id,
        status="pending",
        created_at=seed.created_at,
        topic="Тема",
        volume_pages=volume_pages,
        requirements=None,
        extra_wishes=None,
        document_type="реферат",
        text_style=text_style,
        idempotency_key="key-1",
        source_generation_id=uuid4(),
    )
