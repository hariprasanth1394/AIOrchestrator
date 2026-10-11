"""Static HTML report. Every piece of dynamic text is escaped."""

import json
from html import escape
from pathlib import Path

from day3_lab.review import compute_verdict

VERDICT_COLOURS = {
    "PASS": "#1a7f37",
    "FAIL": "#cf222e",
    "ERROR": "#9a6700",
    "REVIEW_PENDING": "#57606a",
}

CSS = """
body{font-family:system-ui,sans-serif;max-width:60rem;margin:1.5rem auto;padding:0 1rem;color:#1f2328}
.banner{padding:.75rem 1rem;border-radius:6px;margin:1rem 0;font-weight:600}
.mock{background:#fff8c5;border:2px solid #9a6700}.live{background:#ddf4ff;border:2px solid #0969da}
.note{background:#f6f8fa;border-left:4px solid #8c959f;padding:.5rem 1rem;margin:1rem 0}
.case{border:1px solid #d0d7de;border-radius:6px;padding:1rem;margin:1.5rem 0}
.badge{color:#fff;padding:.15rem .6rem;border-radius:1rem;font-weight:600}
pre{background:#f6f8fa;padding:.75rem;overflow:auto;white-space:pre-wrap}
table{border-collapse:collapse}td,th{border:1px solid #d0d7de;padding:.25rem .6rem;text-align:left}
code{background:#f6f8fa;padding:0 .25rem}
"""


def _e(value) -> str:
    return escape("" if value is None else str(value))


def _badge(verdict: str) -> str:
    colour = VERDICT_COLOURS.get(verdict, "#57606a")
    return f'<span class="badge" style="background:{colour}">{_e(verdict)}</span>'


def _pre(value) -> str:
    return f"<pre>{_e(value)}</pre>"


def _record_html(record: dict) -> str:
    verdict = compute_verdict(record)
    ctx = record["approved_context"]
    parts = [
        '<div class="case">',
        f"<h2>{_e(record['record_id'])} {_badge(verdict)} "
        f"<small>[{_e(record['label'])}]</small></h2>",
        f"<p><b>{_e(record['category'])}</b> &middot; requirement IDs: "
        f"{_e(', '.join(record['requirement_ids']))}</p>",
        f"<p><b>Question:</b> {_e(record['question'])}</p>",
        "<h3>Approved context</h3><table>"
        + "".join(f"<tr><th>{_e(k)}</th><td>{_e(v)}</td></tr>" for k, v in ctx.items())
        + "</table>",
    ]
    teaching = record.get("teaching")
    if teaching:
        parts.append(
            f"<div class=\"note\"><b>Clinic: {_e(teaching['name'])}.</b> {_e(teaching['lesson'])}<br>"
            f"Teaching outcome: schema {_e(teaching['expected_schema'])}; "
            f"human {_e(teaching['expected_human'])}.</div>"
        )
    provider = record["provider"]
    if provider["status"] == "error":
        err = provider["error"]
        parts.append(f"<h3>Provider error</h3>{_pre(err['kind'] + ': ' + err['message'])}")
    parts.append("<h3>Raw output</h3>" + _pre(record["raw_output"]))
    if record["parsed_response"] is not None:
        parts.append("<h3>Parsed response</h3>" + _pre(json.dumps(record["parsed_response"], indent=2)))

    structural = record["structural"]
    parts.append(f"<h3>Structural check: {'PASS' if structural['valid'] else 'FAIL'}</h3>")
    if structural["findings"]:
        items = "".join(
            f"<li>{_e(f['kind'])} {_e(f['path'])}: {_e(f['message'])}</li>"
            for f in structural["findings"]
        )
        parts.append(f"<ul>{items}</ul>")
    parts.append(f"<p><i>{_e(structural['note'])}</i></p>")

    naive = record.get("naive_exact_match")
    if naive:
        parts.append(
            "<h3>Naive exact-string comparison</h3>"
            f"<p>Reference sentence: {_e(naive['reference_sentence'])}</p>"
            f"<p>Result: <b>{'matched' if naive['matched'] else 'did NOT match'}</b>. "
            f"<i>{_e(naive['warning'])}</i></p>"
        )

    parts.append(_review_html(record))
    usage = record["token_usage"]
    parts.append(
        f"<p><small>Response hash: <code>{_e(record['response_hash'])}</code> &middot; "
        f"elapsed {_e(record['elapsed_seconds'])}s &middot; token usage: "
        f"{_e(json.dumps(usage) if usage else 'not available')}</small></p></div>"
    )
    return "".join(parts)


def _review_html(record: dict) -> str:
    history = record["human_assessment"]["history"]
    if not history:
        return "<h3>Human assessment: PENDING</h3><p>No review has been entered.</p>"
    rows = "".join(
        f"<tr><td>{_e(r['timestamp'])}</td><td>{_e(r['reviewer'])}</td>"
        f"<td>{_e(' / '.join(f'{k} {v}' for k, v in r['scores'].items()))}</td>"
        f"<td>{'yes' if r['critical'] else 'no'}</td><td>{_e(r['note'])}</td></tr>"
        for r in history
    )
    return (
        "<h3>Human assessment history</h3><table><tr><th>When (UTC)</th><th>Reviewer</th>"
        f"<th>Scores</th><th>Critical</th><th>Note</th></tr>{rows}</table>"
    )


def render_html(run: dict) -> str:
    is_mock = run["mode"] == "mock"
    banner_class = "mock" if is_mock else "live"
    title = f"Day 3 {run['kind']} report ({run['label']})"
    summary = "".join(
        f"<tr><td>{_e(r['record_id'])}</td><td>{_badge(compute_verdict(r))}</td></tr>"
        for r in run["records"]
    )
    variant = ""
    if run.get("correction_note"):
        variant = f'<div class="note">{_e(run["correction_note"])}</div>'
    meta_rows = [
        ("Run ID", run["run_id"]), ("Timestamp (UTC)", run["timestamp"]),
        ("Commit", run["commit"]), ("Working tree dirty", run["dirty"]),
        ("Mode", run["mode"]), ("Model", run["model"]),
        ("Prompt hash", run["prompt_hash"]), ("Dataset hash", run["dataset_hash"]),
        ("Rubric version", run["rubric_version"]),
    ]
    meta = "".join(f"<tr><th>{_e(k)}</th><td>{_e(v)}</td></tr>" for k, v in meta_rows)
    body = "".join(_record_html(r) for r in run["records"])
    return (
        f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{_e(title)}</title><style>{CSS}</style></head><body>"
        f"<h1>{_e(title)}</h1>"
        f"<div class=\"banner {banner_class}\">{_e(run['notice'])}</div>{variant}"
        f"<div class=\"note\">{_e(run['structure_note'])}<br>Scope: {_e(run['review_scope'])}<br>"
        f"Decision rule: {_e(run['decision_rule'])}</div>"
        f"<table>{meta}</table><h2>Summary</h2><table>{summary}</table>{body}</body></html>"
    )


def write_html(run: dict, path: Path) -> None:
    Path(path).write_text(render_html(run), encoding="utf-8")
