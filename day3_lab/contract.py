"""The four-field response contract and its structural validation.

Passing this check means only that the output has the right shape. It says
nothing about whether the content is true, safe or helpful.
"""

import json

from jsonschema import Draft202012Validator

SERVICE_STATUSES = ["operational", "degraded", "outage", "unknown"]
RESPONSE_KEYS = ["answer", "service_status", "recovery_time", "next_step"]

STRUCTURE_NOTE = (
    "Schema validity checks shape only. It is not evidence of factual "
    "accuracy or safety."
)

# Local validation schema: strict, with non-blank strings.
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string", "pattern": r"\S"},
        "service_status": {"type": "string", "enum": SERVICE_STATUSES},
        "recovery_time": {"type": ["string", "null"]},
        "next_step": {"type": "string", "pattern": r"\S"},
    },
    "required": RESPONSE_KEYS,
    "additionalProperties": False,
}

# Schema sent to the provider for structured outputs. Strict mode accepts a
# smaller keyword set, so it omits "pattern"; non-blank is still enforced
# locally by RESPONSE_SCHEMA after the response comes back.
API_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "service_status": {"type": "string", "enum": SERVICE_STATUSES},
        "recovery_time": {"type": ["string", "null"]},
        "next_step": {"type": "string"},
    },
    "required": RESPONSE_KEYS,
    "additionalProperties": False,
}

_VALIDATOR = Draft202012Validator(RESPONSE_SCHEMA)


def check_response(raw_output: str | None) -> dict:
    """Parse and validate raw model output without ever repairing it.

    Returns {"valid", "parsed", "findings", "note"}. "parsed" is the decoded
    object when the text was JSON (even if the schema check failed), so it
    can be kept as evidence.
    """
    if raw_output is None:
        finding = {"kind": "parse", "path": "", "message": "No output to parse."}
        return _result(False, None, [finding])

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        finding = {"kind": "parse", "path": "", "message": f"Invalid JSON: {exc}"}
        return _result(False, None, [finding])

    findings = []
    for error in sorted(_VALIDATOR.iter_errors(parsed), key=lambda e: [str(p) for p in e.path]):
        path = ".".join(str(p) for p in error.path)
        findings.append({"kind": "schema", "path": path, "message": error.message})

    return _result(not findings, parsed, findings)


def _result(valid: bool, parsed, findings: list[dict]) -> dict:
    return {"valid": valid, "parsed": parsed, "findings": findings, "note": STRUCTURE_NOTE}
