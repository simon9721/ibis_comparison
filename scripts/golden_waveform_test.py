#!/usr/bin/env python3
"""Golden-waveform test: does pybis reproduce the model's own V-T tables?

The book's prescribed simulator verification (Leventhal & Green 12.9.6, 17.14,
16.5.1): an IBIS model carries [Rising Waveform] / [Falling Waveform] tables
together with the fixture that produced them, so a correct simulator driving that
same fixture must reproduce the table.

This is the decisive C_comp test, and it is decisive precisely because the
fixture is the characterization fixture:

  * pybis extracts Ku/Kd from these tables with the C_comp displacement current
    subtracted out (`solve_k_params_output`: i1 = ... - i_c_comp).
  * Replaying into the *same* fixture, the simulated dV/dt equals the recorded
    dV/dt, so that subtraction and the explicit C_comp put back in the netlist
    should cancel exactly.

So if pybis with its nominal C_comp reproduces the table, its C_comp handling is
self-consistent and the disagreement with native IBIS lives somewhere else. If
instead C_comp = 0 reproduces the table better, C_comp is being applied more than
once. No transistor and no native IBIS are involved, so neither the engine nor
the reference model can confound the answer.

    py -3.14 scripts/golden_waveform_test.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / ".codex_deps" / "presentation" / "python",
           ROOT / "tools" / "pybis2spice"):
    sys.path.insert(0, str(_p))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import spicelab as sl  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit  # noqa: E402

IBIS = (ROOT / "results" / "inv_chain_variants_2026-09-02" / "base8" /
        "selection" / "tr1ps" / "invchain_base8_tr1ps.ibs")
OUT = ROOT / "results" / "golden_waveform_test_2026-09-03"
MODEL, COMPONENT = "driver2", "invchain"
SUPPLY_V = 1.8
C_COMP_NOMINAL = 4.68e-13
SETTLE_NS = 5.0      # hold before the edge so the model starts settled
NGSPICE_STEP_NS = 0.0002


def read_waveforms(path: Path):
    """Every [Rising/Falling Waveform] block: (kind, R_fixture, V_fixture, t_ns, v)."""
    blocks = []
    kind = rfix = vfix = None
    rows: list[tuple[float, float]] = []

    def flush():
        if kind and rows:
            t = np.array([r[0] for r in rows]) * 1e9
            v = np.array([r[1] for r in rows])
            blocks.append((kind, rfix, vfix, t, v))

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if s.startswith("["):
            flush()
            rows = []
            low = s.lower()
            kind = ("rising" if "rising waveform" in low
                    else "falling" if "falling waveform" in low else None)
            rfix = vfix = None
            continue
        if kind is None:
            continue
        if s.lower().startswith("r_fixture"):
            rfix = float(s.split("=")[1])
            continue
        if s.lower().startswith("v_fixture") and "_min" not in s.lower() and "_max" not in s.lower():
            vfix = float(s.split("=")[1])
            continue
        if s.startswith("|") or not s:
            continue
        parts = s.split()
        if len(parts) >= 2:
            try:
                rows.append((float(parts[0].rstrip("nsNS") or 0)
                             * (1e-9 if parts[0].lower().endswith("n") else 1.0),
                             float(parts[1])))
            except ValueError:
                pass
    flush()
    return blocks


def run_pybis(out_dir: Path, rfix: float, vfix: float, kind: str,
              c_comp: float, stop_ns: float):
    """Drive the subcircuit into the characterization fixture and return the pad."""
    out_dir.mkdir(parents=True, exist_ok=True)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(IBIS)),
                        model_name=MODEL, component_name=COMPONENT)
    subcircuit.generate_spice_model("Output", "InputDriven", data, "Typical",
                                    str(out_dir / "driver.sub"))
    m = re.search(r"^\.SUBCKT\s+(\S+)([^\n]*)",
                  (out_dir / "driver.sub").read_text(), re.M | re.I)
    pins = [p for p in m.group(2).split("params:")[0].split() if "=" not in p]
    nd = {"OUT": "OUT", "IN": "IN", "EN": "EN", "VCC": "VCC", "VSS": "0"}
    nodes = [nd.get(p.upper(), p) for p in pins]
    # The InputDriven model initialises with the pulldown on and establishes
    # state only on the first detected EDGE, so a level it was merely held at is
    # not a settled state. A falling table therefore needs a real rising edge
    # first, or the model enters the transition from the wrong initial level and
    # the comparison measures the test, not the model.
    end = SETTLE_NS + stop_ns + 1
    if kind == "rising":
        pwl = (f"PWL(0n 0  {SETTLE_NS}n 0  {SETTLE_NS + 0.001}n {SUPPLY_V:g}  "
               f"{end:g}n {SUPPLY_V:g})")
    else:
        pre = SETTLE_NS / 2.0          # rise here, settle, then fall at SETTLE_NS
        pwl = (f"PWL(0n 0  {pre:g}n 0  {pre + 0.001:g}n {SUPPLY_V:g}  "
               f"{SETTLE_NS}n {SUPPLY_V:g}  {SETTLE_NS + 0.001}n 0  {end:g}n 0)")
    deck = f"""* golden-waveform replay, {kind}, R={rfix} V={vfix}, C_comp={c_comp:.3e}
