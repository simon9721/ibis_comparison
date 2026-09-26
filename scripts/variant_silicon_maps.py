#!/usr/bin/env python3
"""Track 2 on the nine variants: measured Ku/Kd maps (two full-swing fixture runs of the
variant's transistor plus its last-stage gate node), then the file chain + measured map +
one pad point, scored on the variant's stressed matrix like `gate_chain_prototype.py`.

Per variant this script makes three HSPICE runs from the variant's own full-swing deck
(results/variant_stress_cases_2026-09-04/<v>/full_swing/run.sp, 1 ps input edges like its
stress cases):

    full_swing_fixtures_2026-09-09/<v>/vfix_0     pad through 50 Ohm to 0 V
    full_swing_fixtures_2026-09-09/<v>/vfix_vcc   pad through 50 Ohm to VCC
    predriver_stages_2026-09-09/<v>/full          50 Ohm || 2 pF, gate node probed

and then calls gate_chain_prototype.main() with --maps silicon --calib-pad 50, after
registering the variant's gate node and fixture directory in the modules that need them.

    py -3.14 scripts/variant_silicon_maps.py [--only ex2_base inv_stage4 ...] [--maps-only]
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "tools" / "pybis2spice", ROOT / ".codex_deps" / "presentation" / "python"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import run_three_buffer_realistic_pulse_campaign as base  # noqa: E402
from spice_tool_paths import default_hspice  # noqa: E402
import predriver_stage_probe as psp  # noqa: E402
import gate_replay_prototype as gr  # noqa: E402
import gate_chain_prototype as gch  # noqa: E402
import silicon_map_replay as smr  # noqa: E402

R = ROOT / "results"
VAR = R / "variant_stress_cases_2026-09-04"

# variant: (gate node, C_comp used by the existing chain dirs, chain args)
VARIANTS = {
    "ex2_base": ("v(xdut.n4)", 1.7, ["--K", "3", "--fix-xlin", "0.45"]),
    "ex2_weak": ("v(xdut.n4)", 1.7, ["--K", "3", "--fix-xlin", "0.45"]),
    "ex2_nomiller": ("v(xdut.n4)", 1.7, ["--K", "3", "--fix-xlin", "0.45"]),
    "ex2_skewp": ("v(xdut.n4)", 1.7, ["--K", "3", "--fix-xlin", "0.45"]),
    "ex2_slowpre": ("v(xdut.n4)", 1.7, ["--K", "3", "--fix-xlin", "0.45"]),
    "inv_base8": ("v(xdut.vout7)", 0.6, ["--K", "7", "--fix-xlin", "0.45"]),
    "inv_weak": ("v(xdut.vout7)", 0.3, ["--K", "7", "--fix-xlin", "0.45"]),
    "inv_skewp": ("v(xdut.vout7)", 0.4, ["--K", "7", "--fix-xlin", "0.45"]),
    "inv_stage4": ("v(xdut.vout3)", 0.6, ["--K", "4", "--fix-xlin", "0.45"]),
}


def hspice_run(d: Path, deck: str, src_dir: Path) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    for f in src_dir.iterdir():
        if f.is_file() and not f.name.startswith("run."):
            shutil.copy2(f, d / f.name)
    (d / "run.sp").write_text(deck, encoding="utf-8")
    tr0, lis = d / "run.tr0", d / "run.lis"
    ok = tr0.exists() and lis.exists() and "job concluded" in lis.read_text(errors="replace").lower()
    if not ok:
        rc = base.run_process([str(default_hspice()), "-i", "run.sp", "-o", "run"], d, d / "hspice_stdout.log", 1800)
        if rc != 0 or not tr0.exists():
            raise RuntimeError(f"hspice failed: {d}")
    return tr0


def make_runs(v: str, node: str, sup: float):
    src = VAR / v / "full_swing"
    deck = (src / "run.sp").read_text(encoding="utf-8", errors="replace")
    assert "Rload pad 0" in deck and "Cload pad 0" in deck, v
    for tag, vf in (("vfix_0", 0.0), ("vfix_vcc", sup)):
        fx = re.sub(r"^Rload pad 0 .*\n", f"Vfix fix 0 DC {vf:g}\nRfix pad fix 50\n", deck, count=1, flags=re.M)
        fx = re.sub(r"^Cload pad 0 .*\n", "", fx, count=1, flags=re.M)
        fx = re.sub(r"^\.probe tran .*$", ".probe tran V(in_dig) V(pad)", fx, flags=re.M)
        hspice_run(smr.FSFIX / v / tag, fx, src)
    pr = re.sub(r"^\.probe tran .*$", f".probe tran V(in_dig) {node.upper()} V(pad)", deck, flags=re.M)
    hspice_run(psp.OUT / v / "full", pr, src)


def make_stressed_probe(v: str, node: str, depth: int = 50) -> int:
    """Probe the variant's last stage on its depth-<depth> stressed pulse (for --joint-stress);
    returns the width in ps. Written to predriver_stages_2026-09-09/<v>/w<W> where
    gate_replay_prototype.real_gate looks for it."""
    import gate_ramp_prototype as gp
    cs = gp.cases(v)
    _, w, case = [c for c in cs if c[0] == depth][0]
    W = int(round(w * 1e3))
    src = case / "transistor"
    deck = (src / "run.sp").read_text(encoding="utf-8", errors="replace")
    pr = re.sub(r"^\.probe tran .*$", f".probe tran V(in_dig) {node.upper()} V(pad)", deck, flags=re.M)
    hspice_run(psp.OUT / v / f"w{W}", pr, src)
    return W


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=list(VARIANTS))
    ap.add_argument("--maps-only", action="store_true", help="make the HSPICE runs, skip the chain")
    ap.add_argument("--source", choices=("ibis", "real"), default="ibis", help="fit the chain to the tables (ibis) or to the variant's probed last stage (real)")
    ap.add_argument("--p", type=float, default=1.0, help="drive power law of the stages (1 plain, 0.5 square root)")
    ap.add_argument("--dn-ratio", type=float, nargs="*", default=[1.0], metavar="R",
                    help="fifth stage number: discharge resistive fraction = x_lin * R. Several values build several models")
    ap.add_argument("--free-xlin", action="store_true", help="drop the --fix-xlin 0.45 of the default chain args (let the tail be fitted)")
    ap.add_argument("--joint", action="store_true", help="with --source real: probe the last stage on the depth-50 pulse and fit the chain jointly to it (gate_chain_prototype --joint-stress)")
    args = ap.parse_args()
    for v in args.only:
        node, cc, chain_args = VARIANTS[v]
        sup = gch.gp.VARIANTS[v][0]
        print(f"\n=== {v}: gate {node}, C_comp {cc}, supply {sup}")
        make_runs(v, node, sup)
        # register the variant where the chain script looks things up
        psp.STAGES[v] = ["v(in_dig)", node, "v(pad)"]
        gr.GATES[v] = (node, None)
        gch.FSFIX[v] = smr.FSFIX / v
        if args.maps_only:
            continue
        ca = list(chain_args)
        if args.free_xlin and "--fix-xlin" in ca:
            i = ca.index("--fix-xlin")
            del ca[i:i + 2]
        extra = []
        if args.joint:
            W = make_stressed_probe(v, node, 50)
            extra = ["--joint-stress", str(W)]
        for r in args.dn_ratio:
            sys.argv = ["gate_chain_prototype.py", "--variant", v, "--ccomp", str(cc), "--source", args.source, "--maps", "silicon",
                        "--calib-pad", "50", "--p", str(args.p), "--dn-ratio", str(r)] + ca + extra
            print(f"  --- dn-ratio {r:g}")
            gch.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
