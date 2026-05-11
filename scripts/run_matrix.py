"""
run_matrix.py — Clean test matrix runner for pybis vs refspice convergence study.

Usage:
    python scripts/run_matrix.py [--timeout 30] [--tag D1] [--dry-run]

Issue dimensions
----------------
  D1 (Driver)   : driver subcircuit + Rload + single edge
                  Does the driver alone (no channel) converge for all edge types?
  D2 (Channel)  : full PRBS7, Rload vs T-line
                  Does the T-line cause stalls independent of the driver?
  D3 (Input)    : same driver/channel, varying edge speed / hold time
                  Does PWL transition rate drive Newton failures?

Drivers
-------
  pybis    : B-source table model  (ngspice_pybis/)
  refspice : transistor-level SPICE (ngspice_refspice/)

This script runs each bench with a wall-clock timeout, then prints a summary
table grouped by issue dimension.
"""

import subprocess
import sys
import os
import time
import re
import struct
import argparse
import numpy as np
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT      = Path(__file__).resolve().parents[1]
PYBIS_DIR = ROOT / "ngspice_pybis"
REF_DIR   = ROOT / "ngspice_refspice"
NGSPICE   = Path(r"C:\Users\simom\Desktop\spice\ngspice-46_64\Spice64\bin\ngspice_con.exe")

# ---------------------------------------------------------------------------
# Test matrix definition
# ---------------------------------------------------------------------------
# Each entry: (tag, dimension, driver, channel, input_desc, sp_file, raw_file, sim_end_ns)
TESTS = [
    # ── D1: Driver isolation (Rload, single / short edge) ──────────────────
    dict(
        tag="D1", dim="Driver", driver="pybis", channel="Rload",
        input="rise-only 200ps",
        sp=PYBIS_DIR / "tb_test_rise.sp",
        raw=PYBIS_DIR / "tb_test_rise.raw",
        sim_end_ns=20.0,
    ),
    dict(
        tag="D1", dim="Driver", driver="pybis", channel="Rload",
        input="RSF 200ps tr/tf",
        sp=PYBIS_DIR / "tb_test_rfr.sp",
        raw=PYBIS_DIR / "tb_test_rfr.raw",
        sim_end_ns=20.0,
    ),
    dict(
        tag="D1", dim="Driver", driver="pybis", channel="Rload",
        input="RSF 2ns tr/tf (slow)",
        sp=PYBIS_DIR / "tb_test_rise_fall.sp",
        raw=PYBIS_DIR / "tb_test_rise_fall.raw",
        sim_end_ns=20.0,
    ),
    dict(
        tag="D1", dim="Driver", driver="refspice", channel="Rload",
        input="RSF 200ps tr/tf",
        sp=REF_DIR / "tb_refspice_rsf_rload.sp",
        raw=REF_DIR / "tb_refspice_rsf_rload.raw",
        sim_end_ns=22.0,
    ),
    # ── D2: Channel isolation (PRBS7, Rload vs T-line) ─────────────────────
    dict(
        tag="D2", dim="Channel", driver="pybis", channel="Rload",
        input="PRBS7 1000ns",
        sp=PYBIS_DIR / "tb_pybis_prbs7_rload.sp",
        raw=PYBIS_DIR / "tb_pybis_prbs7_rload.raw",
        sim_end_ns=1000.0,
    ),
    dict(
        tag="D2", dim="Channel", driver="pybis", channel="T-line Td=30p",
        input="PRBS7 1000ns",
        sp=PYBIS_DIR / "tb_pybis_prbs7_batch.sp",
        raw=PYBIS_DIR / "tb_pybis_prbs7_batch.raw",
        sim_end_ns=1000.0,
    ),
    dict(
        tag="D2", dim="Channel", driver="refspice", channel="Rload",
        input="PRBS7 1000ns",
        sp=REF_DIR / "tb_refspice_prbs7_rload.sp",
        raw=REF_DIR / "tb_refspice_prbs7_rload.raw",
        sim_end_ns=1000.0,
    ),
    dict(
        tag="D2", dim="Channel", driver="refspice", channel="T-line Td=30p",
        input="PRBS7 1000ns",
        sp=REF_DIR / "tb_refspice_prbs7_batch.sp",
        raw=REF_DIR / "tb_refspice_prbs7_batch.raw",
        sim_end_ns=1000.0,
    ),
    # ── D3: Input stream (pybis + Rload, vary edge speed and hold) ──────────
    dict(
        tag="D3", dim="Input", driver="pybis", channel="Rload",
        input="RSF 200ps  5ns hold",
        sp=PYBIS_DIR / "tb_test_rf_5ns.sp",
        raw=PYBIS_DIR / "tb_test_rf_5ns.raw",
        sim_end_ns=20.0,
    ),
    dict(
        tag="D3", dim="Input", driver="pybis", channel="Rload",
        input="RSF 200ps 10ns hold",
        sp=PYBIS_DIR / "tb_test_rfr.sp",
        raw=PYBIS_DIR / "tb_test_rfr.raw",
        sim_end_ns=20.0,
    ),
    dict(
        tag="D3", dim="Input", driver="pybis", channel="Rload",
        input="rise-only 200ps (stays HIGH)",
        sp=PYBIS_DIR / "tb_test_rise.sp",
        raw=PYBIS_DIR / "tb_test_rise.raw",
        sim_end_ns=20.0,
    ),
    dict(
        tag="D3", dim="Input", driver="pybis", channel="Rload",
        input="RSF 2ns tr/tf (slow edge)",
        sp=PYBIS_DIR / "tb_test_rise_fall.sp",
        raw=PYBIS_DIR / "tb_test_rise_fall.raw",
        sim_end_ns=20.0,
    ),
]

