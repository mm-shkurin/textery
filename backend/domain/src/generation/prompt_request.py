"""The narrow view of a generation a template is allowed to see.

Its own module so `prompt_template` (the rules) and `prompt_templates_by_type`
(the texts) can both name it without either importing the other.
"""


class PromptRequest:
    """The narrow view of a generation a template is allowed to see.

    Deliberately not the `Generation` entity: `owner_id`, `content` and
    `error_message` are structurally unreachable from a template rather than
    merely unused by today's templates.
    """

    def __init__(self, document_type: str, topic: str, volume_pages: int) -> None:
        self.document_type = document_type
        self.topic = topic
        self.volume_pages = volume_pages
