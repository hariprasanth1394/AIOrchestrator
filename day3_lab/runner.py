"""Run cases through a provider and assemble the evidence record."""

import json
import time
from pathlib import Path

from day3_lab.contract import STRUCTURE_NOTE, check_response
from day3_lab.dataset import load_cases, load_rubric
from day3_lab.evidence import git_info, new_run_id, sha256_file, utc_now_iso
from day3_lab.paths import DATASET_PATH, PROMPT_PATH, ROOT, RUBRIC_PATH
from day3_lab.review import compute_verdict, new_assessment, response_hash

MOCK_NOTE = (
    "MOCK: responses are fixed, reviewed fixtures, not model output. A mock "
    "run validates the lab workflow only, not live model quality. Changing "
    "the prompt does not change them."
)


class OutputExistsError(Exception):
    """The --out directory already holds a previous run."""


def ensure_output_free(out_dir: Path, filenames: list[str]) -> None:
    clash = [n for n in filenames if (out_dir / n).exists()]
    if clash:
        raise OutputExistsError(
            f"{out_dir} already contains {', '.join(clash)}. Runs are never overwritten; "
            "choose a new --out directory."
        )


def build_record(record_id: str, case: dict, provider, prompt_text: str) -> dict:
    started = time.perf_counter()
    result = provider.generate(record_id, case, prompt_text)
    elapsed = round(time.perf_counter() - started, 4)

    structural = check_response(result.raw_output)
    parsed = structural.pop("parsed")
    record = {
        "record_id": record_id,
        "case_id": case["case_id"],
        "label": provider.label,
        "category": case["category"],
        "question": case["question"],
        "approved_context": case["approved_context"],
        "expected_behaviour": case["expected_behaviour"],
        "prohibited_behaviour": case["prohibited_behaviour"],
        "requirement_ids": case["requirement_ids"],
        "provider": {
            "status": "error" if result.error else "ok",
            "error": result.error,
        },
        "raw_output": result.raw_output,
        "parsed_response": parsed,
        "structural": structural,
        "response_hash": response_hash(result.raw_output),
        "elapsed_seconds": elapsed,
        "token_usage": result.token_usage,
        "human_assessment": new_assessment(),
    }
    record["verdict"] = compute_verdict(record)
    return record


def run_metadata(kind: str, provider, extra: dict | None = None) -> dict:
    rubric = load_rubric()
    git = git_info()
    meta = {
        "run_id": new_run_id(),
        "timestamp": utc_now_iso(),
        "kind": kind,
        "commit": git["commit"],
        "dirty": git["dirty"],
        "mode": provider.name,
        "label": provider.label,
        "model": provider.model,
        "prompt_file": str(PROMPT_PATH.relative_to(ROOT)).replace("\\", "/"),
        "prompt_hash": sha256_file(PROMPT_PATH),
        "dataset_hash": sha256_file(DATASET_PATH),
        "rubric_version": rubric["version"],
        "rubric_hash": sha256_file(RUBRIC_PATH),
        "review_scope": rubric["review_scope"],
        "decision_rule": rubric["decision_rule"],
        "structure_note": STRUCTURE_NOTE,
        "notice": MOCK_NOTE if provider.name == "mock" else "LIVE: output came from the configured provider.",
    }
    meta.update(extra or {})
    return meta


def build_run(provider, items: list[tuple[str, dict]], kind: str = "run", extra: dict | None = None) -> dict:
    """items is a list of (record_id, case). Returns the run dict (not yet saved)."""
    prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
    run = run_metadata(kind, provider, extra)
    run["records"] = [build_record(rid, case, provider, prompt_text) for rid, case in items]
    return run


def select_cases(case_id: str | None) -> list[tuple[str, dict]]:
    cases = load_cases()
    if case_id is not None:
        cases = [c for c in cases if c["case_id"] == case_id]
        if not cases:
            raise KeyError(f"Unknown case {case_id!r}.")
    return [(c["case_id"], c) for c in cases]


def write_json(path: Path, data: dict) -> None:
    """Write via a temp file so an interrupted save cannot corrupt the report."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)
