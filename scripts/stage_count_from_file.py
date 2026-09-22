#!/usr/bin/env python3
"""Can track 1 find the predriver stage count K from the IBIS file? (plan: PLAN.md in the output folder)

Step 1 (Python only): for every buffer, fit K = 1 ... 10 identical current-limited stages to
the file's own full-swing Ku(t) - the file-only fit of the track-1 builds,
`gate_chain_prototype.fit_chain_ku` - and pick the smallest K on the rms plateau (the existing
`pick_K` rule). Two passes:

    as_track1   each buffer's existing track-1 settings (C_comp, curve shape, resistive fraction)
    file_only   declared C_comp, one universal curve shape (vt 0.5, alpha 0.7), fraction 0.45

Step 2 (ngspice): build the as_track1 model at the picked K, K - 1, K + 1 and the netlist K,
calibrate the stage threshold on the one stressed pad run, score the five stressed widths.

    py -3.14 scripts/stage_count_from_file.py --step 1 [--workers 4]
    py -3.14 scripts/stage_count_from_file.py --step 1 --summarise
    py -3.14 scripts/stage_count_from_file.py --step 2 [--workers 3]
    py -3.14 scripts/stage_count_from_file.py --step 2 --summarise
    py -3.14 scripts/stage_count_from_file.py --step 3 [--workers 4]     # step 2, strictly file-only
    py -3.14 scripts/stage_count_from_file.py --step 4 [--workers 4]     # step 3's two inputs, one at a time
    py -3.14 scripts/stage_count_from_file.py --step 5 [--workers 4]     # file-only, C_comp from ccomp_from_file.py
    py -3.14 scripts/stage_count_from_file.py --step 6 [--workers 4]     # the whole chain from the file alone

Step 2 needs `--Kd` in gate_chain_prototype.py (io_buf's pull-down chain count), added 09-21.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")            # share the CPU; the fits are single-threaded
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

OUT = ROOT / "results" / "stage_count_from_file_2026-09-21"
KS = list(range(1, 11))
UNIVERSAL = (0.5, 0.7)

# the existing track-1 build of each buffer (results/gate_chain_prototype_2026-09-10/<dev>_c<cc>/...),
# and the netlist predriver stage count: stages from the input to the output transistors' gate
BUFFERS = {
    #  name           C_comp  curve shape                      fraction  calib  netlist K (pull-up, pull-down)
    "ex2":          dict(cc=1.7, prior=(0.57, 0.64), xlin=0.45, calib=810, k_net=(3, None)),
    "ex2_base":     dict(cc=1.7, prior=(0.57, 0.64), xlin=0.45, calib=50, k_net=(3, None)),
    "ex2_slowpre":  dict(cc=1.7, prior=(0.57, 0.64), xlin=0.45, calib=50, k_net=(3, None)),
    "ex2_skewp":    dict(cc=1.7, prior=(0.57, 0.64), xlin=0.45, calib=50, k_net=(3, None)),
    "ex2_weak":     dict(cc=1.7, prior=(0.57, 0.64), xlin=0.45, calib=50, k_net=(3, None)),
    "ex2_nomiller": dict(cc=1.7, prior=(0.57, 0.64), xlin=0.45, calib=50, k_net=(3, None)),
    "inv_chain":    dict(cc=0.6, prior=(0.49, 0.60), xlin=None, calib=104, k_net=(7, None)),
    "inv_base8":    dict(cc=0.6, prior3=(0.42, 1.15, 0.87), xlin=0.45, calib=50, k_net=(7, None)),
    "inv_stage4":   dict(cc=0.6, prior3=(0.42, 1.15, 0.87), xlin=0.45, calib=50, k_net=(3, None)),
    "inv_skewp":    dict(cc=0.4, prior3=(0.42, 1.15, 0.87), xlin=0.45, calib=50, k_net=(7, None)),
    "inv_weak":     dict(cc=0.3, prior3=(0.42, 1.15, 0.87), xlin=0.45, calib=50, k_net=(7, None)),
    "io_buf":       dict(cc=None, prior=(0.50, 0.78), xlin=None, calib=1505, k_net=(1, 3)),
}


def _modules():
    import gate_ramp_prototype as gp
    import gate_chain_prototype as gch
    import physics_map_gate_from_ibis as pm
    return gp, gch, pm


def full_ship(dev: str, cc, pass_: str = "as_track1"):
    """The shipped model's full-swing run.

    as_track1: the cached run the track-1 builds used (gate_cascade_prototype_2026-09-09).
    file_only: the model generated here from the buffer's IBIS file with today's converter,
    at the declared C_comp, and run in this folder - so nothing in the older folders is
    overwritten (8 of their declared-C_comp runs are stale)."""
    gp, gch, _ = _modules()
    gp.VARIANT_NAME = dev                     # sets the input edge, so the cached deck matches
    sup, ibis = gp.VARIANTS[dev]
    if pass_ == "as_track1":
        mdir = gch.G / (dev + (f"_c{cc:g}" if cc else ""))
        return gp.run_ours(mdir / "shipped/full", (mdir / "shipped/driver.sub").read_text(encoding="utf-8"), sup, 10.0)
    from pybis2spice import pybis2spice as pb, subcircuit
    if pass_ == "est_knee":
        # the same folder and the same construction gate_chain_prototype uses for --ccomp, so
        # the step-6 builds reuse this model instead of regenerating it
        mdir = KNEE_MODELS / f"{dev}_c{cc:g}" / "shipped"
        sub = mdir / "driver.sub"
        if not sub.exists():
            import re
            mdir.mkdir(parents=True, exist_ok=True)
            txt = re.sub(r"^C_comp\s+.*$", f"C_comp {cc:.4f}pF {cc:.4f}pF {cc:.4f}pF",
                         ibis.read_text(errors="ignore"), count=1, flags=re.M)
            ibis = mdir.parent / "input_ccomp.ibs"
            ibis.write_text(txt, encoding="utf-8")
            model, comp = gp.ibis_names(ibis)
            data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
            subcircuit.generate_spice_model("Output", gp.BUILD, data, "Typical", str(sub))
        return gp.run_ours(mdir / "full", sub.read_text(encoding="utf-8"), sup, 10.0)
    mdir = OUT / "shipped" / dev
    sub = mdir / "driver.sub"
    if not sub.exists():
        mdir.mkdir(parents=True, exist_ok=True)
        model, comp = gp.ibis_names(ibis)
        data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
        subcircuit.generate_spice_model("Output", gp.BUILD, data, "Typical", str(sub))
    return gp.run_ours(mdir / "full", sub.read_text(encoding="utf-8"), sup, 10.0)


def settings(dev: str, pass_: str):
    b = BUFFERS[dev]
    if pass_ == "as_track1":
        return b["cc"], b.get("prior"), b.get("prior3"), b["xlin"]
    if pass_ == "est_knee":                   # step 6: C_comp from the file's overshoot knee
        return est_cc(dev, "knee"), UNIVERSAL, None, 0.45
    return None, UNIVERSAL, None, 0.45        # file_only: declared C_comp, universal shape


def fit_job(pass_: str, dev: str, chain: str) -> Path:
    """Fit K = 1 ... 10 for one buffer / chain / pass; one CSV per job so partial runs survive."""
    import io
    import contextlib
    gp, gch, pm = _modules()
    cc, prior, prior3, xlin = settings(dev, pass_)
    fs = full_ship(dev, cc, pass_)
    if prior3:
        vt, al, gs = prior3
        gch.PRIOR_FN = lambda g: pm.prior3(g, vt, al, gs)   # noqa: E731
    else:
        vt, al = prior
        gch.PRIOR_FN = lambda g: pm.prior(g, vt, al)         # noqa: E731
    which = "ku" if chain == "pull-up" else "kd"
    path = OUT / "step1" / f"{pass_}__{dev}__{chain}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if path.exists():
        done = {int(r["K"]) for r in csv.DictReader(path.open())}
    new = not path.exists()
    with path.open("a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["pass", "buffer", "chain", "C_comp", "K", "rms", "s_up", "s_dn", "vt", "x_lin"])
        for K in KS:
            if K in done:
                continue
            with contextlib.redirect_stdout(io.StringIO()):
                c, prm = gch.fit_chain_ku(fs, vt, al, [K], which=which, x_lin_fixed=xlin)[K]
            w.writerow([pass_, dev, chain, cc if cc else "declared", K, f"{c:.6f}"] + [f"{x:.5f}" for x in prm[:4]])
            fh.flush()
    return path


def step1(workers: int) -> None:
    jobs = []
    for pass_ in ("as_track1", "file_only"):
        for dev, b in BUFFERS.items():
            jobs.append((pass_, dev, "pull-up"))
            if b["k_net"][1] is not None:
                jobs.append((pass_, dev, "pull-down"))
    # longest first: free-fraction fits and the slow inverter chains
    jobs.sort(key=lambda j: (j[0] != "as_track1", BUFFERS[j[1]]["xlin"] is not None))
    print(f"step 1: {len(jobs)} fits of K = {KS[0]}...{KS[-1]} on {workers} workers", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fit_job, *j): j for j in jobs}
        for f in as_completed(futs):
            j = futs[f]
            try:
                print(f"  done {j}: {f.result().name}", flush=True)
            except Exception as exc:  # one bad buffer must not cost the set
                print(f"  FAILED {j}: {exc!r}", flush=True)
    summarise()


def pick(rows):
    """The existing rule (gate_chain_prototype.pick_K): smallest K within 5 % of the best rms."""
    best = min(r[1] for r in rows)
    return min(k for k, c in rows if c <= 1.05 * best + 1e-4)


def summarise() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = []
    for p in sorted((OUT / "step1").glob("*.csv")):
        rows += list(csv.DictReader(p.open()))
    if not rows:
        print("no step-1 results yet")
        return
    groups = {}
    for r in rows:
        groups.setdefault((r["pass"], r["buffer"], r["chain"]), []).append((int(r["K"]), float(r["rms"])))
    out = []
    for (pass_, dev, chain), kr in sorted(groups.items()):
        kr.sort()
        k_net = BUFFERS[dev]["k_net"][0 if chain == "pull-up" else 1]
        complete = [k for k, _ in kr] == KS
        k_pick = pick(kr) if complete else None
        out.append(dict(pass_=pass_, buffer=dev, chain=chain, netlist_K=k_net, picked_K=k_pick if complete else "",
                        match=("yes" if k_pick == k_net else "no") if complete else "incomplete",
                        rms_by_K=" ".join(f"{c:.4f}" for _, c in kr)))
    with (OUT / "step1_summary.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    for o in out:
        print(f"  {o['pass_']:10s} {o['buffer']:13s} {o['chain']:9s} netlist {o['netlist_K']}  picked {o['picked_K']!s:3s} "
              f"{o['match']:10s} rms {o['rms_by_K']}")
    # figure: rms against K, one panel per pass, one line per buffer/chain, netlist K marked
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.2), sharey=True)
    cmap = plt.get_cmap("tab20")
    keys = sorted({(dev, chain) for (_p, dev, chain) in groups})     # one colour per buffer/chain, both panels
    for ax, pass_ in zip(axes, ("as_track1", "file_only")):
        for (p, dev, chain), kr in sorted(groups.items()):
            if p != pass_:
                continue
            kr.sort()
            k, c = zip(*kr)
            lab = dev + (" (PD)" if chain == "pull-down" else "")
            ln, = ax.plot(k, c, "-o", ms=3.5, lw=1.4, color=cmap(keys.index((dev, chain)) % 20), label=lab)
            k_net = BUFFERS[dev]["k_net"][0 if chain == "pull-up" else 1]
            if k_net in k:
                ax.plot([k_net], [c[k.index(k_net)]], "*", ms=13, color=ln.get_color(), mec="black", mew=0.6)
        ax.set_yscale("log")
        ax.set_xlabel("stage count K")
        ax.set_title({"as_track1": "track-1 settings", "file_only": "strictly file-only"}[pass_] +
                     "  (star = netlist count)", fontweight="bold")
        ax.grid(alpha=0.3, which="both")
        ax.set_xticks(KS)
    axes[0].set_ylabel("Ku-domain fit rms, full swing")
    axes[1].legend(fontsize=8, ncol=2, loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT / "step1_rms_vs_K.png", dpi=170)
    plt.close(fig)
    print(f"  wrote {OUT / 'step1_summary.csv'} and step1_rms_vs_K.png")


# --------------------------------------------------------------------------- step 2
# step 2: the buffer's track-1 settings; step 3: strictly file-only - the declared C_comp and one
# universal curve shape for every buffer, everything else (K range, resistive fraction, pad
# calibration width) as step 2. Step 3's shipped models are generated here from the IBIS files.
# Step 4 separates the two inputs step 3 changed at once, at the netlist K: 4a declared C_comp
# with the family curve shape, 4b the loop-measured C_comp with the universal shape.
FILE_MODELS = OUT / "file_only_models"          # shipped models at the declared C_comp
EST_MODELS = OUT / "est_cc_models"              # shipped models at the file-only C_comp estimate
KNEE_MODELS = OUT / "knee_models"               # shipped models at the knee estimate (step 6)
PASSES = {"step2":  dict(pass_="as_track1", cc="measured", shape="family", models=None),
          "step3":  dict(pass_="file_only", cc="declared", shape="universal", models=FILE_MODELS),
          "step4a": dict(pass_="declared_cc_family_shape", cc="declared", shape="family", models=FILE_MODELS),
          "step4b": dict(pass_="measured_cc_universal_shape", cc="measured", shape="universal", models=None),
          # step 5: strictly file-only again, but with C_comp taken from the file's own Ku
          # overshoot instead of the declared value (scripts/ccomp_from_file.py)
          "step5":  dict(pass_="estimated_cc_universal_shape", cc="estimate", shape="universal", models=EST_MODELS),
          # step 6: the whole chain from the file - C_comp from the overshoot knee (which can
          # correct upward, unlike step 5's cap at the declared value), K from the fit band and
          # the one stressed pad run's timing, universal shape
          "step6":  dict(pass_="est_knee", cc="estimate_knee", shape="universal", models=KNEE_MODELS)}
EST_CC_CSV = ROOT / "results" / "ccomp_from_file_2026-09-22" / "ccomp_from_file.csv"
EST_TOL = 0.02                                  # the Ku-overshoot tolerance the estimate uses


def declared_cc(dev: str) -> float:
    """The C_comp the buffer's IBIS file declares (typical corner)."""
    for r in csv.DictReader(EST_CC_CSV.open()):
        if r["buffer"] == dev:
            return float(r["declared_pF"])
    raise KeyError(f"{dev} not in {EST_CC_CSV}")


