"""Mock provider: replays fixed, reviewed responses. No network, no model.

Success here validates the lab workflow only, not live model quality. The
prompt is accepted but ignored, so changing it never changes these outputs.
"""

import json

from day3_lab.providers.base import ProviderResult


class MockProvider:
    name = "mock"
    label = "MOCK"
    model = None

    def __init__(self, responses: dict[str, dict | str]):
        """responses maps a record_id to a response object (or raw string)."""
        self._responses = responses

    def generate(self, record_id: str, case: dict, prompt_text: str) -> ProviderResult:
        if record_id not in self._responses:
            return ProviderResult(
                error={"kind": "no_fixture", "message": f"No mock fixture for {record_id}."}
            )
        response = self._responses[record_id]
        raw = response if isinstance(response, str) else json.dumps(response, indent=2)
        return ProviderResult(raw_output=raw)
