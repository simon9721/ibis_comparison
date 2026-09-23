#!/usr/bin/env python3
"""Is inv_chain's 26 % the handoff between the two Ku curves?

At the track-1 settings inv_chain's gate is right at the worst width (0.95 against a
transistor 0.94) and its pad is still 26 % high, so the error is in the map, not the gate.
The suspect is the handoff: the file's falling Ku table sits ~19 ps early against the gate, so
KUGATE_OFF reads 0.49 where KUGATE_ON reads 0.96 at the same gate. A stressed pulse turns
round in exactly that region.

Three builds of the same model, differing only in the pull-up map:

    as_built   the file's two curves (the step-7 build, reproduced here as the control)
    one_curve  KUGATE_OFF := KUGATE_ON - one curve both ways, no handoff step at all
    average    KUGATE_OFF := (KUGATE_ON + KUGATE_OFF) / 2 - half the step

If the 26 % collapses under one_curve, the handoff is the cause. If it does not, the map is
wrong in a way the two curves share.

Output: results/inv_chain_single_curve_2026-09-22/

    py -3.14 scripts/inv_chain_single_curve.py
"""
from __future__ import annotations

import contextlib
import csv
import io
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
import stage_count_from_file as sc  # noqa: E402

OUT = ROOT / "results" / "inv_chain_single_curve_2026-09-22"
DEV, K, CC = "inv_chain", 7, 0.6
SRC = sc.MEAS_MODELS / f"{DEV}_c{CC:g}" / "shipped" / "driver.sub"       # step 7's model, today's converter


def table(text: str, name: str):
    """The (gate, value) pairs of one B-source pwl table, with the text around it."""
    line = re.search(rf"^B{name} {name} 0 V = pwl\(.*$", text, re.M).group(0)
    head, body = line.split("), 1),", 1)
    nums = [float(x) for x in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", body)]
    return line, head + "), 1),", np.array(nums).reshape(-1, 2)


def remap(text: str, mode: str) -> str:
    if mode == "as_built":
        return text
    on_line, _on_head, on = table(text, "KUGATE_ON")
    off_line, off_head, off = table(text, "KUGATE_OFF")
    off_at_on_gate = np.interp(on[:, 0], off[:, 0], off[:, 1])
    y = on[:, 1] if mode == "one_curve" else 0.5 * (on[:, 1] + off_at_on_gate)
    new = off_head + " " + ", ".join(f"{g:.6g}, {v:.6g}" for g, v in zip(on[:, 0], y)) + ")"
    return text.replace(off_line, new)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    gp, gch, _ = sc._modules()
    base = SRC.read_text(encoding="utf-8")
    rows = []
    for mode in ("as_built", "one_curve", "average"):
        mdir = OUT / "models" / f"{DEV}_c{CC:g}" / "shipped"
        mdir.mkdir(parents=True, exist_ok=True)
        (mdir / "driver.sub").write_text(remap(base, mode), encoding="utf-8")
        shutil.rmtree(OUT / mode, ignore_errors=True)
        gch.OUT = OUT / mode
        gch.G = OUT / "models"
        sys.argv = ["gate_chain_prototype", "--variant", DEV, "--source", "ibis", "--maps", "prior",
                    "--K", str(K), "--calib-pad", str(sc.BUFFERS[DEV]["calib"]),
                    "--ccomp", f"{CC:g}", "--prior", "0.49", "0.6"]
        log = io.StringIO()
        with contextlib.redirect_stdout(log):
            gch.main()
        (OUT / mode).mkdir(parents=True, exist_ok=True)
        (OUT / mode / "run.log").write_text(log.getvalue(), encoding="utf-8")
        for p in sorted((OUT / mode / f"{DEV}_c{CC:g}").glob(f"ibis_prior_K{K}_*/sweep.csv")):
            for r in list(csv.DictReader(p.open())):
                pk = [float(v) for k, v in r.items() if k.startswith("pk_d")]
                lag = [float(v) for k, v in r.items() if k.startswith("lag_d")]
                rows.append(dict(mode=mode, model="shipped" if not r["K"] else f"chain K={r['K']}",
                                 worst_peak_pct=f"{max(map(abs, pk)):.1f}",
                                 peaks_pct=" / ".join(f"{x:+.1f}" for x in pk),
                                 lag_ps=" / ".join(f"{x:.0f}" for x in lag),
                                 full_pad_rms_mV=r["full_pad_rms_mV"],
                                 gate=" / ".join(v for k, v in r.items() if k.startswith("gate_d"))))
        print(f"  {mode:10s} " + (rows[-1]["worst_peak_pct"] + " %  " + rows[-1]["peaks_pct"] if rows else "no result"), flush=True)
    with (OUT / "single_curve.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT / 'single_curve.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
