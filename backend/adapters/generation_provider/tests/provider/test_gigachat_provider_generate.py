import uuid
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from adapters.generation_provider import ProviderError
from generation.generation import Generation
from provider.gigachat_provider import (
    CA_BUNDLE_ENV_VAR,
    COMPLETIONS_URL,
    CREDENTIALS_ENV_VAR,
    SCOPE,
    TOKEN_URL,
    GigaChatProvider,
)

ACCESS_TOKEN = "tok-abc-123"
GENERATED_CONTENT = "Готовый доклад про космос."
CREDENTIALS = "dGVzdDp0ZXN0"


def _json_response(payload):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value=payload)
    return response


def _token_payload():
    return {"access_token": ACCESS_TOKEN}


def _completions_payload():
    return {"choices": [{"message": {"content": GENERATED_CONTENT}}]}


def _patch_async_client(mocker, post_side_effect):
    client = MagicMock()
    client.post = AsyncMock(side_effect=post_side_effect)
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=client)
    context.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(
        "provider.gigachat_provider.httpx.AsyncClient",
        return_value=context,
    )
    return client


def _build_generation():
    return Generation.create(
        owner_id=uuid.uuid4(),
        topic="Космос",
        volume_pages=3,
        requirements=None,
        extra_wishes=None,
        document_type="Доклад",
    )


def _set_credentials(monkeypatch):
    monkeypatch.setenv(CREDENTIALS_ENV_VAR, CREDENTIALS)
    monkeypatch.setenv(CA_BUNDLE_ENV_VAR, "dummy-ca-bundle")


class TestGenerateHappyPath:
    """generate() fetches a token then returns the completion content
    over the two-step HTTP flow."""

    async def test_should_return_completion_content_and_authorize_with_fetched_token(
        self, monkeypatch, mocker
    ):
        _set_credentials(monkeypatch)
        client = _patch_async_client(
            mocker,
            [_json_response(_token_payload()), _json_response(_completions_payload())],
        )
        generation = _build_generation()

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
        expected_prompt = "Доклад на тему: Космос (3 стр.)"
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
        _set_credentials(monkeypatch)
        not_json = MagicMock()
        not_json.raise_for_status = MagicMock()
        # What a proxy or gateway actually returns with a 200: an HTML error page.
        not_json.json = MagicMock(side_effect=ValueError("Expecting value: line 1 column 1"))
        _patch_async_client(mocker, [_json_response(_token_payload()), not_json])

        with pytest.raises(ProviderError, match="not JSON"):
            await GigaChatProvider().generate(_build_generation())

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
        _set_credentials(monkeypatch)
        _patch_async_client(mocker, [_json_response(_token_payload()), _json_response(payload)])

        with pytest.raises(ProviderError, match="choices\\[0\\].message.content") as exc_info:
            await GigaChatProvider().generate(_build_generation())

        assert type(exc_info.value) is ProviderError, (
            f"{case}: expected the port's declared error type, got {type(exc_info.value)}"
        )


class TestFetchTokenMalformedBody:
    """The token call has the same remote edge and the same contract."""

    async def test_should_raise_provider_error_when_the_token_body_has_no_access_token(
        self, monkeypatch, mocker
    ):
        _set_credentials(monkeypatch)
        _patch_async_client(mocker, [_json_response({"error": "invalid_client"})])

        with pytest.raises(ProviderError, match="access_token"):
            await GigaChatProvider().generate(_build_generation())

    async def test_should_raise_provider_error_when_the_token_body_is_not_json(
        self, monkeypatch, mocker
    ):
        _set_credentials(monkeypatch)
        not_json = MagicMock()
        not_json.raise_for_status = MagicMock()
        not_json.json = MagicMock(side_effect=ValueError("Expecting value"))
        _patch_async_client(mocker, [not_json])

        with pytest.raises(ProviderError, match="not JSON"):
            await GigaChatProvider().generate(_build_generation())


class TestGenerateProviderError:
    """An httpx failure on the completions call surfaces as ProviderError carrying str(error)."""

    async def test_should_raise_provider_error_with_http_error_message(self, monkeypatch, mocker):
        _set_credentials(monkeypatch)
        http_error = httpx.HTTPError("simulated http failure")
        _patch_async_client(
            mocker,
            [_json_response(_token_payload()), http_error],
        )
        generation = _build_generation()

        with pytest.raises(ProviderError) as exc_info:
            await GigaChatProvider().generate(generation)

        assert type(exc_info.value) is ProviderError
        assert str(exc_info.value) == str(http_error)
