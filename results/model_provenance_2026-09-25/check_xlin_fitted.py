# -*- coding: utf-8 -*-
"""Two checks against the critique: is x_lin ever actually fitted, and does our own doc
still carry the endpoint argument it says is false?"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(r"C:/Users/sh3qm/code/ibis_comparison")
sys.path.insert(0, str(ROOT / "scripts"))
import stage_count_from_file as sc          # noqa: E402

print("=== every x_lin value that appears in any step1 fit ===")
vals = {}
for f in sorted((sc.OUT / "step1").glob("*.csv")):
    for r in csv.DictReader(f.open()):
        vals.setdefault(round(float(r["x_lin"]), 4), 0)
        vals[round(float(r["x_lin"]), 4)] += 1
for v, n in sorted(vals.items()):
    print(f"   x_lin = {v}   in {n} fitted rows")

print("\n=== what settings() hands the fitter, per pass ===")
for pass_ in ("as_track1", "est_knee", "file_only"):
    for dev in ("ex2", "inv_chain"):
        try:
            cc, prior, prior3, xlin = sc.settings(dev, pass_)
            print(f"   {pass_:10s} {dev:10s} x_lin_fixed = {xlin}")
        except Exception as e:                       # noqa: BLE001
            print(f"   {pass_:10s} {dev:10s} -> {e}")

print("\n=== does our own writing still carry the endpoint argument? ===")
pat = re.compile(r"agree about the endpoints|only the two ends|visits only", re.I)
for p in (ROOT / "docs/track1_recipe.md", ROOT / "docs/track1_explainer.template.html"):
    hits = [f"      line {i}: {l.strip()[:110]}"
            for i, l in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if pat.search(l)]
    print(f"   {p.name}: {len(hits)} hit(s)")
    print("\n".join(hits))
