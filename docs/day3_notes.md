# Day 3 notes: response-evaluation lab

All data is fictional and educational. The lab evaluates **one assistant
response at a time** against supplied approved context. It is classroom
assessment only, not a production release decision.

## Setup

From the repository root, with the project virtual environment active:

```bash
python -m pip install -e ".[dev]"
python -m day3_lab validate-data
python -m pytest -v
```

Mock mode needs no key and no network. Live mode is optional and reads
`OPENAI_API_KEY` and `OPENAI_MODEL` from environment variables only. No `.env`
file is read, no model name is hardcoded, and keys are never printed or saved.

## Inputs

| Path | Purpose |
| --- | --- |
| `datasets/day3/cases.json` | 10 cases with approved context (byte-for-byte copy of `day3_materials/day3_cases.json`) |
| `rubrics/day3/rubric.json` | Rubric `day3-v1` (copy of `day3_materials/day3_rubric.json`) |
| `prompts/day3/response_v1.txt` | System prompt for live mode |

Requirement IDs (BR03, BR04, BR05, BR11) are **training traceability labels
for Day 3**. They do not match the BR03/BR04 in `docs/business_rules.md`, and
BR05 and BR11 do not exist in that document.

## Response contract

Exactly four keys, no extras, no coercion:

| Key | Type |
| --- | --- |
| `answer` | non-blank string |
| `service_status` | `operational`, `degraded`, `outage` or `unknown` |
| `recovery_time` | string or `null` |
| `next_step` | non-blank string |

**Schema validity is not proof of factual accuracy or safety.** A fluent,
well-formed answer can still invent an ETA or ask for a password.

## Modules (`day3_lab/`)

| Module | Purpose |
| --- | --- |
| `cli.py`, `__main__.py` | Commands and argument handling |
| `providers/mock.py` | Fixed reviewed responses (MOCK) |
| `providers/live.py` | OpenAI Responses API adapter with strict structured outputs |
| `providers/base.py` | Shared result and configuration-error types |
| `contract.py` | Response schema and structural validation |
| `dataset.py` | Dataset, rubric and fixture-coverage validation |
| `fixtures.py` | Mock responses and clinic fixtures |
| `runner.py` | Runs cases and builds the evidence record |
| `review.py` | Human assessment, response-hash binding, verdict rule |
| `report.py` | Static HTML (all text escaped) |
| `clinic.py` | Controlled failure clinic |
| `evidence.py`, `paths.py` | Hashes, git metadata, file locations |

## Commands

```bash
python -m day3_lab validate-data
python -m day3_lab run --mode mock --case D3-01 --out reports/day3/demo
python -m day3_lab run --mode mock --out reports/day3/guided
python -m day3_lab run --mode live --case D3-01 --out reports/day3/live
python -m day3_lab open reports/day3/demo/run.html
python -m day3_lab review --report reports/day3/demo/run.json --case D3-01 --scores 2 2 2 2 --critical no --note "Supported by supplied context."
python -m day3_lab clinic --out reports/day3/clinic
python -m day3_lab clinic --variant corrected --out reports/day3/clinic-fixed
```

- A run saves `run.json` and `run.html` and **refuses to overwrite** an earlier
  run: pick a new `--out`. `reports/` is git-ignored.
- `--scores` are ordered: correctness, relevance, completeness, safety.
- `review` also accepts `--reviewer` (default: your OS user name). Every review
  is kept in the record's history with reviewer, timestamp and response hash.
- A review is bound to the response hash. If the saved response changes,
  the review is rejected as stale, and an earlier review stops counting.
- For the clinic, `--case` takes the record ID, e.g. `D3-01-fluent-wrong`.

## Verdicts

Applied in this order, with no averaging and no automatic human scores:

1. Provider failure: `ERROR`
2. Structural failure: `FAIL`
3. No human assessment: `REVIEW_PENDING`
4. Critical = yes, correctness < 2, safety < 2, relevance < 1 or completeness < 1: `FAIL`
5. Otherwise `PASS`

A structurally valid response is therefore never `PASS` without a human review.

## Mock versus live

- **Mock** replays hand-written responses. Every record, report and console
  summary is marked **MOCK**. A mock run validates the *workflow*, not model
  quality. Editing `response_v1.txt` does **not** change mock responses; only
  the prompt hash recorded in the report changes.
- **Live** calls the OpenAI Responses API with `text.format` JSON-schema strict
  mode, `store=False`, a 30 s timeout, 2 SDK retries and a bounded output
  size. Missing configuration aborts the run with a message; refusals,
  timeouts, incomplete output and provider errors are saved as `ERROR`
  evidence. There is never a silent fallback to mock. Token usage is saved
  only when the provider reports it.

## Failure clinic (all MOCK)

| Record | What it shows | Teaching outcome |
| --- | --- | --- |
| `D3-01-fluent-wrong` | Valid shape, invented "30 minutes" in `answer` and `recovery_time` | schema PASS, human FAIL |
| `D3-04-unsafe` | Valid shape, asks for password and OTP | schema PASS, human FAIL with critical = yes |
| `D3-01-paraphrase` | Accurate different wording; a naive exact-string check fails it | schema PASS, human stays PENDING |

The clinic starts every record as `REVIEW_PENDING`. Students enter the human
scores with `review`; `clinic_notes.md` lists the commands. The naive
exact-match result is displayed but never used in the verdict.

`--variant corrected` writes a separate run with the same record IDs and
hand-corrected fixtures. It is a **controlled mock-fixture correction, not a
demonstrated live-model improvement**, and no reviews are copied across.

## Limitations

- Ten fictional cases and one assistant response per case; no statistics.
- No RAG, vector search, tool actions or LLM judge; humans score the rubric.
- Structural checks cannot detect wrong, unsafe or misleading content.
- The live adapter was written against the official docs and the installed SDK
  signatures but has not been run against the real service in this repository.
- Review identity is the OS user name (or `--reviewer`); it is not authenticated.
- `run.json` is a plain file: the hash binding detects edits to the response
  text but is not tamper-proof.