def est_cc(dev: str, rule: str = "bound") -> float:
    """C_comp from the IBIS file alone (scripts/ccomp_from_file.py), by one of two rules:

    bound  min(declared, largest C_comp whose solved Ku peak stays within EST_TOL of 1) - a cap,
           so it can only correct a declared value downward (step 5).
    knee   the overshoot curve's knee, the tighter of the Ku and Kd readings - an estimate in its
           own right, so it can correct upward too (step 6).

    Neither needs the probed gate."""
    for r in csv.DictReader(EST_CC_CSV.open()):
        if r["buffer"] == dev:
            if rule == "knee":
                return round(float(r["knee_pF"]), 2)
            return round(min(float(r["declared_pF"]), float(r[f"ku_bound_{EST_TOL:g}_pF"])), 2)
    raise KeyError(f"{dev} not in {EST_CC_CSV}")


def dcc_name(step: str, dev: str) -> str:
    """The buffer's folder name as gate_chain_prototype writes it: suffixed with the C_comp when
    one is imposed (measured or estimated), bare when the file's declared C_comp is used."""
    which = PASSES[step]["cc"]
    cc = {"measured": lambda: BUFFERS[dev]["cc"], "estimate": lambda: est_cc(dev),
          "estimate_knee": lambda: est_cc(dev, "knee")}.get(which, lambda: None)()
    return dev + (f"_c{cc:g}" if cc else "")


