from typing import Literal, get_args

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
# `title` is NOT excluded, and the difference between excluding it and what the
# `missing` leg below actually does is the whole point. An exclusion set would
# make an absent `title` PASS -- silently certifying the one body whose meaning
# the fence cannot read. Instead the leg is PARTITIONED: an absent `title` still
# fails, but with a refusal that names the condition and the forbidden call site,
# because absence is the CORRECT shape for a title-untouched save and a
# serializer fault everywhere else, and `body` alone does not say which. Call-site
# placement still carries the rest: this helper is called only from sites that set
# `title` explicitly, and never from the RED class next door, whose whole
# assertion is that `title` is ABSENT. The refusal is what makes that discipline
# self-enforcing rather than a comment.
#
# Weighed and rejected: passing the un-judgeable field set IN from each call site.
# It reads better in the abstract -- the condition is per-request, so the caller
# knows it and the helper does not -- but it moves the wording into a parameter,
# and the wording is what the refusal row asserts by exact equality. Every call
# site would then have to spell (or import) the same set, which is a second
# declaration of a one-element fact, and a site that forgets it gets the generic
# "dropped field" wording back -- the exact defect this partition closes. The
# field-level spelling keeps one declaration and cannot be forgotten.
#
# Module-name note: this file is reachable under TWO names. pytest's `prepend`
# import mode puts each collected test's own directory on `sys.path`, so the
# tests see it as top-level `wire_shape_key_fence`; mypy and `pythonpath` also
# carry `adapters/rest/tests`, under which it is
# `dto.document.wire_shape_key_fence`. `ignore_missing_imports = true` in
# pyproject.toml is what keeps the mismatch silent rather than an error.
WireLeg = Literal["dumped", "dumped JSON"]

# The `missing` partition below spells `title` as a bare literal, and it is the one
# name in this helper NOT read off the model at run time -- `declared` is, and so is
# `WireLeg`'s guard. That asymmetry is a hole with a measured consequence. Renaming
# the field to `heading` leaves this file importing and every existing row green,
# because the refusal branch simply stops matching: measured on the current model
# with `title` renamed in `model_fields`, a body carrying `content` and `version`
# reports
#
#     ['heading'] was declared on the model and dropped by the serializer
#
# -- the GENERIC dropped-field wording, on the one field whose absence lines 159-166
# argue must never be called "dropped", because that wording is what asks a future
# green to emit `"title": null` and erase a title the save never touched. The
# refusal does not fail loudly when it goes stale; it degrades into the exact
# message it exists to prevent.
#
# So the literal is pinned against the model at IMPORT time, mirroring the leg
# guard's run-time check of `get_args(WireLeg)`. Import time rather than inside the
# function because this is a static fact about the class, not a per-call one: the
# guard would otherwise re-check a constant at all 10-plus call sites, and it fires
# at collection -- before any row runs -- so a rename surfaces as one loud error
# naming its own fix instead of a quietly relabelled fault. A bare `assert` gets no
# introspection here (this module is not assert-rewritten -- see
# `test_wire_shape_key_fence.py:44`), hence the explicit message.
assert "title" in SaveDocumentRequestDto.model_fields, (
    "wire_shape_key_fence partitions its `missing` leg on the literal 'title', which "
    "is no longer a declared field of SaveDocumentRequestDto -- rename it in the "
    "refusal branch too, or the absent-title refusal silently degrades to the generic "
    f"dropped-field wording, got declared fields {sorted(SaveDocumentRequestDto.model_fields)}"
)


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
    # anybody reads. Two lines close at run time what the type cannot. The values
    # are read OFF `WireLeg` rather than re-spelled here: a re-spelled tuple is a
    # second declaration of the same closed set, and a leg added to the type but
    # not to the tuple gets rejected by the very guard that exists to police it.
    #
    # This guard sits BEFORE both fault legs and preempts them, so a typo'd leg on
    # a genuinely broken body reports the label and not the fault. Kept that way
    # deliberately: the label is interpolated into every message the legs produce,
    # so under the other order the fault IS reported -- attributed to a leg that
    # does not exist, which is a wrong report, not a partial one. A typo'd leg is a
    # one-edit defect in the caller and the fault re-reports on the very next run,
    # whereas a misattributed fault sends the reader to the wrong serializer. This
    # is the one place where aborting first beats reporting both, and it is the
    # opposite call from the two legs below for that reason.
    assert leg in get_args(WireLeg), (
        f"the leg label must be one of the declared WireLeg values, got {leg!r}"
    )
    declared = set(SaveDocumentRequestDto.model_fields)
    # No emptiness guard here. There was one, justified as closing a vacuous pass;
    # both halves of that were wrong. `declared` cannot be empty -- a pydantic model
    # always populates `model_fields`, so no reachable input trips it -- and with
    # `declared == set()` the `undeclared` leg would fire for ANY non-empty body,
    # so the pass it described needed an empty `body` as well. A guard that cannot
    # fire is not a fence; the accurate statement is this comment.
    missing = declared - body.keys()
    undeclared = body.keys() - declared
    # Both faults are computed before either is asserted, and both are named in
    # the one message. Two sequential `assert`s would abort on `missing` and
    # report one broken direction where two may be broken -- the exact defect the
    # control file's docstring (`test_..._wire_shape_control.py:47-54`) gives as
    # its reason for splitting the JSON leg off the dict leg. The fence should
    # not contradict its own neighbour.
    faults = []
    # The `missing` leg is PARTITIONED, not doubled. `title` is the single declared
    # field whose absence is under dispute, so it gets a refusal that says the fence
    # cannot judge this body and names the class it must not be called from; every
    # other declared field keeps the generic dropped-field wording, because nothing
    # anywhere claims a body may omit `content` or `version`. Calling an absent
    # `title` "dropped" is what asks a future green to emit `"title": null`, and
    # `SaveDocumentRequestDto.title_update()` maps that to `TitleUpdate.clear()` --
    # a silent, unrecoverable title erasure on a save that never touched the title.
    #
    # Collected into `faults` like any other fault rather than raised ahead of them,
    # so an absent-`title` body that ALSO carries a spurious key still reports both
    # directions in the one message -- the shape the both-faults row exists to hold.
    if "title" in missing:
        faults.append(
            "'title' is absent, which this fence cannot judge: absence is the CORRECT "
            "shape for a title-untouched save (TestSaveDocumentRequestDtoWireShape in "
            "test_save_document_request_dto_wire_shape.py) and a serializer fault "
            "everywhere else, and the body alone does not say which -- do not call this "
            "fence on the untouched row"
        )
    dropped = missing - {"title"}
    if dropped:
        faults.append(f"{sorted(dropped)} was declared on the model and dropped by the serializer")
    if undeclared:
        faults.append(f"{sorted(undeclared)} is on the body but declared nowhere on the model")
    assert not faults, (
        f"the {leg} body's key set must be exactly the model's declared fields -- "
        f"{'; and '.join(faults)}, got {body!r}"
    )
