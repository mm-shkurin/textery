"""The narrow view of a generation a template is allowed to see.

Its own module so `prompt_template` (the rules) and `prompt_templates_by_type`
(the texts) can both name it without either importing the other.
"""


class PromptRequest:
    """The narrow view of a generation a template is allowed to see.

    Deliberately not the `Generation` entity: `owner_id`, `content` and
    `error_message` are structurally unreachable from a template rather than
    merely unused by today's templates.

    `requirements` and `extra_wishes` are the two fields the user fills in on the
    form beside the topic. They were absent from this view until 2026-08-06, so
    they were validated, stored, echoed back in the response — and never sent to
    the model. Someone who wrote "не используй сложные термины" got a document
    that ignored it, with nothing anywhere reporting a failure.
    """

    def __init__(
        self,
        document_type: str,
        topic: str | None,
        volume_pages: int | None,
        requirements: str | None = None,
        extra_wishes: str | None = None,
    ) -> None:
        self.document_type = document_type
        # Nullable, matching `Generation`'s own annotations. Narrowing them to
        # `str`/`int` here would be a claim this view cannot make: the storage
        # hydration path builds a `Generation` through `__init__`, which applies
        # neither the required-topic nor the range check that `create` does, so a
        # row written before those checks existed reaches `build_prompt` with
        # either field `None`. `_reject_unrenderable_fields` is the guard that
        # turns that into a terminal `PromptBuildError`; it only has a job to do
        # because the value genuinely can be absent.
        self.topic = topic
        self.volume_pages = volume_pages
        # Optional by the contract, and defaulted here rather than made required:
        # every generation created before this field reached the prompt has none,
        # and the storage hydration path rebuilds those rows as they are.
        self.requirements = requirements
        self.extra_wishes = extra_wishes
