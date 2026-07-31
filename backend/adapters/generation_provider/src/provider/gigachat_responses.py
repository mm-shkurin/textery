"""Reading GigaChat's two response bodies without trusting either of them.

Split out of `gigachat_provider.py` when that file crossed the 200-line limit.
The seam is not arbitrary: everything here answers one question -- "what does this
body actually contain" -- about data whose shape is somebody else's decision and
can change without warning. The provider above owns credentials, the token cache,
the connection and the timeouts; none of that is needed to parse a payload, and
neither function touches `self`, which is why they were already `@staticmethod`.

Both translate every disappointment into `ProviderError`, because that is what the
`GenerationProvider` port promises its callers. Before, only `httpx.HTTPError` was
caught, so a 200 carrying an unexpected shape -- an error envelope, a truncated
body, a proxy's HTML page -- raised `KeyError`, `IndexError` or `JSONDecodeError`
straight through the port's contract and out of the BackgroundTask, stranding the
generation row in `in_progress`.
"""

import httpx

from generation.generation_provider import ProviderError


def read_completion(response: httpx.Response) -> str:
    """The generated text, or a ProviderError naming how the body fell short."""
    try:
        payload = response.json()
    except ValueError as error:
        raise ProviderError(f"provider returned a body that is not JSON: {error}") from error
    try:
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise ProviderError(
            f"provider returned JSON without a completion at choices[0].message.content: {error}"
        ) from error


def read_access_token(response: httpx.Response) -> str:
    """The OAuth token, or a ProviderError naming how the body fell short."""
    try:
        return response.json()["access_token"]
    except ValueError as error:
        raise ProviderError(f"token endpoint returned a body that is not JSON: {error}") from error
    except (KeyError, TypeError) as error:
        raise ProviderError(
            f"token endpoint returned JSON without access_token: {error}"
        ) from error
