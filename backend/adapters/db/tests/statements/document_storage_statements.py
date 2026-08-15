import ast
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text

from document.document import Document
from statements.document_core_statements import DocumentCoreStatements
from statements.page_settings_fakes import configured_page_settings


class DocumentStorageStatements(DocumentCoreStatements):
    """DSL for the document storage adapter's tests -- the arrange and act half.

    The entry point every test fixture builds, and the end of a four-link chain:
    `DocumentRowAssertions` <- `DocumentPageSettingsAssertions` <-
    `DocumentStorageAssertions` <- `DocumentCoreStatements` <- this. Inherited
    rather than delegated at every link so all of it stays reachable as
    `document_storage_statements.<verb>`, and split at all only to keep each file
    under the 200-line cap.

    What this link itself owns is scenario 2.1: seeding the `page_settings`
    column, and reading it back by the three routes the guards need -- through the
    mapper, raw from Postgres, and out of the migration script.
    """

    async def given_a_configured_document(self, owner_id: UUID) -> Document:
        """A row whose `page_settings` column holds a full nine-key object.

        Seeded in raw SQL rather than through `save_new`, deliberately. Scenario
        2.1 is the READ path; routing the seed through the mapper's write half
        would let a mapper that is symmetrically wrong in both directions --
        writing and reading the same six keys, say -- round-trip its own mistake
        and report green. The blob is derived from the value object with
        `asdict`, not hand-written, so `page_settings_fakes` stays the single
        place that says what "configured" means.

        The fake is sourced here rather than passed in by the test. It was being
        called twice at the call site -- once to seed and once as the expectation
        -- which put a non-DSL factory in the test body for no gain: there is one
        configured object in this story and both halves must be the same one.
        `assert_page_settings_round_tripped` reads the same factory for its
        expectation, so the two halves cannot drift.
        """
        document = await self.given_a_saved_document(owner_id)
        await self._seed_stored_page_settings(
            document.id, json.dumps(asdict(configured_page_settings()))
        )
        return document

    async def given_a_document_configured_to_nothing(self, owner_id: UUID) -> Document:
        """A row whose column holds an empty *configured* object, not SQL NULL.

        The `"{}"` storage-format literal lives here rather than in the test body:
        it is how the blob is spelled on the wire to Postgres, which is a fact
        about storage, not about what the test is asserting.
        """
        document = await self.given_a_saved_document(owner_id)
        await self._seed_stored_page_settings(document.id, "{}")
        return document

    async def _seed_stored_page_settings(self, document_id: UUID, blob: str | None) -> None:
        await self._session.execute(
            text("UPDATE documents SET page_settings = CAST(:blob AS jsonb) WHERE id = :id"),
            {"blob": blob, "id": document_id},
        )

    async def stored_page_settings_column(self, document_id: UUID) -> Any:
        """The column exactly as Postgres holds it -- SQL NULL comes back as None.

        Read in raw SQL on purpose: the mapper is the thing under test in the
        sibling guard, so asking it what the column contains would be circular.
        """
        result = await self._session.execute(
            text("SELECT page_settings FROM documents WHERE id = :id"),
            {"id": document_id},
        )
        return result.scalar_one()

    async def page_settings_column_shape(self) -> tuple[str, str, str | None] | None:
        """`(data_type, is_nullable, column_default)` for the column, or None if absent."""
        result = await self._session.execute(
            text(
                "SELECT data_type, is_nullable, column_default FROM information_schema.columns "
                "WHERE table_name = 'documents' AND column_name = 'page_settings'"
            )
        )
        row = result.first()
        return (row[0], row[1], row[2]) if row else None

    def page_settings_migration_upgrades(self) -> list[str]:
        """The `upgrade()` source of EVERY revision that mentions `documents.page_settings`.

        Read from the revision scripts because the property under guard -- "this
        migration writes nothing into rows that already exist" -- is not observable
        in the database the suite connects to. That database is already at head, so
        every row any test can create post-dates the migration, and a data backfill
        is invisible to every query. Re-running the migration against a populated
        table would mean driving alembic through a downgrade on a database this
        suite shares across tests, dropping a column out from under whatever else
        is running.

        Every revision, not the first. The earlier form returned the first match in
        `sorted(versions.glob("*.py"))` and stopped -- but revision filenames here
        are hand-chosen hex, so alphabetical order says nothing about lineage. A
        backfill living in a second revision (an index, a type fix, a "seed the
        preset" follow-up) was never parsed at all, and the guard reported green
        on the additive one it happened to read first.
        """
        versions = Path(__file__).resolve().parents[2] / "migrations" / "versions"
        upgrades = []
        for revision in sorted(versions.glob("*.py")):
            source = revision.read_text(encoding="utf-8")
            if "page_settings" not in source:
                continue
            upgrade = self._upgrade_source_in(source)
            if upgrade is not None:
                upgrades.append(upgrade)
        return upgrades

    @staticmethod
    def _upgrade_source_in(source: str) -> str | None:
        """The text of the top-level `upgrade()` in one revision file, if it has one.

        Split from the search above because that method was doing two things at
        once: deciding WHICH revision is the page-settings one, and digging
        `upgrade()` out of a file. The second is an AST walk whose mechanics say
        nothing about page settings, and inlining it put a three-clause generator
        predicate inside the loop body.

        Returning None rather than raising when there is no `upgrade()` keeps the
        caller's behaviour: such a revision is skipped and the search continues to
        the next file, rather than the whole lookup reporting "no migration".
        """
        upgrade = next(
            (
                node
                for node in ast.parse(source).body
                if isinstance(node, ast.FunctionDef) and node.name == "upgrade"
            ),
            None,
        )
        return ast.get_source_segment(source, upgrade) if upgrade is not None else None

    async def page_settings_read_outcome(
        self, document_id: UUID, owner_id: UUID
    ) -> tuple[str, str]:
        """What reading this row's page settings *does*, as a comparable token.

        The `try` is not defensive coding. `PageSettings` has nine required fields
        and `from_stored` belongs to 2.3/2.4, so there is no domain value that can
        hold a stored `{}` today and the read may legitimately raise. This method
        may therefore not presuppose a return value.

        It catches `TypeError`/`ValueError` ONLY -- the two a nine-required-field
        constructor raises when handed an empty mapping. A bare `except Exception`
        was laundering every other failure into a token: an `AttributeError` from a
        genuine mapper bug, a SQLAlchemy error from an unrelated column, a mistyped
        DSL call, all came back as `("raised", ...)` and the assertion, which only
        required the two tokens to differ, went green on them. Everything outside
        those two now propagates and fails the test as the error it is.

        Which of the admissible tokens is correct is settled by
        `ADMISSIBLE_EMPTY_OBJECT_OUTCOMES` on the assertion side. The classification
        here is only the read's raw shape; the judgement is not made in this method.
        """
        try:
            document = await self.find_by_id_and_owner(document_id, owner_id)
        except (TypeError, ValueError) as error:
            return ("raised", type(error).__name__)
        if document is None:
            return ("read", "no-document")
        return ("read", "absent" if document.page_settings is None else "present")
