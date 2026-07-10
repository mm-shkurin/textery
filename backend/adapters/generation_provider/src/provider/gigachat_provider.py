import os
import uuid

import httpx

from adapters.generation_provider import ProviderError
from generation.generation import Generation
from shared.exceptions import ConfigurationException

MISSING_CREDENTIALS_MESSAGE = "GIGACHAT_CREDENTIALS environment variable is not set"
TOKEN_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
COMPLETIONS_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
SCOPE = "GIGACHAT_API_PERS"
CREDENTIALS_ENV_VAR = "GIGACHAT_CREDENTIALS"
CA_BUNDLE_ENV_VAR = "GIGACHAT_CA_BUNDLE"
# GigaChat's TLS cert chains to the Russian Minsvyaz trust CA, which is not in
# most system trust stores. Bundled PEM fetched from gu-st.ru — GIGACHAT_CA_BUNDLE
# overrides it, but this is the working default rather than disabling verification.
_DEFAULT_CA_BUNDLE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "certs",
    "russiantrustedca.pem",
)


class GigaChatProvider:
    def __init__(self) -> None:
        credentials = os.environ.get(CREDENTIALS_ENV_VAR)
        if not credentials:
            raise ConfigurationException(MISSING_CREDENTIALS_MESSAGE)
        self._credentials = credentials
        self._verify = os.environ.get(CA_BUNDLE_ENV_VAR, _DEFAULT_CA_BUNDLE)

    async def generate(self, generation: Generation) -> str:
        try:
            token = await self._fetch_token()
            prompt = f"{generation.document_type} на тему: {generation.topic} ({generation.volume_pages} стр.)"
            async with httpx.AsyncClient(verify=self._verify, timeout=30) as client:
                response = await client.post(
                    COMPLETIONS_URL,
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "model": "GigaChat",
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except httpx.HTTPError as error:
            raise ProviderError(str(error)) from error

    async def _fetch_token(self) -> str:
        async with httpx.AsyncClient(verify=self._verify, timeout=30) as client:
            response = await client.post(
                TOKEN_URL,
                headers={
                    "Authorization": f"Basic {self._credentials}",
                    "RqUID": str(uuid.uuid4()),
                },
                data={"scope": SCOPE},
            )
            response.raise_for_status()
            return response.json()["access_token"]
