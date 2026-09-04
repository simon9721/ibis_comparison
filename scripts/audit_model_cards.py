#!/usr/bin/env python3
"""Find HSPICE runs built on the ngspice model card.

`hspice_ngspice.mod` zeroes RDSW/PRWG/PRWB so ngspice does not stall on the small
devices. That makes the output stage ~12% stronger than the I-V tables the IBIS
models were characterised from, so an HSPICE *transistor reference* built on it is
graded against the wrong silicon -- on io_buf its first rising edge lands ~110 ps
early, which reads as a timing defect in the model and is not one.

The rule and the evidence are in docs/model_card_rule.md. `spicelab.hspice()` now
refuses such a deck, but 536 runs predate that check, so this reports what is
already on disk.

A deck is counted as an HSPICE run when a `.tr0` sits beside it. The same card in
a deck with only a `.raw` is an ngspice run and is correct.

    py -3.14 scripts/audit_model_cards.py
    py -3.14 scripts/audit_model_cards.py --root results/_baseline_edgecmd
"""
from __future__ import annotations

import argparse
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BAD_CARD = "hspice_ngspice.mod"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=ROOT / "results")
    ap.add_argument("--list", action="store_true", help="print every offending deck")
    args = ap.parse_args()
    root = args.root if args.root.is_absolute() else ROOT / args.root

    bad: collections.Counter[str] = collections.Counter()
    clean: collections.Counter[str] = collections.Counter()
    offenders: list[Path] = []
    for sp in root.rglob("run.sp"):
        try:
            text = sp.read_text(errors="ignore")
        except OSError:
            continue
        if not (sp.parent / "run.tr0").exists():
            continue                       # not an HSPICE run
        tree = sp.relative_to(root).parts[0] if sp.relative_to(root).parts else "."
        if BAD_CARD in text:
            bad[tree] += 1
            offenders.append(sp)
        elif "hspice.mod" in text:
            clean[tree] += 1

    if bad:
        print(f"HSPICE runs on {BAD_CARD} -- graded against ~12% strong silicon:")
        for tree, n in bad.most_common():
            print(f"  {n:>5}  {tree}")
        print(f"  {sum(bad.values()):>5}  total")
    else:
        print(f"No HSPICE run uses {BAD_CARD}.")

    if clean:
        print("\nHSPICE runs on the stock hspice.mod -- these are the trustworthy ones:")
        for tree, n in clean.most_common(8):
            print(f"  {n:>5}  {tree}")
        print(f"  {sum(clean.values()):>5}  total")

    if args.list:
        print()
        for sp in offenders:
            print(f"  {sp.relative_to(ROOT)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