def build_dir(step: str, dev: str, K: int, Kd):
    """The folder gate_chain_prototype writes this build to (its label starts ibis_prior_K<K>_),
    or None if it does not exist yet."""
    dcc = dcc_name(step, dev)
    for p in sorted((OUT / step / dcc).glob(f"ibis_prior_K{K}_*")):
        if (Kd is None) == ("_Kd" not in p.name) and (Kd is None or f"_Kd{Kd}_" in p.name):
            return p
    return None


def build_job(dev: str, K: int, Kd, step: str = "step2") -> str:
    """One track-1 build at stage count K (io_buf: K for the pull-up chain, Kd for the pull-down),
    calibrated on the one stressed pad run and scored on the five widths by
    gate_chain_prototype itself, into OUT/<step>."""
    import contextlib
    import io
    import spicelab as sl
    gp, gch, _ = _modules()
    orig = sl.ngspice
    sl.ngspice = lambda d, deck="run.sp", raw="run.raw", timeout_s=600, ngspice_path=None: \
        orig(d, deck, raw, min(timeout_s, 600), ngspice_path)          # a stalled run costs 10 min, not 30
    gp.sl.ngspice = sl.ngspice
    gch.OUT = OUT / step
    # a pool worker keeps module state between jobs, and one pool may run several passes:
    # set the shipped-model folder on every job, back to gate_chain_prototype's own default
    gch._G_DEFAULT = getattr(gch, "_G_DEFAULT", gch.G)
    gch.G = PASSES[step]["models"] or gch._G_DEFAULT
    b = BUFFERS[dev]
    argv = ["gate_chain_prototype", "--variant", dev, "--source", "ibis", "--maps", "prior",
            "--K", str(K), "--calib-pad", str(b["calib"])]
    if PASSES[step]["cc"] == "declared":
        argv += ["--ccomp", "0"]                       # 0 = as declared in the IBIS file
    elif PASSES[step]["cc"] == "estimate":
        argv += ["--ccomp", f"{est_cc(dev):g}"]
    elif PASSES[step]["cc"] == "estimate_knee":
        argv += ["--ccomp", f"{est_cc(dev, 'knee'):g}"]
    elif b["cc"]:
        argv += ["--ccomp", f"{b['cc']:g}"]
    if PASSES[step]["shape"] == "universal":
        argv += ["--prior", f"{UNIVERSAL[0]:g}", f"{UNIVERSAL[1]:g}"]
    elif b.get("prior3"):
        argv += ["--prior3"] + [f"{x:g}" for x in b["prior3"]]
    else:
        argv += ["--prior"] + [f"{x:g}" for x in b["prior"]]
    if b["xlin"] is not None:
        argv += ["--fix-xlin", f"{b['xlin']:g}"]
    if Kd is not None:
        argv += ["--Kd", str(Kd)]
    sys.argv = argv
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        gch.main()
    (OUT / step / "logs").mkdir(parents=True, exist_ok=True)
    (OUT / step / "logs" / f"{dev}_K{K}" f"{'_Kd' + str(Kd) if Kd else ''}.log").write_text(log.getvalue(), encoding="utf-8")
    # the threshold search's intermediate runs are not read by anything after the build; on
    # 09-21 they filled the disk (9.2 GB of 16). This build's own folder only.
    tag = build_dir(step, dev, K, Kd)
    if tag is not None:
        for r in tag.glob("calib*/it[0-9][0-9]/run.raw"):
            r.unlink(missing_ok=True)
    return " ".join(argv[1:])


