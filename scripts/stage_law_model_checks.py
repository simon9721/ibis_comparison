#!/usr/bin/env python3
"""Two checks on the stage-law model, by rebuilding candidates with the track-1 recipe.

1. One rule for x_lin. The pad-level results of the paper fit x_lin on inv_chain and io_buf and
   fix it at 0.45 on the other ten. This rebuilds the candidate grid of those two buffers with
   x_lin = 0.45 (inv_chain: the band K = 6, 7, 8 x three map shapes; io_buf: K = 1, K_d = 3 x three
   shapes), calibrates each on the one stressed pad run and scores it at the five widths, and
   selects by the waveform rms at the calibration width as the procedure does. If the result holds,
   the method is one rule everywhere and the exception leaves the paper.

2. Sensitivity to x_lin. The selected candidate of ex2 (K = 3, map (0.5, 0.7), C_comp 2.64 pF) and
   of inv_chain (K = 6, (0.4, 0.9), 0.66 pF) rebuilt with x_lin = 0.35 and 0.55, against 0.45.

Every build is gate_chain_prototype.main() with the arguments stage_count_from_file's step 8
used (source ibis, prior maps, the knee C_comp, calibration on the pad), plus --fix-xlin, into
results/stage_law_model_checks_2026-10-22/builds/<buffer>_c<cc>/. The shipped models at the knee
C_comp are reused from stage_count_from_file_2026-09-21/knee_models. The threshold search's
intermediate raws are deleted after each build, as step 8 did.

Output: results/stage_law_model_checks_2026-10-22/{checks.csv, FINDINGS.md}

    py -3.14 scripts/stage_law_model_checks.py [--workers 4] [--only xlin|sens] [--resume]

Jobs of one buffer share that buffer's shipped full-swing run folder (gate_ramp_prototype.run_ours
rewrites it), so workers must not run the same buffer at once: the job list is round-robin over
buffers, and --resume rebuilds only the jobs whose folder has no sweep.csv, with one worker.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import io
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402

OUT = ROOT / "results" / "stage_law_model_checks_2026-10-22"
BUILDS = OUT / "builds"
SHAPES = [(0.5, 0.7), (0.4, 0.6), (0.4, 0.9)]


def jobs(which: str):
    import stage_count_from_file as sc
    out = []
    if which in ("xlin", "all"):
        for K in sc.plateau_band("inv_chain"):
            for sh in SHAPES:
                out.append(dict(dev="inv_chain", K=K, Kd=None, shape=sh, xlin=0.45, check="xlin_uniform"))
        for sh in SHAPES:
            out.append(dict(dev="io_buf", K=1, Kd=sc.plateau_band("io_buf", "pull-down")[0], shape=sh, xlin=0.45, check="xlin_uniform"))
    if which in ("sens", "all"):
        for xl in (0.35, 0.55):
            out.append(dict(dev="ex2", K=3, Kd=None, shape=(0.5, 0.7), xlin=xl, check="xlin_sensitivity"))
            out.append(dict(dev="inv_chain", K=6, Kd=None, shape=(0.4, 0.9), xlin=xl, check="xlin_sensitivity"))
    return out


def folder_of(job: dict) -> Path:
    import stage_count_from_file as sc
    b, cc = sc.BUFFERS[job["dev"]], sc.est_cc(job["dev"], "knee")
    return BUILDS / f"{job['dev']}_c{cc:g}" / (f"ibis_prior_K{job['K']}" + (f"_Kd{job['Kd']}" if job["Kd"] else "")
                                               + f"_prior{job['shape'][0]:g}_{job['shape'][1]:g}_xlin{job['xlin']:g}_calibpad{b['calib']}")


def build(job: dict) -> dict:
    """One build in a pool worker: the step-8 arguments plus --fix-xlin, into this study's folder."""
    import gate_chain_prototype as gch
    import gate_ramp_prototype as gp
    import spicelab as sl
    import stage_count_from_file as sc
    orig = sl.ngspice
    sl.ngspice = lambda d, deck="run.sp", raw="run.raw", timeout_s=600, ngspice_path=None: \
        orig(d, deck, raw, min(timeout_s, 600), ngspice_path)
    gp.sl.ngspice = sl.ngspice
    gch.OUT = BUILDS
    gch.G = sc.KNEE_MODELS
    dev, b = job["dev"], sc.BUFFERS[job["dev"]]
    cc = sc.est_cc(dev, "knee")
    argv = ["gate_chain_prototype", "--variant", dev, "--source", "ibis", "--maps", "prior",
            "--K", str(job["K"]), "--calib-pad", str(b["calib"]), "--ccomp", f"{cc:g}",
            "--prior", f"{job['shape'][0]:g}", f"{job['shape'][1]:g}", "--fix-xlin", f"{job['xlin']:g}"]
    if job["Kd"] is not None:
        argv += ["--Kd", str(job["Kd"])]
    sys.argv = argv
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        gch.main()
    (OUT / "logs").mkdir(parents=True, exist_ok=True)
    name = f"{dev}_K{job['K']}" + (f"_Kd{job['Kd']}" if job["Kd"] else "") + f"_prior{job['shape'][0]:g}_{job['shape'][1]:g}_xlin{job['xlin']:g}"
    (OUT / "logs" / f"{name}.log").write_text(log.getvalue(), encoding="utf-8")
    folder = BUILDS / f"{dev}_c{cc:g}" / (f"ibis_prior_K{job['K']}" + (f"_Kd{job['Kd']}" if job["Kd"] else "")
                                         + f"_prior{job['shape'][0]:g}_{job['shape'][1]:g}_xlin{job['xlin']:g}_calibpad{b['calib']}")
    for r in folder.glob("calib*/it[0-9][0-9]/run.raw"):
        r.unlink(missing_ok=True)
    return dict(job, cc=cc, folder=str(folder))


