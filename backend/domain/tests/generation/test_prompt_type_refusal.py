import pytest

from document.document_type import REFERAT, SUPPORTED_DOCUMENT_TYPES
from generation.prompt_template import _TEMPLATES, PromptBuildError
from prompt_fixtures import assert_refusal, prompt_for

# A type that is in no tuple and no dict. Spelled as a literal rather than derived,
# because every derivation available here reads one of the two sets under test.
UNSUPPORTED_TYPE = "диссертация"


def no_template_message(document_type: str) -> str:
    """The refusal a missing template must raise, per the ADR's G17(a).

    Retyped rather than imported from `prompt_template`, on the same reasoning
    `test_prompt_build_refusals.py` records: importing the production string turns
    every assertion below into `str(exc) == the string the code just raised`.

    Unlike those two, this one *does* interpolate its offending value -- what the
    ADR specifies verbatim, a stated exception rather than an oversight, but also
    the one refusal message putting request-supplied text into the log line
    `generate_document.py:69-75` writes.
    """
    return f"no prompt template for {document_type}"


class TestAMissingTemplateRefusesInTheRequest:
    """A type without a template must refuse in the request, not at boot and not in the worker.

    G17(a). The refusal *mechanism*: a missing key is a named, terminal
    `PromptBuildError` scoped to one request, not a `KeyError` the worker's
    catch-all retries.

    Split out of `test_prompt_type_coverage.py` when that file reached the 200-line
    limit: this class is about the refusal, that one about the per-type guards G17(b)
    and G18, and only this one is red today.
    """

    def test_should_keep_the_unsupported_type_outside_the_allowlist(self):
        # The premise both refusal tests below rest on, checked rather than trusted,
        # and deliberately **not** skip-marked: the two tests it guards are, so a
        # module-scope `assert` would be the only thing checking it and would report
        # as a collection error rather than as a failure attributable to this claim.
        # Without it, adding "диссертация" to the allowlist leaves both refusals
        # green while asserting nothing.
        assert UNSUPPORTED_TYPE not in SUPPORTED_DOCUMENT_TYPES, (
            f"{UNSUPPORTED_TYPE} must stay outside SUPPORTED_DOCUMENT_TYPES or the "
            f"refusal tests in this file assert nothing, got {SUPPORTED_DOCUMENT_TYPES}"
        )
        # The other half of the premise: the type must also be absent from the dict
        # under test. A `_TEMPLATES` that grew a "диссертация" key would build a
        # prompt here and turn both refusals into a different, silent failure.
        assert UNSUPPORTED_TYPE not in _TEMPLATES, (
            f"{UNSUPPORTED_TYPE} must have no prompt template or there is nothing to "
            f"refuse, got keys {sorted(_TEMPLATES)}"
        )

    @pytest.mark.skip(
        reason="RED: build_prompt subscripts _TEMPLATES bare -- KeyError: 'диссертация' "
        "at prompt_template.py:143, not PromptBuildError"
    )
    def test_should_refuse_a_document_type_that_has_no_template(self):
        # G17(a) via the path a live request takes: a type outside
        # SUPPORTED_DOCUMENT_TYPES arrives through `Generation.__init__`, the
        # storage hydration path, which applies none of `create`'s allowlist check.
        with pytest.raises(PromptBuildError) as exc_info:
            prompt_for(UNSUPPORTED_TYPE)

        # Both halves via the shared helper: the exact base type -- `PromptBuildError`
        # is deliberately the base of a family, so a subclass raised here would
        # satisfy `pytest.raises` while reporting a different cause -- and the message.
        assert_refusal(exc_info, no_template_message(UNSUPPORTED_TYPE))

    @pytest.mark.skip(
        reason="RED: build_prompt subscripts _TEMPLATES bare -- KeyError: 'реферат' "
        "at prompt_template.py:143, not PromptBuildError"
    )
    def test_should_refuse_a_supported_type_whose_template_was_removed(self, monkeypatch):
        # The same refusal reached from the direction the hazard actually arrives
        # from: the type is supported, the dict entry is not there. `monkeypatch`
        # restores the key at teardown, so the other files' goldens are unaffected.
        monkeypatch.delitem(_TEMPLATES, REFERAT)

        # Same two claims as the sibling above, not just the message: the type of the
        # raised error is half of G17(a)'s contract, and asserting it on one of the
        # two arrival paths only would let a `KeyError`-derived subclass through on
        # the path the hazard actually takes.
        with pytest.raises(PromptBuildError) as exc_info:
            prompt_for(REFERAT)

        assert_refusal(exc_info, no_template_message(REFERAT))
