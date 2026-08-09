from typing import Literal

from dto.document.document_dtos import SaveDocumentRequestDto

# The leg the body was produced on, spelled as a closed type rather than a bare
# `str`. It is interpolation-only -- no branch reads it -- so a typo or a swapped
# label is invisible to every assertion here and would misname the broken leg in
# the one report anybody reads. NOTE: this is documentation, not enforcement --
# the call sites spell the import `from wire_shape_key_fence import ...`, which
# mypy cannot resolve (see the module-name note below), so it types the callee
# `Any` and never checks the argument.
#
# Re-spelling the import `dto.document.wire_shape_key_fence` does NOT fix that,
# though it reads as though it should. Measured: with both call sites qualified,
# `mypy --no-incremental` still accepts a deliberately typo'd `"dmped JSON"`.
# `mypy_path` (backend/pyproject.toml) lists `adapters/rest/src` BEFORE
# `adapters/rest/tests`, so `dto.document` resolves to the src directory, the
# helper is not found under it, and `ignore_missing_imports = true` silences the
# miss into `Any` again -- same hole, reached by a longer path. Enforcement needs
# the path order changed or the helper moved beside the code it types, neither of
# which is a test-file edit. Left as the short spelling until then.
#
# There is deliberately NO field-level exclusion set. `title` would be the only
# candidate, and excluding it is exactly the hole this helper exists to close:
# its omission on the absent row is a PER-REQUEST condition, not a field-level
# policy -- the same field is required on the body for the null row and the
# real-title row. Call-site placement carries that instead: this helper is
# called only from sites that set `title` explicitly, and never from the RED
# class next door, whose whole assertion is that `title` is ABSENT.
#
# Module-name note: this file is reachable under TWO names. pytest's `prepend`
# import mode puts each collected test's own directory on `sys.path`, so the
# tests see it as top-level `wire_shape_key_fence`; mypy and `pythonpath` also
# carry `adapters/rest/tests`, under which it is
# `dto.document.wire_shape_key_fence`. `ignore_missing_imports = true` in
# pyproject.toml is what keeps the mismatch silent rather than an error.
WireLeg = Literal["dumped", "dumped JSON"]


def assert_body_keys_track_the_model(body: dict[str, object], leg: WireLeg):
    """The half of the shape that whole-body equality against a literal cannot hold.

    Equality with a frozen dict is asymmetric under extension. It catches a
    SPURIOUS key -- that is why it was chosen -- but it cannot catch a DROPPED
    declared one: the day a later scenario adds a field to
    `SaveDocumentRequestDto`, a green whose serializer hand-builds its dict (a
    non-`wrap` `@model_serializer` returning `{"content": ..., "version": ...}`)
    silently omits the new field, and every `body == {...}` in this pair still
    holds, because the literal was frozen beside the old model. This assertion
    reads `model_fields` at run time, so it grows with the model instead of
    freezing next to it.

    The `missing` leg reads `model_fields` -- the DECLARED set -- and NOT
    `model_fields_set`, which is what it read when it shipped and which made it
    silent in the exact window this docstring claims as its only reason to exist.
    A field ADDED WITH A DEFAULT is never in `model_fields_set` unless a call
    site passes it, and no call site passes a field that does not exist yet.
    Measured on pydantic 2.13.4 against a model grown a defaulted `note` and a
    dict-building serializer that drops it:

        declared:   {'content','note','title','version'}
        fields_set: {'content','title','version'}
        missing, model_fields_set leg: []        # silent, while `note` is dropped
        missing, model_fields    leg: ['note']   # fires

    A WEAKER pin than the whole-body literals, not a stronger one: `model_fields`
    is read off the class under test, so a serializer wrong in the same direction
    agrees with itself. On the CURRENT model it catches nothing the literals
    miss. It is here for what they provably cannot cover, and every call site
    asserts whole-body equality against a frozen literal alongside it rather than
    delegating to it.

    Called only from the LIVE classes: the same hole exists in the skipped RED
    class in `test_save_document_request_dto_wire_shape.py`, but a call there
    would be dark for exactly the red period, which is when the green that could
    trip it gets written.
    """
    # `WireLeg` is documentation, not enforcement (see the module comment): mypy
    # types this callee `Any` at every call site, and a typo'd "dmped JSON" was
    # measured as accepted. Since the label is interpolation-only, a wrong one is
    # invisible to every assertion and misnames the broken leg in the one report
    # anybody reads. Two lines close at run time what the type cannot.
    assert leg in ("dumped", "dumped JSON"), (
        f"the leg label must be one of the declared WireLeg values, got {leg!r}"
    )
    declared = set(SaveDocumentRequestDto.model_fields)
    # Without this, an empty declared set skips both `if`s below and the final
    # assert passes without having examined `body` at all -- a vacuous pass in the
    # one helper whose whole job is to notice an absence.
    assert declared, "the model declares no fields -- the fence has nothing to check"
    missing = declared - body.keys()
    undeclared = body.keys() - declared
    # Both faults are computed before either is asserted, and both are named in
    # the one message. Two sequential `assert`s would abort on `missing` and
    # report one broken direction where two may be broken -- the exact defect the
    # control file's docstring (`test_..._wire_shape_control.py:47-54`) gives as
    # its reason for splitting the JSON leg off the dict leg. The fence should
    # not contradict its own neighbour.
    faults = []
    if missing:
        faults.append(f"{sorted(missing)} was declared on the model and dropped by the serializer")
    if undeclared:
        faults.append(f"{sorted(undeclared)} is on the body but declared nowhere on the model")
    assert not faults, (
        f"the {leg} body's key set must be exactly the model's declared fields -- "
        f"{'; and '.join(faults)}, got {body!r}"
    )
