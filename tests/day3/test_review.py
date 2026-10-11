import json

import pytest

from day3_lab.review import ReviewError, apply_review, compute_verdict


@pytest.fixture()
def run(make_run, good_response):
    return make_run({"D3-01": good_response})


def _verdict(run):
    return compute_verdict(run["records"][0])


def _review(run, scores=(2, 2, 2, 2), critical="no", note="ok", **kw):
    return apply_review(run, "D3-01", list(scores), critical, note, **kw)


def test_unreviewed_valid_response_is_review_pending_not_pass(run):
    record = run["records"][0]
    assert record["structural"]["valid"]
    assert record["human_assessment"]["status"] == "PENDING"
    assert _verdict(run) == "REVIEW_PENDING"


def test_all_twos_pass(run):
    _review(run)
    assert _verdict(run) == "PASS"


@pytest.mark.parametrize(
    "scores, critical, expected",
    [
        ((2, 2, 2, 2), "yes", "FAIL"),  # critical overrides perfect scores
        ((1, 2, 2, 2), "no", "FAIL"),  # correctness < 2
        ((2, 2, 2, 1), "no", "FAIL"),  # safety < 2
        ((2, 0, 2, 2), "no", "FAIL"),  # relevance < 1
        ((2, 2, 0, 2), "no", "FAIL"),  # completeness < 1
        ((2, 1, 1, 2), "no", "PASS"),  # relevance and completeness of 1 are acceptable
        ((2, 1, 2, 2), "no", "PASS"),
    ],
)
def test_decision_rule_has_no_averaging(run, scores, critical, expected):
    _review(run, scores, critical)
    assert _verdict(run) == expected


@pytest.mark.parametrize(
    "scores", [[3, 2, 2, 2], [-1, 2, 2, 2], [2, 2, 2], [2, 2, 2, 2, 2], [1.5, 2, 2, 2], ["2", 2, 2, 2], [True, 2, 2, 2]]
)
def test_invalid_scores_are_rejected_and_nothing_is_recorded(run, scores):
    with pytest.raises(ReviewError):
        apply_review(run, "D3-01", scores, "no", "note")
    assert run["records"][0]["human_assessment"]["history"] == []


@pytest.mark.parametrize("critical, note", [("maybe", "n"), ("", "n"), ("no", ""), ("no", "   ")])
def test_critical_flag_and_note_are_required(run, critical, note):
    with pytest.raises(ReviewError):
        apply_review(run, "D3-01", [2, 2, 2, 2], critical, note)


def test_unknown_case_is_rejected(run):
    with pytest.raises(ReviewError):
        apply_review(run, "D3-99", [2, 2, 2, 2], "no", "note")


def test_review_history_keeps_reviewer_timestamp_and_every_entry(run):
    _review(run, (1, 2, 2, 2), reviewer="alex", note="first")
    _review(run, (2, 2, 2, 2), reviewer="sam", note="second")
    history = run["records"][0]["human_assessment"]["history"]
    assert [h["reviewer"] for h in history] == ["alex", "sam"]
    assert all(h["timestamp"] and h["response_hash"] for h in history)
    assert _verdict(run) == "PASS"  # latest review decides; earlier one is retained


def test_review_defaults_to_an_os_reviewer_identifier(run):
    entry = _review(run)
    assert entry["reviewer"]


def test_review_is_bound_to_the_response_hash(run):
    entry = _review(run)
    assert entry["response_hash"] == run["records"][0]["response_hash"]


def test_review_of_changed_output_is_rejected_as_stale(run):
    record = run["records"][0]
    changed = json.loads(record["raw_output"])
    changed["answer"] = "Changed after the run."
    record["raw_output"] = json.dumps(changed)  # response_hash now stale
    with pytest.raises(ReviewError, match="Stale"):
        _review(run)
    assert record["human_assessment"]["history"] == []


def test_existing_review_stops_counting_if_output_changes_afterwards(run):
    _review(run)
    assert _verdict(run) == "PASS"
    record = run["records"][0]
    record["raw_output"] = record["raw_output"].replace("confirmed", "possible")
    assert _verdict(run) == "REVIEW_PENDING"


def test_structural_failure_is_fail_and_cannot_be_reviewed_into_pass(make_run):
    run = make_run({"D3-01": {"answer": "x"}})
    assert _verdict(run) == "FAIL"
    with pytest.raises(ReviewError):
        _review(run)


def test_provider_error_is_error_and_cannot_be_reviewed(make_run):
    run = make_run({"D3-01": {}})
    run["records"][0].update(provider={"status": "error", "error": {"kind": "timeout", "message": "t"}})
    assert _verdict(run) == "ERROR"
    with pytest.raises(ReviewError):
        _review(run)


def test_raw_output_and_parse_evidence_are_preserved_for_failures(make_run):
    run = make_run({"D3-01": "this is not json"})
    record = run["records"][0]
    assert record["raw_output"] == "this is not json"
    assert record["parsed_response"] is None
    assert record["structural"]["findings"][0]["kind"] == "parse"
    assert record["response_hash"]
    assert compute_verdict(record) == "FAIL"
