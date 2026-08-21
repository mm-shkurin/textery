"""Composing the prompt one generation is phrased as.

Extracted from `generate_document.py` when that file reached the 200-line cap
(analytics emission landed there): it is the only piece of that module which is
a pure function of a `Generation`, and the one a reader looking for the retry
policy never needs on screen.

Composed at the CALL SITE, and not inside the provider. Placement is the guard:
a build nested in `GenerationProvider.generate` means the provider was called
before the request could be refused. The refusal happens once, before the retry
loop -- and the composed result is also what the provider is handed, so this is
the only composer there is.
"""

from generation.generation import Generation
from generation.prompt_template import PromptRequest, build_prompt


def compose_prompt(generation: Generation) -> str:
    return build_prompt(
        PromptRequest(
            document_type=generation.document_type,
            topic=generation.topic,
            volume_pages=generation.volume_pages,
            requirements=generation.requirements,
            extra_wishes=generation.extra_wishes,
            text_style=generation.text_style,
        )
    )