# ---------------------------------------------------------------------------
# Raw file parser
# ---------------------------------------------------------------------------
def parse_raw_end_time(raw_path):
    """Return (n_rows, t_end_ns) or (None, None) if file is missing/corrupt."""
    try:
        with open(raw_path, "rb") as f:
            header = f.read(4096)
        nv = int(re.search(rb"No\. Variables:\s+(\d+)", header).group(1))
        bi = header.find(b"Binary:\x0a") + 8
        file_size = raw_path.stat().st_size
        n = (file_size - bi) // (nv * 8)
        if n <= 0:
            return None, None
        offset = bi + (n - 1) * nv * 8
        with open(raw_path, "rb") as f:
            f.seek(offset)
            t = struct.unpack("<d", f.read(8))[0]
        return n, t * 1e9
    except Exception as e:
        return None, None

# ---------------------------------------------------------------------------
# Run a single test
# ---------------------------------------------------------------------------
def run_test(t, timeout_s, dry_run=False):
    sp  = t["sp"]
    raw = t["raw"]
    if not sp.exists():
        return dict(status="MISSING_SP", wall_s=0, n_rows=None, t_end_ns=None)

    if dry_run:
        n, tend = parse_raw_end_time(raw) if raw.exists() else (None, None)
        if tend is not None:
            pct = tend / t["sim_end_ns"] * 100
            ok = abs(tend - t["sim_end_ns"]) < 0.5
            return dict(status="OK" if ok else "STALL", wall_s=0, n_rows=n, t_end_ns=tend)
        return dict(status="NO_RAW", wall_s=0, n_rows=None, t_end_ns=None)

    raw.unlink(missing_ok=True)
    t0 = time.time()
    try:
        subprocess.run(
            [str(NGSPICE), "-b", "-r", str(raw), str(sp)],
            timeout=timeout_s,
            capture_output=True,
            cwd=sp.parent,
        )
    except subprocess.TimeoutExpired:
        pass
    wall_s = round(time.time() - t0, 1)

    n, tend = parse_raw_end_time(raw) if raw.exists() else (None, None)
    if tend is None:
        return dict(status="NO_RAW", wall_s=wall_s, n_rows=None, t_end_ns=None)

    ok = abs(tend - t["sim_end_ns"]) < 0.5
    status = "OK" if ok else "STALL"
    return dict(status=status, wall_s=wall_s, n_rows=n, t_end_ns=tend)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=float, default=60,
                    help="Per-test wall-clock timeout (s). Default 60.")
    ap.add_argument("--tag", default=None,
                    help="Only run tests with this tag, e.g. D1 D2 D3.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Skip simulation; report from existing raw files only.")
    args = ap.parse_args()

    tests = TESTS
    if args.tag:
        tests = [t for t in tests if t["tag"] == args.tag]

    print(f"\n{'='*90}")
    print(f"  {'Tag':<4}  {'Dim':<9}  {'Driver':<10}  {'Channel':<16}  {'Input':<28}  {'Status':<7}  {'t_end':>8}  {'Wall':>6}")
    print(f"{'='*90}")

    results = {}
    current_dim = None
    for t in tests:
        if t["dim"] != current_dim:
            current_dim = t["dim"]
            if current_dim == "Driver":
                print(f"\n── D1: Driver isolation (Rload + single edge — does subcircuit alone converge?) ──")
            elif current_dim == "Channel":
                print(f"\n── D2: Channel isolation (PRBS7 Rload vs T-line — does the channel cause stalls?) ──")
            elif current_dim == "Input":
                print(f"\n── D3: Input stream (pybis + Rload, vary edge speed/hold — is stimulus the trigger?) ──")

        label = f"{t['driver']}/{t['channel']}/{t['input']}"
        if not args.dry_run:
            print(f"  running  {label[:60]}...", end="\r", flush=True)

        r = run_test(t, args.timeout, dry_run=args.dry_run)
        results[label] = r

        tend_str  = f"{r['t_end_ns']:>7.1f}ns" if r["t_end_ns"] is not None else "    —   "
        wall_str  = f"{r['wall_s']:>5.1f}s" if not args.dry_run else "  (cached)"
        status_str = r["status"]

        pct = ""
        if r["t_end_ns"] is not None and t["sim_end_ns"] > 0:
            pct = f"  ({r['t_end_ns']/t['sim_end_ns']*100:.0f}%)"

        print(f"  {t['tag']:<4}  {t['dim']:<9}  {t['driver']:<10}  {t['channel']:<16}  {t['input']:<28}  {status_str:<7}  {tend_str}{pct}  {wall_str}")

    print(f"\n{'='*90}")
    n_ok    = sum(1 for r in results.values() if r["status"] == "OK")
    n_stall = sum(1 for r in results.values() if r["status"] == "STALL")
    n_miss  = sum(1 for r in results.values() if r["status"] in ("NO_RAW", "MISSING_SP"))
    print(f"  Summary: {n_ok} OK  |  {n_stall} STALL  |  {n_miss} missing\n")

if __name__ == "__main__":
    main()
