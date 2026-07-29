"""Scenario 3.2 -- the save port's `title` argument is required and keyword-only.

Why a STRUCTURAL test, in the same idiom as the db layer's
`test_document_storage_cas_shape.py` ("must not SELECT"): the property this
pins has no behavioural witness. Commit `6d1ea08` removed
`= TitleUpdate.preserve()` from `DocumentRepository.save_content_if_version_matches`
so the argument became required -- and that change is invisible to every other
guard in the repo. Re-adding the default to the port and to `document_fakes.py`
left every suite green when the coverage pass over `6d1ea08` tried it, because
every call site already passes `title` explicitly, so no test ever exercises the
omission the default would answer for. Nor would the type checker object: ADDING
a default is legal, and CI runs `pytest --cov` with no mypy step at all. A
decision nothing can notice being reverted is not pinned.

The port's own docstring and the commit that landed it claim three things about
`title`, so all three are pinned here in one structural comparison against the
whole `inspect.Parameter` -- see `EXPECTED_TITLE_PARAMETER`. Pinning `default`
and `kind` while leaving `annotation` open would have let green satisfy the
letter of the scenario with `title: str | None`, which is the exact type the
value object was introduced to replace.

The fake is asserted alongside the port because its own comment already claims
this contract ("an omitted argument is now a TypeError, which is a constraint
rather than a convention") -- a claim that is only true while something checks
it. A fake that drifts looser than its port is how a usecase test passes against
a call the real adapter would reject.

The remaining tests pin the other half of that drift, and they are split because
they fail for different reasons. Argument ORDER is pinned against a literal list
in the Statements module rather than by comparing the carriers to each other: a
reorder applied to both at once satisfies a carrier-to-carrier comparison, so
that comparison would have pinned agreement while claiming to pin order. The
carrier-to-carrier test then compares whole `inspect.Parameter` objects, not
names -- names alone let the fake declare `content: int` or default
`expected_version` and stay green. Finally the return annotation is pinned
because the `None` arm IS the compare-and-swap miss; a carrier annotated
`-> Document` makes every CAS-miss test unrepresentable.
"""

import pytest

from statements.port_shape_statements import SAVE_SIGNATURE_CARRIERS, PortShapeStatements


@pytest.mark.skip(
    reason="RED: `title` is POSITIONAL_OR_KEYWORD on both DocumentRepository and "
    "FakeDocumentRepository -- neither signature has a `*` separator, so KEYWORD_ONLY is unmet"
)
class TestSaveTitleIsARequiredKeywordOnlyArgument:
    @pytest.mark.parametrize("implementor", SAVE_SIGNATURE_CARRIERS)
    def test_title_has_no_default_and_cannot_be_passed_positionally(
        self, implementor, port_shape_statements: PortShapeStatements
    ):
        port_shape_statements.assert_title_is_a_required_keyword_only_title_update(implementor)


class TestTheCarriersDeclareTheSameSaveSignature:
    """Deliberately NOT skipped -- these are green today.

    The properties they pin already hold, so they are satisfied invariants, not
    RED tests. They stay live rather than sharing the class above's marker,
    because a passing assertion parked under a skip marker is an assertion that
    has stopped running without anyone deciding it should.
    """

    @pytest.mark.parametrize("implementor", SAVE_SIGNATURE_CARRIERS)
    def test_the_save_arguments_are_declared_in_the_pinned_order(
        self, implementor, port_shape_statements: PortShapeStatements
    ):
        port_shape_statements.assert_the_save_arguments_are_declared_in_the_pinned_order(
            implementor
        )

    def test_the_fake_mirrors_every_field_of_every_port_parameter(
        self, port_shape_statements: PortShapeStatements
    ):
        port_shape_statements.assert_the_fake_declares_the_same_save_signature_as_the_port()

    @pytest.mark.parametrize("implementor", SAVE_SIGNATURE_CARRIERS)
    def test_save_is_annotated_to_return_an_optional_document(
        self, implementor, port_shape_statements: PortShapeStatements
    ):
        port_shape_statements.assert_the_save_return_annotation_is_the_pinned_optional_document(
            implementor
        )
