import json
import webbrowser

import pytest

from day3_lab.cli import main
from day3_lab.review import compute_verdict


def _load(path):
    return json.loads((path / "run.json").read_text(encoding="utf-8"))


def test_validate_data_prints_ten_cases(capsys):
    assert main(["validate-data"]) == 0
    assert "10 cases" in capsys.readouterr().out


def test_mock_run_saves_evidence_and_starts_pending(tmp_path):
    out = tmp_path / "demo"
    assert main(["run", "--mode", "mock", "--case", "D3-01", "--out", str(out)]) == 0
    run = _load(out)
    assert (out / "run.html").is_file()
    assert run["mode"] == "mock" and run["label"] == "MOCK" and run["model"] is None
    for key in ("run_id", "timestamp", "commit", "dirty", "prompt_hash", "dataset_hash", "rubric_version"):
        assert key in run
    record = run["records"][0]
    assert record["human_assessment"]["status"] == "PENDING"
    assert record["verdict"] == "REVIEW_PENDING"
    assert record["token_usage"] is None
    assert record["approved_context"]["service_status"] == "outage"
    assert record["raw_output"] and record["parsed_response"] and record["response_hash"]
    assert "MOCK" in (out / "run.html").read_text(encoding="utf-8")


def test_full_mock_run_covers_all_ten_cases(tmp_path):
    assert main(["run", "--mode", "mock", "--out", str(tmp_path / "all")]) == 0
    assert len(_load(tmp_path / "all")["records"]) == 10


def test_run_refuses_to_overwrite_and_leaves_original_untouched(tmp_path, capsys):
    out = tmp_path / "demo"
    main(["run", "--mode", "mock", "--case", "D3-01", "--out", str(out)])
    before = (out / "run.json").read_text(encoding="utf-8")
    assert main(["run", "--mode", "mock", "--case", "D3-02", "--out", str(out)]) == 2
    assert "new --out directory" in capsys.readouterr().err
    assert (out / "run.json").read_text(encoding="utf-8") == before


def test_unknown_case_is_an_error(tmp_path):
    assert main(["run", "--mode", "mock", "--case", "D3-99", "--out", str(tmp_path / "x")]) == 2


def test_live_without_configuration_fails_loudly_without_mock_fallback(tmp_path, capsys):
    out = tmp_path / "live"
    assert main(["run", "--mode", "live", "--case", "D3-01", "--out", str(out)]) == 2
    assert "OPENAI_API_KEY" in capsys.readouterr().err
    assert not out.exists()


def test_review_round_trip_updates_json_and_regenerates_html(tmp_path):
    out = tmp_path / "demo"
    main(["run", "--mode", "mock", "--case", "D3-01", "--out", str(out)])
    html_before = (out / "run.html").read_text(encoding="utf-8")
    argv = ["review", "--report", str(out / "run.json"), "--case", "D3-01", "--scores", "2", "2", "2", "2",
            "--critical", "no", "--note", "Supported by supplied context.", "--reviewer", "tester"]
    assert main(argv) == 0
    record = _load(out)["records"][0]
    assert record["verdict"] == "PASS"
    assert record["human_assessment"]["history"][0]["reviewer"] == "tester"
    html_after = (out / "run.html").read_text(encoding="utf-8")
    assert html_after != html_before and "tester" in html_after


@pytest.mark.parametrize(
    "extra",
    [["--scores", "2", "2", "2", "3"], ["--scores", "2", "2", "2"], ["--scores", "a", "2", "2", "2"]],
)
def test_review_rejects_bad_scores_at_the_command_line(tmp_path, extra):
    out = tmp_path / "demo"
    main(["run", "--mode", "mock", "--case", "D3-01", "--out", str(out)])
    with pytest.raises(SystemExit):
        main(["review", "--report", str(out / "run.json"), "--case", "D3-01", *extra,
              "--critical", "no", "--note", "n"])
    assert _load(out)["records"][0]["human_assessment"]["history"] == []


def test_review_rejects_stale_report_through_the_cli(tmp_path, capsys):
    out = tmp_path / "demo"
    main(["run", "--mode", "mock", "--case", "D3-01", "--out", str(out)])
    run = _load(out)
    run["records"][0]["raw_output"] = run["records"][0]["raw_output"].replace("confirmed", "rumoured")
    (out / "run.json").write_text(json.dumps(run), encoding="utf-8")
    code = main(["review", "--report", str(out / "run.json"), "--case", "D3-01", "--scores", "2", "2", "2", "2",
                 "--critical", "no", "--note", "n"])
    assert code == 2 and "Stale" in capsys.readouterr().err


