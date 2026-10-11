"""Live OpenAI provider (Responses API with strict structured outputs).

Written against the official docs (Responses API, `text.format` json_schema)
and the installed `openai` SDK signatures. It has NOT been exercised against
the real service in this repository; tests use a fake client.

Settings come only from the environment: OPENAI_API_KEY and OPENAI_MODEL.
Nothing is hardcoded, no .env file is read, and nothing falls back to mock.
"""

import json
import os
import re

from day3_lab.contract import API_RESPONSE_SCHEMA
from day3_lab.providers.base import ConfigurationError, ProviderResult

REQUEST_TIMEOUT_SECONDS = 30.0
MAX_RETRIES = 2  # SDK-level retries for connection errors, 429 and 5xx
MAX_OUTPUT_TOKENS = 600

_KEY_LIKE = re.compile(r"sk-[A-Za-z0-9_\-\*\.]+")


def _redact(text: str, api_key: str | None) -> str:
    if api_key:
        text = text.replace(api_key, "[redacted]")
    return _KEY_LIKE.sub("[redacted]", text)[:500]


def build_client(api_key: str):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ConfigurationError(
            "The 'openai' package is not installed. Run: python -m pip install -e \".[dev]\""
        ) from exc
    return OpenAI(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=MAX_RETRIES)


class LiveProvider:
    name = "live"
    label = "LIVE"

    def __init__(self, model: str, client, api_key: str | None = None):
        self.model = model
        self._client = client
        self._api_key = api_key

    @classmethod
    def from_env(cls) -> "LiveProvider":
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        model = os.environ.get("OPENAI_MODEL", "").strip()
        missing = [n for n, v in (("OPENAI_API_KEY", api_key), ("OPENAI_MODEL", model)) if not v]
        if missing:
            raise ConfigurationError(
                "Live mode needs environment variable(s): "
                + ", ".join(missing)
                + ". Nothing was run and no mock fallback was used."
            )
        return cls(model, build_client(api_key), api_key)

    def generate(self, record_id: str, case: dict, prompt_text: str) -> ProviderResult:
        user_input = json.dumps(
            {"question": case["question"], "approved_context": case["approved_context"]}
        )
        try:
            response = self._client.responses.create(
                model=self.model,
                instructions=prompt_text,
                input=user_input,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "service_desk_response",
                        "schema": API_RESPONSE_SCHEMA,
                        "strict": True,
                    }
                },
                max_output_tokens=MAX_OUTPUT_TOKENS,
                store=False,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except Exception as exc:  # provider failures are evidence, not crashes
            kind = "timeout" if "Timeout" in type(exc).__name__ else "provider_error"
            message = f"{type(exc).__name__}: {_redact(str(exc), self._api_key)}"
            return ProviderResult(error={"kind": kind, "message": message})
        return self._read(response)

    def _read(self, response) -> ProviderResult:
        usage = _usage(response)
        for item in getattr(response, "output", None) or []:
            if getattr(item, "type", None) == "message":
                for part in getattr(item, "content", None) or []:
                    if getattr(part, "type", None) == "refusal":
                        refusal = getattr(part, "refusal", "")
                        return ProviderResult(
                            error={"kind": "refusal", "message": f"Model refused: {refusal}"},
                            token_usage=usage,
                        )
        if getattr(response, "status", "completed") == "incomplete":
            details = getattr(response, "incomplete_details", None)
            return ProviderResult(
                error={"kind": "incomplete", "message": f"Response incomplete: {details}"},
                token_usage=usage,
            )
        text = getattr(response, "output_text", None)
        if not text:
            return ProviderResult(
                error={"kind": "empty_output", "message": "Provider returned no text."},
                token_usage=usage,
            )
        return ProviderResult(raw_output=text, token_usage=usage)


def _usage(response) -> dict | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    fields = {
        name: getattr(usage, name, None)
        for name in ("input_tokens", "output_tokens", "total_tokens")
    }
    return fields if any(v is not None for v in fields.values()) else None
