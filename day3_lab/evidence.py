"""Hashing, timestamps and git metadata saved as run evidence."""

import hashlib
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from day3_lab.paths import ROOT

UNAVAILABLE = "unavailable"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def _git(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def git_info() -> dict:
    """Commit hash and dirty flag, or "unavailable"/None if git cannot say."""
    commit = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain")
    if commit is None or status is None:
        return {"commit": UNAVAILABLE, "dirty": None}
    return {"commit": commit, "dirty": bool(status)}
