#!/usr/bin/env python3
"""Compress ngspice .raw files in place, verifying each one parses back identically.

The raws are not disposable: 65 scripts read them at build time, including every deck figure
builder, so deleting a study's raws means re-running its ngspice campaign to draw a figure
again. They do compress about 6x, which is the cheaper answer - 91 GB across results/ becomes
roughly 15 GB and stays readable, because `eye_diagram.resolve_raw` falls back to `<name>.gz`
when the plain file is gone.

Safety, in order of application:

  * dry run unless --apply is given;
  * every file is re-parsed from its .gz and compared array-by-array against the original
    before the original is removed - a mismatch leaves both files and stops the run;
  * the original is only unlinked after that comparison passes;
  * --keep leaves originals in place, for a first pass you want to check by hand.

    py -3.14 scripts/compress_raws.py results/gate_cascade_prototype_2026-09-09
    py -3.14 scripts/compress_raws.py results/gate_cascade_prototype_2026-09-09 --apply
"""
from __future__ import annotations

import argparse
import gzip
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402

from eye_diagram import parse_ngspice_raw  # noqa: E402

LEVEL = 6          # 5.9x on a sample; xz reaches 6.6x but is far slower


def same(a: dict, b: dict) -> bool:
    """Every signal present in both, and every sample equal."""
    if sorted(a) != sorted(b):
        return False
    return all(np.array_equal(a[k], b[k]) for k in a)


def compress_one(raw: Path, apply: bool, keep: bool) -> tuple[int, int, str]:
    """(original bytes, compressed bytes, note). Nothing is written unless apply."""
    before = raw.stat().st_size
    gz = raw.with_suffix(raw.suffix + ".gz")
    if gz.exists():
        return before, gz.stat().st_size, "already compressed, skipped"
    if not apply:
        return before, 0, "would compress"

    with raw.open("rb") as fh, gzip.open(gz, "wb", compresslevel=LEVEL) as out:
        shutil.copyfileobj(fh, out)

    try:
        original, restored = parse_ngspice_raw(raw), parse_ngspice_raw(gz)
    except Exception as exc:                                    # noqa: BLE001
        gz.unlink(missing_ok=True)
        return before, 0, f"FAILED to re-parse, .gz removed: {exc}"
    if not same(original, restored):
        gz.unlink(missing_ok=True)
        return before, 0, "FAILED verification, .gz removed: arrays differ"

    after = gz.stat().st_size
    if not keep:
        raw.unlink()
    return before, after, "ok"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", type=Path, help="a results/ folder to walk")
    ap.add_argument("--apply", action="store_true", help="actually write (default: dry run)")
    ap.add_argument("--keep", action="store_true", help="keep the originals after verifying")
    ap.add_argument("--limit", type=int, default=0, help="stop after N files, for a trial")
    a = ap.parse_args()

    folder = (a.folder if a.folder.is_absolute() else ROOT / a.folder).resolve()
    if not folder.is_dir():
        print(f"not a directory: {folder}")
        return 2

    raws = sorted(folder.rglob("*.raw"))
    if a.limit:
        raws = raws[:a.limit]
    if not raws:
        print(f"no .raw under {folder}")
        return 0

    print(f"{'DRY RUN - nothing written' if not a.apply else 'APPLYING'}: "
          f"{len(raws)} .raw under {folder.relative_to(ROOT)}\n")

    tot_before = tot_after = 0
    failures = []
    for i, raw in enumerate(raws, 1):
        before, after, note = compress_one(raw, a.apply, a.keep)
        tot_before += before
        tot_after += after if after else before
        if note.startswith("FAILED"):
            failures.append((raw, note))
            print(f"  [{i}/{len(raws)}] {raw.relative_to(folder)}: {note}")
            break
        if i % 200 == 0 or i == len(raws):
            print(f"  [{i}/{len(raws)}] {tot_before / 2**30:.2f} GB -> "
                  f"{tot_after / 2**30:.2f} GB")

    print()
    if failures:
        print("STOPPED on a verification failure; nothing further was touched.")
        for f, n in failures:
            print(f"  {f}: {n}")
        return 1

    if a.apply:
        print(f"{tot_before / 2**30:.2f} GB -> {tot_after / 2**30:.2f} GB "
              f"({tot_before / max(tot_after, 1):.1f}x), "
              f"{(tot_before - tot_after) / 2**30:.2f} GB freed"
              f"{' (originals kept)' if a.keep else ''}")
    else:
        est = tot_before / 5.9
        print(f"{len(raws)} files, {tot_before / 2**30:.2f} GB. At the measured 5.9x that is "
              f"about {est / 2**30:.2f} GB, freeing {(tot_before - est) / 2**30:.2f} GB.")
        print("Re-run with --apply to do it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
