"""File locations used by the lab (all relative to the repository root)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROMPT_PATH = ROOT / "prompts" / "day3" / "response_v1.txt"
DATASET_PATH = ROOT / "datasets" / "day3" / "cases.json"
RUBRIC_PATH = ROOT / "rubrics" / "day3" / "rubric.json"
