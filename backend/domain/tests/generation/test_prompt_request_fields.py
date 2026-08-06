import inspect

from document.document_type import DOKLAD
from generation.generation import Generation
from generation.prompt_template import PromptRequest
from prompt_fixtures import prompt_request

# The `Generation` attributes `PromptRequest` exists to keep away from a template.
# Named individually rather than covered by the parameter-set equality alone: the
# equality states what is allowed, this states what the object is *for*, and the
# failure message then names the field that leaked instead of printing two tuples.
# Cross-checked against `Generation.__init__` below rather than trusted: a list of
# forbidden names that no longer matches the entity guards nothing, and a rename on
# `Generation` is exactly the change that would silently empty it.
FORBIDDEN_GENERATION_FIELDS = ("owner_id", "content", "error_message", "id", "status", "version")

# `(name, kind)` pairs rather than names alone. The names state which fields are
# allowed; the kinds close the escape the names leave open -- a `**kwargs` swallows
# `owner_id` while `inspect` still reports exactly three named parameters, so a
# name-only equality passes an object that accepts the whole entity. One structural
# comparison also fails with one diff instead of three sequential asserts, the third
# of which could never fire once the first pinned the names.
EXPECTED_PROMPT_REQUEST_SIGNATURE = (
    ("document_type", inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ("topic", inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ("volume_pages", inspect.Parameter.POSITIONAL_OR_KEYWORD),
    # Added 2026-08-06, deliberately and not by drift. These two are the fields
    # the USER fills in beside the topic, and the whole reason this view exists is
    # to admit user input while excluding server-owned state -- so widening it
    # here is the guard working, not the guard being worked around. They had been
    # validated, stored and echoed back for weeks while never reaching the model.
    ("requirements", inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ("extra_wishes", inspect.Parameter.POSITIONAL_OR_KEYWORD),
)

# The attributes a built `PromptRequest` may carry. Asserted separately from the
# signature because they are separately reachable: an `__init__` taking exactly the
# three declared parameters can still assign `self.owner_id` from a module-level
# lookup, which satisfies every signature assertion while putting a server-owned
# field one attribute access away from a template.
EXPECTED_PROMPT_REQUEST_ATTRIBUTES = (
    "document_type",
    "topic",
    "volume_pages",
    "requirements",
    "extra_wishes",
)


class TestPromptRequestCarriesOnlyTheFieldsATemplateMayRead:
    """`PromptRequest` is not the `Generation` entity, and that is its whole purpose.

    `owner_id`, `content` and `error_message` are meant to be structurally
    unreachable from a template rather than merely unused by today's templates --
    the reason the "method on Generation" option was rejected. A field set that
    grows by accident silently undoes that, so it is declared, not grown.
    """

    def test_should_accept_exactly_the_three_declared_fields(self):
        parameters = inspect.signature(PromptRequest.__init__).parameters
        accepted = tuple(
            (name, parameter.kind) for name, parameter in parameters.items() if name != "self"
        )

        # One structural comparison over names *and* kinds, rather than a name
        # equality followed by a separate variadic check and a third assert that
        # could never fire once the names were pinned. A `**kwargs` swallowing
        # `owner_id` still reports three named parameters, so the kind is what
        # actually closes the hole.
        assert accepted == EXPECTED_PROMPT_REQUEST_SIGNATURE, (
            f"PromptRequest's field set is the reason the 'method on Generation' "
            f"option was rejected; it must be declared, not grown: got {accepted}"
        )
        # The tuple above pins `(name, kind)` and nothing else, so a GREEN author who
        # wrote `volume_pages: int | None = None` would satisfy every assertion in
        # this file while making the field omissible -- and an omitted volume is the
        # exact hole the volume guards elsewhere exist to close, since a request that
        # never carried the value cannot state it in the prompt.
        assert parameters["volume_pages"].default is inspect.Parameter.empty, (
            f"volume_pages must be required, not defaulted: it is range-validated, "
            f"echoed in the response DTO and now interpolated into every template, "
            f"got default {parameters['volume_pages'].default!r}"
        )

    def test_should_keep_the_entity_s_server_owned_fields_out_of_a_template_s_reach(self):
        generation_fields = tuple(inspect.signature(Generation.__init__).parameters)

        # The forbidden list pinned against the entity before it is used as a guard.
        # A rename on `Generation` would otherwise leave this naming fields that no
        # longer exist -- vacuously green, guarding nothing, which is exactly the
        # failure mode the ADR records for hand-maintained lists elsewhere.
        unknown = [name for name in FORBIDDEN_GENERATION_FIELDS if name not in generation_fields]
        assert unknown == [], (
            f"these names no longer exist on Generation, so guarding against them "
            f"guards nothing: {unknown}"
        )

        # Asserted on the built instance, not on the signature. The signature test
        # above forbids these arriving as *parameters*; this forbids them arriving at
        # all -- an `__init__` taking exactly the three declared names can still
        # assign `self.owner_id`, which every signature assertion passes while
        # putting a server-owned field one attribute access from a template.
        request = prompt_request(DOKLAD)
        attributes = tuple(vars(request))

        assert attributes == EXPECTED_PROMPT_REQUEST_ATTRIBUTES, (
            f"PromptRequest carries attributes it does not declare: {attributes}"
        )
        leaked = [name for name in FORBIDDEN_GENERATION_FIELDS if name in attributes]
        assert leaked == [], (
            f"these Generation fields must be structurally unreachable from a template: {leaked}"
        )
        # `vars()` and `hasattr` say different things and both are kept. `vars()`
        # states that the *instance* carries exactly three entries -- the thing that
        # would show up in the deepcopy baseline the determinism guard takes, and the
        # thing a `__dict__` dump into a log would print. `hasattr` states the threat
        # model this guard was actually written against: what a template can *reach*
        # through `request.owner_id`. A class attribute or a `@property def owner_id`
        # is invisible to `vars()` and resolves fine inside an f-string, so the
        # `vars()` form alone passes the exact leak it is named for.
        reachable = [name for name in FORBIDDEN_GENERATION_FIELDS if hasattr(request, name)]
        assert reachable == [], (
            f"these Generation fields resolve on a PromptRequest -- a template can "
            f"interpolate them however they are declared: {reachable}"
        )
