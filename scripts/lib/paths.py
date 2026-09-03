"""Locate the repository root without depending on how deep the caller sits."""
from __future__ import annotations

from pathlib import Path

# A directory is the repo root if it holds all of these.
MARKERS = ("scripts", "results", ".git")


def repo_root(start: Path | str | None = None) -> Path:
    """Walk up from `start` (default: this file) until the markers are found.

    `Path(__file__).resolve().parents[1]` is the idiom used across scripts/, and
    it encodes the caller's depth. Anything using it cannot be moved without
    being edited. This does not care where the caller lives.
    """
    here = Path(start).resolve() if start else Path(__file__).resolve()
    if here.is_file():
        here = here.parent
    for candidate in (here, *here.parents):
        if all((candidate / m).exists() for m in MARKERS):
            return candidate
    raise RuntimeError(f"repo root not found above {here}")
