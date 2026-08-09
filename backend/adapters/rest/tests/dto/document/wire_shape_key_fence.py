from dto.document.document_dtos import SaveDocumentRequestDto

# Fields declared on the model that are intentionally kept OFF the wire. Empty,
# and deliberately spelled as an empty frozenset rather than dropped from the
# expression: on the current `SaveDocumentRequestDto` every declared field
# (`content`, `title`, `version`) belongs on the body, so there is nothing to
# exclude, and the day a server-derived or internal field is added the exclusion
# is a one-line edit here instead of a re-argument at the call sites.
#
# `title` is NOT listed, and that is the point of the whole leg. Its omission on
# the absent row is a PER-REQUEST condition, not a field-level policy -- the same
# field is required on the body for the null row and the real-title row. A
# field-level exclusion for `title` would re-open exactly the hole this helper
# exists to close. That is also why this helper is called only from call sites
# that set `title` explicitly, and never from the RED class next door, whose
# whole assertion is that `title` is ABSENT from the body.
FIELDS_KEPT_OFF_THE_WIRE: frozenset[str] = frozenset()


def assert_body_keys_track_the_model(body: dict, leg: str):
    """The half of the shape that whole-body equality against a literal cannot hold.

    Equality with a frozen dict is asymmetric under extension. It catches a
    SPURIOUS key -- that is why it was chosen -- but it cannot catch a DROPPED
    declared one: the day a later scenario adds a field to
    `SaveDocumentRequestDto`, a green whose serializer hand-builds its dict (a
    non-`wrap` `@model_serializer` returning `{"content": ..., "version": ...}`)
    silently omits the new field, and every `body == {...}` in this pair still
    holds, because the literal was frozen beside the old model. These two
    assertions read `model_fields` at run time, so they grow with the model
    instead of freezing next to it.

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
    miss. It is here for what they provably cannot cover.

    Called only from the LIVE classes: the same hole exists in the skipped RED
    class in `test_save_document_request_dto_wire_shape.py`, but a call there
    would be dark for exactly the red period, which is when the green that could
    trip it gets written.
    """
    declared = set(SaveDocumentRequestDto.model_fields)
    missing = declared - body.keys() - FIELDS_KEPT_OFF_THE_WIRE
    assert not missing, (
        f"every field declared on the model must appear in the {leg} body -- "
        f"{sorted(missing)} was declared and dropped by the serializer, got {body!r}"
    )
    undeclared = body.keys() - declared
    assert not undeclared, (
        f"the {leg} body must carry no key outside the model's declared fields, "
        f"got {sorted(undeclared)} in {body!r}"
    )
