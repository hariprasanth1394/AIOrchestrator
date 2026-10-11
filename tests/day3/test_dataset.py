import copy

import pytest

from day3_lab import dataset
from day3_lab.evidence import sha256_file
from day3_lab.fixtures import MOCK_RESPONSES
from day3_lab.paths import DATASET_PATH, ROOT, RUBRIC_PATH


def test_dataset_and_rubric_are_valid_with_ten_unique_cases():
    problems, count, version = dataset.validate_all()
    assert problems == []
    assert count == 10
    assert version == "day3-v1"
    ids = [c["case_id"] for c in dataset.load_cases()]
    assert len(set(ids)) == 10


def test_copies_match_supplied_materials_byte_for_byte():
    assert sha256_file(DATASET_PATH) == sha256_file(ROOT / "day3_materials" / "day3_cases.json")
    assert sha256_file(RUBRIC_PATH) == sha256_file(ROOT / "day3_materials" / "day3_rubric.json")


def test_every_case_has_a_reviewed_mock_fixture():
    assert set(MOCK_RESPONSES) == {c["case_id"] for c in dataset.load_cases()}


@pytest.fixture()
def raw_dataset():
    return dataset.load_json(DATASET_PATH)


def _mutate(raw, fn):
    data = copy.deepcopy(raw)
    fn(data)
    return dataset.validate_dataset(data)


@pytest.mark.parametrize(
    "mutation, fragment",
    [
        (lambda d: d["cases"][1].update(case_id="D3-01"), "duplicate case_id"),
        (lambda d: d["cases"][0].pop("question"), "missing keys"),
        (lambda d: d["cases"][0].update(surprise=1), "unexpected keys"),
        (lambda d: d["cases"][0]["approved_context"].update(service_status="down"), "service_status"),
        (lambda d: d["cases"][0]["approved_context"].update(recovery_time=5), "recovery_time"),
        (lambda d: d["cases"][0].update(evaluation_method=["schema"]), "evaluation_method"),
        (lambda d: d["cases"].pop(), "expected 10 cases"),
        (lambda d: d.update(synthetic=False), "synthetic"),
    ],
)
def test_dataset_problems_are_reported(raw_dataset, mutation, fragment):
    problems = _mutate(raw_dataset, mutation)
    assert any(fragment in p for p in problems)


def test_rubric_inconsistencies_are_reported():
    rubric = dataset.load_rubric()
    assert dataset.validate_rubric(rubric, "day3-v1") == []
    bad = copy.deepcopy(rubric)
    del bad["scales"]["safety"]["2"]
    assert any("safety" in p for p in dataset.validate_rubric(bad))
    assert any("does not match" in p for p in dataset.validate_rubric(rubric, "day3-v2"))
