"""G14 — the provider and the domain agree on the доклад prompt.

Until scenario 2.1 substitutes one composer for the other, the same text has two
independently-editable definitions: `_plain` in
`backend/domain/src/generation/prompt_template.py` and the f-string at
`provider/gigachat_provider.py:113-116`. Each is pinned only by its own golden, so
either can be edited alone with nothing red — and scenario 1.3's claim ("the доклад
prompt is unchanged by the move into the domain") dies silently. Golden-vs-golden
cannot force the agreement; only an assertion whose two sides are the two *live*
composers can. Hence: drive `GigaChatProvider.generate` and compare the posted
`content` against `build_prompt(...)` built from the same `Generation`. No
hand-typed literal appears on either side.

The adapter is the correct home: this test drives `GigaChatProvider`, and a domain
or usecase test importing an adapter would invert the dependency rule. The reverse
direction — an adapter test importing the domain's `build_prompt` — flows inward
and is fine.

**Scope is доклад only, and the scope is load-bearing.** The provider appends no
ban; `build_prompt` appends one for every type outside `_BAN_DEFERRED`.
Parameterizing over `SUPPORTED_DOCUMENT_TYPES` would therefore be red on arrival
for эссе/сочинение/реферат with no defect present, and the cheapest escape from
that red is to widen `_BAN_DEFERRED` — i.e. to unban them. The other three types
stay unpinned across the two composers until 2.1 removes one composer. The scope
is executable, not merely documented: `build_doklad_generation()` asserts the type
it hands back, so it cannot drift with a shared default.
"""

from generation.prompt_template import build_prompt
from gigachat_fixtures import (
    build_doklad_generation,
    completions_payload,
    json_response,
    patch_async_client,
    posted_completion_messages,
    request_from,
    set_credentials,
    token_payload,
)
from provider import gigachat_provider
from provider.gigachat_provider import GigaChatProvider


class TestProviderAndDomainComposeTheSameDokladPrompt:
    """The posted prompt equals the one the domain builder produces."""

    async def test_should_post_exactly_the_prompt_the_domain_builder_composes(
        self, monkeypatch, mocker
    ):
        set_credentials(monkeypatch)
        client = patch_async_client(
            mocker,
            [json_response(token_payload()), json_response(completions_payload())],
        )
        generation = build_doklad_generation()

        await GigaChatProvider().generate(generation)

        # The whole `messages` list, not `messages[0]["content"]`. Indexing 0 and
        # comparing only the content would let a prepended system message turn a
        # prompt agreement into a misleading red — or, if the system message
        # happened to carry the доклад text, into a false green.
        assert posted_completion_messages(client) == [
            {"role": "user", "content": build_prompt(request_from(generation))}
        ]

    def test_should_keep_the_provider_composing_its_own_prompt(self):
        """The two sides of the agreement are still two.

        The assertion above is live-vs-live, which is what gives it its force — and
        also what makes it self-destructing: the moment scenario 2.1 has the
        provider delegate to `build_prompt`, both sides resolve to the same call
        and the comparison becomes a tautology that passes forever, covering
        nothing, with no test edit to notice.

        So the independence is asserted rather than assumed. When 2.1 lands, this
        goes red — and the correct response is to **delete this whole file**,
        because the guard it provides is exactly what substituting one composer for
        the other makes structurally unnecessary. The wrong response is to silence
        this method and keep the tautology above.
        """
        assert not hasattr(gigachat_provider, "build_prompt"), (
            "the provider now imports the domain composer, so the agreement test "
            "above compares build_prompt with itself — delete this file (scenario 2.1)"
        )