.options reltol=1e-5 abstol=1e-10 vntol=1e-7 trtol=1
.include driver.sub
Vdd VCC 0 DC {SUPPLY_V}
Vin IN 0 {pwl}
Ven EN 0 DC {SUPPLY_V}
X1 {' '.join(nodes)} {m.group(1)} C_comp={c_comp:.6e}
Vfix FIX 0 DC {vfix}
Rfix OUT FIX {rfix}
.tran {NGSPICE_STEP_NS}n {SETTLE_NS + stop_ns + 1:g}n
.save V(OUT)
.end
"""
    (out_dir / "run.sp").write_text(deck, encoding="utf-8")
    raw = sl.ngspice(out_dir)
    if raw is None:
        return None
    r = sl.parse_ngspice_raw(raw)
    return sl.time_ns(r), sl.trace(r, "out")


def fom_percent(golden_v, sim_v, dx):
    """IBIS Accuracy Handbook curve-overlay metric, as a percent of full swing."""
    span = max(np.ptp(golden_v), 1e-12)
    return 100.0 * np.sum(np.abs(golden_v - sim_v)) / (len(golden_v) * span)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    blocks = read_waveforms(IBIS)
    print(f"{len(blocks)} waveform tables in {IBIS.name}\n")
    print(f"{'table':<26}{'C_comp':>10}{'FOM %':>9}{'RMSE mV':>10}{'worst mV':>10}{'shift ps':>11}")

    results = []
    for kind, rfix, vfix, t_tab, v_tab in blocks:
        stop_ns = float(t_tab[-1])
        label = f"{kind} R={rfix:g} V={vfix:g}"
        for tag, c_comp in (("nominal", C_COMP_NOMINAL), ("zero", 0.0)):
            d = OUT / f"{kind}_{rfix:g}_{vfix:g}_{tag}"
            got = run_pybis(d, rfix, vfix, kind, c_comp, stop_ns)
            if got is None:
                print(f"{label:<26}{tag:>10}   run failed")
                continue
            t_sim, v_sim = got
            # Align in time FIRST, per the book: the table's t=0 is not the input
            # step -- it starts before the transition, with the buffer's own
            # delay folded in -- so an arbitrary offset separates the two. Sweep
            # the shift for the best FOM, then report the shift and the aligned
            # FOM separately, so timing and shape errors stay distinguishable.
            best = None
            for shift in np.arange(-0.40, 1.20, 0.002):
                cand = np.interp(t_tab + SETTLE_NS + shift, t_sim, v_sim)
                f = fom_percent(v_tab, cand, 1.0)
                if best is None or f < best[0]:
                    best = (f, shift, cand)
            fom, shift, v_on_tab = best
            rmse = float(np.sqrt(np.mean((v_on_tab - v_tab) ** 2))) * 1e3
            worst = float(np.max(np.abs(v_on_tab - v_tab))) * 1e3
            print(f"{label:<26}{tag:>10}{fom:9.2f}{rmse:10.2f}{worst:10.1f}{shift*1e3:11.1f}")
            results.append((label, tag, fom, rmse, worst, t_tab, v_tab, v_on_tab))

    # one figure per table, nominal vs zero against the golden trace
    seen = set()
    for label, tag, *_ in results:
        seen.add(label)
    fig, axes = plt.subplots(len(seen), 1, figsize=(11, 3.1 * len(seen)), squeeze=False)
    for ax, label in zip(axes[:, 0], sorted(seen)):
        for r in results:
            if r[0] != label:
                continue
            _, tag, fom, rmse, worst, t_tab, v_tab, v_sim = r
            if tag == "nominal":
                ax.plot(t_tab, v_tab, color="#111111", lw=3.0, label="golden V-T table")
            colour = "#C02626" if tag == "nominal" else "#1B6B4F"
            ax.plot(t_tab, v_sim, color=colour, lw=1.9, ls=(0, (5, 2.2)),
                    label=f"pybis C_comp {tag} (FOM {fom:.2f}%)")
        ax.set_title(label, fontsize=12, fontweight="bold")
        ax.set_ylabel("Pad (V)", fontsize=10.5)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=9.5)
    axes[-1, 0].set_xlabel("Time (ns)", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "golden_waveform_test.png", dpi=165)
    plt.close(fig)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
