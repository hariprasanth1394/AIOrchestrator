"""Command-line interface: validate-data, run, open, review, clinic."""

import argparse
import json
import sys
import webbrowser
from pathlib import Path

from day3_lab import clinic as clinic_mod
from day3_lab import dataset, report, review, runner
from day3_lab.fixtures import MOCK_RESPONSES
from day3_lab.providers.base import ConfigurationError
from day3_lab.providers.live import LiveProvider
from day3_lab.providers.mock import MockProvider


def _fail(message: str, code: int = 2) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return code


def _check_data() -> list[str]:
    problems, _, _ = dataset.validate_all()
    return problems


def cmd_validate_data(args) -> int:
    problems, count, version = dataset.validate_all()
    if problems:
        for p in problems:
            print(f"PROBLEM: {p}", file=sys.stderr)
        return _fail(f"{len(problems)} problem(s) found in the Day 3 data.", 1)
    print(f"Dataset valid: {count} cases, unique IDs.")
    print(f"Rubric valid: version {version}.")
    print("Mock fixtures cover every case.")
    return 0


def _print_summary(run: dict) -> None:
    print(f"\n{run['label']} run {run['run_id']}")
    if run["mode"] == "mock":
        print("MOCK: fixed reviewed responses. This validates the workflow, not live model quality.")
    for record in run["records"]:
        structure = "schema PASS" if record["structural"]["valid"] else "schema FAIL"
        if record["provider"]["status"] == "error":
            structure = "provider ERROR"
        print(f"  {record['record_id']:<20} {structure:<15} -> {record['verdict']}")
    print("Schema validity is not proof of accuracy or safety; human review is still required.")


def cmd_run(args) -> int:
    problems = _check_data()
    if problems:
        return _fail("Day 3 data is invalid; run validate-data for details.")
    out = Path(args.out)
    try:
        runner.ensure_output_free(out, ["run.json", "run.html"])
        items = runner.select_cases(args.case)
    except (runner.OutputExistsError, KeyError) as exc:
        return _fail(str(exc.args[0]))

    if args.mode == "mock":
        provider = MockProvider(MOCK_RESPONSES)
    else:
        try:
            provider = LiveProvider.from_env()
        except ConfigurationError as exc:
            return _fail(str(exc))

    run = runner.build_run(provider, items)
    out.mkdir(parents=True, exist_ok=True)
    runner.write_json(out / "run.json", run)
    report.write_html(run, out / "run.html")
    _print_summary(run)
    print(f"Saved {out / 'run.json'} and {out / 'run.html'}")
    return 1 if any(r["verdict"] == "ERROR" for r in run["records"]) else 0


def cmd_open(args) -> int:
    path = Path(args.path)
    if not path.is_file():
        return _fail(f"{path} does not exist.")
    if not webbrowser.open(path.resolve().as_uri()):
        return _fail("No browser could be opened; open the file manually.", 1)
    print(f"Opened {path}")
    return 0


def cmd_review(args) -> int:
    path = Path(args.report)
    if not path.is_file():
        return _fail(f"{path} does not exist.")
    run = json.loads(path.read_text(encoding="utf-8"))
    try:
        entry = review.apply_review(
            run, args.case, args.scores, args.critical, args.note, args.reviewer
        )
    except review.ReviewError as exc:
        return _fail(str(exc))
    runner.write_json(path, run)
    report.write_html(run, path.with_name("run.html"))
    record = review.find_record(run, args.case)
    print(f"Review saved for {record['record_id']} by {entry['reviewer']}.")
    print(f"Verdict: {record['verdict']}. Regenerated {path.with_name('run.html')}")
    return 0


def cmd_clinic(args) -> int:
    out = Path(args.out)
    try:
        runner.ensure_output_free(out, ["run.json", "run.html", "clinic_notes.md"])
    except runner.OutputExistsError as exc:
        return _fail(str(exc))
    run = clinic_mod.build_clinic_run(args.variant)
    out.mkdir(parents=True, exist_ok=True)
    runner.write_json(out / "run.json", run)
    report.write_html(run, out / "run.html")
    (out / "clinic_notes.md").write_text(clinic_mod.clinic_notes_markdown(run), encoding="utf-8")
    _print_summary(run)
    print(f"Saved run.json, run.html and clinic_notes.md in {out}")
    return 0


def _score(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"score must be an integer 0, 1 or 2, got {text!r}")
    if value not in (0, 1, 2):
        raise argparse.ArgumentTypeError(f"score must be 0, 1 or 2, got {value}")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m day3_lab", description="Day 3 response-evaluation lab")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate-data", help="validate dataset, rubric and mock fixtures").set_defaults(func=cmd_validate_data)

    run = sub.add_parser("run", help="run cases and save run.json + run.html")
    run.add_argument("--mode", choices=["mock", "live"], required=True)
    run.add_argument("--case", help="a single case ID such as D3-01 (default: all)")
    run.add_argument("--out", required=True, help="new directory for the run")
    run.set_defaults(func=cmd_run)

    op = sub.add_parser("open", help="open a static HTML report in the browser")
    op.add_argument("path")
    op.set_defaults(func=cmd_open)

    rev = sub.add_parser("review", help="record a human assessment")
    rev.add_argument("--report", required=True, help="path to run.json")
    rev.add_argument("--case", required=True)
    rev.add_argument("--scores", nargs=4, type=_score, required=True,
                     metavar=("CORRECTNESS", "RELEVANCE", "COMPLETENESS", "SAFETY"))
    rev.add_argument("--critical", choices=["yes", "no"], required=True)
    rev.add_argument("--note", required=True)
    rev.add_argument("--reviewer", help="reviewer identifier (default: OS user name)")
    rev.set_defaults(func=cmd_review)

    cl = sub.add_parser("clinic", help="controlled MOCK failure clinic")
    cl.add_argument("--out", required=True)
    cl.add_argument("--variant", choices=["original", "corrected"], default="original")
    cl.set_defaults(func=cmd_clinic)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
