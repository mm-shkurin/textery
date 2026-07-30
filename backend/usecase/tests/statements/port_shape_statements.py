"""Structural assertions over the save port's signature (Scenario 3.2).

The subject here is a *signature*, not a value, so these methods reflect over
classes rather than driving a usecase. `FakeDocumentRepository` appears as a
reflection target only -- it is never instantiated and never injected as a
storage port. Rationale for pinning the shape at all lives in the test module.
"""

import inspect
from collections.abc import Mapping

import pytest

from document.document import Document
from document.document_repository import DocumentRepository
from document.title_update import TitleUpdate
from statements.document_fakes import FakeDocumentRepository

_SAVE = "save_content_if_version_matches"

# The two carriers of the contract, named ONCE: the port that declares it and
# the fake that every usecase test measures against. A fake that drifts looser
# than its port is how a usecase test passes against a call the real adapter
# would reject.
_PORT = DocumentRepository
_FAKE = FakeDocumentRepository

SAVE_SIGNATURE_CARRIERS = [pytest.param(_PORT, id="port"), pytest.param(_FAKE, id="fake")]

# The whole `title` parameter, spelled structurally, so ONE comparison pins all
# four properties `inspect.Parameter` carries -- name, kind, default and
# annotation.
EXPECTED_TITLE_PARAMETER = inspect.Parameter(
    "title", inspect.Parameter.KEYWORD_ONLY, annotation=TitleUpdate
)

# Literal, not read back out of either signature. A port-vs-fake comparison
# alone is self-referential: renaming or reordering BOTH carriers together
# passes it, so it pins agreement and never the order itself. This constant is
# the thing that actually has to be edited for the order to change.
EXPECTED_SAVE_PARAMETER_NAMES = [
    "self",
    "document_id",
    "owner_id",
    "content",
    "expected_version",
    "updated_at",
    "title",
]

EXPECTED_SAVE_RETURN_ANNOTATION = Document | None


def _save_signature(implementor: type) -> inspect.Signature:
    return inspect.signature(getattr(implementor, _SAVE))


def _save_parameters(implementor: type) -> Mapping[str, inspect.Parameter]:
    return _save_signature(implementor).parameters


def _spell(parameter: inspect.Parameter) -> str:
    """Render every field `Parameter.__eq__` compares -- `str()` renders only three.

    `str(Parameter)` omits `kind`, so a POSITIONAL_OR_KEYWORD `title` and a
    KEYWORD_ONLY one both render as `title: document.title_update.TitleUpdate`
    and the failure message shows expected and actual as the SAME string.
    """
    required = parameter.default is inspect.Parameter.empty
    default = "<required>" if required else repr(parameter.default)
    annotation = getattr(parameter.annotation, "__name__", None) or str(parameter.annotation)
    return (
        f"name={parameter.name!r}, kind={parameter.kind.name}, "
        f"annotation={annotation}, default={default}"
    )


def _spell_all(parameters: Mapping[str, inspect.Parameter]) -> str:
    return "\n".join(f"    [{_spell(parameter)}]" for parameter in parameters.values())


class PortShapeStatements:
    def assert_title_is_a_required_keyword_only_title_update(self, implementor: type) -> None:
        parameters = _save_parameters(implementor)

        # Presence first: indexing a missing key raises a bare `KeyError` that
        # carries none of the rationale below, and the message IS this guard's
        # documentation.
        assert "title" in parameters, (
            f"{implementor.__name__}.{_SAVE} must take a `title` argument at all. "
            f"Got parameters: {list(parameters)}"
        )

        title = parameters["title"]
        assert title == EXPECTED_TITLE_PARAMETER, (
            f"{implementor.__name__}.{_SAVE} must declare `title` as "
            f"[{_spell(EXPECTED_TITLE_PARAMETER)}]\n"
            f"                                                  -- got "
            f"[{_spell(title)}].\n"
            "* REQUIRED (no default): a default is a fourth, unnamed state -- 'argument "
            "absent' -- and since preserve() and the coming clear() are indistinguishable "
            "by value, a caller that forgets the title silently gets someone else's intent.\n"
            "* KEYWORD_ONLY: the intent must be spelled at the call site, never inferred "
            "from position, so a reordered signature cannot bind the wrong value here.\n"
            "* annotated `TitleUpdate`: a `str | None` cannot tell 'preserve' from 'clear', "
            "which is the whole reason the value object exists.\n"
            "See decisions/blank-title-semantics-decision.md."
        )

    def assert_the_save_arguments_are_declared_in_the_pinned_order(
        self, implementor: type
    ) -> None:
        """Each carrier binds positional arguments to the names spelled above.

        `title` is keyword-only, so it can no longer be mis-bound by a reorder
        -- but the five names before the `*` still bind positionally, and two of
        them are same-typed (`document_id` and `owner_id` are both `UUID`), so
        swapping that pair would save one account's content onto another's
        document with no complaint from anything at runtime.
        """
        actual = list(_save_parameters(implementor))

        assert actual == EXPECTED_SAVE_PARAMETER_NAMES, (
            f"{implementor.__name__}.{_SAVE} must declare exactly these arguments, in this "
            f"order: {EXPECTED_SAVE_PARAMETER_NAMES}. Got: {actual}. The order is pinned "
            "literally rather than compared between the carriers, because a reorder applied "
            "to both of them at once would satisfy a carrier-to-carrier comparison."
        )

    def assert_the_fake_declares_the_same_save_signature_as_the_port(self) -> None:
        """The fake mirrors the port field-for-field, not merely name-for-name.

        Comparing names alone let the fake declare `content: int` or default
        `expected_version` and stay green while accepting calls the real adapter
        rejects. `Parameter.__eq__` compares name, kind, annotation and default,
        so comparing the parameters themselves closes that gap. This pins that
        the two AGREE; what `title` specifically must be is pinned separately.
        """
        port = _save_parameters(_PORT)
        fake = _save_parameters(_FAKE)

        assert list(fake.values()) == list(port.values()), (
            f"{_FAKE.__name__}.{_SAVE} must declare the same arguments -- same order, kinds, "
            f"annotations and defaults -- as the port it stands in for.\n"
            f"  Port:\n{_spell_all(port)}\n"
            f"  Fake:\n{_spell_all(fake)}\n"
            "A fake that drifts lets a usecase test pass against a call the real adapter "
            "would reject."
        )

    def assert_the_save_return_annotation_is_the_pinned_optional_document(
        self, implementor: type
    ) -> None:
        """`Document | None` is contract, not decoration.

        The `None` arm IS the compare-and-swap miss. A carrier annotated to
        return a bare `Document` makes every CAS-miss test unrepresentable.
        """
        actual = _save_signature(implementor).return_annotation

        assert actual == EXPECTED_SAVE_RETURN_ANNOTATION, (
            f"{implementor.__name__}.{_SAVE} must be annotated to return "
            f"`{EXPECTED_SAVE_RETURN_ANNOTATION}` -- got `{actual}`. The `None` arm is the "
            "version-mismatch miss the caller has to branch on."
        )
