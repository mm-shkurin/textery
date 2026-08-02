class PromptRequest:
    """The narrow view of a generation a template is allowed to see.

    Deliberately not the `Generation` entity: `owner_id`, `content` and
    `error_message` are structurally unreachable from a template rather than
    merely unused by today's templates.
    """

    def __init__(self, document_type: str, topic: str) -> None:
        self.document_type = document_type
        self.topic = topic


def build_prompt(request: PromptRequest) -> str:
    raise NotImplementedError()
