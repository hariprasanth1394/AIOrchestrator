import json

import pytest

from day3_lab.contract import check_response
from day3_lab.fixtures import MOCK_RESPONSES


@pytest.mark.parametrize("case_id", sorted(MOCK_RESPONSES))
def test_every_mock_response_is_structurally_valid(case_id):
    assert check_response(json.dumps(MOCK_RESPONSES[case_id]))["valid"]


def _check(obj):
    return check_response(json.dumps(obj))


@pytest.mark.parametrize("missing", ["answer", "service_status", "recovery_time", "next_step"])
def test_missing_field_fails(good_response, missing):
    del good_response[missing]
    result = _check(good_response)
    assert not result["valid"]
    assert any(missing in f["message"] for f in result["findings"])


def test_extra_field_fails(good_response):
    good_response["confidence"] = 0.9
    result = _check(good_response)
    assert not result["valid"]
    assert any("confidence" in f["message"] for f in result["findings"])


@pytest.mark.parametrize(
    "field, value",
    [
        ("answer", 42),
        ("answer", ""),
        ("answer", "   "),
        ("answer", None),
        ("next_step", ""),
        ("next_step", ["wait"]),
        ("service_status", "down"),
        ("service_status", "OUTAGE"),
        ("service_status", 1),
        ("recovery_time", 30),
        ("recovery_time", False),
        ("recovery_time", ["30 minutes"]),
    ],
)
def test_wrong_types_and_enums_fail_without_coercion(good_response, field, value):
    good_response[field] = value
    result = _check(good_response)
    assert not result["valid"]
    # The invalid value is kept as evidence, never repaired.
    assert result["parsed"][field] == value


@pytest.mark.parametrize("raw", ["not json", "", "[]", '"text"', "null", "```json\n{}\n```"])
def test_non_object_or_unparseable_output_fails(raw):
    result = check_response(raw)
    assert not result["valid"]
    assert result["findings"]


def test_none_output_fails():
    assert not check_response(None)["valid"]


def test_null_recovery_time_is_allowed(good_response):
    good_response["recovery_time"] = None
    assert _check(good_response)["valid"]


def test_result_states_that_schema_is_not_accuracy(good_response):
    assert "not evidence of factual accuracy or safety" in _check(good_response)["note"]
