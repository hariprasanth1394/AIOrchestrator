"""Day 3 fixtures. Everything here is offline: no network, no API key, no app import.

The Day 2 fixtures (client, auth_headers, assert_matches_schema) are not needed
by the lab, so nothing was moved into tests/conftest.py.
"""

import json

import pytest

from day3_lab.dataset import load_cases
from day3_lab.fixtures import MOCK_RESPONSES
from day3_lab.providers.mock import MockProvider
from day3_lab.runner import build_run


@pytest.fixture(autouse=True)
def no_live_credentials(monkeypatch):
    """Make sure a developer's real key can never reach a Day 3 test."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)


@pytest.fixture()
def cases():
    return {c["case_id"]: c for c in load_cases()}


@pytest.fixture()
def make_run(cases):
    """Build an in-memory run from {record_id: response object or raw string}."""

    def _make(responses: dict, case_id: str = "D3-01"):
        items = [(rid, cases[case_id]) for rid in responses]
        return build_run(MockProvider(responses), items)

    return _make


@pytest.fixture()
def good_response():
    return json.loads(json.dumps(MOCK_RESPONSES["D3-01"]))
