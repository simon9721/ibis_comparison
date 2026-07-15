from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
CACHE_ROOT = ROOT / "results" / "_golden_hspice_cache"
HSPICE_SUFFIXES = [".sp", ".tr0", ".lis", ".st0", ".ic0", ".pa0"]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def reference_signature(deck_text: str, input_paths: list[Path], extra: dict[str, object] | None = None) -> tuple[str, dict[str, object]]:
    payload: dict[str, object] = {
        "deck_sha256": hashlib.sha256(deck_text.encode("utf-8")).hexdigest(),
        "inputs": [
            {
                "name": path.name,
                "sha256": file_sha256(path),
                "size": path.stat().st_size,
            }
            for path in input_paths
        ],
        "extra": extra or {},
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16], payload


def cache_dir(family: str, case_id: str, signature_id: str) -> Path:
    safe_case = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in case_id)
    return CACHE_ROOT / family / safe_case / signature_id


def restore(cache_path: Path, dest_dir: Path, dest_stem: str, deck_text: str) -> bool:
    if not (cache_path / "run.tr0").exists():
        return False
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / f"{dest_stem}.sp").write_text(deck_text, encoding="ascii")
    for suffix in HSPICE_SUFFIXES:
        src = cache_path / f"run{suffix}"
        if src.exists():
            shutil.copy2(src, dest_dir / f"{dest_stem}{suffix}")
    meta = cache_path / "reference_meta.json"
    if meta.exists():
        shutil.copy2(meta, dest_dir / "hspice_reference_meta.json")
    return True


def save(cache_path: Path, source_dir: Path, source_stem: str, deck_text: str, signature: dict[str, object]) -> None:
    if not (source_dir / f"{source_stem}.tr0").exists():
        return
    cache_path.mkdir(parents=True, exist_ok=True)
    (cache_path / "run.sp").write_text(deck_text, encoding="ascii")
    for suffix in HSPICE_SUFFIXES:
        src = source_dir / f"{source_stem}{suffix}"
        if src.exists():
            shutil.copy2(src, cache_path / f"run{suffix}")
    (cache_path / "reference_meta.json").write_text(
        json.dumps(signature, indent=2, sort_keys=True),
        encoding="utf-8",
    )
