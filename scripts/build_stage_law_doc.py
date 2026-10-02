#!/usr/bin/env python3
"""Build the stage-law derivation document (Word, native equations, embedded figures).

Sections II-A to II-E of `results/stage_law_doc_2026-10-01/source/stage_law_derivation_original.docx`
(the derivation of the stage law from the alpha-power law) are kept as they are, with two
figures and one table added. Everything from the old Section F onward is rebuilt here from
the repository's own code and results, so that every statement can be traced:

    how the chain is built and emitted        tools/pybis2spice/pybis2spice/chain_command.py
    the Ku-domain fit                         scripts/gate_chain_prototype.py  (fit_chain_ku)
    the vt calibration on the pad peak        scripts/gate_chain_prototype.py  (calibrate_pad)
    the selection on the pad waveform         scripts/selector_from_one_run.py
    the pad current                           a generated driver.sub (B3/B4/C2 and the clamps)
    gate-level verification                   scripts/current_limited_stage_model.py --shared
    pad-level verification                    results/selector_from_one_run_2026-09-23
    measured alpha and V_D0                   scripts/device_alpha_extract.py

Figures come from scripts/build_stage_law_doc_figures.py (run that first).

    py -3.14 scripts/build_stage_law_doc.py

Output: results/stage_law_doc_2026-10-01/stage_law_derivation_v2.docx
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stage_law_docx import Package, equation, heading, para, table  # noqa: E402

DOC = ROOT / "results" / "stage_law_doc_2026-10-01"
FIG = DOC / "figures"
SRC = DOC / "source" / "stage_law_derivation_original.docx"
OUT = DOC / "stage_law_derivation_v2.docx"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def rows_of(path: Path):
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ----------------------------------------------------------------------------- data
def data():
    d = {}
    d["dev"] = rows_of(ROOT / "results/device_taper_2026-09-28/alpha_extract/results.csv")
    s1 = [r for r in rows_of(ROOT / "results/stage_count_from_file_2026-09-21/step1_summary.csv")
          if r["pass_"] == "as_track1"]
    d["rms"] = {(r["buffer"], r["chain"]): r for r in s1}
    d["ex2"] = rows_of(ROOT / "results/current_limited_stages_2026-09-10/ex2_chain_shared_K.csv")
    d["inv"] = rows_of(DOC / "inv_chain_chain_shared_K_regenerated.csv")
    d["sel"] = {r["buffer"]: r for r in rows_of(ROOT / "results/selector_from_one_run_2026-09-23/selector_picks.csv")}
    d["knet"] = {r["buffer"]: r["K_netlist"] for r in
                 rows_of(ROOT / "results/stage_count_from_file_2026-09-21/step8_picks.csv")}
    d["ku"] = {(r["device"], r["kind"]): r for r in
               rows_of(ROOT / "results/device_taper_2026-09-28/ku_domain/results.csv")}
    import build_stage_law_doc_figures as figs
    devs, nat, t1, dead = figs.fig_pad_summary()
    d["pad"] = list(zip(devs, nat, t1, dead))
    return d


def peaks(rows, K, col="pred_max"):
    return [float(r[col]) for r in rows if int(r["K"]) == K]


def f3(v):
    return f"{v:.3f}"


# ----------------------------------------------------------------------------- content
def build(pkg: Package, d) -> dict:
    """Returns {'after_eq7': xml, 'after_eq19': xml, 'tail': xml}."""
    out = {}

    # ---------------- inserted into Section B: the device, measured -----------------
    dev_rows = []
    for r in d["dev"]:
        card = "hspice.mod (BSIM3v3)" if "ex2" in r["device"] else "HL18G-S3.7S"
        dev_rows.append([r["device"], card, f"{float(r['L_m']) * 1e9:.0f} nm", f"{float(r['vdd']):.1f} V",
                         f"{float(r['vd0_over_vdd']):.3f}", f"{float(r['alpha']):.2f}"])
    al = [float(r["alpha"]) for r in d["dev"]]
    x0 = [float(r["vd0_over_vdd"]) for r in d["dev"]]
    rng = {"a": f"{min(al):.2f}–{max(al):.2f}", "x": f"{min(x0):.2f}–{max(x0):.2f}"}
    out["rng"] = rng
    out["after_eq7"] = (
        para("The device model (2)–(5) was checked against the transistors actually used in the predrivers "
             "of two test buffers, simulated in HSPICE from their model cards at their drawn dimensions. "
             "$V_{TH}$ and $\\alpha$ are extracted as in [1, App. A]: $V_{TH}$ is the value for which the "
             "saturation current is a straight line against $V_{GS} - V_{TH}$ on logarithmic axes, and "
             "$\\alpha$ is the slope of that line. Reference [1] gives no procedure for $V_{D0}$; it is taken "
             "here as the breakpoint that best fits the piecewise form (6) to the output curve at full gate "
             "drive. Fig. 1 shows the result and Table II lists the two normalized parameters. The measured "
             f"$\\alpha$ is {rng['a']}, between the short-channel limit of 1 and the long-channel value of 2 "
             f"[2], and the saturation voltage is {rng['x']} of the supply, comparable to the 0.5–0.55 "
             "used in [1].")
        + pkg.figure(FIG / "fig_device.png",
                     "Fig. 1. HSPICE characteristics of the predriver devices of test buffers ex2 and inv_chain, at "
                     "their drawn dimensions. (a) Output curves at full gate drive, normalized; the legend gives "
                     "the fitted $x_0 = V_{D0}/V_{DD}$. (b) Output curves of one device at five gate drives (solid) against the "
                     "α-power law (2) with the extracted $\\alpha$ and $V_{D0}$ (dashed; dots mark the saturation "
                     "voltage $V'_{D0}$ of (4)). (c) Saturation current against gate drive; the slope is $\\alpha$.")
        + table(["Device", "Model card", "Drawn length", "$V_{DD}$", "$x_0 = V_{D0}/V_{DD}$", "$\\alpha$"],
                dev_rows, [2500, 2000, 1300, 900, 1800, 1100],
                "Table II: Device parameters of (2)–(5) extracted in HSPICE from the predriver transistors"))

    # ---------------- inserted into Section E: the stage law, pictured ---------------
    out["after_eq19"] = (
        pkg.figure(FIG / "fig_stage_law.png",
                   "Fig. 2. The stage law (19). (a) Gate factor $h(u)$ of (17) for three exponents. (b) Drain factor "
                   "of the charging term: the fixed boundary $r(1-v)$ of (18), against the drive-dependent boundary "
                   "of (15) at three gate drives ($\\alpha = 1$, $x_0 = 0.45$); the two coincide at full drive. "
                   "(c) Response of one stage to an input step: a constant-slope ramp while $1-v > x_{lin}$, then an "
                   "exponential approach to the rail.")
        + para("The value used is $x_{lin} = 0.45$. It is a built-in constant of the method, not a quantity read "
               "from the IBIS file. It was chosen during development from fits of (19) to the individual probed "
               "predriver stages of two test buffers, which gave 0.37–0.47 on ex2 and 0.52–0.63 on "
               "inv_chain. Later evidence agrees with it: fitted to the probed gate with $x_{lin}$ free, the chain "
               f"gives 0.41 on ex2 and 0.48 on inv_chain; the measured $x_0$ of Table II is {rng['x']}; and [1] "
               "uses 0.5–0.55. In the pad-level tests of Section II-L it is fixed at 0.45 on ten of the "
               "twelve buffers; on inv_chain and io_buf it was instead fitted to the file together with the other "
               "stage parameters. Section II-J shows why the file constrains it only weakly. The default $p = 1$ is "
               f"likewise a built-in constant; it is the lower limit of the measured $\\alpha$ ({rng['a']}).")
        + para("As a check that (19) is the model of [1] and not merely similar to it, one stage with $p = \\alpha$ "
               "was driven by a linear input ramp and its delay compared with the closed-form delay of [1, eq. (5)]. "
               "The two agree within 4 ps for input ramps of 0.05 to 0.8 ns (stage delays of 0.24 to 0.35 ns), "
               "with the opposing device either present or switched off; they separate only for ramps slower "
               "than the range of validity stated in [1]."))

    # =================================================================================
    t = []
    A = t.append

    # ---------------- F. overview --------------------------------------------------
    A(heading("F. From the stage law to a buffer model: overview"))
    A(para("Equation (19) describes one predriver stage. Sections II-G to II-L turn it into a model of a "
           "complete output buffer and verify it. The argument has six steps, one per section:", "FirstParagraph"))
    A(para("(i) $K$ stages in cascade generate the trajectory of the output device's gate (Section II-G); "
           "(ii) a static map converts that gate trajectory into the conducting fractions $K_u$ and $K_d$, which "
           "scale the I–V tables of the IBIS file exactly as in the existing converter (Section II-H); "
           "(iii) the stage rates are fitted to the $K_u(t)$ that the file already contains (Section II-I); "
           "(iv) that fit is shown to leave the stage count, the stage threshold and the map shape undetermined "
           "(Section II-J); (v) one stressed pad measurement calibrates the threshold and selects among a small "
           "set of candidates (Section II-K); (vi) the model is verified at the internal gate node and at the pad "
           "(Section II-L). Fig. 3 shows the signal path and Table III the procedure."))
    A(pkg.figure(FIG / "fig_blocks.png",
                 "Fig. 3. Signal path of the model. The blocks added by the proposed method replace the way the "
                 "conducting fractions $K_u(t)$ and $K_d(t)$ are generated; the I–V tables, $C_{comp}$ and the "
                 "package elements are those of the IBIS file and are unchanged. Numbers in parentheses are equation "
                 "numbers.", width_in=6.3))
    A(table(["Step", "What is determined", "Data used", "Eq."],
            [["0", "I–V tables, $C_{comp}$, full-swing $K_u(t)$ and $K_d(t)$", "IBIS file, existing converter", "(24), (25)"],
             ["1", "$s_{up}$, $s_{dn}$ and an initial $v_t$, for each candidate stage count and map shape",
              "full-swing $K_u(t)$ of the file", "(26)"],
             ["2", "Candidate set: three stage counts × three map shapes", "fit residuals of step 1", "(27)"],
             ["3", "$v_t$, for each candidate", "peak of one stressed pad waveform", "(28)"],
             ["4", "Stage count $K$ and map shape", "the same stressed pad waveform, whole shape", "(29)"]],
            [700, 4300, 3300, 1300],
            "Table III: The procedure. $p = 1$ is fixed; $x_{lin} = 0.45$ is fixed on ten of the twelve test "
            "buffers and fitted in step 1 on the other two."))
    A(table(["Input", "Origin"],
            [["I–V tables, $C_{comp}$, package elements, full-swing $K_u(t)$ and $K_d(t)$", "the IBIS file"],
             ["$s_{up}$, $s_{dn}$, initial $v_t$", "fitted to the file (step 1)"],
             ["final $v_t$, stage count $K$, map shape", "one stressed pad measurement (steps 3 and 4)"],
             ["$x_{lin} = 0.45$, $p = 1$, the three candidate map shapes, the band rule (27)",
              "built-in constants, chosen during development on the twelve test buffers with "
              "transistor-level information"]],
            [5200, 4400], "Table IV: Inputs of the model and their origin"))
    A(para("Applying the method to a new buffer therefore needs no transistor-level information, but the "
           "method is not derived from the IBIS file alone: it uses one measurement, and four built-in constants "
           "whose values were chosen with knowledge of the test buffers' transistors. Whether those constants suit "
           "buffers outside the test set has not been tested.", "FirstParagraph"))

    # ---------------- G. the chain -----------------------------------------------------
    A(heading("G. The chain: from the input pin to the output gate"))
    A(para("The predriver is modeled as $K$ stages, each obeying (19) with one shared parameter set "
           "$\\{s_{up}, s_{dn}, v_t, x_{lin}, p\\}$ (approximation A3, identical normalized stages). Because (8) "
           "expresses every node as its own progress from 0 to 1, an inverting stage needs no sign: each stage's "
           "output is simply the next stage's input. The first stage is driven by a comparator on the input pin "
           "at half the supply:", "FirstParagraph"))
    A(equation("u_1(t) = 1~\\text{if}~V_{in}(t) > V_{DD}/2,~\\text{else}~0;\\quad u_{k+1}(t) = v_k(t),\\quad k = 1,\\ldots,K-1", 20))
    A(para("The output of the last stage is the gate of the output pull-up device, normalized from off to on, "
           "and the pull-down gate is taken as its complement:", "FirstParagraph"))
    A(equation("G_{UP}(t) \\triangleq v_K(t),\\quad G_{DN}(t) \\triangleq 1 - G_{UP}(t)", 21))
    A(para("The complement in (21) corresponds to an output stage whose two devices are driven from one predriver "
           "node, which is the case for ex2 and inv_chain and their variants. Where the netlist has separate "
           "pull-up and pull-down predriver paths, as in io_buf, a second chain with its own stage count and "
           "parameters is fitted for $G_{DN}$.", "FirstParagraph"))
    A(para("Fig. 4 shows what the chain does. For a full transition every stage completes its swing and the chain "
           "contributes only a delay and an edge shape. For a pulse shorter than the chain's own delay, the input "
           "reverses while the later stages are still rising: each stage turns back before reaching its rail, and "
           "the gate reaches only part of its swing (0.74 in Fig. 4(b)). Because a stage delivers no current until "
           "its input passes $v_t$, a pulse loses amplitude at every stage and, once its peak falls below $v_t$, it "
           "is not passed on at all. This is why the stage count is a first-order parameter of the model rather "
           "than a refinement. The abrupt cutoff is a property of the hard threshold in (17); in a transistor "
           "chain the loss is gradual."))
    A(pkg.figure(FIG / "fig_chain.png",
                 "Fig. 4. One chain, two inputs (ex2: $K = 3$, $s_{up} = 2.19$/ns, $s_{dn} = 2.12$/ns, $v_t = 0.487$, "
                 "$x_{lin} = 0.45$). Top: the stage nodes of (19)–(21). Bottom: the conducting fraction obtained "
                 "from the gate through the map (22), normalized. (a) Full transition. (b) An 810 ps input pulse: "
                 "the gate turns back at 0.74 of its swing and $K_u$ reaches 0.56.", width_in=6.0))
    A(para("For the fits of Sections II-I and II-L, (19)–(21) are integrated with Heun's method (second-order "
           "Runge–Kutta) at 1 ps steps, each state limited to $[-0.05, 1.05]$. Explicit Euler at 2 ps was found "
           "to be inadequate for the fastest stages (time constants near 20 ps): it passed a 119 ps pulse that the "
           "same chain extinguished in ngspice, whereas Heun agrees with ngspice. In the circuit model each stage "
           "is a behavioral current source charging an explicit capacitor $C_g$, so that $v_k$ is a circuit node:"))
    A(equation("C_g \\frac{dv_k}{dt} = C_g \\cdot 10^{9} \\left[ s_{up}~h(v_{k-1})~r(1 - v_k) - s_{dn}~h(1 - v_{k-1})~r(v_k) \\right]"))
    A(para("with the rates in swings per nanosecond; $C_g$ cancels and its value is immaterial.", "FirstParagraph"))

    # ---------------- H. gate -> conducting fraction -> pad --------------------------------
    A(heading("H. From the gate to the conducting fraction and the pad"))
    A(para("The stage law produces the gate trajectory $G_{UP}(t)$ and nothing else; it makes no statement about "
           "the output current. An IBIS-based driver model, on the other hand, needs at each instant the fraction "
           "$K_u$ of the pull-up I–V table that is conducting, and the fraction $K_d$ of the pull-down table. "
           "A second relation, separate from the stage law, connects the two.", "FirstParagraph"))
    A(para("*The map.* The pull-up table of the file is the current of the output transistor against pad voltage "
           "with its gate fully on. With the gate only partly on, the transistor delivers less, and the reduction "
           "is taken to be one multiplier at every pad voltage, which is the assumption any $K_u$-based IBIS model "
           "already makes:"))
    A(equation("I(V_{pad}, g) = K_u(g)~I_{PU}(V_{pad})"))
    A(para("$K_u$ is therefore a property of the output transistor: how far it is turned on when its gate is at "
           "level $g$. It is modeled by a static curve of transistor shape, scaled between the settled off and on "
           "levels of the file's own $K_u$ and $K_d$:", "FirstParagraph"))
    A(equation("K_u(t) = k_{off} + (k_{on} - k_{off})~M(G_{UP}(t)),\\quad M(g) \\triangleq \\clip\\left( \\frac{g - v_{t,map}}{g_s - v_{t,map}}, 0, 1 \\right)^{a}", 22))
    A(equation("K_d(t) = d_{off} + (d_{on} - d_{off})~M(G_{DN}(t))", 23))
    A(para("Below $v_{t,map}$ the output device is off and $M = 0$; above it $M$ rises with the gate drive, with "
           "curvature $a$, and reaches 1 at $g = g_s$ ($g_s = 1$ in the two-parameter form used below). The levels "
           "$k_{off}, k_{on}, d_{off}, d_{on}$ are close to 0 and 1 (0.0035 and 0.998 for $K_u$ on ex2). The map "
           "parameters describe the output device and are distinct from the stage parameters $v_t$ and $p$ of "
           "(17), which describe the predriver; the two have the same clip-and-power form because both are "
           "gate-drive factors of the kind (5), but they are different quantities.", "FirstParagraph"))
    A(para("That $K_u$ depends on the gate alone, without memory, was checked on the three buffers whose gate "
           "node can be probed: when the $K_u$ solved from the pad is plotted against the probed gate, the rising "
           "and falling branches coincide within 0.07–0.11. The shape of the curve, however, cannot be read "
           "from an IBIS file, because the file does not contain the gate. The shape parameters are therefore not "
           "fitted in step 1; they are taken from a small fixed set and selected in step 4 (Section II-K)."))
    A(para("*From the gate waveform to the conducting fraction.* The model's $K_u(t)$ is obtained by evaluating the two relations "
           "one after the other: (19)–(21) give $G_{UP}(t)$, and (22) is applied to each of its values. Table V "
           "does this for a single stage after an input step; Fig. 5 does it for the fitted three-stage chain of "
           "ex2."))
    import numpy as _np
    import current_limited_stage_model as _cl
    _t = _np.arange(-0.1, 1.5, _cl.DT)
    _g = _cl.simulate((_t >= 0).astype(float), 2.0, 2.0, 0.3, 0.45, 1.0)
    _rows = []
    for _tt in (0.10, 0.20, 0.30, 0.40, 0.60, 1.00):
        _gi = float(_np.interp(_tt, _t, _g))
        _ki = float(_np.clip((_gi - 0.57) / 0.43, 0, 1) ** 0.64)
        _rows.append([f"{_tt:.2f}", f"{_gi:.2f}", "0 (gate below $v_{t,map}$)" if _ki == 0 else f"{_ki:.2f}"])
    A(table(["Time after the input step (ns)", "Gate $g$, from the stage law (19)", "$M(g)$, from the map (22)"],
            _rows, [3200, 3200, 3200],
            "Table V: Worked example: one stage ($s_{up} = 2$ per ns, $x_{lin} = 0.45$) read through the map "
            "($v_{t,map} = 0.57$, $a = 0.64$)"))
    A(para("The gate rises as a ramp of 2 per ns until it is within $x_{lin}$ of its rail and then approaches it "
           "exponentially. Nothing conducts until the gate passes 0.57, 0.29 ns after the step; the conducting "
           "fraction then rises quickly, because the map is steep just above its threshold.", "FirstParagraph"))
    A(pkg.figure(FIG / "fig_gate_to_ku.png",
                 "Fig. 5. Construction of the conducting fraction on ex2 ($K = 3$, map shape (0.57, 0.64)). Left: the "
                 "gate trajectory given by the stage law. Middle: the map (22); the dots are the gate values of the "
                 "left panel at six instants. Right: the resulting $K_u(t)$, normalized, with the same instants "
                 "marked. (a)–(c) Full transition, with the parameters of the fit (26); in (c) the model is "
                 "compared with the $K_u(t)$ of the IBIS file, and this comparison is the fit of Section II-I. "
                 "(d)–(f) An 810 ps input pulse, after calibration: the gate turns back at 0.74, the map is read "
                 "only up to that level, and $K_u$ reaches 0.56.", width_in=6.3))
    A(para("The top row of Fig. 5 is the situation the file records. The gate sweeps its full range, the whole "
           "map is read, and the result in (c) can be compared with the file. The stage parameters are adjusted "
           "until the two curves in (c) agree; the map is not changed in that process. The bottom row is the "
           "situation the file does not record. The input is cut short, the gate turns back before reaching its "
           "rail, and only the lower part of the map is read. The conducting fraction in (f) rises to 0.56 and "
           "returns to zero: a waveform that no table of the file contains, produced by the same two relations "
           "with no additional parameter."))
    A(para("*From the conducting fraction to the pad.* The current delivered to the die node is that of the existing converter:"))
    A(equation("I_{die}(t) = K_u(t)~I_{PU}(V_{die}) + K_d(t)~I_{PD}(V_{die}) + I_{PC}(V_{die}) + I_{GC}(V_{die})", 24))
    A(para("where $I_{PU}$ and $I_{PD}$ are the pull-up and pull-down I–V tables of the file, held at their end "
           "values outside the tabulated range, and $I_{PC}$, $I_{GC}$ are the power- and ground-clamp tables, "
           "present only when the file contains them (io_buf does; ex2 and inv_chain do not). $C_{comp}$ loads the "
           "die node and the package $R$, $L$, $C$ of the file connect it to the pad. Equation (24) was checked "
           "against the generated subcircuits and is unchanged by the proposed method, which replaces only the "
           "source of $K_u(t)$ and $K_d(t)$; the converter's short first-order lag on the fractions (5 ps) and its "
           "residual correction term are also retained as they are.", "FirstParagraph"))
    A(para("*The ambiguity this creates.* In Fig. 5(c) only the composition of the two relations is tested. For "
           "any monotone trajectory $G(t)$, the map $K_u \\circ G^{-1}$ reproduces the same full-swing $K_u(t)$ "
           "exactly, so a faster gate with a later-starting map, or a slower gate with an earlier one, fits the "
           "file equally well. The two differ under a truncated pulse, because where the gate turns back depends "
           "on how fast it was moving. The stage law restricts the admissible trajectories to those a cascade of "
           "current-limited stages can produce, and the map shape is held fixed while the stage parameters are "
           "fitted, otherwise (19) and (22) trade off against each other. What remains undetermined is the "
           "subject of Section II-J."))

    # ---------------- I. fitting ---------------------------------------------------------
    A(heading("I. Step 1: fitting the stage parameters to the IBIS file"))
    A(para("The fitting target is the gate-driven part of the file's own $K_u(t)$. It is obtained by simulating "
           "the existing IBIS-derived subcircuit of the buffer through one full transition and recording its "
           "internal conducting fraction, without the converter's residual term. Target and model are both "
           "normalized from the settled off level to the settled on level:", "FirstParagraph"))
    A(equation("\\hat{K}_u(t) = \\clip\\left( \\frac{K_u(t) - K_u(t_{rest})}{K_u(t_{on}) - K_u(t_{rest})}, 0, 1 \\right),\\quad t_{rest} = 4.5~\\text{ns},~t_{on} = 12~\\text{ns}", 25))
    A(para("(the input edge is at 5 ns). For a given stage count $K$ and map shape $(v_{t,map}, a)$, the stage "
           "parameters minimize the root-mean-square mismatch over 4–21 ns, sampled every 2 ps:", "FirstParagraph"))
    A(equation("\\{ s_{up}, s_{dn}, v_t \\}^{\\star} = \\arg \\min~\\rms_t \\left[ M(v_K(t)) - \\hat{K}_u^{file}(t) \\right],\\quad x_{lin},~p~\\text{fixed}", 26))
    A(para("During the fit the chain input is an ideal 10 ns pulse starting at the mid-point of the input edge. "
           "The minimization is Nelder–Mead from three starting points ($s_{up} = s_{dn} = 2$, 8 and 30 per "
           "ns; 800 iterations each) with $0 \\le v_t \\le 0.7$, and it is repeated for every candidate $K$ and map "
           "shape. The comparison is made in the $K_u$ domain because the gate is not observable from the file: the "
           "model gate is passed through the map and only then compared. For a buffer with a separate pull-down "
           "path, the pull-down chain is fitted in the same way to $K_d(t)$ through its own map; fitting it through "
           "the $K_u$ target leaves its onset unconstrained, because that target is zero wherever $K_d$ turns on "
           "(an onset 250 ps early was observed on an open-drain test buffer).", "FirstParagraph"))
    ex, iv = d["ku"][("ex2", "linear_const")], d["ku"][("inv_chain", "linear_const")]
    A(pkg.figure(FIG / "fig_ku_fit.png",
                 "Fig. 6. Result of the fit (26) with $x_{lin} = 0.45$: the file's normalized $K_u(t)$, the fitted "
                 "model, and the model's gate trajectory, which the file does not contain. (a) ex2, $K = 3$, map "
                 "shape (0.57, 0.64). (b) inv_chain, $K = 7$, map shape (0.49, 0.60).", width_in=6.0))
    A(para("*Example.* For ex2 with $K = 3$, map shape (0.57, 0.64) and $x_{lin} = 0.45$, (26) gives "
           "$s_{up} = 2.190$/ns, $s_{dn} = 2.124$/ns and $v_t = 0.528$ at a residual of 0.023 (Fig. 6(a)). Three "
           "numbers are fitted, to a curve that the file already contains; no stressed data is used in this step."))

    # ---------------- J. identifiability ---------------------------------------------------
    A(heading("J. What the file cannot determine"))
    A(para("The fit (26) determines the rates well and the structure poorly. Table VI and Fig. 7 give its "
           "residual as a function of the stage count for three of the twelve test buffers, each $K$ fitted "
           "independently. The transistor netlists of the test buffers are available, so the true stage count "
           "is known.", "FirstParagraph"))
    hdr = ["Buffer"] + [f"$K$ = {k}" if k == 1 else str(k) for k in range(1, 11)] + ["Netlist"]
    rws = []
    for key, name in ((("ex2", "pull-up"), "ex2"), (("inv_chain", "pull-up"), "inv_chain"),
                      (("io_buf", "pull-up"), "io_buf (pull-up)")):
        r = d["rms"][key]
        rws.append([name] + [f"{float(x):.4f}"[1:] for x in r["rms_by_K"].split()] + [r["netlist_K"]])
    A(table(hdr, rws, [1500] + [720] * 10 + [800],
            "Table VI: Residual of the fit (26) in the $K_u$ domain against the stage count $K$", size=16))
    A(pkg.figure(FIG / "fig_rms_vs_k.png",
                 "Fig. 7. Residual of (26) against stage count for the thirteen predriver chains of the twelve test "
                 "buffers (io_buf has two). Circles mark the netlist stage count; the thick segments mark the band "
                 "(27).", width_in=5.6))
    A(para("Two features are evident. First, $K = 1$ fails on ex2 and inv_chain: a single stage cannot produce "
           "the required delay together with the required edge rate, so the full swing does constrain the rate. "
           "Second, beyond that the residual is flat: on ex2, $K = 3$ to 6 lie within 0.002 of each other and the "
           "minimum is at $K = 5$ although the netlist has three stages; on inv_chain, $K = 6$ to 9 differ in the "
           "fourth decimal. The margin between the best and the second-best $K$ is at most 0.0007 on twelve of the "
           "thirteen chains. Only io_buf's pull-up, which is a single stage, has a distinct minimum (margin "
           "0.0088). This is the composition degeneracy of Section II-H in numbers."))
    A(para("The same holds for the other quantities that act only under partial drive. *The threshold:* the "
           "fitted $v_t$ of ex2 is 0.029 in one fitting pass ($K = 6$) and 0.528 in another ($K = 3$) that differs "
           "in $C_{comp}$ and map shape, at residuals of 0.0202 and 0.0233. *The exponent:* at full swing each stage input dwells at "
           "the rail, where (17) does not depend on $p$; in fits of the individual probed stages every $p$ between 1 and 2 "
           f"reaches a residual of 0.002–0.007. *The saturation boundary:* if $x_{{lin}}$ is left free in (26) it settles at "
           f"{float(ex['x_lin']):.3f} on ex2 and {float(iv['x_lin']):.3f} on inv_chain, less than half the measured "
           "$x_0$ of Table II, and replacing (18) by the drive-dependent boundary of (15) changes the residual by "
           "about 1 % on ex2 and not at all on inv_chain. The file cannot distinguish these alternatives, which is "
           "why $x_{lin}$ and $p$ are normally held fixed (Table IV) rather than fitted."))
    A(para("A fit with every stage free is worse than uninformative. On ex2 with $K = 2$ and all eight "
           "parameters free, the full-swing residual against the probed gate falls to 0.0046, below the 0.0066 of "
           "the identical-stage fit with the correct $K = 3$; it achieves this with one very slow stage and one "
           "fast one, and such a "
           "chain extinguishes short pulses: it predicts a stressed gate peak of 0.228 where 0.758 is measured. "
           "Sharing one parameter set among the stages (A3) removes this solution and leaves $K$ as the single "
           "structural unknown."))
    A(para("The procedure therefore keeps a band of stage counts instead of a point estimate:"))
    A(equation("\\text{band} = \\text{the~three~smallest}~K~\\text{with}~\\rms(K) \\le 1.25~\\min_{K'}~\\rms(K')", 27))
    A(para("On the twelve test buffers the band contains the netlist stage count in every case. The tolerance "
           "of 25 % and the band width of three were chosen on these same buffers, so this is a property of the "
           "rule as tuned and not an independent validation.", "FirstParagraph"))

    # ---------------- K. the stressed measurement -----------------------------------------
    A(heading("K. Steps 2–4: the single stressed measurement"))
    A(para("What the file cannot determine is settled by one measurement that the file does not contain: the pad "
           "voltage for a single short pulse into a known load. In the tests below the pulse is the one that "
           "reaches about 50 % of the buffer's settled swing into a 50 Ω, 2 pF load, and the measurement is a "
           "transistor-level simulation of the buffer. The measurement is used twice.", "FirstParagraph"))
    A(para("*Candidates (step 2).* The band (27) supplies three stage counts. The map shape, the other factor "
           "of the composition, is taken from three shapes, $(v_{t,map}, a) \\in$ {(0.50, 0.70), (0.40, 0.60), "
           "(0.40, 0.90)}. Each of the nine candidates has its own fit (26)."))
    A(para("*Calibration of the threshold (step 3).* For each candidate, with $\\hat{V}$ the measured peak of the "
           "pad voltage, define the peak error"))
    A(equation("e(v_t) \\triangleq \\frac{\\max_t V_{pad}^{model}(t; v_t) - \\hat{V}}{\\hat{V}},\\quad e(v_t^{cal}) = 0", 28))
    A(para("and solve $e = 0$ for $v_t$ by bisection on $[0, 0.7]$, all other parameters held at their values "
           "from (26). Each evaluation is one circuit simulation of the complete model; three bracket the "
           "interval and seven bisect it. If the threshold cannot bracket the peak, $s_{up}$ and $s_{dn}$ are scaled "
           "together within $[0.5, 2]$ instead. The threshold is used, and not the rates, because the rates were "
           "fitted to reproduce the full swing and moving them degrades it, whereas $v_t$ changes when each stage "
           "hands over without changing how fast it runs. For ex2 the calibration moves $v_t$ from 0.528 to 0.487 "
           "(Fig. 8(b)).", "FirstParagraph"))
    A(para("*Selection of the stage count and map shape (step 4).* After calibration all nine candidates "
           "reproduce the measured peak, so the peak carries no further information; they differ in the rest of "
           "the waveform (Fig. 8(c)). The candidate is chosen by the waveform error over the pulse and its return,"))
    A(equation("(K, v_{t,map}, a)^{\\star} = \\arg \\min~\\rms_{t \\in [t_f - 0.3~\\text{ns},~t_f + 1.5~\\text{ns}]} \\left[ V_{pad}^{model}(t) - V_{pad}^{meas}(t) \\right]", 29))
    A(para("where $t_f$ is the falling edge of the input pulse. The window was chosen once and was not tuned.",
           "FirstParagraph"))
    A(pkg.figure(FIG / "fig_calibration.png",
                 "Fig. 8. Use of the stressed measurement on ex2 (810 ps input pulse). (a) The measurement and its "
                 "peak. (b) Calibration (28): pad waveform of the model as $v_t$ is bisected; the final curve meets "
                 "the measured peak (dashed). (c) Selection (29): the nine calibrated candidates all reach the "
                 "measured peak and differ elsewhere; the shaded interval is the window of (29). Time is measured "
                 "from the input edge.", width_in=6.3))
    A(para("The stage count and the threshold are thus both taken from one waveform, but from different features "
           "of it: the threshold from its height, the stage count and map shape from its shape. Selecting on the "
           "peak instead of the waveform is markedly worse. Averaged over the twelve buffers, the pad-waveform "
           "error at all five stressed widths (the rms of (29) evaluated at each width) is 52.3 mV for the "
           "candidates chosen by (29), against 51.7 mV for the best candidate available in each grid and 217.3 mV "
           "for the candidates that minimize the worst peak error, which achieve their peak by arriving 155–300 "
           "ps late."))

    # ---------------- L. verification ------------------------------------------------------
    A(heading("L. Verification"))
    A(para("Two claims are verified separately. The first concerns the stage law itself: fitted to a full "
           "transition only, a cascade of (19) predicts how the gate responds to a truncated pulse. The second "
           "concerns the complete method: built from the IBIS file and one stressed measurement, the model "
           "reproduces the pad voltage of stressed pulses.", "FirstParagraph"))
    A(heading("1) Gate level: the stage law extrapolates from full swing to truncated pulses", 3))
    A(para("This test uses the internal gate node of the transistor netlist (node n4 of ex2, vout7 of inv_chain) "
           "and therefore is not available to a user of the method; its purpose is to test (19). $K$ identical "
           "stages are fitted in the gate domain to the probed full-swing gate; the chain is then driven by the "
           "stressed input and compared with the probed stressed gate at five pulse widths, which correspond to "
           "pad amplitudes of about 50, 60, 70, 80 and 90 % of the settled swing. No stressed data enters the fit. "
           "The comparison is linear superposition of the node's own full-swing rise and fall responses, which is "
           "what any linear model of the predriver (an RC cascade, a delay followed by an RC) reduces to.",
           "FirstParagraph"))
    e = d["ex2"]
    wid = [r["width_ps"] for r in e if int(r["K"]) == 3]
    A(table(["Pulse width (ps)"] + wid,
            [["Measured"] + [f3(float(r["meas_max"])) for r in e if int(r["K"]) == 3],
             ["Stage law, $K$ = 3"] + [f3(v) for v in peaks(e, 3)],
             ["Stage law, $K$ = 2"] + [f3(v) for v in peaks(e, 2)],
             ["Linear superposition"] + [f3(v) for v in peaks(e, 3, "lin_max")]],
            [3100] + [1300] * 5, "Table VII: Peak of the stressed gate, ex2 (fitted at full swing only)"))
    r3 = [r for r in e if int(r["K"]) == 3]
    worst3 = max(abs(float(r["pred_max"]) - float(r["meas_max"])) for r in r3)
    lin0 = float(r3[0]["lin_max"]) - float(r3[0]["meas_max"])
    k2 = peaks(e, 2)
    A(para(f"On ex2 the stage law with the netlist stage count is within {worst3:.2f} of the measured peak at "
           f"every width, where linear superposition is off by {lin0:.2f} at the narrowest pulse (Table VII, "
           f"Fig. 9(a)). The waveform error at the narrowest pulse is {float(r3[0]['rms']):.3f} for the stage law, "
           f"from a full-swing fit residual of {float(r3[0]['full_rms']):.4f}. The stage count matters as Section "
           f"II-J predicts: $K = 2$ gives {min(k2):.2f}–{max(k2):.2f}, far below the measurement."))
    iv_rows = d["inv"]
    wid = [r["width_ps"] for r in iv_rows if int(r["K"]) == 7]
    have = sorted({int(r["K"]) for r in iv_rows})
    A(table(["Pulse width (ps)"] + wid + ["Full-swing residual"],
            [["Measured"] + [f3(float(r["meas_max"])) for r in iv_rows if int(r["K"]) == 7] + [""]]
            + [[f"Stage law, $K$ = {k}"] + [f3(v) for v in peaks(iv_rows, k)]
               + [f"{float(next(r for r in iv_rows if int(r['K']) == k)['full_rms']):.4f}"] for k in (7, 5, 3, 9) if k in have]
            + [["Linear superposition"] + [f3(v) for v in peaks(iv_rows, 7, "lin_max")] + [""]],
            [2700] + [1050] * 5 + [1650], "Table VIII: Peak of the stressed gate, inv_chain (fitted at full swing only)"))
    out["inv_table_done"] = have
    A(pkg.figure(FIG / "fig_gate_verify.png",
                 "Fig. 9. Stressed gate of the transistor netlist against the stage law fitted at full swing only, "
                 "and against linear superposition, at the narrowest, middle and widest of the five pulse widths. "
                 "(a) ex2. (b) inv_chain.", width_in=6.2))
    return out, t


def build_tail(pkg: Package, d, t):
    A = t.append
    iv = d["inv"]
    k7 = [r for r in iv if int(r["K"]) == 7]
    err7 = [float(r["pred_max"]) - float(r["meas_max"]) for r in k7]

    def swallowed(K):
        return sum(1 for v in peaks(iv, K) if v < 0.05)

    txt = (f"On inv_chain (Table VIII, Fig. 9(b)) the stage law with the netlist stage count follows the measurement "
           f"at the three widest pulses (within {max(abs(x) for x in err7[2:]):.2f}) and undershoots at the two "
           f"narrowest, by {abs(err7[0]):.2f} at 104 ps. This is the partial-drive regime in which approximation A2 "
           "is active (Section II-M).")
    if 5 in {int(r["K"]) for r in iv} and 3 in {int(r["K"]) for r in iv}:
        f7 = float(k7[0]["full_rms"])
        f5 = float(next(r for r in iv if int(r["K"]) == 5)["full_rms"])
        f3_ = float(next(r for r in iv if int(r["K"]) == 3)["full_rms"])
        txt += (f" The other rows show the consequence of the flat residual of Section II-J. The full-swing "
                f"residuals of $K = 7$, 5 and 3 are {f7:.4f}, {f5:.4f} and {f3_:.4f}; with $K = 5$ the chain "
                f"extinguishes {swallowed(5)} of the five stressed pulses and with $K = 3$ it extinguishes "
                f"{swallowed(3)}. (Both of those fits end with $v_t$ at its upper bound of 0.7, so they are "
                "constrained fits, not free ones.) With $K = 9$, at the same residual as $K = 7$, the pulse passes "
                "almost unattenuated. The file supplies the band (27); only the stressed measurement can choose "
                "within it.")
    A(para(txt))
    A(para("A control establishes that the nonlinearity captured by (19) is a property of the buffers and not "
           "of the fit. On io_buf, for input pulses of 1505–2354 ps, every probed predriver node and the pad "
           "follow linear superposition (pad peak 0.373 measured against 0.371 predicted at 1505 ps), whereas the "
           "same test fails on the output gate of ex2 (0.758 against 0.926) and at the pad of inv_chain (0.490 "
           "against 0.853). This statement covers high-going pulses of those widths; the pull-down path of io_buf "
           "under much shorter low-going pulses (163–322 ps) is not linear."))

    A(heading("2) Pad level: the complete method on twelve buffers", 3))
    A(para("The complete procedure of Table III was applied to twelve test buffers: ex2, inv_chain and io_buf, and "
           "nine variants of the first two. For each buffer the model was built from its IBIS file and from one transistor-level pad waveform "
           "at the pulse width giving about 50 % of the settled swing; $C_{comp}$ was taken from the file, reduced "
           "where the declared value implied a conducting fraction above unity. The model was then simulated at five "
           "pulse widths (about 50 to 90 % of the settled swing) into the same load and compared with "
           "transistor-level simulation of the same buffer. The score is the worst peak error over the five widths, "
           "with the peak error defined as in (28). The calibration width is one of the five, so the score is not "
           "entirely held out. HSPICE's native IBIS element with the same file is given for comparison.",
           "FirstParagraph"))
    A(pkg.figure(FIG / "fig_pad_waveforms.png",
                 "Fig. 10. Pad voltage for the narrowest stressed pulse of three buffers: transistor-level reference, "
                 "HSPICE native IBIS, and the proposed model built from the IBIS file and one stressed measurement. "
                 "The percentages are peak errors against the reference. Time is measured from the input edge.",
                 width_in=6.3))
    rows = []
    for dev, nat, t1, dead in d["pad"]:
        k_sh = d["sel"][dev]["rms"].split()
        rows.append([dev, d["knet"][dev], k_sh[0][1:], "(" + k_sh[1].replace("/", ", ") + ")", f"{t1:.1f}",
                     "no valid run" if dead else f"{nat:.1f}"])
    t1s = [x[2] for x in d["pad"]]
    A(table(["Buffer", "Netlist $K$", "Selected $K$", "Selected map shape", "Proposed: worst peak error (%)",
             "Native IBIS: worst peak error (%)"], rows, [1700, 1100, 1200, 1700, 2000, 1900],
            "Table IX: Pad-level result on the twelve test buffers (worst of five stressed pulse widths)"))
    A(pkg.figure(FIG / "fig_pad_summary.png",
                 "Fig. 11. Worst stressed peak error at the pad for the twelve test buffers.", width_in=6.3))
    live = [x[1] for x in d["pad"] if not x[3]]
    A(para(f"The proposed model is within 10 % on all twelve buffers (range {min(t1s):.1f}–{max(t1s):.1f} %, "
           f"mean {sum(t1s) / len(t1s):.1f} %). On the seven buffers for which the native IBIS element produced a "
           f"valid run, its worst peak error is {min(live):.0f}–{max(live):.0f} %; on the five ex2 variants it "
           "did not produce a valid waveform at any pulse width with the simulation settings used, and no number is "
           "reported. The selected stage count equals the netlist count on eleven buffers (inv_chain selects 6 "
           "against 7)."))

    A(heading("3) Limits of the evidence", 3))
    A(para("The gate-level test establishes that the structure of (19) extrapolates from full swing to truncated "
           "pulses when it is fitted to the true gate; it does not by itself establish the accuracy of the "
           "file-only procedure, in which the gate is never observed. That is what the pad-level test addresses, "
           "and the two are complementary. Both have a narrow statistical base: the five pulse widths of a buffer "
           "sample one stressed trajectory and are strongly correlated, so the evidence rests on the number of "
           "buffers. The pad-level test covers single high-going pulses, one load and the typical corner; trains "
           "of pulses, low-going pulses (examined so far only on io_buf), other loads and other corners are outside "
           "it. The map-shape grid and the band rule (27) were chosen on these same twelve buffers.",
           "FirstParagraph"))
    A(para("One limit is inherited from the device model. Reference [1] states that the α-power law does not "
           "reproduce the region near and below threshold, and its delay analysis neglects the opposing device, "
           "which is justified for fast inputs [3]. A truncated pulse holds the stages near $v_t$ with both "
           "devices conducting, which is outside the regime for which [1] validated the model. Equation (19) "
           "keeps both devices, but its accuracy there rests on the tests of this section and not on [1]."))

    # ---------------- M. approximations ----------------------------------------------------
    A(heading("M. Summary of approximations"))
    A(table(["Label", "Approximation", "Introduced at", "What it removes", "Evidence"],
            [["A0", "One $V_{TH}$, $\\alpha$, $V_{D0}$ for both devices of a stage", "(13)–(14)",
              "Per-device parameters", "As in [1, Sec. VI]. Table II: the N and P devices differ ($x_0$ 0.34 against 0.57 on inv_chain)"],
             ["A1", "$p$ in place of $\\alpha$, with $p = 1$", "(17)", "The measured $\\alpha$ (Table II)",
              "Not identifiable from the file (Section II-J)"],
             ["A2", "$x_0 g^{\\alpha/2} \\to x_{lin}$, with $x_{lin} = 0.45$", "(18)",
              "Drive dependence of the saturation boundary",
              "Not identifiable from the file (Section II-J); candidate cause of the inv_chain undershoot in Table VIII"],
             ["A3", "$K$ identical normalized stages", "(20)", "$4(K - 1)$ free parameters",
              "Free fit fails (Section II-J); $K$ selected by (29)"],
             ["A4", "Map shape taken from a grid of three", "(22), (26)", "Trade-off between gate and map",
              "Selected by (29); grid chosen on the test buffers"]],
            [650, 2700, 1300, 2150, 2800], "Table X: Approximations of the model", size=16))
    A(para("Everything else in (19) is inherited from (1) and (2)–(5): the threshold, the constant-current "
           "ramp, the straight-line resistive tail and the two-device structure. Equation (24) is the existing "
           "converter's and is unchanged."))

    # ---------------- notation -------------------------------------------------------------
    A(heading("Table I: Notation"))
    A(table(["Symbol", "Definition", "Origin"],
            [["$u$, $v$", "Normalized stage input and output, 0 → 1", "(8)"],
             ["$v_t$", "$V_{TH}/V_{DD}$; in the fitted model, the effective stage threshold", "(9)"],
             ["$x_0$", "$V_{D0}/V_{DD}$, saturation boundary at full drive", "(9)"],
             ["$x_{lin}$", "Fixed value replacing $x_0 g^{\\alpha/2}$", "(18)"],
             ["$g(x)$", "Normalized gate drive with cutoff", "(11)"],
             ["$h(x)$", "Gate factor, $g^{p}$", "(17)"],
             ["$r(x)$", "Drain factor, $\\min(1, x/x_{lin})$", "(18)"],
             ["$s_{up}$, $s_{dn}$", "$I_{D0}/(C V_{DD})$ per device, swings per unit time", "(16)"],
             ["$p$", "Gate exponent, model counterpart of $\\alpha$", "(17)"],
             ["$K$", "Number of stages", "(20)"],
             ["$G_{UP}$, $G_{DN}$", "Normalized gate trajectories of the output pull-up and pull-down devices", "(21)"],
             ["$M$, $(v_{t,map}, a, g_s)$", "Static gate-to-fraction map and its shape parameters", "(22)"],
             ["$K_u$, $K_d$", "Conducting fractions of the output pull-up and pull-down devices", "(22), (23)"],
             ["$\\hat{K}_u$", "$K_u$ normalized from its settled off level to its settled on level", "(25)"],
             ["$e(v_t)$", "Relative error of the model's pad peak against the measured peak", "(28)"]],
            [2400, 5600, 1600]))

    # ---------------- references -----------------------------------------------------------
    A(heading("References"))
    A(para("[1] T. Sakurai and A. R. Newton, “Alpha-power law MOSFET model and its applications to CMOS "
           "inverter delay and other formulas,” IEEE J. Solid-State Circuits, vol. 25, no. 2, pp. 584–594, "
           "Apr. 1990.", "FirstParagraph"))
    A(para("[2] H. Shichman and D. A. Hodges, “Modeling and simulation of insulated-gate field-effect "
           "transistor switching circuits,” IEEE J. Solid-State Circuits, vol. SC-3, 1968."))
    A(para("[3] N. Hedenstierna and K. O. Jeppson, “CMOS circuit speed and buffer optimization,” IEEE "
           "Trans. Computer-Aided Design, vol. CAD-6, no. 2, pp. 270–280, Mar. 1987."))

    A(heading("Remarks for the manuscript"))
    A(para("*Sources.* Every statement in Sections II-F to II-M was checked against the code and result files of "
           "the project; the builder script of this document lists the file behind each. Reference [1] was read "
           "in full: equations (2)–(5) here are its (2)–(4), the straight-line triode region of (6) "
           "is its own, the single-stage response of Fig. 2(c) is its Appendix B, and approximation A0 is its "
           "Section VI. Reference [3] is given as it appears in the reference list of [1]. Reference [2] is "
           "given as it appears in the bibliography of Leventhal and Green, *Semiconductor Modeling* (Springer, "
           "2006); its issue and page numbers were not available for checking and are omitted.",
           "FirstParagraph"))
    A(para("*Regenerated numbers.* Table VIII was regenerated for this document. The earlier committed table had been "
           "produced with an explicit-Euler integrator that was later replaced (Section II-G); ex2 (Table VII) is "
           "unaffected to the third decimal for $K = 3$."))
    A(para("*Open points.* (1) A drive-dependent boundary (15) in place of A2 reduces the inv_chain undershoot at "
           "the gate (mean peak error 0.077 to 0.016) but is neutral on ex2 and cannot be identified in the $K_u$ "
           "domain, so it has not been adopted; fixing $x_{lin}$ per buffer from a measured $x_0$ (Table II) is "
           "untested at the pad. (2) The pad-level score includes the calibration width. (3) Pulse trains, "
           "low-going pulses and other loads and corners are not covered by Table IX."))
    return t


def main() -> int:
    d = data()
    pkg = Package(SRC, DOC / "_build")
    doc_xml = pkg.dir / "word" / "document.xml"
    tree = etree.parse(str(doc_xml))
    body = tree.getroot().find(f"{{{W}}}body")

    for el in list(body):
        if etree.QName(el).localname in ("bookmarkStart", "bookmarkEnd"):
            body.remove(el)
    for el in body.iter(f"{{{W}}}bookmarkStart", f"{{{W}}}bookmarkEnd"):
        el.getparent().remove(el)

    kids = list(body)
    text = lambda el: "".join(el.itertext())                       # noqa: E731
    i_f = next(i for i, k in enumerate(kids) if text(k).startswith("F. Chain model"))
    sect = kids[-1]
    assert etree.QName(sect).localname == "sectPr"
    for k in kids[i_f:-1]:
        body.remove(k)

    def frag(xml: str):
        return list(etree.fromstring(f"<root {Package.NS}>{xml}</root>"))

    ins, tail = build(pkg, d)
    tail = build_tail(pkg, d, tail)

    def insert_after(startswith: str, xml: str):
        el = next(k for k in body if text(k).startswith(startswith))
        pos = list(body).index(el)
        for j, new in enumerate(frag(xml), 1):
            body.insert(pos + j, new)

    insert_after("Equation (7) is the device model", ins["after_eq7"])
    insert_after("Comparing (19) with (15) term by term", ins["after_eq19"])
    for new in frag("".join(tail)):
        sect.addprevious(new)

    # the intro pointed at the old section letter for the approximations
    n = 0
    for tnode in body.iter(f"{{{W}}}t"):
        if tnode.text and "Section II-G" in tnode.text and "isolated" in tnode.text:
            tnode.text = tnode.text.replace("Section II-G", "Section II-M")
            n += 1
    assert n == 1, n
    tree.write(str(doc_xml), xml_declaration=True, encoding="UTF-8", standalone=True)
    pkg.finish(OUT)
    print(f"wrote {OUT}  ({OUT.stat().st_size / 1024:.0f} kB, {len(pkg.images)} figures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