# Step 1's picks were scattered (ex2 family 2...7 against a netlist 3, inverter chains 6...9
# against 7), so step 2 sweeps one range per family that covers every pick and the netlist count,
# rather than pick +- 1 per buffer. io_buf: pull-up 1 (picked and netlist), pull-down 2...5.
FAMILY_RANGE = {"ex2": range(2, 8), "inv7": range(5, 11), "inv_stage4": range(2, 7)}


def step2_jobs():
    jobs = []
    for dev, b in BUFFERS.items():
        if dev == "io_buf":
            jobs += [(dev, 1, kd) for kd in range(2, 6)]
        elif dev == "inv_stage4":
            jobs += [(dev, k, None) for k in FAMILY_RANGE["inv_stage4"]]
        elif dev.startswith("inv"):
            jobs += [(dev, k, None) for k in FAMILY_RANGE["inv7"]]
        else:
            jobs += [(dev, k, None) for k in FAMILY_RANGE["ex2"]]
    # the netlist-count build first on every buffer, so a partial run already has the reference;
    # then round-robin over buffers, so one buffer's builds rarely run at the same time
    jobs.sort(key=lambda j: (j[1] != BUFFERS[j[0]]["k_net"][0] or (j[2] is not None and j[2] != BUFFERS[j[0]]["k_net"][1]), j[0]))
    first, rest = [j for j in jobs if j[1] == BUFFERS[j[0]]["k_net"][0] and j[0] != "io_buf"], \
                  [j for j in jobs if not (j[1] == BUFFERS[j[0]]["k_net"][0] and j[0] != "io_buf")]
    by_dev = {}
    for j in rest:
        by_dev.setdefault(j[0], []).append(j)
    spread = []
    while any(by_dev.values()):
        for dev in list(by_dev):
            if by_dev[dev]:
                spread.append(by_dev[dev].pop(0))
    return first + spread


def prepare_models(step: str) -> None:
    """Step 3: generate each buffer's shipped model from its IBIS file (declared C_comp) and run
    its full swing and the five stressed widths once, serially, so parallel builds of one buffer
    never race to create the same folders."""
    models = PASSES[step]["models"]
    if models is None:
        return
    gp, _gch, _ = _modules()
    from pybis2spice import pybis2spice as pb, subcircuit
    for dev in BUFFERS:
        gp.VARIANT_NAME = dev
        sup, ibis = gp.VARIANTS[dev]
        sub = models / dev / "shipped" / "driver.sub"
        if not sub.exists():
            sub.parent.mkdir(parents=True, exist_ok=True)
            model, comp = gp.ibis_names(ibis)
            data = pb.DataModel(pb.get_ibis_model_ecdtools(str(ibis)), model_name=model, component_name=comp)
            subcircuit.generate_spice_model("Output", gp.BUILD, data, "Typical", str(sub))
        text = sub.read_text(encoding="utf-8")
        gp.run_ours(sub.parent / "full", text, sup, 10.0)
        for depth, w, _d in gp.cases(dev):
            gp.run_ours(sub.parent / f"d{depth}", text, sup, w)
        print(f"  {dev}: shipped model and its reference runs ready", flush=True)


