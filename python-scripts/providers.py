"""Provider-specific, non-generative API-key checks.

Each check makes one authenticated GET request to list available models. It
never submits prompts or creates a billable generation/session.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderConfig:
    """Model-list request details for a supported API provider."""

    label: str
    endpoint: str
    auth_header: str
    response_list_key: str
    extra_headers: tuple[tuple[str, str], ...] = ()
    api_key_query_parameter: bool = False


PROVIDERS: dict[str, ProviderConfig] = {
    "gemini": ProviderConfig(
        label="Google Gemini",
        endpoint="https://generativelanguage.googleapis.com/v1beta/models?pageSize=1",
        auth_header="x-goog-api-key",
        response_list_key="models",
    ),
    "openai": ProviderConfig(
        label="OpenAI",
        endpoint="https://api.openai.com/v1/models",
        auth_header="Authorization",
        response_list_key="data",
    ),
    "xai": ProviderConfig(
        label="xAI",
        endpoint="https://api.x.ai/v1/models",
        auth_header="Authorization",
        response_list_key="data",
    ),
    "anthropic": ProviderConfig(
        label="Anthropic Claude",
        endpoint="https://api.anthropic.com/v1/models?limit=1",
        auth_header="x-api-key",
        response_list_key="data",
        extra_headers=(("anthropic-version", "2023-06-01"),),
    ),
    "groq": ProviderConfig(
        label="Groq-hosted Llama",
        endpoint="https://api.groq.com/openai/v1/models",
        auth_header="Authorization",
        response_list_key="data",
    ),
}


class ProviderValidationError(RuntimeError):
    """Safe-to-display provider authentication or availability error."""


def validate_api_key(
    provider: str,
    api_key: str,
    *,
    opener: Callable[..., Any] | None = None,
    timeout: int = 15,
) -> int:
    """Validate a key with one non-generation GET and return accessible models.

    ``opener`` can be injected by tests. API key values and response bodies are
    deliberately excluded from raised errors.
    """
    config = PROVIDERS.get(provider)
    if config is None:
        raise ProviderValidationError("Choose a supported API provider.")
    if not api_key or not api_key.strip():
        raise ProviderValidationError("Enter an API key to continue.")

    headers = {"Accept": "application/json", **dict(config.extra_headers)}
    if config.auth_header == "Authorization":
        headers[config.auth_header] = f"Bearer {api_key.strip()}"
    else:
        headers[config.auth_header] = api_key.strip()

    endpoint = config.endpoint
    if config.api_key_query_parameter:
        separator = "&" if "?" in endpoint else "?"
        endpoint = f"{endpoint}{separator}key={urllib.parse.quote(api_key.strip(), safe='')}"

    request = urllib.request.Request(endpoint, headers=headers, method="GET")
    request_opener = opener or urllib.request.urlopen
    try:
        with request_opener(request, timeout=timeout) as response:
            body = response.read().decode("utf-8-sig")
    except urllib.error.HTTPError as error:
        response_body = error.read().decode("utf-8", errors="replace").lower()
        if error.code == 402 or any(
            marker in response_body
            for marker in ("insufficient_quota", "billing", "payment required", "out of credits")
        ):
            raise ProviderValidationError("Payment gateway unavailable.") from None
        if error.code in (401, 403):
            raise ProviderValidationError("The API key was rejected by this provider.") from None
        if error.code == 429:
            raise ProviderValidationError("The provider rate limit was reached; try again later.") from None
        raise ProviderValidationError(
            f"{config.label} could not validate the key (HTTP {error.code})."
        ) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ProviderValidationError(
            f"Could not reach {config.label}; check your connection and try again."
        ) from None

    try:
        payload: Any = json.loads(body)
    except json.JSONDecodeError:
        raise ProviderValidationError(f"{config.label} returned an unreadable response.") from None
    models = payload.get(config.response_list_key) if isinstance(payload, Mapping) else None
    if not isinstance(models, list):
        raise ProviderValidationError(f"{config.label} returned an unexpected model-list response.")
    if not models:
        raise ProviderValidationError(f"The key is valid, but {config.label} returned no available models.")
    return len(models)