def score(row: dict) -> dict:
    import gate_ramp_prototype as gp
    import selector_from_one_run as sel
    folder = Path(row["folder"])
    sweep = list(csv.DictReader((folder / "sweep.csv").open()))[-1]
    pk = [float(v) for k, v in sweep.items() if k.startswith("pk_d")]
    lag = [float(v) for k, v in sweep.items() if k.startswith("lag_d")]
    gp.VARIANT_NAME = row["dev"]
    cases = gp.cases(row["dev"])
    rms_calib = sel.pad_rms_one(row["dev"], folder, cases[-1])
    rms_all = float(np.mean([v for v in (sel.pad_rms_one(row["dev"], folder, c) for c in cases) if v == v]))
    return dict(row, worst_peak_pct=round(max(map(abs, pk)), 1), peak_calib_pct=round(pk[-1], 1),
                lag_calib_ps=round(lag[-1]), pad_rms_calib_mV=round(rms_calib, 1), pad_rms_all_mV=round(rms_all, 1),
                peaks=" ".join(f"{v:+.1f}" for v in pk))


def write_findings(rows):
    paper = {"inv_chain": (5.1, "x_lin fitted, 0.28"), "io_buf": (7.7, "x_lin fitted, 0.41"), "ex2": (8.3, "x_lin 0.45")}
    L = ["# Two checks on the stage-law model", "", "*2026-10-22.* `scripts/stage_law_model_checks.py`; builds with the",
         "track-1 recipe (`gate_chain_prototype`, step-8 arguments plus `--fix-xlin`), scored at the five widths.", ""]
    L += ["## 1. One rule for x_lin: inv_chain and io_buf rebuilt with x_lin = 0.45", "",
          "The paper's pad-level result fitted x_lin on these two (0.28 and 0.41) and fixed it at 0.45 elsewhere.",
          "Here every candidate of the two buffers is rebuilt with x_lin = 0.45 and the procedure's selector",
          "(waveform rms at the calibration width) picks one.", "",
          "| buffer | K | K_d | shape | fit rms (26) | peak at calib. (%) | lag at calib. (ps) | pad rms at calib. (mV) | worst peak, five widths (%) |",
          "|---|---:|---:|---|---:|---:|---:|---:|---:|"]
    for dev in ("inv_chain", "io_buf"):
        rs = [r for r in rows if r["check"] == "xlin_uniform" and r["dev"] == dev]
        if not rs:
            continue
        pick = min(rs, key=lambda r: r["pad_rms_calib_mV"])
        for r in sorted(rs, key=lambda r: (r["K"], r["shape"])):
            mark = " **selected**" if r is pick else ""
            L.append(f"| {dev} | {r['K']} | {r['Kd'] or ''} | ({r['shape'][0]:g}, {r['shape'][1]:g}) | {r.get('fit_rms', '')} | "
                     f"{r['peak_calib_pct']:+.1f} | {r['lag_calib_ps']:+.0f} | {r['pad_rms_calib_mV']:.0f} | {r['worst_peak_pct']:.1f}{mark} |")
        L.append(f"| | | | | | | | **{dev}: selected {pick['worst_peak_pct']:.1f} % with x_lin = 0.45; the paper's result "
                 f"{paper[dev][0]} % ({paper[dev][1]})** | |")
    L += ["", "## 2. Sensitivity to x_lin on the selected candidates", "",
          "| buffer | K | shape | x_lin | peak at calib. (%) | lag at calib. (ps) | pad rms at calib. (mV) | worst peak, five widths (%) | peaks at the five widths (%) |",
          "|---|---:|---|---:|---:|---:|---:|---:|---|"]
    for r in sorted((r for r in rows if r["check"] == "xlin_sensitivity"), key=lambda r: (r["dev"], r["xlin"])):
        L.append(f"| {r['dev']} | {r['K']} | ({r['shape'][0]:g}, {r['shape'][1]:g}) | {r['xlin']:.2f} | {r['peak_calib_pct']:+.1f} | "
                 f"{r['lag_calib_ps']:+.0f} | {r['pad_rms_calib_mV']:.0f} | {r['worst_peak_pct']:.1f} | {r['peaks']} |")
    L += ["", "At x_lin = 0.45 the same candidates score 8.3 % (ex2) and 5.1 % (inv_chain, with x_lin fitted at 0.28)",
          "in the paper's Table VIII; the inv_chain row at 0.45 of check 1 is the like-for-like comparison.", ""]
    (OUT / "FINDINGS.md").write_text("\n".join(L), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", choices=("xlin", "sens", "all"), default="all")
    ap.add_argument("--resume", action="store_true", help="build only the jobs without a sweep.csv, one worker")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    js = jobs(args.only)
    # round-robin over buffers, so that one buffer's builds rarely share a worker slot
    by_dev: dict[str, list] = {}
    for j in js:
        by_dev.setdefault(j["dev"], []).append(j)
    ordered = []
    while any(by_dev.values()):
        for dev in list(by_dev):
            if by_dev[dev]:
                ordered.append(by_dev[dev].pop(0))
    js = ordered
    todo = [j for j in js if not (folder_of(j) / "sweep.csv").exists()] if args.resume else js
    workers = 1 if args.resume else args.workers
    print(f"{len(todo)} of {len(js)} builds to run, {workers} workers", flush=True)
    if todo:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            list(ex.map(build, todo))
    import stage_count_from_file as sc
    built = [dict(j, cc=sc.est_cc(j["dev"], "knee"), folder=str(folder_of(j))) for j in js]
    rows = []
    for b in built:
        try:
            rows.append(score(b))
            print(f"  {b['dev']:9s} K{b['K']} {b['shape']} x_lin {b['xlin']}: worst {rows[-1]['worst_peak_pct']} %, "
                  f"rms at calib {rows[-1]['pad_rms_calib_mV']} mV", flush=True)
        except Exception as e:                                       # noqa: BLE001
            print(f"  {b['dev']} K{b['K']} {b['shape']} x_lin {b['xlin']}: scoring failed: {e}", flush=True)
    for r in rows:                                                   # the fit residual, from the build's log
        try:
            log = (OUT / "logs" / (f"{r['dev']}_K{r['K']}" + (f"_Kd{r['Kd']}" if r["Kd"] else "")
                                   + f"_prior{r['shape'][0]:g}_{r['shape'][1]:g}_xlin{r['xlin']:g}.log")).read_text(encoding="utf-8")
            import re
            m = re.search(r"K=%d: Ku-domain rms ([0-9.]+)" % r["K"], log)
            r["fit_rms"] = m.group(1) if m else ""
        except OSError:
            r["fit_rms"] = ""
    fields = ["check", "dev", "K", "Kd", "shape", "xlin", "cc", "fit_rms", "peak_calib_pct", "lag_calib_ps",
              "pad_rms_calib_mV", "pad_rms_all_mV", "worst_peak_pct", "peaks", "folder"]
    with (OUT / "checks.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{r[k][0]:g}/{r[k][1]:g}" if k == "shape" else r.get(k, "")) for k in fields})
    write_findings(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