def step2(workers: int, step: str = "step2") -> None:
    prepare_models(step)
    jobs = step2_jobs()
    done = [j for j in jobs if (build_dir(step, *j) or Path("_none")).joinpath("sweep.csv").exists()]
    jobs = [j for j in jobs if j not in done]
    if done:
        print(f"  {len(done)} builds already complete, skipped", flush=True)
    print(f"{step} ({PASSES[step]['pass_']}): {len(jobs)} builds on {workers} workers", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(build_job, *j, step): j for j in jobs}
        for f in as_completed(futs):
            j = futs[f]
            try:
                print(f"  done {j}: {f.result()}", flush=True)
            except Exception as exc:
                print(f"  FAILED {j}: {exc!r}", flush=True)
    summarise2(step)


def step4(workers: int) -> None:
    """Both halves of the split at the netlist K, in one pool, alternating passes. io_buf is not
    built: its C_comp is the declared one in every pass, so 4a is its step-2 build and 4b its
    step-3 build."""
    prepare_models("step4a")
    jobs = []
    for dev, b in BUFFERS.items():
        if dev != "io_buf":
            jobs += [(dev, b["k_net"][0], None, "step4a"), (dev, b["k_net"][0], None, "step4b")]
    todo = [j for j in jobs if not (build_dir(j[3], *j[:3]) or Path("_none")).joinpath("sweep.csv").exists()]
    if len(todo) < len(jobs):
        print(f"  {len(jobs) - len(todo)} builds already complete, skipped", flush=True)
    print(f"step 4: {len(todo)} builds on {workers} workers", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(build_job, *j): j for j in todo}
        for f in as_completed(futs):
            j = futs[f]
            try:
                print(f"  done {j}: {f.result()}", flush=True)
            except Exception as exc:
                print(f"  FAILED {j}: {exc!r}", flush=True)
    summarise4()


def step5(workers: int) -> None:
    """The file-only pass again, with C_comp from the file's Ku overshoot. A buffer whose
    estimate equals its declared C_comp needs no build: that is its step-3 build."""
    jobs = []
    for dev, b in BUFFERS.items():
        e, declared = est_cc(dev), declared_cc(dev)
        if abs(e - declared) <= 0.01 * declared:      # the estimate is the declared value
            print(f"  {dev}: estimate {e} pF = declared, its step-3 build stands", flush=True)
            continue
        jobs.append((dev, b["k_net"][0], None, "step5"))
    todo = [j for j in jobs if not (build_dir(j[3], *j[:3]) or Path("_none")).joinpath("sweep.csv").exists()]
    if len(todo) < len(jobs):
        print(f"  {len(jobs) - len(todo)} builds already complete, skipped", flush=True)
    print(f"step 5: {len(todo)} builds on {workers} workers "
          f"(C_comp: " + ", ".join(f"{d} {est_cc(d):g}" for d, *_ in jobs) + ")", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(build_job, *j): j for j in todo}
        for f in as_completed(futs):
            j = futs[f]
            try:
                print(f"  done {j}: {f.result()}", flush=True)
            except Exception as exc:
                print(f"  FAILED {j}: {exc!r}", flush=True)
    summarise4()


BAND_TOL = 1.25          # a K belongs to the fit's plateau if its rms is within this of the best
BAND_N = 3               # how many of the plateau's smallest K to build


def plateau_band(dev: str, chain: str = "pull-up") -> list[int]:
    """The BAND_N smallest stage counts whose Ku-domain fit rms is within BAND_TOL of the best.

    Read off the file's own fit (step 1 at the knee C_comp), so nothing here knows the netlist
    count. Smallest-first matches the existing pick_K philosophy: the cheapest chain that
    explains the curve."""
    for r in csv.DictReader((OUT / "step1_summary.csv").open()):
        if r["pass_"] == "est_knee" and r["buffer"] == dev and r["chain"] == chain and r["rms_by_K"]:
            c = [float(x) for x in r["rms_by_K"].split()]
            best = min(c)
            return [i + 1 for i, v in enumerate(c) if v <= BAND_TOL * best][:BAND_N]
    raise KeyError(f"no est_knee fit for {dev} {chain}")


