"""Provider tests. The live adapter is exercised only with fake clients: no network."""

import json
from types import SimpleNamespace

import pytest

from day3_lab.contract import API_RESPONSE_SCHEMA, check_response
from day3_lab.fixtures import MOCK_RESPONSES
from day3_lab.providers import live
from day3_lab.providers.base import ConfigurationError
from day3_lab.providers.live import LiveProvider
from day3_lab.providers.mock import MockProvider
from day3_lab.runner import build_record


def test_mock_provider_is_labelled_and_has_no_model(cases):
    record = build_record("D3-01", cases["D3-01"], MockProvider(MOCK_RESPONSES), "prompt")
    assert record["label"] == "MOCK"
    assert record["token_usage"] is None


def test_changing_the_prompt_does_not_change_mock_output(cases):
    provider = MockProvider(MOCK_RESPONSES)
    a = provider.generate("D3-01", cases["D3-01"], "prompt A").raw_output
    b = provider.generate("D3-01", cases["D3-01"], "a completely different prompt").raw_output
    assert a == b


def test_mock_reports_missing_fixture_as_error(cases):
    result = MockProvider({}).generate("D3-01", cases["D3-01"], "p")
    assert result.error["kind"] == "no_fixture"


# ---- live adapter with a fake client -------------------------------------------------


class FakeResponses:
    def __init__(self, response=None, exc=None):
        self.response, self.exc, self.calls = response, exc, []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.exc:
            raise self.exc
        return self.response


def _provider(response=None, exc=None, key="sk-test-secret-123"):
    responses = FakeResponses(response, exc)
    client = SimpleNamespace(responses=responses)
    return LiveProvider("test-model", client, key), responses


def _ok_response(text, usage=None):
    return SimpleNamespace(
        status="completed",
        output=[SimpleNamespace(type="message", content=[SimpleNamespace(type="output_text", text=text)])],
        output_text=text,
        usage=usage,
    )


def test_live_from_env_requires_both_settings(monkeypatch):
    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY, OPENAI_MODEL"):
        LiveProvider.from_env()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with pytest.raises(ConfigurationError, match="OPENAI_MODEL") as info:
        LiveProvider.from_env()
    assert "sk-test" not in str(info.value)


def test_live_from_env_builds_client_with_bounded_timeout_and_retries(monkeypatch):
    seen = {}
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "some-model")
    monkeypatch.setattr(live, "build_client", lambda key: seen.setdefault("key", key) or object())
    provider = LiveProvider.from_env()
    assert provider.model == "some-model"
    assert live.REQUEST_TIMEOUT_SECONDS > 0 and 0 <= live.MAX_RETRIES <= 3


def test_live_success_sends_structured_output_request(cases):
    text = json.dumps(MOCK_RESPONSES["D3-01"])
    usage = SimpleNamespace(input_tokens=10, output_tokens=5, total_tokens=15)
    provider, responses = _provider(_ok_response(text, usage))
    result = provider.generate("D3-01", cases["D3-01"], "PROMPT")
    assert result.raw_output == text
    assert result.token_usage == {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}
    call = responses.calls[0]
    assert call["model"] == "test-model"
    assert call["instructions"] == "PROMPT"
    assert call["text"]["format"]["strict"] is True
    assert call["text"]["format"]["schema"] == API_RESPONSE_SCHEMA
    assert call["timeout"] > 0 and call["max_output_tokens"] > 0
    # Only the question and approved context are sent, not the rubric expectations.
    sent = json.loads(call["input"])
    assert set(sent) == {"question", "approved_context"}


def test_live_token_usage_is_never_invented(cases):
    provider, _ = _provider(_ok_response(json.dumps(MOCK_RESPONSES["D3-01"]), usage=None))
    assert provider.generate("D3-01", cases["D3-01"], "p").token_usage is None


def test_live_refusal_is_an_explicit_error(cases):
    refusal = SimpleNamespace(
        status="completed",
        output=[SimpleNamespace(type="message", content=[SimpleNamespace(type="refusal", refusal="No.")])],
        output_text="",
        usage=None,
    )
    result = _provider(refusal)[0].generate("D3-01", cases["D3-01"], "p")
    assert result.raw_output is None
    assert result.error["kind"] == "refusal"


def test_live_incomplete_and_empty_responses_are_errors(cases):
    incomplete = SimpleNamespace(status="incomplete", incomplete_details="max_output_tokens", output=[], output_text="", usage=None)
    assert _provider(incomplete)[0].generate("D3-01", cases["D3-01"], "p").error["kind"] == "incomplete"
    empty = SimpleNamespace(status="completed", output=[], output_text="", usage=None)
    assert _provider(empty)[0].generate("D3-01", cases["D3-01"], "p").error["kind"] == "empty_output"


class APITimeoutError(Exception):
    pass


def test_live_timeout_and_provider_failures_are_reported_with_secrets_redacted(cases):
    timeout = _provider(exc=APITimeoutError("Request timed out."))[0].generate("D3-01", cases["D3-01"], "p")
    assert timeout.error["kind"] == "timeout"
    failure = _provider(exc=RuntimeError("Bad key sk-test-secret-123 rejected"))[0].generate(
        "D3-01", cases["D3-01"], "p"
    )
    assert failure.error["kind"] == "provider_error"
    assert "sk-test-secret-123" not in failure.error["message"]


def test_provider_failure_becomes_error_verdict_never_a_mock_answer(cases):
    provider, _ = _provider(exc=RuntimeError("boom"))
    record = build_record("D3-01", cases["D3-01"], provider, "p")
    assert record["verdict"] == "ERROR"
    assert record["label"] == "LIVE"
    assert record["raw_output"] is None
    assert not check_response(record["raw_output"])["valid"]
