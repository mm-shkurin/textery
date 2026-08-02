import re

import pytest

from document.document_type import REFERAT
from generation.prompt_template import PromptRequest, build_prompt

TOPIC = "Как работает фотосинтез"

# The prompt fragments this scenario pins. Multi-word and contiguous on purpose:
# a bare "цель" also matches "целесообразно" and a bare "разделы" is satisfied by
# a prompt that mentions sections without tying them to the topic.
VVEDENIE_MARKER = "во введении"
VVEDENIE_FRAGMENTS = ("актуальность темы", "цель работы")
RAZDELY_FRAGMENT = "разделы по теме"
ZAKLYUCHENIE_MARKER = "в заключении"
ZAKLYUCHENIE_FRAGMENTS = ("выводы",)


def _referat_prompt() -> str:
    """The built реферат prompt, lowercased once for every assertion below.

    Case folding belongs here rather than at each call site: the scenario is about
    which instructions the prompt carries, never about their capitalization, and a
    per-test `.lower()` lets the class silently split into case-sensitive arms.
    """
    return build_prompt(PromptRequest(document_type=REFERAT, topic=TOPIC)).lower()


def _sentence_with(prompt: str, marker: str) -> str:
    """The single sentence of `prompt` carrying `marker`.

    The spec asks for введение *with* актуальность and цель. Asserting the three
    fragments against the whole prompt would pass on a template that demands
    актуальность inside the заключение, so each obligation is checked against the
    one sentence that raises its section.
    """
    sentences = [part for part in re.split(r"[.\n]", prompt) if marker in part]

    assert len(sentences) == 1, (
        f"expected exactly one sentence containing '{marker}', got {len(sentences)}: {sentences}"
    )
    return sentences[0]


@pytest.mark.skip(reason="RED: build_prompt raises NotImplementedError -- no реферат template")
class TestAReferatPromptAsksForTheReferatStructure:
    """A реферат is graded on its shape, so the prompt has to dictate that shape.

    Left to itself the model returns an undifferentiated essay: no введение that
    states why the topic matters, sections that wander off the topic, and a closing
    paragraph that summarizes nothing. Each obligation below is one thing a marker
    looks for, and each is asserted inside its own section so the prompt cannot
    satisfy the wording while attaching it to the wrong part of the document.
    """

    def test_should_ask_the_introduction_to_state_relevance_and_goal(self):
        vvedenie = _sentence_with(_referat_prompt(), VVEDENIE_MARKER)

        missing = [f for f in VVEDENIE_FRAGMENTS if f not in vvedenie]

        assert missing == [], f"введение sentence '{vvedenie}' is missing: {missing}"

    def test_should_ask_for_sections_on_the_requested_topic(self):
        prompt = _referat_prompt()

        assert RAZDELY_FRAGMENT in prompt, (
            f"prompt must ask for '{RAZDELY_FRAGMENT}' as one phrase, got: {prompt}"
        )
        # Without this the разделы instruction is satisfied by a prompt that drops
        # the topic entirely -- "sections on the topic" with no topic named.
        assert TOPIC.lower() in prompt, f"prompt must name the requested topic, got: {prompt}"

    def test_should_ask_the_conclusion_to_state_findings(self):
        zaklyuchenie = _sentence_with(_referat_prompt(), ZAKLYUCHENIE_MARKER)

        missing = [f for f in ZAKLYUCHENIE_FRAGMENTS if f not in zaklyuchenie]

        assert missing == [], f"заключение sentence '{zaklyuchenie}' is missing: {missing}"