def step6(workers: int, band: str = "plateau") -> None:
    """The whole recipe from the file: C_comp from the overshoot knee, K = 1...10 fitted to THAT
    model's full-swing Ku(t), a band of K built, and the K whose pad timing matches the one
    stressed run kept. The netlist count is used for nothing but the final comparison.

    band="plateau" (default) the three smallest K whose fit rms is within BAND_TOL of the best -
                   file-only, and it contains the netlist count on all 12 buffers
    band="fit"     the plateau pick +- 1: too narrow, and biased high (the ex2 family's pick is
                   4-6 against a netlist 3, so the selector never sees a low K)
    band="family"  the per-family range steps 2 and 3 swept - NOT file-only, those ranges were
                   drawn to cover the netlist counts; kept only for comparison"""
    fits = [("est_knee", dev, "pull-up") for dev in BUFFERS]
    fits += [("est_knee", dev, "pull-down") for dev, b in BUFFERS.items() if b["k_net"][1] is not None]
    ccs = ", ".join(f"{d} {est_cc(d, 'knee'):g}" for d in BUFFERS)
    print(f"step 6, part 1: {len(fits)} fits of K = {KS[0]}...{KS[-1]} at the knee C_comp ({ccs})", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fit_job, *j): j for j in fits}
        for f in as_completed(futs):
            j = futs[f]
            try:
                f.result()
                print(f"  fitted {j[1]} {j[2]}", flush=True)
            except Exception as exc:
                print(f"  FAILED {j}: {exc!r}", flush=True)
    summarise()
    picks = {(r["buffer"], r["chain"]): int(r["picked_K"]) for r in csv.DictReader((OUT / "step1_summary.csv").open())
             if r["pass_"] == "est_knee" and r["picked_K"]}
    jobs = []
    for dev, b in BUFFERS.items():
        pu = picks.get((dev, "pull-up"))
        if pu is None:
            print(f"  {dev}: no complete fit, skipped", flush=True)
            continue
        kd = picks.get((dev, "pull-down")) if b["k_net"][1] is not None else None
        if band == "plateau":
            ks = plateau_band(dev, "pull-up")
            if kd is not None:
                kd = plateau_band(dev, "pull-down")[0]      # the smallest K the fit allows
        elif band == "family" and dev != "io_buf":
            rng = FAMILY_RANGE["inv_stage4" if dev == "inv_stage4" else ("inv7" if dev.startswith("inv") else "ex2")]
            ks = list(rng)
        else:
            ks = [k for k in (pu - 1, pu, pu + 1) if k >= 1]
        jobs += [(dev, k, kd, "step6") for k in ks]
        print(f"  {dev}: file picks K = {pu}" + (f", Kd = {kd}" if kd else "") + f"; building {ks}", flush=True)
    todo = [j for j in jobs if not (build_dir(j[3], *j[:3]) or Path("_none")).joinpath("sweep.csv").exists()]
    print(f"step 6, part 2: {len(todo)} builds on {workers} workers", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(build_job, *j): j for j in todo}
        for f in as_completed(futs):
            j = futs[f]
            try:
                print(f"  done {j}: {f.result()}", flush=True)
            except Exception as exc:
                print(f"  FAILED {j}: {exc!r}", flush=True)
    summarise6()


