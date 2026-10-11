# Day 2 Instructor Map

Prepared by inspecting the repository as it actually exists on
2026-09-27 (branch `main`, commit `64f4caf`, working tree clean, up to
date with `origin/main`). Nothing below is assumed — every path, ID,
and status code was read from the current files or from a live test
run, not carried over from earlier lesson plans.

## 0. Day 1 baseline test files (do not move or rename)

Re-verified on 2026-10-11 (commit `276db27`, Windows 11, `.venv`
Python 3.12.10). The Day 1 baseline is exactly these files:

| Path | Tests |
| --- | --- |
| `tests/conftest.py` | `client` fixture (shared with Day 2 via pytest's conftest inheritance) |
| `tests/test_employees.py` | `test_get_my_profile_returns_known_employee` |
| `tests/test_service_status.py` | `test_health_check_returns_ok`, `test_vpn_status_has_defined_status_and_update_time` |
| `tests/test_tickets.py` | `test_get_own_ticket_returns_200`, `test_get_other_employees_ticket_returns_403`, `test_ticket_matches_schema`, `test_missing_ticket_returns_404` |

**Run only the Day 1 files** (same command on Windows and macOS, with the venv activated):

```
python -m pytest -v tests/test_employees.py tests/test_service_status.py tests/test_tickets.py
```

Verified result: `7 passed, 1 warning`. Once `tests/day2/` exists, a
bare `python -m pytest` will collect Day 2 tests as well (because
`testpaths = ["tests"]`), so use the explicit command above whenever
you want the Day 1 baseline alone. Day 2 only:
`python -m pytest -v tests/day2`.

## 1. Exact files to open during the lesson

In this order:

1. [`app/main.py`](../app/main.py) — the 4 routes and the
   `get_current_employee` dependency (the identity mechanism).
2. [`app/rules.py`](../app/rules.py) — `find_employee_by_id`,
   `find_ticket_by_id`, `employee_owns_ticket`. This is the file Day 2's
   parametrized and ownership tests will exercise most.
3. [`app/data.py`](../app/data.py) — how the JSON files get loaded.
4. [`data/employees.json`](../data/employees.json),
   [`data/tickets.json`](../data/tickets.json),
   [`data/service_status.json`](../data/service_status.json) — the
   fixture data itself.
5. [`schemas/ticket.schema.json`](../schemas/ticket.schema.json) — the
   contract used in the schema test.
6. [`tests/conftest.py`](../tests/conftest.py) — the single `client`
   fixture every test uses.
7. [`tests/test_tickets.py`](../tests/test_tickets.py) — today's
   richest file: ownership, schema validation, and a 404 case.

## 2. Actual identity mechanism

There is no login, token, or session. Every protected route depends on
`get_current_employee()` in `app/main.py` (lines 27–51), which:

1. Reads the `X-Demo-Employee-ID` request header.
2. Returns `400` with `"Missing required header: X-Demo-Employee-ID"`
   if the header is absent or empty.
3. Loads `data/employees.json` and looks for a matching
   `employee_id`.
4. Returns `400` with `"Unknown demo employee id: {id}"` if no match.
5. Otherwise returns the matching employee dict, which the route then
   uses.

This is intentionally not real authentication — say so explicitly to
students, since it's easy to mistake a header check for a security
control.

## 3. Employee / ticket ownership table (from the actual JSON files)

| Employee ID | Name | Department | Tickets owned |
| --- | --- | --- | --- |
| `EMP001` | Dana Whitfield | Finance | `TCK-1001` (open), `TCK-1005` (in_progress) |
| `EMP002` | Marcus Lee | Sales | `TCK-1002` (resolved), `TCK-1006` (resolved) |
| `EMP003` | Priya Nair | Engineering | `TCK-1003` (in_progress) |
| `EMP004` | Oliver Grant | Human Resources | `TCK-1004` (open) |

For the recap and for cross-ownership demos, the two simplest employees
to use are **EMP001 owning TCK-1001** and **EMP002 owning TCK-1002**
— asking for EMP001's ticket while sending `EMP002`'s header is the
existing 403 test's exact scenario.

## 4. Status code and response contracts (verified against the running code)

| Route | Condition | Status | Body |
| --- | --- | --- | --- |
| `GET /health` | always | 200 | `{"status": "ok", "service": "northstar-it-service-desk"}` |
| `GET /employees/me` | header missing | 400 | `{"detail": "Missing required header: X-Demo-Employee-ID"}` |
| `GET /employees/me` | header unknown | 400 | `{"detail": "Unknown demo employee id: <value>"}` |
| `GET /employees/me` | header valid | 200 | the matching employee object |
| `GET /services/vpn/status` | always | 200 | `data/service_status.json` verbatim |
| `GET /tickets/{id}` | header missing/unknown | 400 | same as above (shared dependency) |
| `GET /tickets/{id}` | ticket id not found | 404 | `{"detail": "Ticket not found: <id>"}` |
| `GET /tickets/{id}` | ticket exists, different owner | 403 | `{"detail": "You may not view another employee's ticket."}` |
| `GET /tickets/{id}` | ticket exists, owned by caller | 200 | the ticket object |

## 5. Setup and execution commands

**Dependency file:** only `pyproject.toml` (PEP 621 `[project.dependencies]`
+ `[project.optional-dependencies].dev`). There is no `requirements.txt`
in this repo — that's intentional, not missing.

### macOS / Linux

```bash
cd ai-qa-orchestration
source .venv/bin/activate
python -m pip show fastapi        # sanity check — confirms the right venv
python -m pytest -v
```

If `.venv` doesn't exist yet or `pip show fastapi` comes back empty:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### Windows PowerShell

```powershell
cd ai-qa-orchestration
.venv\Scripts\Activate.ps1
python -m pip show fastapi
python -m pytest -v
```

If `.venv` doesn't exist yet or `pip show fastapi` comes back empty:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## 6. Does Day 2 need a separate API terminal?

**No, not for the automated tests.** `tests/conftest.py` builds a
`fastapi.testclient.TestClient(app)`, which calls the ASGI app directly
in-process — confirmed by grepping the whole `tests/` and `app/`
trees for any real network call (`localhost`, `127.0.0.1`, `requests.`,
`httpx.Client`): there are none. `python -m pytest -v` is
self-contained.

A second terminal running the API is only needed if you want to demo it
manually with curl or `/docs` during the lesson. That's optional and
separate from testing. Startup (verified 2026-10-11, live responses
matched section 4 exactly):

```bash
# macOS / Linux
source .venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
curl -i http://127.0.0.1:8000/health
```

```powershell
# Windows PowerShell — use curl.exe; plain `curl` is an alias for Invoke-WebRequest
.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8000
curl.exe -i http://127.0.0.1:8000/health
curl.exe -i -H "X-Demo-Employee-ID: EMP001" http://127.0.0.1:8000/tickets/TCK-1001
```

## 7. Plain-English request flow

1. A test (or curl) sends `GET /tickets/TCK-1001` with header
   `X-Demo-Employee-ID: EMP001`.
2. FastAPI runs the `get_current_employee` dependency first: it reads
   the header, loads `employees.json`, and finds the Dana Whitfield
   record. If the header were missing or unrecognized, the request
   would stop here with a 400 and the route body would never run.
3. The route handler (`get_ticket` in `app/main.py`) loads
   `tickets.json` and calls `rules.find_ticket_by_id` to look for
   `TCK-1001`. If nothing matches, it stops with a 404.
4. If the ticket exists, `rules.employee_owns_ticket` compares the
   ticket's `employee_id` to the caller's. A mismatch stops here with
   403.
5. Only if all three checks pass does the route return the ticket JSON
   with a 200.

This is the flow every Day 2 test ultimately exercises, whether it's
checking the happy path, a 403, a 404, or a 400.

## 8. Baseline results (this run, this machine)

```
$ source .venv/bin/activate
$ python -m pytest -v
...
tests/test_employees.py::test_get_my_profile_returns_known_employee PASSED
tests/test_service_status.py::test_health_check_returns_ok PASSED
tests/test_service_status.py::test_vpn_status_has_defined_status_and_update_time PASSED
tests/test_tickets.py::test_get_own_ticket_returns_200 PASSED
tests/test_tickets.py::test_get_other_employees_ticket_returns_403 PASSED
tests/test_tickets.py::test_ticket_matches_schema PASSED
tests/test_tickets.py::test_missing_ticket_returns_404 PASSED
======================== 7 passed, 1 warning in 0.05s =========================
```

- Python: 3.11.0 (satisfies `pyproject.toml`'s `>=3.11,<3.13`)
- pytest: 8.4.2
- The one warning is a harmless Starlette deprecation notice about
  `httpx`/`httpx2`, unrelated to test correctness.
- `test_missing_ticket_returns_404` (BR03) was added since the Day 1
  starter was first written — it is now part of the baseline, not a
  Day 2 exercise, so Day 2 material should not reintroduce it as new.

## 9. Unresolved issues / notes for the instructor

- **Extra pytest plugins in this machine's `.venv`:** `pytest-html`,
  `pytest-json-report`, and `pytest-metadata` are installed here but
  are **not** declared in `pyproject.toml`. A student's fresh
  `pip install -e ".[dev]"` will not get them (their pytest output
  will look slightly plainer — no "Plugins: json-report..." line) but
  will still pass the same 7 tests. Don't demo anything that depends on
  these plugins unless you add them to `pyproject.toml` first.
- **Minor style nit, not a defect:** `tests/test_tickets.py` is missing
  a blank line between `test_ticket_matches_schema` and
  `test_missing_ticket_returns_404` (PEP 8 wants two). Cosmetic only —
  left as-is rather than reformatting someone else's recent commit
  without being asked.
- **2026-10-11 Windows re-run:** `.venv` here is Python 3.12.10
  (still within `>=3.11,<3.13`), fastapi 0.143.0, uvicorn 0.54.0,
  httpx 0.28.1, jsonschema 4.26.0, pytest 8.4.2. The Day 1 command in
  section 0 gave `7 passed, 1 warning in 0.17s`.
- **`.env` is a directory, not a file.** On this machine `.env/` holds
  a second virtual environment (`Include/`, `Lib/`, `Scripts/`,
  `pyvenv.cfg`). It is git-ignored and the app doesn't read it, so it
  doesn't block anything. But it's confusing next to `.env.example`, so
  tell students to use `.venv`. No secrets are required.
- **Windows curl gotcha:** in PowerShell, `curl` is `Invoke-WebRequest`.
  Use `curl.exe` (see section 6).
- **No blockers found.** All 7 existing tests pass from a clean
  `.venv` activation with no code changes required.

## 10. Proposed Day 2 test layout (not created yet)

A new `tests/day2/` folder, planned but intentionally not scaffolded
until the lesson itself. Pytest automatically shares fixtures from a
parent `conftest.py`, so every file below reuses the existing `client`
fixture from `tests/conftest.py` without redefining it.

| File | Purpose |
| --- | --- |
| `tests/day2/conftest.py` | Day-2-only fixtures layered on top of the existing `client` fixture — e.g. a small `auth_headers(employee_id)` helper that returns `{"X-Demo-Employee-ID": employee_id}`, so later files stop repeating that dict literal. |
| `tests/day2/test_01_fixtures.py` | Introduces fixtures as a concept: rewrite Day 1's `/employees/me` and `/services/vpn/status` checks using the new `auth_headers` fixture, so students see *why* a fixture is useful before anything more advanced. |
| `tests/day2/test_02_parameterized.py` | `@pytest.mark.parametrize` over the real ownership table in section 3 — one test function driving all 4 employee/own-ticket 200 cases (`EMP001`/`TCK-1001`, `EMP002`/`TCK-1002`, `EMP003`/`TCK-1003`, `EMP004`/`TCK-1004`) instead of four near-duplicate tests. |
| `tests/day2/test_03_ownership.py` | Extends BR01–BR03 systematically with parametrization: several mismatched employee/ticket pairs expecting 403, a missing-header case expecting 400, an unknown-employee-id case expecting 400, and the existing missing-ticket 404 case, but now table-driven instead of one-off. |
| `tests/day2/test_04_schema.py` | Builds on Day 1's single `test_ticket_matches_schema`: parametrize it across every ticket ID owned by the calling employee, and add one negative case asserting `jsonschema.validate` raises `ValidationError` against a deliberately malformed payload (e.g. a `status` value outside the enum). |

Status: all five files are implemented (see sections 11 and 12).
Day 1's passing tests in
`tests/test_tickets.py`, `tests/test_employees.py`, and
`tests/test_service_status.py` are left untouched — Day 2 adds a
parallel folder rather than replacing the baseline.

## 11. Lesson 1 — fixtures (implemented 2026-10-11)

**Files to open, in order:**

1. `tests/conftest.py` — Day 1's `client` fixture (unchanged, reused).
2. `tests/day2/conftest.py` — new `auth_headers` fixture.
3. `tests/day2/test_01_fixtures.py` — the two lesson tests.
4. `data/tickets.json` — where the expected owners come from.

**Fixtures used:**

| Fixture | Defined in | What it gives the test |
| --- | --- | --- |
| `client` | `tests/conftest.py` | A `TestClient(app)` that calls the API in-process (no server). Reused, not redefined; pytest shares parent-folder conftest fixtures automatically. |
| `auth_headers` | `tests/day2/conftest.py` | A small function: `auth_headers("EMP001")` → `{"X-Demo-Employee-ID": "EMP001"}`. The header name is imported from `app.main.DEMO_HEADER_NAME`, the app's own constant, so no second copy of it exists. It's the only extra fixture needed: Day 1 repeated this dict literal in every test. |

**Tests (identities hard-coded from `data/tickets.json`, not read from the response):**

| Test | Header | Request | Asserts |
| --- | --- | --- | --- |
| `test_employee_a_retrieves_own_ticket` | `EMP001` | `GET /tickets/TCK-1001` | 200, `ticket_id == "TCK-1001"`, `employee_id == "EMP001"` |
| `test_employee_b_retrieves_own_ticket` | `EMP002` | `GET /tickets/TCK-1002` | 200, `ticket_id == "TCK-1002"`, `employee_id == "EMP002"` |

**Commands and actual results (Windows, `.venv` Python 3.12.10):**

```
python -m pytest -v tests/day2/test_01_fixtures.py
  -> 2 passed, 1 warning in 0.07s
python -m pytest -v tests/test_employees.py tests/test_service_status.py tests/test_tickets.py
  -> 7 passed, 1 warning in 0.11s   (Day 1 baseline unchanged)
python -m pytest -q
  -> 9 passed, 1 warning in 0.11s   (Day 1 + Day 2)
```

The warning is the same Starlette `httpx` deprecation notice as before.
No Day 1 files were modified.

## 12. Lessons 2–4 (implemented 2026-10-11)

| File | Lesson | Tests (collected) | What it checks |
| --- | --- | --- | --- |
| `tests/day2/test_02_parameterized.py` | `@pytest.mark.parametrize` | 5 | Replaced 2026-10-11; see section 13. |
| `tests/day2/test_03_ownership.py` | BR01–BR03, table-driven | 8 | 4 cross-owner pairs → 403 with exact `detail`; no header → 400; `EMP999` → 400; `TCK-9999` / `TCK-0000` → 404. |
| `tests/day2/test_04_schema.py` | Schema validation | 7 | All 6 tickets, each fetched by its real owner, match `schemas/ticket.schema.json`; a ticket with `status: "deleted"` (outside the `open`/`in_progress`/`resolved` enum) raises `ValidationError`. |

New fixture: `ticket_schema` (local to `test_04_schema.py`) loads the
schema file. It's local because only that file uses it.

All expected owners and pairs are hard-coded from `data/tickets.json`.

**Actual results (Windows, `.venv` Python 3.12.10):**

```
python -m pytest -v tests/day2
  -> 21 passed, 1 warning in 0.29s   (before section 13; now 22)
python -m pytest -v tests/test_employees.py tests/test_service_status.py tests/test_tickets.py
  -> 7 passed, 1 warning in 0.13s   (Day 1 baseline unchanged)
python -m pytest -q
  -> 28 passed, 1 warning in 0.29s
```

## 13. Lesson 2 revised — parametrized ticket access (2026-10-11)

`tests/day2/test_02_parameterized.py` was rewritten to this spec: one
function, `test_ticket_access`, with 5 `pytest.param` rows, each with a
readable `id`. Employee A = `EMP001` (owns `TCK-1001`), Employee B =
`EMP002` (owns `TCK-1002`), both from `data/tickets.json`.

| Case ID | Header | Request | Status | Body check | Overlaps with (not a new unique case) |
| --- | --- | --- | --- | --- | --- |
| `employee_a_own_ticket` | EMP001 | TCK-1001 | 200 | `ticket_id`, `employee_id` | **OVERLAP:** `test_01_fixtures::test_employee_a_retrieves_own_ticket`; Day 1 `test_get_own_ticket_returns_200` |
| `employee_b_own_ticket` | EMP002 | TCK-1002 | 200 | `ticket_id`, `employee_id` | **OVERLAP:** `test_01_fixtures::test_employee_b_retrieves_own_ticket` |
| `employee_a_denied_employee_b_ticket` | EMP001 | TCK-1002 | 403 | body is exactly `{"detail": "You may not view another employee's ticket."}` | **OVERLAP:** `test_03_ownership` row `EMP001`/`TCK-1002` |
| `employee_b_denied_employee_a_ticket` | EMP002 | TCK-1001 | 403 | same exact body | **OVERLAP:** Day 1 `test_get_other_employees_ticket_returns_403`; `test_03_ownership` row `EMP002`/`TCK-1001` |
| `valid_employee_missing_ticket` | EMP001 | TCK-9999 | 404 | body is exactly `{"detail": "Ticket not found: TCK-9999"}` | **OVERLAP:** Day 1 `test_missing_ticket_returns_404`; `test_03_ownership` `[TCK-9999]` |

**Unique-case count:** all 5 rows repeat request scenarios already
covered elsewhere. This file adds **0 new unique request scenarios**.
Its purpose is teaching the parametrize syntax. What it adds is a
stricter check: for 403 and 404, the whole body must equal
`{"detail": ...}`, so a denied request that leaked `subject`,
`description`, or any other ticket field would fail. Exact statuses
only; no alternative codes are accepted.

**Actual results (Windows, `.venv` Python 3.12.10):**

```
python -m pytest -v tests/day2/test_02_parameterized.py
  -> 5 passed, 1 warning in 0.06s
python -m pytest -v tests/test_employees.py tests/test_service_status.py tests/test_tickets.py
  -> 7 passed, 1 warning in 0.12s   (Day 1 baseline unchanged)
python -m pytest -q tests/day2
  -> 22 passed, 1 warning in 0.20s
python -m pytest -q
  -> 29 passed, 1 warning in 0.24s
```

## 14. Lesson 3 revised — ownership + injected fault (2026-10-11)

**Files to open:** `app/main.py` (`get_ticket`), `app/rules.py`
(`employee_owns_ticket`), `conftest.py` (project root, new),
`tests/day2/conftest.py` (`inject_day2_fault`),
`tests/day2/test_03_ownership.py`.

**Enforcement location:** `get_ticket()` calls
`rules.employee_owns_ticket(ticket, caller_id)`. If it returns False the
route raises 403 before the ticket is returned.

**Tests (2, rewritten):** `emp001_requests_emp002_ticket` and
`emp002_requests_emp001_ticket`. Each asserts status 403, body exactly
`{"detail": "You may not view another employee's ticket."}`, and that
`subject`, `description`, `status`, `ticket_id` do not appear in the
response text. Real endpoint via `client`; nothing fabricated.
Overlap: both rows repeat section 13's denied cases and Day 1's 403 test
(0 new unique scenarios). The earlier 400/404 cases in this file were
removed; 400 and 404 remain covered by Day 1 and section 13. The old
test_03 and test_04 counts in section 12 are therefore out of date.

**Fault injection (TEST-ONLY):** `--day2-fault=ownership`, registered in
the new project-root `conftest.py` (Day 1's conftest is untouched). The
autouse fixture `inject_day2_fault` uses pytest `monkeypatch` to replace
`rules.employee_owns_ticket` with "always True" for the test process
only. `monkeypatch` restores it after every test. No app code, data
file, or auth is changed, and a normal run or `uvicorn` never sees it.
It only applies to tests under `tests/day2/`; Day 1 tests are unaffected.

**Verification (Windows):**

| Step | Command | Result |
| --- | --- | --- |
| 1. Normal | `python -m pytest -q tests/day2/test_03_ownership.py` | 2 passed |
| 2. Fault | `python -m pytest -q tests/day2 --day2-fault=ownership` | 4 failed, 12 passed. Failures: both test_03 cases and both 403 rows of test_02 (`employee_a_denied_employee_b_ticket`, `employee_b_denied_employee_a_ticket`). Tests are unchanged and not xfail. |
| 3. After | `python -m pytest -q` | 23 passed (7 Day 1 + 16 Day 2) |

## 15. Lesson 4 — reusable schema validation (2026-10-11)

**Dependency:** `jsonschema>=4.21,<5.0` is already in `pyproject.toml`
(the only dependency file), so nothing was added. Installed: 4.26.0.

**New files:** `schemas/employee.schema.json`,
`schemas/service_status.schema.json`, `schemas/error.schema.json`
(existing `ticket.schema.json` reused), and a rewritten
`tests/day2/test_04_schema.py`. Reusable fixture
`assert_matches_schema(response, status, "name")` in
`tests/day2/conftest.py` asserts the HTTP status first, then validates
the body against `schemas/<name>.schema.json`.

| Test | Request | Status | Schema |
| --- | --- | --- | --- |
| `test_employee_profile_matches_schema` | `/employees/me` as EMP001 | 200 | employee |
| `test_ticket_matches_schema` | `/tickets/TCK-1001` as EMP001 | 200 | ticket |
| `test_service_status_matches_schema` | `/services/vpn/status` | 200 | service_status |
| `test_error_response_matches_schema` | `/tickets/TCK-9999` as EMP001 | 404 | error |

Overlap: the ticket case repeats Day 1 `test_ticket_matches_schema`;
the others are new schema-level checks of already-covered requests.
The earlier 6-ticket parametrized schema test and the "deleted" status
negative case were removed in this rewrite (section 12's test_04 row is
out of date).

**Schema words:** `type: object` = body is `{...}`; `properties` = each
known field and its type; `type: string` = must be text; `required` =
fields that must be present.

**Faults (TEST-ONLY, `--day2-fault=...`)**, in `inject_day2_fault`:
- `missing-status` — `data.load_tickets` and `data.load_service_status`
  return copies without `status`.
- `wrong-status-type` — the same functions return `status: 1`.

They patch the app's own data-loading functions with `monkeypatch`, so
the real endpoint builds the bad response; no test edits a response.
Files and normal runs are untouched. FastAPI's own response validation
did NOT catch either fault first: the routes are annotated `-> dict`,
which accepts any dict. The schema tests were the first line of defence.

| Step | Command | Result |
| --- | --- | --- |
| Baseline | `python -m pytest -q` | 20 passed (7 Day 1 + 13 Day 2) |
| missing-status | `python -m pytest -q tests/day2 --day2-fault=missing-status` | ticket and service-status schema tests fail ("'status' is a required property") |
| wrong-status-type | `... --day2-fault=wrong-status-type` | 2 failed, 11 passed (ticket and service-status; "type" violation on `status`) |
| After | `python -m pytest -q` | 20 passed |
