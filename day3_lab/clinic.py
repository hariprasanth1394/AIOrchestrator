"""Controlled failure clinic: fixed MOCK fixtures that teach what each check can and cannot see."""

import json

from day3_lab.dataset import load_cases
from day3_lab.fixtures import CLINIC_FIXTURES, MOCK_RESPONSES
from day3_lab.providers.mock import MockProvider
from day3_lab.review import response_hash
from day3_lab.runner import build_run

CORRECTION_NOTE = (
    "Controlled mock-fixture correction: the fixed responses were rewritten by hand "
    "from the approved context. This is NOT a demonstrated live-model improvement. "
    "Human reviews are never copied from the original run; every response here "
    "starts PENDING."
)


def _raw(response: dict) -> str:
    # Same serialisation as MockProvider, so hashes compare across runs.
    return json.dumps(response, indent=2)


def build_clinic_run(variant: str = "original") -> dict:
    if variant not in ("original", "corrected"):
        raise ValueError(f"Unknown clinic variant {variant!r}.")
    cases = {c["case_id"]: c for c in load_cases()}
    items = [(fx["record_id"], cases[fx["case_id"]]) for fx in CLINIC_FIXTURES]
    provider = MockProvider({fx["record_id"]: fx[variant] for fx in CLINIC_FIXTURES})

    extra = {"variant": variant}
    if variant == "corrected":
        extra["correction_note"] = CORRECTION_NOTE
    run = build_run(provider, items, kind="clinic", extra=extra)

    reference = MOCK_RESPONSES["D3-01"]["answer"]
    for record, fx in zip(run["records"], CLINIC_FIXTURES):
        record["teaching"] = fx["teaching"]
        record["original_response_hash"] = response_hash(_raw(fx["original"]))
        if fx["record_id"] == "D3-01-paraphrase":
            answer = (record["parsed_response"] or {}).get("answer")
            record["naive_exact_match"] = {
                "reference_sentence": reference,
                "matched": answer == reference,
                "warning": (
                    "Deliberately naive exact-string comparison, shown only to "
                    "demonstrate its weakness. It is not a quality verdict."
                ),
            }
    return run


def clinic_notes_markdown(run: dict) -> str:
    corrected = run["variant"] == "corrected"
    lines = [
        f"# Day 3 failure clinic notes ({run['variant']})",
        "",
        "**MOCK**: every response is a fixed, hand-written fixture. No model and no live call was used.",
        "",
    ]
    if corrected:
        lines += [f"> {run['correction_note']}", ""]
    lines += [
        f"Run ID: `{run['run_id']}`  ",
        f"Rubric: `{run['rubric_version']}`  ",
        f"Scope: {run['review_scope']}",
        "",
        "Schema validity shows shape only, never accuracy or safety. Human review",
        "scores are entered by a person; this tool never fills them in.",
        "",
    ]
    for record in run["records"]:
        t = record["teaching"]
        lines += [
            f"## {record['record_id']}: {t['name']}",
            "",
            f"- Case: {record['case_id']} ({record['category']})",
            f"- Structural check: {'PASS' if record['structural']['valid'] else 'FAIL'}",
            f"- Current verdict: **{record['verdict']}** (no human review entered yet)",
            f"- Teaching outcome in the original run: schema {t['expected_schema']}; human {t['expected_human']}",
            f"- Lesson: {t['lesson']}",
        ]
        naive = record.get("naive_exact_match")
        if naive:
            result = "matched" if naive["matched"] else "did NOT match"
            lines += [
                f"- Naive exact-string comparison: response {result} the reference sentence. {naive['warning']}",
            ]
        lines += [
            "- To record your own assessment (replace the four scores with your judgement,",
            "  ordered correctness relevance completeness safety):",
            "",
            "  ```",
            "  python -m day3_lab review --report <this-run>/run.json "
            f"--case {record['record_id']} --scores <c> <r> <comp> <s> --critical <yes|no> --note \"<why>\"",
            "  ```",
            "",
        ]
    return "\n".join(lines)