def summarise6() -> None:
    """Keep, per buffer, the built K whose pad timing at the calibration width is closest to the
    stressed run - the selector step 2 validated - and report what that model scores."""
    summarise2("step6")
    rows = list(csv.DictReader((OUT / "step6_summary.csv").open()))
    out = []
    for dev in BUFFERS:
        rr = [r for r in rows if r["buffer"] == dev]
        if not rr:
            continue
        sel = min(rr, key=lambda r: abs(float(r["lag_ps"].split(" / ")[-1])))
        net = [r for r in rr if int(r["K"]) == BUFFERS[dev]["k_net"][0]]
        out.append(dict(buffer=dev, c_comp_pF=est_cc(dev, "knee"), K_built=" ".join(r["K"] for r in rr),
                        K_selected=sel["K"], K_netlist=BUFFERS[dev]["k_net"][0],
                        worst_peak_pct=sel["worst_abs_pct"], peaks_pct=sel["peak_err_pct"],
                        lag_calib_ps=sel["lag_ps"].split(" / ")[-1], full_pad_rms_mV=sel["full_pad_rms_mV"],
                        worst_peak_at_netlist_K=net[0]["worst_abs_pct"] if net else ""))
    with (OUT / "step6_endtoend.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print("\n  file in, model out: C_comp from the file, K from the file + one stressed pad run")
    print(f"  {'buffer':13s} {'C_comp':>7s} {'K sel':>6s} {'K net':>6s} {'worst peak':>11s} {'at K net':>9s} {'lag ps':>7s}")
    for o in out:
        print(f"  {o['buffer']:13s} {o['c_comp_pF']:7.2f} {o['K_selected']:>6s} {o['K_netlist']:>6d} "
              f"{o['worst_peak_pct']:>10s} % {o['worst_peak_at_netlist_K']:>8s} {o['lag_calib_ps']:>7s}")
    ok = sum(1 for o in out if float(o["worst_peak_pct"]) <= 10)
    same = sum(1 for o in out if int(o["K_selected"]) == o["K_netlist"])
    print(f"  within 10 %: {ok} of {len(out)}   K equals the netlist count: {same} of {len(out)}")
    print(f"  wrote {OUT / 'step6_endtoend.csv'}")


def summarise4() -> None:
    """Worst stressed peak error, timing at the calibration width and full-swing rms of the
    four passes at the netlist K - which of the two inputs costs step 3 its accuracy."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    have5 = (OUT / "step5").exists()
    for s in ("step4a", "step4b") + (("step5",) if have5 else ()):
        summarise2(s)
    rows = {}
    for s in ("step2", "step3", "step4a", "step4b", "step5"):
        p = OUT / f"{s}_summary.csv"
        if not p.exists():
            continue
        for r in csv.DictReader(p.open()):
            b = BUFFERS[r["buffer"]]
            if int(r["K"]) != b["k_net"][0] or (r["Kd"] and int(r["Kd"]) != b["k_net"][1]):
                continue
            rows[(r["buffer"], s)] = r
    # passes that need no build of their own: io_buf's C_comp is the declared one in every pass,
    # and a buffer whose estimate came out equal to its declared C_comp has step 3's build
    declared = {r["buffer"]: float(r["declared_pF"]) for r in csv.DictReader(EST_CC_CSV.open())}
    for dev in BUFFERS:
        if dev == "io_buf":
            for s, same in (("step4a", "step2"), ("step4b", "step3")):
                if (dev, same) in rows:
                    rows[(dev, s)] = rows[(dev, same)]
        if (dev, "step5") not in rows and (dev, "step3") in rows                 and abs(est_cc(dev) - declared[dev]) <= 0.01 * declared[dev]:
            rows[(dev, "step5")] = rows[(dev, "step3")]
    order = [("step2", "measured C_comp, family shape (track-1 settings)"),
             ("step4a", "declared C_comp, family shape"),
             ("step4b", "measured C_comp, universal shape"),
             ("step3", "declared C_comp, universal shape (file only)")]
    if have5:
        order.insert(3, ("step5", "estimated C_comp, universal shape (file only)"))
    out = []
    for dev in BUFFERS:
        o = dict(buffer=dev, netlist_K=BUFFERS[dev]["k_net"][0])
        for s, _ in order:
            r = rows.get((dev, s))
            o[f"{s}_worst_peak_pct"] = r["worst_abs_pct"] if r else ""
            o[f"{s}_peaks_pct"] = r["peak_err_pct"] if r else ""
            o[f"{s}_lag_calib_ps"] = r["lag_ps"].split(" / ")[-1] if r else ""
            o[f"{s}_full_pad_rms_mV"] = r["full_pad_rms_mV"] if r else ""
        out.append(o)
    with (OUT / "step4_split.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print("\n  worst stressed peak error at the netlist K (%)")
    print(f"  {'buffer':13s}" + "".join(f"{s:>9s}" for s, _ in order))
    for o in out:
        print(f"  {o['buffer']:13s}" + "".join(f"{o[s + '_worst_peak_pct']:>9s}" for s, _ in order))
    within = {s: sum(1 for o in out if o[f"{s}_worst_peak_pct"] and float(o[f"{s}_worst_peak_pct"]) <= 10) for s, _ in order}
    have = {s: sum(1 for o in out if o[f"{s}_worst_peak_pct"]) for s, _ in order}
    print(f"  {'within 10 %':13s}" + "".join(f"{str(within[s]) + '/' + str(have[s]):>9s}" for s, _ in order))
    # figure: worst peak per buffer, the four passes side by side
    import numpy as np
    fig, ax = plt.subplots(figsize=(12.5, 4.8))
    devs = [o["buffer"] for o in out]
    colours = ("#2E86C1", "#E67E22", "#8E44AD", "#C0392B")
    for i, ((s, label), c) in enumerate(zip(order, colours)):
        y = [float(o[f"{s}_worst_peak_pct"]) if o[f"{s}_worst_peak_pct"] else np.nan for o in out]
        ax.bar(np.arange(len(devs)) + (i - 1.5) * 0.2, y, 0.2, color=c, label=label)
    ax.axhline(10, color="#555555", ls="--", lw=1.1)
    ax.set_xticks(np.arange(len(devs)), devs, rotation=30, ha="right")
    ax.set_ylabel("worst stressed peak error (%)")
    ax.set_title("Which non-file input costs track 1 its accuracy? (netlist K, pad-calibrated)", fontweight="bold")
    ax.set_ylim(0, 22)
    ax.legend(fontsize=9, loc="upper right")    # the right-hand buffers stay below 13 %
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "step4_split.png", dpi=170)
    plt.close(fig)
    print(f"  wrote step4_split.csv, step4_split.png")


def summarise2(step: str = "step2") -> None:
    """Collect every build's scores, with the step-1 pick (same pass) and the netlist count."""
    picks = {(r["buffer"], r["chain"]): r["picked_K"] for r in csv.DictReader((OUT / "step1_summary.csv").open())
             if r["pass_"] == PASSES[step]["pass_"]}
    out = []
    for p in sorted((OUT / step).glob("*/*/sweep.csv")):
        rows = list(csv.DictReader(p.open(encoding="utf-8")))
        import re
        dev = re.sub(r"_c[0-9.]+$", "", p.parent.parent.name)     # strip the C_comp suffix, not "_chain"
        ship, build = rows[0], rows[-1]
        pk = [float(v) for k_, v in build.items() if k_.startswith("pk_d")]
        lag = [float(v) for k_, v in build.items() if k_.startswith("lag_d")]
        label = p.parent.name
        kd = label.split("_Kd")[1].split("_")[0] if "_Kd" in label else ""
        out.append(dict(buffer=dev, K=build["K"], Kd=kd, netlist_K=BUFFERS[dev]["k_net"][0],
                        picked_K=picks.get((dev, "pull-up"), ""),
                        peak_err_pct=" / ".join(f"{x:+.1f}" for x in pk),
                        worst_abs_pct=f"{max(abs(x) for x in pk):.1f}",
                        lag_ps=" / ".join(f"{x:.0f}" for x in lag),
                        full_pad_rms_mV=build["full_pad_rms_mV"],
                        shipped_peak_err_pct=" / ".join(f"{float(v):+.1f}" for k_, v in ship.items() if k_.startswith("pk_d")),
                        widths=" / ".join(k_[4:] for k_ in build if k_.startswith("pk_d")), build=label))
    if not out:
        print(f"no {step} results yet")
        return
    out.sort(key=lambda o: (list(BUFFERS).index(o["buffer"]), int(o["K"]), o["Kd"]))
    with (OUT / f"{step}_summary.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    for o in out:
        tag = ("netlist" if int(o["K"]) == o["netlist_K"] else "") + (" picked" if o["K"] == o["picked_K"] else "")
        print(f"  {o['buffer']:13s} K {o['K']:>2s}{'/' + o['Kd'] if o['Kd'] else '':3s} {tag:15s} peak {o['peak_err_pct']}   "
              f"worst {o['worst_abs_pct']:>5s} %   lag {o['lag_ps']}   full {o['full_pad_rms_mV']} mV")
    print(f"  wrote {OUT / (step + '_summary.csv')}")
    if step in ("step2", "step3"):              # step 4 builds one K per buffer: nothing to select
        selectors(step)


def selectors(step: str = "step2") -> None:
    """Which K would each score select, per buffer? Three candidate selectors, all computed on
    the pad-calibrated builds:
      lag     |timing error| at the calibration width - the same stressed pad run the threshold
              was placed with (file + one pad run)
      full    full-swing pad rms against the SHIPPED model's full swing (which reproduces the
              IBIS tables - file only)
      peak    worst stressed peak error (what calibration optimises)"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import spicelab as sl
    _gp, gch, _ = _modules()
    rows = list(csv.DictReader((OUT / f"{step}_summary.csv").open()))
    models = PASSES[step]["models"] or gch.G
    grid = np.arange(4.5, 20.0, 0.005)
    out = []
    for r in rows:
        dev = r["buffer"]
        b = BUFFERS[dev]
        dcc = dcc_name(step, dev)
        ship = sl.parse_ngspice_raw(models / dcc / "shipped" / "full" / "run.raw")
        ch = sl.parse_ngspice_raw(OUT / step / dcc / r["build"] / "full" / "run.raw")
        ps = np.interp(grid, sl.time_ns(ship), sl.trace(ship, "out"))
        pc = np.interp(grid, sl.time_ns(ch), sl.trace(ch, "out"))
        out.append(dict(buffer=dev, K=int(r["K"]), Kd=r["Kd"], netlist_K=b["k_net"][0],
                        full_vs_shipped_mV=1000 * float(np.sqrt(np.mean((pc - ps) ** 2))),
                        lag_calib_ps=float(r["lag_ps"].split(" / ")[-1]),
                        worst_peak_pct=float(r["worst_abs_pct"]), full_vs_transistor_mV=float(r["full_pad_rms_mV"])))
    with (OUT / f"{step}_selectors.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows([{k: (f"{v:.1f}" if isinstance(v, float) else v) for k, v in o.items()} for o in out])
    picks = []
    for dev in BUFFERS:
        rr = [o for o in out if o["buffer"] == dev]
        if dev == "io_buf" or not rr:
            continue
        picks.append((dev, rr[0]["netlist_K"], min(rr, key=lambda o: abs(o["lag_calib_ps"]))["K"],
                      min(rr, key=lambda o: o["full_vs_shipped_mV"])["K"], min(rr, key=lambda o: o["worst_peak_pct"])["K"]))
    with (OUT / f"{step}_picks.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["buffer", "netlist_K", "pick_by_lag_at_calib_width", "pick_by_fullswing_vs_shipped", "pick_by_worst_peak"])
        w.writerows(picks)
    for p in picks:
        print(f"  {p[0]:13s} netlist {p[1]}   by lag {p[2]}   by full swing {p[3]}   by peak {p[4]}")
    # figure: each score against K - netlist K, so every buffer's true count sits at 0
    cmap = plt.get_cmap("tab20")
    devs = [d for d in BUFFERS if d != "io_buf"]
    fig, axes = plt.subplots(1, 3, figsize=(12.2, 4.6))
    for i, dev in enumerate(devs):
        rr = sorted((o for o in out if o["buffer"] == dev), key=lambda o: o["K"])
        x = [o["K"] - o["netlist_K"] for o in rr]
        kw = dict(color=cmap(i), lw=1.6, marker="o", ms=4, label=dev)
        axes[0].plot(x, [o["worst_peak_pct"] for o in rr], **kw)
        axes[1].plot(x, [o["lag_calib_ps"] for o in rr], **kw)
        axes[2].plot(x, [o["full_vs_shipped_mV"] for o in rr], **kw)
    heads = ("worst stressed peak error (%)\n(what the calibration matches)",
             "timing error at the calibration width (ps)\n(the same one pad run)",
             "full-swing pad rms vs shipped (mV)\n(file only)")
    for ax, h in zip(axes, heads):
        ax.axvline(0, color="#555555", ls="--", lw=1.2)
        ax.set_xlabel("K - netlist stage count")
        ax.set_title(h, fontweight="bold", fontsize=11.5)
        ax.grid(alpha=0.3)
    axes[1].axhline(0, color="#555555", lw=0.8)
    axes[1].set_ylim(-320, 320)
    axes[2].set_yscale("log")
    axes[0].legend(fontsize=8, ncol=2, loc="upper left")
    what = {"step2": "track-1 settings", "step3": "strictly file-only (declared C_comp, universal curve)"}[step]
    fig.suptitle(f"track 1, pad-calibrated, per K  |  {what}", fontweight="bold", fontsize=12.5)
    fig.tight_layout()
    fig.savefig(OUT / f"{step}_scores_vs_K.png", dpi=170)
    plt.close(fig)
    print(f"  wrote {step}_selectors.csv, {step}_picks.csv, {step}_scores_vs_K.png")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=int, choices=(1, 2, 3, 4, 5, 6), required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--summarise", action="store_true")
    ap.add_argument("--band", choices=("plateau", "fit", "family"), default="plateau",
                    help="step 6: which K to build - the fit's plateau pick +-1, or the family range")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.step == 1:
        summarise() if args.summarise else step1(args.workers)
    elif args.step == 4:
        summarise4() if args.summarise else step4(args.workers)
    elif args.step == 5:
        summarise4() if args.summarise else step5(args.workers)
    elif args.step == 6:
        summarise6() if args.summarise else step6(args.workers, args.band)
    else:
        step = f"step{args.step}"
        summarise2(step) if args.summarise else step2(args.workers, step)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
