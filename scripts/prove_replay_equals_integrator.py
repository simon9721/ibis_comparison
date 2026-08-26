#!/usr/bin/env python3
"""One circuit, two gates: integrated and replayed, driving identical pads.

The question is small -- does replaying a fitted exponential from an inverted
entry time give the same value as integrating it? -- and it does not need the
production model to answer. Seven attempts to add this as another mode inside
`create_ngspice_two_state_gate_input_control_netlist` (820 lines, 53 branches,
14 interacting flags) each failed on a coupling rather than on the physics.

So this builds the comparison standalone. Both gates live in one netlist, share
one command, one transfer map and two identical pad stages, and are probed in a
single run. Nothing here touches the production builder, so nothing in it can
collide with those flags.

  gate A   integrated by ngspice:  dG/dt = (target - G) / tau
  gate B   replayed:               invert to a table time at each edge, then
                                   advance along the fitted curve

Gate B is computed in Python and played back as a PWL source. That is the
honest division of labour: the replay *algorithm* runs where it can be checked,
and ngspice does the integration and the circuit. The pad stage is lifted
verbatim from the generated io_buf model, so both branches see the real I-V
tables, clamps and C_comp.

    py -3.14 scripts/prove_replay_equals_integrator.py
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
for q in (ROOT / ".codex_deps" / "presentation" / "python", ROOT, ROOT / "scripts",
          ROOT / "tools" / "pybis2spice"):
    sys.path.insert(0, str(q))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from eye_diagram import parse_ngspice_raw  # noqa: E402
from pybis2spice import pybis2spice as pb, subcircuit as sc  # noqa: E402
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
from spice_tool_paths import default_ngspice  # noqa: E402

DEVICE = "io_buf"
GENERATED = (ROOT / "results" / "stress_method_matrix_2026-08-20" / "gate_state" /
             "generated_models" / DEVICE / "driver_OutputInput_Typical.sub")
OUT = ROOT / "results" / "replay_vs_integrator_2026-08-26"

EDGE_NS = 5.0        # command asserted
WIDTH_NS = 2.2259    # reversed here, with the pullup gate about two thirds up
STOP_NS = 14.0

INTEG = "#1F6FB2"
REPLAY = "#C02626"
DPI = 180


def pad_stage_lines():
    """The pullup, pulldown, clamp and C_comp lines from the generated model.

    Taken verbatim rather than rebuilt so both branches are driven through the
    same I-V tables the real model uses; only node names are rewritten.
    """
    wanted = re.compile(r"^(R1|L1|C1|C2|V[1-4]|B[1-4]) ")
    lines = [l.rstrip("\n") for l in GENERATED.read_text(encoding="utf-8").splitlines()
             if wanted.match(l)]
    if len(lines) != 12:
        raise SystemExit(f"expected 12 pad-stage lines, found {len(lines)}")
    return lines


def branch(lines, tag):
    """One pad stage, with every node suffixed so the two cannot interact."""
    out = []
    for line in lines:
        for node in ("OUT", "MID", "DIE", "PWR_CLAMP_REF", "GND_CLAMP_REF",
                     "PULLUP_REF", "PULLDOWN_REF"):
            line = re.sub(rf"\b{node}\b", f"{node}{tag}", line)
        line = re.sub(r"\bV\(Ku\)", f"V(KU{tag})", line)
        line = re.sub(r"\bV\(Kd\)", f"V(KD{tag})", line)
        line = re.sub(r"^([A-Z]+[0-9]+) ", rf"\1{tag} ", line)
        out.append(line)
    return out


def replay_gate(times_ns, first_ns, first_tau, second_ns, second_tau, start_value):
    """Gate value by inverting at each edge and advancing along the fitted curve.

    The onset delay is already in `first_ns` and `second_ns`, because the command
    carries it -- so the trajectory measured from those instants is a plain
    exponential and must not subtract the delay a second time. Doing so was the
    first thing this test caught: it shifted the replay a full pu_on_delay late
    and opened a 0.586 gap that had nothing to do with the method.
    """
    def forward(elapsed, tau, lo, hi):
        return lo + (hi - lo) * (1.0 - np.exp(-np.maximum(0.0, elapsed) / tau))

    def invert(value, tau, lo, hi):
        progress = np.clip((value - lo) / (hi - lo), 1e-12, 1.0 - 1e-12)
        return tau * (-np.log(1.0 - progress))

    end_first = 1.0 - start_value
    gate = np.full_like(times_ns, start_value)
    # First edge: the state sits on its rail, so the entry is the start of the
    # trajectory and the replay is the curve itself.
    seg = times_ns >= first_ns
    gate[seg] = forward(times_ns[seg] - first_ns, first_tau, start_value, end_first)
    # Reversal: invert wherever it had reached, then advance from there.
    held = forward(second_ns - first_ns, first_tau, start_value, end_first)
    entry = invert(held, second_tau, end_first, start_value)
    seg = times_ns >= second_ns
    gate[seg] = forward(entry + (times_ns[seg] - second_ns), second_tau,
                        end_first, start_value)
    return np.clip(gate, 0.0, 1.0)


def pwl_source(name, node, times_ns, values):
    points = " ".join(f"{t:.6f}n {v:.9g}" for t, v in zip(times_ns, values))
    return f"{name} {node} 0 PWL({points})\n"


def step_source(name, node, start, edges):
    """A PWL that steps between levels at the given (time_ns, level) points."""
    pts = [(0.0, start)]
    for t, level in edges:
        pts.append((t - 1e-4, pts[-1][1]))
        pts.append((t, level))
    pts.append((STOP_NS, pts[-1][1]))
    body = " ".join(f"{t:.6f}n {v:.9g}" for t, v in pts)
    return f"{name} {node} 0 PWL({body})\n"


def build_netlist(fit, pad_lines, grid):
    t_rev = EDGE_NS + WIDTH_NS
    # Targets carry the fitted onset delay for their own direction, which is what
    # the production command layer produces; putting it here keeps the test on
    # the question and out of the edge-detect machinery.
    gup_edges = [(EDGE_NS + fit["pu_on_delay"], 1.0), (t_rev + fit["pu_off_delay"], 0.0)]
    gdn_edges = [(EDGE_NS + fit["pd_off_delay"], 0.0), (t_rev + fit["pd_on_delay"], 1.0)]

    gup_b = replay_gate(grid, EDGE_NS + fit["pu_on_delay"], fit["pu_on_tau"],
                        t_rev + fit["pu_off_delay"], fit["pu_off_tau"], start_value=0.0)
    gdn_b = replay_gate(grid, EDGE_NS + fit["pd_off_delay"], fit["pd_off_tau"],
                        t_rev + fit["pd_on_delay"], fit["pd_on_tau"], start_value=1.0)

    ku_on = sc.convert_iv_table_to_str(fit["ku_on_map_x"], fit["ku_on_map_y"])
    ku_off = sc.convert_iv_table_to_str(fit["ku_off_map_x"], fit["ku_off_map_y"])
    kd_on = sc.convert_iv_table_to_str(fit["kd_on_map_x"], fit["kd_on_map_y"])
    kd_off = sc.convert_iv_table_to_str(fit["kd_off_map_x"], fit["kd_off_map_y"])

    st = "* Replay against integrator: same command, same map, same pad.\n"
    st += ".param C_pkg=0 L_pkg=0 R_pkg=0 C_comp=1.2e-12\n"
    st += "VVCC VCC 0 3.3\nVVSS VSS 0 0\n"
    st += step_source("VGUPT", "GUPTARGET", 0.0, gup_edges)
    st += step_source("VGDNT", "GDNTARGET", 1.0, gdn_edges)

    # Gate A: ngspice integrates the same ODE the production model does.
    st += (f"BGUPA GUPA 0 I = -1p * (V(GUPTARGET) - V(GUPA)) / "
           f"((V(GUPTARGET) > V(GUPA)) ? {fit['pu_on_tau']:.9g}n : {fit['pu_off_tau']:.9g}n)\n")
    st += "CGUPA GUPA 0 1p ic=0\nRGUPA GUPA 0 1e12\n"
    st += (f"BGDNA GDNA 0 I = -1p * (V(GDNTARGET) - V(GDNA)) / "
           f"((V(GDNTARGET) > V(GDNA)) ? {fit['pd_on_tau']:.9g}n : {fit['pd_off_tau']:.9g}n)\n")
    st += "CGDNA GDNA 0 1p ic=1\nBGDNABASE GDNABASE 0 V = 1.0\nRGDNA GDNA GDNABASE 1e12\n"

    # Gate B: the replay, computed in Python and played back.
    st += pwl_source("VGUPB", "GUPB", grid, gup_b)
    st += pwl_source("VGDNB", "GDNB", grid, gdn_b)

    for tag in ("A", "B"):
        st += (f"BKUON{tag} KUON{tag} 0 V = pwl(min(max(V(GUP{tag}), 0), 1), {ku_on})\n")
        st += (f"BKUOFF{tag} KUOFF{tag} 0 V = pwl(min(max(V(GUP{tag}), 0), 1), {ku_off})\n")
        st += (f"BKU{tag} KU{tag} 0 V = (V(GUPTARGET) >= V(GUP{tag})) ? "
               f"V(KUON{tag}) : V(KUOFF{tag})\n")
        st += (f"BKDON{tag} KDON{tag} 0 V = pwl(min(max(V(GDN{tag}), 0), 1), {kd_on})\n")
        st += (f"BKDOFF{tag} KDOFF{tag} 0 V = pwl(min(max(V(GDN{tag}), 0), 1), {kd_off})\n")
        st += (f"BKD{tag} KD{tag} 0 V = (V(GDNTARGET) >= V(GDN{tag})) ? "
               f"V(KDON{tag}) : V(KDOFF{tag})\n")
        st += "\n".join(branch(pad_lines, tag)) + "\n"
        st += f"RLOAD{tag} OUT{tag} VSS 50\nCLOAD{tag} OUT{tag} VSS 2p\n"

    st += f".tran 1p {STOP_NS}n uic\n"
    st += ".control\nrun\nset filetype=ascii\nwrite run.raw\nquit\n.endc\n.end\n"
    return st, t_rev


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--ngspice", type=Path, default=default_ngspice(console=True))
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    device = next(d for d in base.DEVICES if d.device_id == DEVICE)
    data = pb.DataModel(pb.get_ibis_model_ecdtools(str(device.fast_ibis)),
                        model_name=device.model, component_name=device.component)
    kr = pb.solve_k_params_output(data, corner=1, waveform_type="Rising")
    kf = pb.solve_k_params_output(data, corner=1, waveform_type="Falling")
    # The directional maps live in the directional fit, not the base one;
    # the production builder calls this when use_directional_map is set.
    fit = sc.two_state_directional_gate_fit(kr, kf)

    grid = np.arange(0.0, STOP_NS + 1e-9, 0.002)
    netlist, t_rev = build_netlist(fit, pad_stage_lines(), grid)
    deck = out / "replay_vs_integrator.cir"
    deck.write_text(netlist, encoding="utf-8")

    # Same check that would have caught the floating-node failures earlier.
    defined = set(re.findall(r"^[A-Z]+[A-Za-z0-9_]* ([A-Z][A-Za-z0-9_]*) ", netlist, re.M))
    used = set(re.findall(r"V\(([A-Z][A-Za-z0-9_]*)[,)]", netlist))
    missing = sorted(used - defined - {"VCC", "VSS"})
    if missing:
        print("undefined nodes:", missing)
        return 1

    run = subprocess.run([str(args.ngspice), "-b", deck.name], cwd=out,
                         capture_output=True, text=True, timeout=600)
    raw = out / "run.raw"
    if not raw.exists():
        print(run.stdout[-2000:] or run.stderr[-2000:])
        return 1

    r = parse_ngspice_raw(raw)
    k = {x.lower(): x for x in r}
    t = np.asarray(r[k["time"]]) * 1e9
    get = lambda n: np.asarray(r[k[f"v({n})"]])
    pairs = (("gate GUP", "gupa", "gupb"), ("gate GDN", "gdna", "gdnb"),
             ("Ku", "kua", "kub"), ("Kd", "kda", "kdb"), ("pad", "outa", "outb"))
    window = (t >= 4.0) & (t <= STOP_NS)

    print(f"{DEVICE}, command at {EDGE_NS} ns, reversed at {t_rev:.4f} ns\n")
    print(f"{'quantity':12s} {'worst |A-B|':>13s}   {'A range':>18s}")
    worst = {}
    for label, a, b in pairs:
        d = float(np.max(np.abs(get(a)[window] - get(b)[window])))
        worst[label] = d
        unit = " V" if label == "pad" else ""
        print(f"{label:12s} {d:13.3e}{unit}   "
              f"{get(a)[window].min():8.4f} .. {get(a)[window].max():.4f}")

    fig, axes = plt.subplots(3, 1, figsize=(14.2, 10.5), sharex=True)
    for axis, (label, a, b) in zip(axes, (pairs[0], pairs[2], pairs[4])):
        axis.plot(t, get(a), color=INTEG, lw=5.0, label="integrated  dG/dt = (target - G)/tau")
        axis.plot(t, get(b), color=REPLAY, lw=2.0, ls=(0, (5, 2.4)),
                  label="replayed  invert at the edge, advance along the curve")
        axis.axvline(t_rev, color="#8A8A8A", ls="--", lw=1.8)
        axis.set_ylabel({"gate GUP": "GUP", "Ku": "Ku", "pad": "Pad voltage (V)"}[label],
                        fontsize=14)
        axis.grid(alpha=0.3, color="#C9D3DE", lw=0.8)
        axis.tick_params(labelsize=12)
        for spine in axis.spines.values():
            spine.set_color("#3A4753")
    axes[0].set_title(f"{DEVICE}  |  {WIDTH_NS * 1000:.0f} ps pulse  |  "
                      "gate by integration vs by replay",
                      fontsize=18, fontweight="bold", pad=12)
    axes[0].legend(fontsize=12.5, loc="upper left", framealpha=0.94)
    axes[2].set_xlabel("Time (ns)", fontsize=13)
    axes[0].set_xlim(4.0, min(STOP_NS, t_rev + 4.0))
    fig.tight_layout()
    fig.savefig(out / "18_replay_vs_integrator.png", dpi=DPI)
    plt.close(fig)
    print(f"\nwrote {(out / '18_replay_vs_integrator.png').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
