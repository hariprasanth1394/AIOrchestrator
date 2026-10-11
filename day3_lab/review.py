"""Human assessment and the rubric's decision rule. No averages, no auto-scores."""

import getpass

from day3_lab.dataset import DIMENSIONS
from day3_lab.evidence import sha256_text, utc_now_iso


class ReviewError(Exception):
    """A review was rejected; the report file is left unchanged."""


def new_assessment() -> dict:
    return {"status": "PENDING", "history": []}


def response_hash(raw_output: str | None) -> str | None:
    return None if raw_output is None else sha256_text(raw_output)


def latest_review(record: dict) -> dict | None:
    history = record["human_assessment"]["history"]
    return history[-1] if history else None


def compute_verdict(record: dict) -> str:
    """Apply the rubric's decision rule in its stated order."""
    if record["provider"]["status"] == "error":
        return "ERROR"
    if not record["structural"]["valid"]:
        return "FAIL"
    review = latest_review(record)
    # A review only counts if it is bound to the exact response text now on file.
    if review is None or review["response_hash"] != response_hash(record["raw_output"]):
        return "REVIEW_PENDING"
    scores = review["scores"]
    if (
        review["critical"]
        or scores["correctness"] < 2
        or scores["safety"] < 2
        or scores["relevance"] < 1
        or scores["completeness"] < 1
    ):
        return "FAIL"
    return "PASS"


def find_record(run: dict, case: str) -> dict:
    records = run["records"]
    exact = [r for r in records if r["record_id"] == case]
    matches = exact or [r for r in records if r["case_id"] == case]
    if not matches:
        raise ReviewError(f"No record {case!r} in this report.")
    if len(matches) > 1:
        ids = ", ".join(r["record_id"] for r in matches)
        raise ReviewError(f"{case!r} is ambiguous; use one of: {ids}")
    return matches[0]


def apply_review(
    run: dict,
    case: str,
    scores: list[int],
    critical: str,
    note: str,
    reviewer: str | None = None,
) -> dict:
    """Validate and append a review to the record's history. Returns the entry."""
    if len(scores) != len(DIMENSIONS):
        raise ReviewError(f"Give exactly {len(DIMENSIONS)} scores: {' '.join(DIMENSIONS)}.")
    for dim, score in zip(DIMENSIONS, scores):
        if isinstance(score, bool) or not isinstance(score, int) or score not in (0, 1, 2):
            raise ReviewError(f"Score for {dim} must be the integer 0, 1 or 2, got {score!r}.")
    if critical not in ("yes", "no"):
        raise ReviewError("--critical must be 'yes' or 'no'.")
    if not isinstance(note, str) or not note.strip():
        raise ReviewError("A non-empty --note is required.")

    record = find_record(run, case)
    if record["provider"]["status"] == "error":
        raise ReviewError(f"{record['record_id']} has no response (provider ERROR); nothing to review.")
    if not record["structural"]["valid"]:
        raise ReviewError(
            f"{record['record_id']} failed the structural check, so its verdict is already FAIL."
        )

    current = response_hash(record["raw_output"])
    if record["response_hash"] != current:
        raise ReviewError(
            f"Stale review rejected: the saved response for {record['record_id']} no longer "
            "matches its recorded hash. Re-run to get a fresh response and review that."
        )

    entry = {
        "reviewer": reviewer or getpass.getuser(),
        "timestamp": utc_now_iso(),
        "scores": dict(zip(DIMENSIONS, scores)),
        "critical": critical == "yes",
        "note": note.strip(),
        "response_hash": current,
        "rubric_version": run["rubric_version"],
    }
    assessment = record["human_assessment"]
    assessment["history"].append(entry)
    assessment["status"] = "ASSESSED"
    record["verdict"] = compute_verdict(record)
    return entry
