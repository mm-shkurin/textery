import uuid

import httpx
import pytest

from generation.generation_provider import ProviderError
from gigachat_fixtures import (
    ACCESS_TOKEN,
    CREDENTIALS,
    GENERATED_CONTENT,
    build_generation,
    completions_payload,
    json_response,
    non_json_response,
    patch_async_client,
    set_credentials,
    token_payload,
)
from provider.gigachat_provider import COMPLETIONS_URL, SCOPE, TOKEN_URL, GigaChatProvider


class TestGenerateHappyPath:
    """generate() fetches a token then returns the completion content
    over the two-step HTTP flow."""

    async def test_should_return_completion_content_and_authorize_with_fetched_token(
        self, monkeypatch, mocker
    ):
        set_credentials(monkeypatch)
        client = patch_async_client(
            mocker,
            [json_response(token_payload()), json_response(completions_payload())],
        )
        generation = build_generation()

        result = await GigaChatProvider().generate(generation)

        assert result == GENERATED_CONTENT
        assert client.post.await_count == 2
        token_call, completions_call = client.post.await_args_list

        assert token_call.args[0] == TOKEN_URL
        assert token_call.kwargs["headers"]["Authorization"] == f"Basic {CREDENTIALS}"
        # RqUID is a per-request uuid4 generated inside production (opaque, no
        # retrieval API) — pin its format/version rather than an exact value.
        assert uuid.UUID(token_call.kwargs["headers"]["RqUID"]).version == 4
        assert token_call.kwargs["data"] == {"scope": SCOPE}

        assert completions_call.args[0] == COMPLETIONS_URL
        assert completions_call.kwargs["headers"] == {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        expected_prompt = "доклад на тему: Космос (3 стр.)"
        assert completions_call.kwargs["json"] == {
            "model": "GigaChat",
            "messages": [{"role": "user", "content": expected_prompt}],
        }


class TestGenerateMalformedProviderBody:
    """A 200 whose body is not the agreed shape is still a ProviderError.

    The GenerationProvider port declares ProviderError as its failure mode, and
    GenerateDocument has already persisted the row as in_progress by the time it
    calls generate(). Anything escaping raw -- KeyError, IndexError,
    JSONDecodeError -- breaks the port's contract and strands that row.
    """

    async def test_should_raise_provider_error_when_the_body_is_not_json(self, monkeypatch, mocker):
        set_credentials(monkeypatch)
        patch_async_client(mocker, [json_response(token_payload()), non_json_response()])

        with pytest.raises(ProviderError, match="not JSON"):
            await GigaChatProvider().generate(build_generation())

    @pytest.mark.parametrize(
        ("payload", "case"),
        [
            ({"error": "quota exceeded"}, "an error envelope instead of choices"),
            ({"choices": []}, "choices present but empty"),
            ({"choices": [{"message": {}}]}, "message present but no content key"),
            ({"choices": [{}]}, "choice present but no message key"),
            ({"choices": "not-a-list"}, "choices of the wrong type"),
        ],
    )
    async def test_should_raise_provider_error_for_json_without_a_completion(
        self, monkeypatch, mocker, payload, case
    ):
        set_credentials(monkeypatch)
        patch_async_client(mocker, [json_response(token_payload()), json_response(payload)])

        with pytest.raises(ProviderError, match="choices\\[0\\].message.content") as exc_info:
            await GigaChatProvider().generate(build_generation())

        assert type(exc_info.value) is ProviderError, (
            f"{case}: expected the port's declared error type, got {type(exc_info.value)}"
        )


class TestFetchTokenMalformedBody:
    """The token call has the same remote edge and the same contract."""

    async def test_should_raise_provider_error_when_the_token_body_has_no_access_token(
        self, monkeypatch, mocker
    ):
        set_credentials(monkeypatch)
        patch_async_client(mocker, [json_response({"error": "invalid_client"})])

        with pytest.raises(ProviderError, match="access_token"):
            await GigaChatProvider().generate(build_generation())

    async def test_should_raise_provider_error_when_the_token_body_is_not_json(
        self, monkeypatch, mocker
    ):
        set_credentials(monkeypatch)
        patch_async_client(mocker, [non_json_response("Expecting value")])

        with pytest.raises(ProviderError, match="not JSON"):
            await GigaChatProvider().generate(build_generation())


class TestGenerateProviderError:
    """An httpx failure on the completions call surfaces as ProviderError carrying str(error)."""

    async def test_should_raise_provider_error_with_http_error_message(self, monkeypatch, mocker):
        set_credentials(monkeypatch)
        http_error = httpx.HTTPError("simulated http failure")
        patch_async_client(mocker, [json_response(token_payload()), http_error])

        with pytest.raises(ProviderError) as exc_info:
            await GigaChatProvider().generate(build_generation())

        assert type(exc_info.value) is ProviderError
        assert str(exc_info.value) == str(http_error)
