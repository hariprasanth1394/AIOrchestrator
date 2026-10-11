"""Loading and validating the Day 3 dataset and rubric (offline, read-only)."""

import json
from pathlib import Path

from day3_lab.contract import SERVICE_STATUSES, check_response
from day3_lab.paths import DATASET_PATH, RUBRIC_PATH

EXPECTED_CASE_COUNT = 10
DIMENSIONS = ["correctness", "relevance", "completeness", "safety"]
CASE_KEYS = {
    "case_id", "category", "question", "approved_context",
    "expected_behaviour", "prohibited_behaviour", "evaluation_method",
    "requirement_ids",
}
CONTEXT_KEYS = {"device", "service_status", "recovery_time", "guidance"}


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_cases(path: Path = DATASET_PATH) -> list[dict]:
    return load_json(path)["cases"]


def load_rubric(path: Path = RUBRIC_PATH) -> dict:
    return load_json(path)


def _is_str_list(value) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(v, str) and v.strip() for v in value)
    )


def validate_dataset(dataset) -> list[str]:
    """Return a list of problems; empty means the dataset is structurally valid."""
    if not isinstance(dataset, dict):
        return ["dataset must be a JSON object"]
    problems: list[str] = []
    if dataset.get("dataset_version") != "day3-v1":
        problems.append("dataset_version must be 'day3-v1'")
    if dataset.get("synthetic") is not True:
        problems.append("synthetic must be true")
    cases = dataset.get("cases")
    if not isinstance(cases, list):
        return problems + ["cases must be a list"]
    if len(cases) != EXPECTED_CASE_COUNT:
        problems.append(f"expected {EXPECTED_CASE_COUNT} cases, found {len(cases)}")

    seen: set = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            problems.append(f"cases[{index}] must be an object")
            continue
        cid = case.get("case_id")
        label = cid if isinstance(cid, str) and cid.strip() else f"cases[{index}]"
        if label.startswith("cases["):
            problems.append(f"{label}: case_id must be a non-empty string")
        elif cid in seen:
            problems.append(f"{label}: duplicate case_id")
        else:
            seen.add(cid)
        missing = CASE_KEYS - set(case)
        extra = set(case) - CASE_KEYS
        if missing:
            problems.append(f"{label}: missing keys {sorted(missing)}")
        if extra:
            problems.append(f"{label}: unexpected keys {sorted(extra)}")
        for key in ("category", "question"):
            if key in case and not (isinstance(case[key], str) and case[key].strip()):
                problems.append(f"{label}: {key} must be a non-empty string")
        for key in ("expected_behaviour", "prohibited_behaviour", "requirement_ids"):
            if key in case and not _is_str_list(case[key]):
                problems.append(f"{label}: {key} must be a non-empty list of strings")
        if case.get("evaluation_method") != ["schema", "human_rubric"]:
            problems.append(f"{label}: evaluation_method must be ['schema', 'human_rubric']")
        problems += _validate_context(label, case.get("approved_context"))
    return problems


def _validate_context(label: str, ctx) -> list[str]:
    if not isinstance(ctx, dict):
        return [f"{label}: approved_context must be an object"]
    if set(ctx) != CONTEXT_KEYS:
        return [f"{label}: approved_context keys must be {sorted(CONTEXT_KEYS)}"]
    problems = []
    for key in ("device", "recovery_time"):
        if ctx[key] is not None and not isinstance(ctx[key], str):
            problems.append(f"{label}: approved_context.{key} must be a string or null")
    if ctx["service_status"] not in SERVICE_STATUSES:
        problems.append(
            f"{label}: approved_context.service_status must be one of {SERVICE_STATUSES}"
        )
    if not (isinstance(ctx["guidance"], str) and ctx["guidance"].strip()):
        problems.append(f"{label}: approved_context.guidance must be a non-empty string")
    return problems


def validate_rubric(rubric, dataset_version: str | None = None) -> list[str]:
    if not isinstance(rubric, dict):
        return ["rubric must be a JSON object"]
    problems: list[str] = []
    if not rubric.get("version"):
        problems.append("rubric version is missing")
    elif dataset_version and rubric["version"] != dataset_version:
        problems.append(
            f"rubric version {rubric['version']!r} does not match dataset {dataset_version!r}"
        )
    if rubric.get("dimension_order") != DIMENSIONS:
        problems.append(f"dimension_order must be {DIMENSIONS}")
    scales = rubric.get("scales")
    if not isinstance(scales, dict) or list(scales) != DIMENSIONS:
        problems.append("scales must define exactly the four dimensions in order")
    else:
        for dim, scale in scales.items():
            if not isinstance(scale, dict) or set(scale) != {"0", "1", "2"}:
                problems.append(f"scales.{dim} must define exactly 0, 1 and 2")
            elif not all(isinstance(v, str) and v.strip() for v in scale.values()):
                problems.append(f"scales.{dim} descriptions must be non-empty strings")
    for key in ("decision_rule", "review_scope"):
        if not (isinstance(rubric.get(key), str) and rubric[key].strip()):
            problems.append(f"{key} must be a non-empty string")
    if not _is_str_list(rubric.get("critical_examples")):
        problems.append("critical_examples must be a non-empty list of strings")
    return problems


def validate_all(dataset_path: Path = DATASET_PATH, rubric_path: Path = RUBRIC_PATH):
    """Validate dataset, rubric and mock-fixture coverage.

    Returns (problems, case_count, rubric_version).
    """
    from day3_lab.fixtures import MOCK_RESPONSES

    dataset = load_json(dataset_path)
    rubric = load_json(rubric_path)
    version = dataset.get("dataset_version") if isinstance(dataset, dict) else None
    problems = validate_dataset(dataset) + validate_rubric(rubric, version)

    cases = dataset.get("cases", []) if isinstance(dataset, dict) else []
    case_ids = [c["case_id"] for c in cases if isinstance(c, dict) and "case_id" in c]
    if set(case_ids) != set(MOCK_RESPONSES):
        problems.append("mock fixtures do not cover exactly the dataset case IDs")
    for cid, response in MOCK_RESPONSES.items():
        if not check_response(json.dumps(response))["valid"]:
            problems.append(f"mock fixture {cid} fails the response contract")
    rubric_version = rubric.get("version") if isinstance(rubric, dict) else None
    return problems, len(case_ids), rubric_version
