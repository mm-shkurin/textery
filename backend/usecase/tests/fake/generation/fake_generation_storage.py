import copy
from datetime import datetime
from uuid import UUID

from fake.generation.call_order_recording_fake import CallOrderRecordingFake
from generation.generation import Generation
from shared.keyset_cursor import KeysetCursor

CALL_SAVE = "save"
CALL_GET = "get_by_id_and_owner"
CALL_UPDATE = "update"
CALL_LIST_STALE = "list_stale"
CALL_LIST_BY_OWNER = "list_by_owner"
CALL_FIND_BY_IDEMPOTENCY_KEY = "find_by_owner_and_idempotency_key"
CALL_COUNT_RETRIES = "count_retries_of"


class FakeGenerationStorage(CallOrderRecordingFake):
    def __init__(self, call_order: list) -> None:
        super().__init__(call_order)
        self.saved_generations: list[Generation] = []
        self.updated_generations: list[Generation] = []
        self._by_id: dict[UUID, Generation] = {}
        # id -> exception update() should raise once for that row, letting a test
        # stage a lost CAS race without needing two real sessions.
        self.raise_on_update_for: dict[UUID, Exception] = {}

    async def save(self, generation: Generation) -> None:
        self._record(CALL_SAVE, generation)
        self.saved_generations.append(generation)
        self._by_id[generation.id] = generation

    async def get_by_id_and_owner(self, generation_id: UUID, owner_id: UUID) -> Generation | None:
        self._record(CALL_GET, generation_id)
        # The owner predicate is mirrored, not ignored: a fake that returned the row
        # on id alone would keep every ownership test green against a storage that
        # had lost its WHERE clause -- the exact bug this whole change closes.
        generation = self._by_id.get(generation_id)
        if generation is None or generation.owner_id != owner_id:
            return None
        return generation

    async def update(self, generation: Generation) -> None:
        self._record(CALL_UPDATE, generation)
        # Mirrors the real adapter's CAS: it raises when another writer already
        # claimed the row (ConflictException) or the row is gone
        # (NotFoundException). Both are outcomes a caller must handle, so the fake
        # has to be able to produce them.
        error = self.raise_on_update_for.pop(generation.id, None)
        if error is not None:
            raise error
        # generation is mutated in place by the usecase after each update() call
        # (mark_in_progress -> update -> complete/fail -> update); snapshot the
        # status at call time so assertions can see the intermediate state.
        self.updated_generations.append(copy.deepcopy(generation))
        self._by_id[generation.id] = generation

    async def list_by_owner(
        self, owner_id: UUID, limit: int, cursor: KeysetCursor | None
    ) -> list[Generation]:
        """Newest first, owner-scoped, anchored strictly after `cursor`.

        Same shape as FakeDocumentRepository.list_by_owner, and mirrored from the
        real adapter for the same reason the owner predicate above is: a fake that
        returned insertion order would keep a usecase that never trimmed the
        has-next probe row green.
        """
        self._record(CALL_LIST_BY_OWNER, owner_id)
        rows = sorted(
            (g for g in self._by_id.values() if g.owner_id == owner_id),
            key=lambda g: (g.created_at, g.id),
            reverse=True,
        )
        if cursor is not None:
            rows = [g for g in rows if (g.created_at, g.id) < (cursor.created_at, cursor.id)]
        return rows[:limit]

    async def find_by_owner_and_idempotency_key(
        self, owner_id: UUID, idempotency_key: str
    ) -> Generation | None:
        """Owner-scoped, mirroring the port's own reason for being owner-scoped.

        Implemented rather than omitted: the port has carried this method since
        the retry path landed, and a double missing it is not a stand-in for the
        storage -- the usecase reaches it through structural typing, so the gap
        stays invisible until a test wires this fake into the one usecase that
        calls it. Keying on the pair and not on the key alone is the same rule the
        real adapter follows: a key-only lookup returns another account's row on
        the replay path, which short-circuits before any ownership check runs.
        """
        self._record(CALL_FIND_BY_IDEMPOTENCY_KEY, idempotency_key)
        return next(
            (
                generation
                for generation in self._by_id.values()
                if generation.owner_id == owner_id and generation.idempotency_key == idempotency_key
            ),
            None,
        )

    async def count_retries_of(self, source_generation_id: UUID) -> int:
        """Counted over the stored rows, as the real adapter counts them in SQL.

        Not a settable integer: a fake returning a staged number would keep a
        usecase green that had stopped writing `source_generation_id` at all, and
        the retry ceiling it guards would then bound nothing.
        """
        self._record(CALL_COUNT_RETRIES, source_generation_id)
        return sum(
            1
            for generation in self._by_id.values()
            if generation.source_generation_id == source_generation_id
        )

    def seed(self, generation: Generation) -> None:
        self._by_id[generation.id] = generation

    async def list_stale(self, older_than: datetime) -> list[Generation]:
        self._record(CALL_LIST_STALE, older_than)
        return [
            generation
            for generation in self._by_id.values()
            if generation.status in ("pending", "in_progress")
            and generation.created_at < older_than
        ]
