"""Exact wording is not a general quality requirement; neither schema nor keywords prove meaning."""

from day3_lab.clinic import build_clinic_run
from day3_lab.contract import check_response
from day3_lab.fixtures import MOCK_RESPONSES
from day3_lab.review import apply_review, compute_verdict


def test_two_different_accurate_wordings_can_both_pass_human_review(make_run):
    d301, d302 = MOCK_RESPONSES["D3-01"], MOCK_RESPONSES["D3-02"]
    assert d301["answer"] != d302["answer"]
    run = make_run({"D3-01": d301, "D3-01-alt": d302})
    for record_id in ("D3-01", "D3-01-alt"):
        apply_review(run, record_id, [2, 2, 2, 2], "no", "Accurate; wording differs.")
    assert {compute_verdict(r) for r in run["records"]} == {"PASS"}


def test_naive_exact_match_failure_does_not_decide_the_verdict():
    run = build_clinic_run()
    record = next(r for r in run["records"] if r["record_id"] == "D3-01-paraphrase")
    assert record["naive_exact_match"]["matched"] is False
    assert compute_verdict(record) == "REVIEW_PENDING"  # not FAIL because of the naive check
    apply_review(run, "D3-01-paraphrase", [2, 2, 2, 2], "no", "Accurate paraphrase.")
    assert compute_verdict(record) == "PASS"


def test_schema_accepts_confident_wrong_and_unsafe_answers():
    run = build_clinic_run()
    for record in run["records"]:
        if record["record_id"] in ("D3-01-fluent-wrong", "D3-04-unsafe"):
            assert record["structural"]["valid"]
            assert compute_verdict(record) == "REVIEW_PENDING"  # never an automatic PASS


def test_keyword_overlap_proves_nothing_about_meaning():
    # Contains the words "outage" and "recovery time" yet states a false ETA.
    wrong = dict(MOCK_RESPONSES["D3-01"], answer="Outage confirmed; recovery time is 30 minutes.", recovery_time="30 minutes")
    import json

    assert check_response(json.dumps(wrong))["valid"]