def test_html_escapes_response_text(tmp_path, make_run):
    from day3_lab.report import render_html

    payload = {"answer": "<script>alert(1)</script>", "service_status": "outage",
               "recovery_time": None, "next_step": "<img src=x onerror=alert(2)>"}
    html = render_html(make_run({"D3-01": payload}))
    assert "<script>alert(1)</script>" not in html
    assert "<img src=x" not in html
    assert "&lt;script&gt;" in html


def test_open_uses_standard_library_browser(tmp_path, monkeypatch):
    out = tmp_path / "demo"
    main(["run", "--mode", "mock", "--case", "D3-01", "--out", str(out)])
    opened = []
    monkeypatch.setattr(webbrowser, "open", lambda url: opened.append(url) or True)
    assert main(["open", str(out / "run.html")]) == 0
    assert opened and opened[0].startswith("file:")
    assert main(["open", str(tmp_path / "missing.html")]) == 2


# ---- clinic ---------------------------------------------------------------------------


def test_clinic_original_teaches_schema_pass_with_human_pending(tmp_path):
    out = tmp_path / "clinic"
    assert main(["clinic", "--out", str(out)]) == 0
    assert {p.name for p in out.iterdir()} == {"run.json", "run.html", "clinic_notes.md"}
    records = {r["record_id"]: r for r in _load(out)["records"]}
    assert set(records) == {"D3-01-fluent-wrong", "D3-04-unsafe", "D3-01-paraphrase"}
    assert all(r["structural"]["valid"] and r["label"] == "MOCK" for r in records.values())
    assert all(r["verdict"] == "REVIEW_PENDING" for r in records.values())  # no auto human scores

    wrong = records["D3-01-fluent-wrong"]["parsed_response"]
    assert "30 minutes" in wrong["answer"] and wrong["recovery_time"] == "30 minutes"
    unsafe = records["D3-04-unsafe"]["parsed_response"]
    assert "password" in unsafe["answer"] and "OTP" in unsafe["answer"]

    naive = records["D3-01-paraphrase"]["naive_exact_match"]
    assert naive["matched"] is False and "not a quality verdict" in naive["warning"]


def test_clinic_human_review_produces_the_taught_outcomes(tmp_path):
    out = tmp_path / "clinic"
    main(["clinic", "--out", str(out)])
    report = str(out / "run.json")
    main(["review", "--report", report, "--case", "D3-01-fluent-wrong", "--scores", "0", "2", "2", "2",
          "--critical", "no", "--note", "Invented 30 minute ETA."])
    main(["review", "--report", report, "--case", "D3-04-unsafe", "--scores", "0", "2", "2", "0",
          "--critical", "yes", "--note", "Requests password and OTP."])
    verdicts = {r["record_id"]: r["verdict"] for r in _load(out)["records"]}
    assert verdicts["D3-01-fluent-wrong"] == "FAIL"
    assert verdicts["D3-04-unsafe"] == "FAIL"
    assert verdicts["D3-01-paraphrase"] == "REVIEW_PENDING"  # stays pending until a human acts


def test_clinic_refuses_overwrite(tmp_path):
    out = tmp_path / "clinic"
    assert main(["clinic", "--out", str(out)]) == 0
    assert main(["clinic", "--out", str(out)]) == 2


def test_corrected_clinic_is_separate_labelled_and_review_free(tmp_path):
    original, fixed = tmp_path / "clinic", tmp_path / "clinic-fixed"
    main(["clinic", "--out", str(original)])
    main(["review", "--report", str(original / "run.json"), "--case", "D3-01-fluent-wrong",
          "--scores", "0", "2", "2", "2", "--critical", "no", "--note", "Invented ETA."])
    original_json = (original / "run.json").read_text(encoding="utf-8")

    assert main(["clinic", "--variant", "corrected", "--out", str(fixed)]) == 0
    assert (original / "run.json").read_text(encoding="utf-8") == original_json  # untouched

    before = {r["record_id"]: r for r in json.loads(original_json)["records"]}
    after_run = _load(fixed)
    after = {r["record_id"]: r for r in after_run["records"]}
    assert set(after) == set(before)  # same IDs for comparison
    assert "NOT a demonstrated live-model improvement" in after_run["correction_note"]

    assert after["D3-01-fluent-wrong"]["parsed_response"]["recovery_time"] is None
    assert "30 minutes" not in after["D3-01-fluent-wrong"]["raw_output"]
    secret_text = after["D3-04-unsafe"]["parsed_response"]["answer"].lower()
    assert "don't share" in secret_text and "send me" not in secret_text
    assert after["D3-01-fluent-wrong"]["response_hash"] != before["D3-01-fluent-wrong"]["response_hash"]

    # The earlier review is not carried over to changed responses.
    for record in after.values():
        assert record["human_assessment"]["history"] == []
        assert compute_verdict(record) == "REVIEW_PENDING"
