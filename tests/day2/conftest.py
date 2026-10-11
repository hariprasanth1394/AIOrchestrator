"""
Day 2 fixtures, layered on top of tests/conftest.py.

The `client` fixture is NOT redefined here. pytest automatically shares
fixtures from a parent folder's conftest.py, so every test in tests/day2/
can already ask for `client`.
"""

import json
from pathlib import Path

import jsonschema
import pytest

from app.main import DEMO_HEADER_NAME


@pytest.fixture()
def auth_headers():
    """Build the demo identity header for a given employee id.

    Usage in a test:  auth_headers("EMP001")
    Returns:          {"X-Demo-Employee-ID": "EMP001"}

    The header name comes from app/main.py, so tests stay correct if the
    app ever renames it.
    """

    def _build(employee_id: str) -> dict:
        return {DEMO_HEADER_NAME: employee_id}

    return _build


SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"


@pytest.fixture()
def assert_matches_schema():
    """Check a response's status code FIRST, then validate its JSON body.

    Usage: assert_matches_schema(response, 200, "ticket")
    "ticket" loads schemas/ticket.schema.json. Checking the status first
    means a 500 or 403 fails with a clear status message instead of a
    confusing schema error about the wrong body.
    """

    def _check(response, expected_status: int, schema_name: str):
        assert response.status_code == expected_status
        with open(SCHEMA_DIR / f"{schema_name}.schema.json", encoding="utf-8") as f:
            schema = json.load(f)
        jsonschema.validate(instance=response.json(), schema=schema)

    return _check


@pytest.fixture(autouse=True)
def inject_day2_fault(request, monkeypatch):
    """TEST-ONLY fault injection, active only with --day2-fault=<name>.

    "autouse" means every test in tests/day2/ gets this fixture without
    asking. With no option it does nothing. Each fault replaces a function
    the app itself calls while building a response, so the real endpoint
    produces the bad output. monkeypatch restores everything after each
    test; app code and data files are never changed.

    ownership         - rules.employee_owns_ticket always says "yes"
    missing-status    - data.load_tickets / load_service_status drop "status"
    wrong-status-type - the same two functions return status as the number 1
    """
    fault = request.config.getoption("--day2-fault")
    if fault is None:
        return

    from app import data, rules

    if fault == "ownership":
        monkeypatch.setattr(rules, "employee_owns_ticket", lambda ticket, employee_id: True)
        return

    def break_status(record: dict) -> dict:
        broken = dict(record)  # copy: the loaded data is never modified
        if fault == "missing-status":
            broken.pop("status", None)
        else:
            broken["status"] = 1
        return broken

    real_tickets, real_status = data.load_tickets, data.load_service_status
    monkeypatch.setattr(data, "load_tickets", lambda: [break_status(t) for t in real_tickets()])
    monkeypatch.setattr(data, "load_service_status", lambda: break_status(real_status()))
