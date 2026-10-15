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
    the converter's Ku/Kd solution            tools/pybis2spice/pybis2spice/pybis2spice.py (solve_k_params_output)
    the residual landscape and search paths   results/stage_law_doc_2026-10-01/fit_search.py
    the calibration iterations                results/stage_law_doc_2026-10-01/calib_iterations.py
    the twelve file-only fits, ex2's ledger   stage_count_from_file steps 6/8 builds (read by the figure script)

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
    import json
    import build_stage_law_doc_figures as figs
    d["shape_order"] = [(0.3, 0.6), (0.4, 0.6), (0.4, 0.9), (0.5, 0.7), (0.6, 0.6), (0.6, 0.9)]
    d["shapes"] = {}
    for p in (DOC / "shape_from_file").glob("shape_*.json"):
        r = json.loads(p.read_text())
        d["shapes"][(r["dev"], r["vt_map"], r["a"])] = r
    d["knobs"] = figs.fig_fit_knobs()
    d["gate_int"] = figs.fig_gate_internal()
    d["stress"] = figs.fig_stress_use()                     # (lowest, highest candidate peak, measured)
    devs, nat, t1, dead = figs.fig_pad_summary()
    d["pad"] = list(zip(devs, nat, t1, dead))
    d["target_info"] = figs.fig_target()
    d["score"] = figs.fig_fit_score()
    d["search"] = figs.fig_fit_search()
    d["one_vs"] = figs.fig_one_vs_chain()
    d["fit_all"] = figs.fig_fit_all()
    d["calib"] = figs.fig_calib_mech()
    d["ledger"] = figs.ex2_ledger()
    import numpy as np
    L = np.load(DOC / "fit_search" / "landscape.npz")
    i = int(np.argmin(np.abs(np.log(L["s_up"]) - np.log(L["fit"][0]))))
    z = L["rms_sup_vt"][i]
    d["land"] = dict(z0=float(z[0]), zmin=float(z.min()), vt_min=float(L["vt"][int(np.argmin(z))]), z07=float(z[-1]))
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
    out["min_form"] = (
        para("Equation (2) has no single-expression form in [1]; the one used here is ours, and it follows from "
             "factoring $I'_{D0}$ out of the triode row. The two conducting rows then read", "FirstParagraph")
        + equation("I_D = I'_{D0} \\cdot \\frac{V_{DS}}{V'_{D0}}~~(V_{DS} < V'_{D0}),\\quad I_D = I'_{D0} \\cdot 1~~(V_{DS} \\ge V'_{D0})")
        + para("In the first row the ratio $V_{DS}/V'_{D0}$ is below 1 and in the second it is 1 or above, so in "
               "each row the multiplier of $I'_{D0}$ is whichever of 1 and $V_{DS}/V'_{D0}$ is the smaller. The two "
               "rows meet at $V_{DS} = V'_{D0}$, where both give $I'_{D0}$, and the current is continuous. The "
               "conducting part of (2) is therefore", "FirstParagraph"))
    out["prelim"] = (
        heading("Preliminaries: the problem, the idea and the terms")
        + para("*What an IBIS file contains.* An IBIS file describes an output buffer from its pins. For the "
               "driver it holds three things: I–V tables, which give the current the output transistors deliver "
               "against pad voltage with the pull-up fully on (and likewise the pull-down); V–T waveforms, which "
               "give the pad voltage against time for one complete rising and one complete falling transition "
               "into a stated load; and the die capacitance $C_{comp}$ with the package parasitics. The standard "
               "way to simulate from such a file is to solve, from the V–T waveforms, two time-varying "
               "coefficients $K_u(t)$ and $K_d(t)$, the fraction of the pull-up and of the pull-down table that is "
               "conducting at each instant, such that $K_u I_{PU} + K_d I_{PD}$ reproduces the recorded waveforms. "
               "In simulation the coefficients are then replayed against time from the input edge. This is what "
               "the document calls the existing converter, and “the file's $K_u(t)$” means these "
               "coefficients.", "FirstParagraph")
        + para("*The problem.* Those coefficients describe complete transitions, and that is what the file "
               "records (Fig. 1(a)). When the input pulse is shorter than the buffer's own delay and edge, the "
               "transition is cut short: in Fig. 1(b) an 810 ps pulse drives ex2's pad to 0.77 V of its 1.55 V "
               "swing, and the model replayed from the file overshoots the peak by 71 %. On the twelve test "
               "buffers of this work the error of such a model is 20–100 % (Table XIII). Physically the "
               "pulse is interrupted inside the predriver, the chain of inverters between the input pin and the "
               "output transistors, while it is still travelling: the gate of the output transistor turns back "
               "partway, and a coefficient replayed against time has no way to represent that.")
        + pkg.figure(FIG / "fig_problem.png",
                     "Fig. 1. The problem, on test buffer ex2. (a) A complete transition into the test load: the "
                     "situation an IBIS file records. (b) An input pulse of 810 ps, shorter than the buffer's delay "
                     "and edge: the transistor-level pad voltage against HSPICE's native IBIS model of the same "
                     "file, which replays the file's coefficients against time.", width_in=6.2)
        + para("*The idea.* Model the predriver as a chain of stages whose output is the gate of the output "
               "transistor; convert that gate into $K_u$ and $K_d$ through a static map, so that the fractions "
               "follow the gate rather than the clock; fit the chain's rates to the $K_u(t)$ that the file already "
               "contains; and use one measured short pulse to settle what the file cannot. Sections II-A to II-E "
               "derive the stage law from the transistor. Sections II-F to II-M build the buffer model from it, "
               "fit it, and verify it at the gate and at the pad.")
        + table(["Term", "Meaning"],
                [["the file", "the IBIS file of the buffer being modeled"],
                 ["the existing converter; native model", "the IBIS-to-SPICE converter this work extends, which replays the file's $K_u(t)$, $K_d(t)$ against time; HSPICE's own IBIS element does the same"],
                 ["pad; die node", "the buffer's output pin; the node inside the package where the output transistors and $C_{comp}$ connect"],
                 ["complete (full) transition; settled swing", "an input edge the buffer finishes before the next one; the pad voltage it reaches"],
                 ["stressed pulse; depth", "an input pulse too short for the transition to complete; the fraction of the settled swing the pad reaches (the tests use about 50–90 %)"],
                 ["predriver; stage", "the chain of inverters between the input pin and the output transistors; one inverter of it"],
                 ["output device; gate", "the pull-up (or pull-down) transistor that drives the pad; its gate node, written $g$ or $G_{UP}$ on a 0-to-1 scale"],
                 ["$K_u$, $K_d$; conducting fraction", "the multiplier on the pull-up (pull-down) I–V table at a given instant"],
                 ["the map $M$", "the fixed curve giving $K_u$ as a function of the gate"],
                 ["candidate", "one complete model: a stage count, a map shape and the stage numbers fitted for them"],
                 ["probed", "read from an internal node of the transistor netlist, which only the development tests can do"]],
                [3000, 6600], "Table II: Terms used throughout")
        + para("Three thresholds and three exponents appear and should not be confused. $V_{TH}$ is the device "
               "threshold of Section II-B; $v_t$ is the stage threshold, defined from $V_{TH}$ in (9) but treated "
               "from Section II-I onward as an effective, fitted number; $v_{t,map}$ is the gate level at which the "
               "output device starts to conduct in the map. $\\alpha$ is the device's velocity-saturation index, "
               "$p$ its stand-in in the stage law (fixed at 1), and $a$ the curvature of the map. Table I at the "
               "end collects every symbol."))
    out["a1a2"] = (
        para("*A1 (gate exponent).* In (15) the gate factor is $g(u)^{\\alpha}$ with the measured device "
             "exponent $\\alpha$, 1.10\u20131.63 for the devices of Table III. The model keeps the form but treats "
             "the exponent as a model parameter $p$:", "FirstParagraph")
        + equation("h(x) \\triangleq g(x)^{p} = \\clip\\left(\\frac{x - v_t}{1 - v_t},~0,~1\\right)^{p}", 17)
        + para("The symbol $h$ marks nothing more than that the exponent is no longer the device's. A "
               "full-swing waveform cannot set $p$: the stage input dwells near $g = 1$, where $g^{p} = 1$ for "
               "every $p$, and only the brief passage through intermediate drives depends on it "
               "(Section II-J). In this work $p = 1$ is adopted, so (17) reduces to $h(x) = g(x)$. That is the "
               "approximation: A1 drops the measured exponent and makes the drive current linear in the gate "
               "above threshold, the short-channel limit of [1]. The parameter $p$ is kept in the formula only "
               "so that the exponent can be restored if a measurement supplies it.", "FirstParagraph")
        + para("*A2 (fixed saturation boundary).* In (15) the boundary between the constant-current ramp and "
               "the resistive tail is $x_0 g^{\\alpha/2}$: it equals $x_0$ at full drive and shrinks when the "
               "gate is only partly on. The model replaces it by a constant that does not depend on the gate:",
               "FirstParagraph")
        + equation("r(x) \\triangleq \\min\\left(1,~\\frac{x}{x_{lin}}\\right)", 18)
        + para("For a known device the natural value is the full-drive boundary, $x_{lin} = x_0$, and at "
               "$g = 1$ (18) then coincides with the boundary in (15); the two differ only under partial drive. "
               "The model, however, never knows the device, so the constant is given its own name: $x_{lin}$ "
               "is an effective number, set to 0.45 in this work for the reasons given after Fig. 3, and the "
               "measured $x_0$ of Table III (0.34\u20130.57) is only a check on it.", "FirstParagraph"))
    out["after_eq7"] = (
        para("The device model (2)–(5) was checked against the transistors actually used in the predrivers "
             "of two test buffers, simulated in HSPICE from their model cards at their drawn dimensions. "
             "$V_{TH}$ and $\\alpha$ are extracted as in [1, App. A]: $V_{TH}$ is the value for which the "
             "saturation current is a straight line against $V_{GS} - V_{TH}$ on logarithmic axes, and "
             "$\\alpha$ is the slope of that line. Reference [1] gives no procedure for $V_{D0}$; it is taken "
             "here as the breakpoint that best fits the piecewise form (6) to the output curve at full gate "
             "drive. Fig. 2 shows the result and Table III lists the two normalized parameters. The measured "
             f"$\\alpha$ is {rng['a']}, between the short-channel limit of 1 and the long-channel value of 2 "
             f"[2], and the saturation voltage is {rng['x']} of the supply, comparable to the 0.5–0.55 "
             "used in [1].")
        + pkg.figure(FIG / "fig_device.png",
                     "Fig. 2. HSPICE characteristics of the predriver devices of test buffers ex2 and inv_chain, at "
                     "their drawn dimensions. (a) Output curves at full gate drive, normalized; the legend gives "
                     "the fitted $x_0 = V_{D0}/V_{DD}$. (b) Output curves of one device at five gate drives (solid) against the "
                     "α-power law (2) with the extracted $\\alpha$ and $V_{D0}$ (dashed; dots mark the saturation "
                     "voltage $V'_{D0}$ of (4)). (c) Saturation current against gate drive; the slope is $\\alpha$.")
        + table(["Device", "Model card", "Drawn length", "$V_{DD}$", "$x_0 = V_{D0}/V_{DD}$", "$\\alpha$"],
                dev_rows, [2500, 2000, 1300, 900, 1800, 1100],
                "Table III: Device parameters of (2)–(5) extracted in HSPICE from the predriver transistors"))

    # ---------------- inserted into Section E: the stage law, pictured ---------------
    out["after_eq19"] = (
        pkg.figure(FIG / "fig_stage_law.png",
                   "Fig. 3. The stage law (19). (a) Gate factor $h(u)$ of (17) for three exponents. (b) Drain factor "
                   "of the charging term: the fixed boundary $r(1-v)$ of (18), against the drive-dependent boundary "
                   "of (15) at three gate drives ($\\alpha = 1$, $x_0 = 0.45$); the two coincide at full drive. "
                   "(c) Response of one stage to an input step: a constant-slope ramp while $1-v > x_{lin}$, then an "
                   "exponential approach to the rail.")
        + para("The value used is $x_{lin} = 0.45$. It is a built-in constant of the method, not a quantity read "
               "from the IBIS file. It was chosen during development from fits of (19) to the individual probed "
               "predriver stages of two test buffers, which gave 0.37–0.47 on ex2 and 0.52–0.63 on "
               "inv_chain. Later evidence agrees with it: fitted to the probed gate with $x_{lin}$ free, the chain "
               f"gives 0.41 on ex2 and 0.48 on inv_chain; the measured $x_0$ of Table III is {rng['x']}; and [1] "
               "uses 0.5–0.55. In the pad-level tests of Section II-L it is fixed at 0.45 on ten of the "
               "twelve buffers; on inv_chain and io_buf it was instead fitted to the file together with the other "
               "stage parameters. Section II-J shows why the file constrains it only weakly. The default $p = 1$ is "
               f"likewise a built-in constant; it is the lower limit of the measured $\\alpha$ ({rng['a']}).")
        + para("As a check that (19) is the model of [1] and not merely similar to it, one stage with $p = \\alpha$ "
               "was driven by a linear input ramp and its delay compared with the closed-form delay of [1, eq. (5)]. "
               "The two agree within 4 ps for input ramps of 0.05 to 0.8 ns (stage delays of 0.24 to 0.35 ns), "
               "with the opposing device either present or switched off; they separate only for ramps slower "
               "than the range of validity stated in [1]."))

    return out


# ----------------------------------------------------------------------------- numbering
# Figures and tables are numbered by their position in these lists, so that a cross-reference
# in the text can never drift from the order in which the objects appear. Tables I-III are
# referenced by the kept Sections A-E and stay where they are.
FIGS = ["problem", "device", "stage_law", "blocks", "workflow", "chain", "map", "gate_to_ku", "target",
        "fit_score", "fit_knobs", "fit_search", "one_vs_chain", "ku_fit", "fit_all", "ambiguity", "rms_vs_k",
        "stress_use", "calib_mech", "gate_verify", "gate_internal", "pad_waveforms", "pad_summary"]
TABS = ["notation", "terms", "device", "procedure", "inputs", "map_symbols", "worked", "fit_problem", "fit_all",
        "shapes", "rms_vs_k", "ledger_steps", "ledger_cands", "gate_ex2", "gate_inv", "gate_internal", "pad", "approx"]
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI",
         "XVII", "XVIII", "XIX", "XX"]
SEC = dict(road="F", chain="G", map="H", target="I", fit="J", ident="K", stress="L", ledger="M", verify="N", approx="O")


def F(key: str) -> str:
    return f"Fig. {FIGS.index(key) + 1}"


def T(key: str) -> str:
    return "Table " + ROMAN[TABS.index(key)]


def S(key: str) -> str:
    return f"Section II-{SEC[key]}"


def build_sections(pkg: Package, d) -> list[str]:
    """Sections F to O, Table I, the references and the remarks, as a list of XML fragments."""
    t: list[str] = []
    A = t.append
    fig = lambda key, caption, width_in=6.2: pkg.figure(FIG / f"fig_{key}.png", f"{F(key)}. {caption}", width_in=width_in)  # noqa: E731
    ti, sc, se, ov, fa, cb, lg, land = (d["target_info"], d["score"], d["search"], d["one_vs"], d["fit_all"],
                                        d["calib"], d["ledger"], d["land"])
    hand = ov["hand"]

    # ================================================================ F. road map
    A(heading(f"{SEC['road']}. From the stage law to a buffer model: the road map"))
    A(para("Sections II-A to II-E ended with (19), the law of one predriver stage. A buffer is more than one "
           "stage: $K$ of them in a row, then the output transistor whose gate the last stage drives, then the "
           "die capacitance, the package and the pad. This section lays out the pieces of the complete model, "
           "the order in which their numbers are found, and the example that runs through the rest of "
           "Section II. Each later section then takes one piece.", "FirstParagraph"))
    A(heading("1) The pieces", 3))
    A(para(f"{F('blocks')} shows the signal path. From left to right: a comparator turns the input pin into a "
           "0-or-1 command; $K$ identical stages obeying (19) pass that command along, each adding delay and "
           "rounding the edge, and the output of the last stage is the gate of the output pull-up transistor on "
           "a 0-to-1 scale; a static map $M$ turns the gate level into the conducting fraction $K_u$, and its "
           "complement into $K_d$; and the fractions scale the I–V tables of the file to give the current into "
           "the die node, which $C_{comp}$ and the package turn into the pad voltage. Everything from the "
           "fractions onward is the existing converter's and is unchanged. The proposed method replaces only how "
           "$K_u(t)$ and $K_d(t)$ are generated: by a gate that moves, instead of a table replayed against the "
           "clock.", "FirstParagraph"))
    A(fig("blocks", "Signal path of the model. The blocks added by the proposed method replace the way the "
                    "conducting fractions $K_u(t)$ and $K_d(t)$ are generated; the I–V tables, $C_{comp}$ and the "
                    "package elements are those of the IBIS file and are unchanged. Numbers in parentheses are "
                    "equation numbers.", 6.3))
    A(heading("2) What is known, what is assumed, what is fitted", 3))
    A(para(f"The pieces carry four kinds of numbers ({T('inputs')}). The I–V tables, $C_{{comp}}$, the package and "
           "the full-swing $K_u(t)$, $K_d(t)$ come from the file and are never changed. Two constants of the stage "
           "law, $x_{lin}$ and $p$, and the three candidate shapes of the map are built into the method; their "
           "values were chosen during development with knowledge of the test buffers' transistors, and they are "
           "the method's assumptions. The stage rates $s_{up}$, $s_{dn}$ and a first value of the threshold $v_t$ "
           "are fitted to the file. The stage count $K$, the map shape and the final $v_t$ are settled by one "
           "measurement.", "FirstParagraph"))
    A(table(["Input", "Origin", "Fixed when"],
            [["I–V tables, $C_{comp}$, package elements, full-swing $K_u(t)$ and $K_d(t)$", "the IBIS file", "step 0"],
             ["$x_{lin}$ = 0.45, $p$ = 1, the three candidate map shapes, the band rule (27)",
              "built-in constants, chosen during development on the twelve test buffers with transistor-level "
              "information", "before any buffer is seen"],
             ["$s_{up}$, $s_{dn}$, a first $v_t$", "fitted to the file", "step 1"],
             ["stage count $K$, map shape, final $v_t$", "one stressed pad measurement", "steps 3 and 4"]],
            [4200, 3900, 1500], f"{T('inputs')}: Inputs of the model and their origin"))
    A(para("Applying the method to a new buffer therefore needs no transistor-level information, but the "
           "method is not derived from the IBIS file alone: it uses one measurement, and four built-in constants "
           "whose values were chosen with knowledge of the test buffers' transistors. Whether those constants suit "
           "buffers outside the test set has not been tested.", "FirstParagraph"))
    A(heading("3) The procedure, step by step", 3))
    A(para(f"{F('workflow')} draws the procedure and {T('procedure')} lists it. The steps are numbered 0 to 4, "
           "and that numbering is used throughout.", "FirstParagraph"))
    A(para(f"*Step 0, the target ({S('target')}).* The existing converter solves the file's V–T waveforms for "
           "$K_u(t)$ and $K_d(t)$ over one complete transition. Normalised from the settled off level to the "
           "settled on level, this curve is the target: the only thing the stage law is ever fitted to."))
    A(para(f"*Step 1, the fit ({S('fit')}).* For an assumed stage count and an assumed map shape, the two rates "
           "and the threshold are adjusted until the model's $K_u(t)$, produced by running the chain and reading "
           "its gate through the map, lies on the target. The fit is repeated for every candidate stage count "
           "and shape."))
    A(para(f"*Step 2, the candidates ({S('ident')}).* The fit cannot choose the stage count or the map shape: "
           "several of each reproduce the file equally well. The three stage counts whose residual is within "
           "25 % of the best are kept, and with the three map shapes they make nine candidate models."))
    A(para(f"*Step 3, calibration ({S('stress')}).* One pad waveform is measured for an input pulse too short to "
           "complete. For each candidate the threshold is bisected until the model's pad peak equals the "
           "measured one."))
    A(para(f"*Step 4, selection ({S('stress')}).* The candidate whose whole pad waveform is closest to the "
           f"measured one is kept. {S('ledger')} walks ex2 through all five steps with its numbers, and "
           f"{S('verify')} verifies the result at the gate and at the pad on twelve buffers."))
    A(fig("workflow", "The procedure as a flow. Grey: taken from the IBIS file. Orange: assumed, built into the "
                      "method. Teal: fitted or computed. Red: the one measurement. Numbers in parentheses are "
                      "equation numbers.", 6.3))
    A(table(["Step", "What is determined", "Data used", "Eq."],
            [["0", "I–V tables, $C_{comp}$, full-swing $K_u(t)$ and $K_d(t)$; the normalised target", "IBIS file, existing converter", "(24), (25)"],
             ["1", "$s_{up}$, $s_{dn}$ and an initial $v_t$, for each candidate stage count and map shape",
              "full-swing $K_u(t)$ of the file", "(26)"],
             ["2", "Candidate set: three stage counts × three map shapes", "fit residuals of step 1", "(27)"],
             ["3", "$v_t$, for each candidate", "peak of one stressed pad waveform", "(28)"],
             ["4", "Stage count $K$ and map shape", "the same stressed pad waveform, whole shape", "(29)"]],
            [700, 4300, 3300, 1300],
            f"{T('procedure')}: The procedure. $p = 1$ is fixed; $x_{{lin}} = 0.45$ is fixed on ten of the twelve test "
            "buffers and fitted in step 1 on the other two."))
    A(heading("4) The running example", 3))
    A(para("ex2 is the running example: a 3.3 V buffer with a three-inverter predriver, whose transistor netlist "
           "is available so that every internal quantity can be checked. Two settings of it appear. The figures "
           f"that explain the chain, the map and the fit ({F('chain')} to {F('ambiguity')}) use the map shape and "
           "$C_{comp}$ measured on its netlist, (0.57, 0.64) and 1.7 pF, so that the model's gate can be compared "
           f"with the probed gate. The procedure itself, in Sections II-{SEC['stress']} to II-{SEC['verify']}, uses "
           f"only what the file and one measurement provide: $C_{{comp}}$ estimated from the file ({lg['cc_knee']} pF, "
           f"{S('ledger')}) and the three candidate shapes. The two settings give different fitted numbers for the "
           "same buffer, and the text says which is in use.", "FirstParagraph"))

    # ================================================================ G. the chain
    A(heading(f"{SEC['chain']}. The chain: from the input pin to the output gate"))
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
    A(para("*In words.* A stage is a bucket. It fills at the rate $s_{up}$ once the bucket before it is more than "
           "$v_t$ full, and drains at the rate $s_{dn}$ once that bucket has emptied below $1 - v_t$; within "
           "$x_{lin}$ of the rim or of the floor the flow tapers off, as the resistive tail of (19) prescribes. A "
           "step at the input starts filling the first bucket at once; the second waits until the first passes "
           "$v_t$, and the third waits for the second. The delay of the chain is spent in these handovers, and the "
           f"shape of its last edge is set by the rate. {F('one_vs_chain')}(b) shows the three fitted stages of "
           f"ex2: the handovers come at {hand[0]:.2f} and {hand[1]:.2f} ns, the gate reaches the map's threshold "
           f"at {hand[2]:.2f} ns, and the file's own $K_u(t)$ leaves zero at {ov['file_start']:.2f} ns."))
    A(para(f"{F('chain')} shows what the chain does. For a full transition every stage completes its swing and the "
           "chain contributes only a delay and an edge shape. For a pulse shorter than the chain's own delay, the "
           "input reverses while the later stages are still rising: each stage turns back before reaching its "
           f"rail, and the gate reaches only part of its swing (0.74 in {F('chain')}(b)). Because a stage delivers "
           "no current until its input passes $v_t$, a pulse loses amplitude at every stage and, once its peak "
           "falls below $v_t$, it is not passed on at all. This is why the stage count is a first-order parameter "
           "of the model rather than a refinement. The abrupt cutoff is a property of the hard threshold in (17); "
           "in a transistor chain the loss is gradual."))
    A(fig("chain", "One chain, two inputs (ex2: $K = 3$, $s_{up} = 2.19$/ns, $s_{dn} = 2.12$/ns, $v_t = 0.487$, "
                   "$x_{lin} = 0.45$). Top: the stage nodes of (19)–(21). Bottom: the conducting fraction obtained "
                   "from the gate through the map (22), normalized. (a) Full transition. (b) An 810 ps input pulse: "
                   "the gate turns back at 0.74 of its swing and $K_u$ reaches 0.56.", 6.0))
    A(para(f"For the fits of Sections II-{SEC['fit']} and II-{SEC['verify']}, (19)–(21) are integrated with Heun's "
           "method (second-order Runge–Kutta) at 1 ps steps, each state limited to $[-0.05, 1.05]$. Explicit Euler "
           "at 2 ps was found to be inadequate for the fastest stages (time constants near 20 ps): it passed a "
           "119 ps pulse that the same chain extinguished in ngspice, whereas Heun agrees with ngspice. In the "
           "circuit model each stage is a behavioral current source charging an explicit capacitor $C_g$, so that "
           "$v_k$ is a circuit node:"))
    A(equation("C_g \\frac{dv_k}{dt} = C_g \\cdot 10^{9} \\left[ s_{up}~h(v_{k-1})~r(1 - v_k) - s_{dn}~h(1 - v_{k-1})~r(v_k) \\right]"))
    A(para("with the rates in swings per nanosecond; $C_g$ cancels and its value is immaterial.", "FirstParagraph"))

    # ================================================================ H. the map
    A(heading(f"{SEC['map']}. The map: from the gate to the conducting fraction and the pad"))
    A(para("The stage law produces the gate trajectory $G_{UP}(t)$ and nothing else; it makes no statement about "
           "the output current. An IBIS-based driver model, on the other hand, needs at each instant the fraction "
           "$K_u$ of the pull-up I–V table that is conducting, and the fraction $K_d$ of the pull-down table. "
           "A second relation, separate from the stage law, connects the two. It is called the map here.",
           "FirstParagraph"))
    A(heading("1) What the map is", 3))
    A(para("The pull-up table of the file is the current of the output transistor against pad voltage with its "
           "gate fully on. With the gate only partly on, the transistor delivers less, and the reduction is taken "
           "to be one multiplier at every pad voltage, which is the assumption any $K_u$-based IBIS model already "
           "makes:", "FirstParagraph"))
    A(equation("I(V_{pad}, g) = K_u(g)~I_{PU}(V_{pad})"))
    A(para("Here $g$ is the gate of the output transistor on a scale from 0 (device off) to 1 (device fully on); "
           "in the model, $g = G_{UP}$, the output of the last stage. The map is the function $K_u(g)$: how much "
           "of the table conducts when the gate is at level $g$. It is a curve against the gate, not against time.",
           "FirstParagraph"))
    A(para("Where the gate node can be probed, this curve can be measured, and no formula is needed. At each "
           f"instant of a full transition the gate level and the file's $K_u$ are read together ({F('map')}(a)); "
           f"plotting one against the other gives $K_u$ as a function of the gate ({F('map')}(b)). On the three "
           "buffers where this was done the curve traced while the gate rises coincides with the one traced "
           "while it falls, within 0.07–0.11, so $K_u$ does depend on the gate alone, without memory."))
    A(fig("map", "The map. (a) With the gate node of ex2 probed, the gate level (squares) and the file's "
                 "$K_u$ (circles) are read at the same instants of a full transition. (b) Plotting $K_u$ against "
                 "the gate gives the measured map; the dashed line is the formula (22) fitted to it, with "
                 "$(v_{t,map}, a) = (0.57, 0.64)$. (c) The three shapes offered by the method when the gate cannot "
                 "be probed, with the measured map of ex2 for reference.", 6.4))
    A(heading("2) The formula", 3))
    A(para("The measured curve is described by a formula with two shape parameters, scaled between the settled "
           "off and on levels of the file's own $K_u$ and $K_d$:", "FirstParagraph"))
    A(equation("K_u(t) = k_{off} + (k_{on} - k_{off})~M(G_{UP}(t)),\\quad M(g) \\triangleq \\clip\\left( \\frac{g - v_{t,map}}{g_s - v_{t,map}}, 0, 1 \\right)^{a}", 22))
    A(equation("K_d(t) = d_{off} + (d_{on} - d_{off})~M(G_{DN}(t))", 23))
    A(table(["Symbol", "Meaning", "Values"],
            [["$g$", "Gate of the output transistor, 0 (off) to 1 (fully on); the output of the last stage", "a waveform"],
             ["$v_{t,map}$", "Gate level at which $M$ leaves zero", "0.4 or 0.5 in the candidates; 0.49–0.57 measured"],
             ["$a$", "Exponent that bends the curve: 1 is a straight line, below 1 rises steeply and then flattens",
              "0.6, 0.7 or 0.9 in the candidates; 0.60–0.78 measured"],
             ["$g_s$", "Gate level at which $M$ reaches 1", "1 in all results reported here"],
             ["$k_{off}, k_{on}, d_{off}, d_{on}$", "Settled levels of the file's $K_u$ and $K_d$", "close to 0 and 1"]],
            [2300, 4600, 2700], f"{T('map_symbols')}: The symbols of the map (22)–(23)"))
    A(para("Read from the inside out, $M$ does three things. Subtracting $v_{t,map}$ sets where the curve starts: "
           "below that gate level nothing conducts. Dividing by $g_s - v_{t,map}$ rescales the remainder so that "
           "it runs from 0 at the start to 1 at $g = g_s$; the clip keeps it there. The exponent $a$ bends the "
           "curve between those two ends. With $g_s = 1$ two numbers therefore fix the whole curve.",
           "FirstParagraph"))
    A(para("The form is borrowed from the gate factor (5) of a transistor, a threshold followed by a power of the "
           "drive, because the map describes how the output transistor turns on. Its parameters are nevertheless "
           "empirical. Fitted to the measured maps they are (0.57, 0.64) on ex2, (0.49, 0.60) on inv_chain and "
           "(0.50, 0.78) on io_buf; they are not identified with the threshold voltage or the index $\\alpha$ of "
           "the output device, and no derivation of their values is offered. They are also distinct from the "
           "stage parameters $v_t$ and $p$ of (17), which describe the predriver. The formula follows the main "
           "rise of the measured map of ex2 within about 0.06 and does not reproduce its slow foot between "
           f"$g = 0.4$ and $0.57$ ({F('map')}(b))."))
    A(heading("3) Why the file does not contain the map", 3))
    A(para("The file gives $K_u$ against time. The map is $K_u$ against the gate. Converting one into the other "
           f"requires the gate against time, as in {F('map')}(a), and that is the one waveform an IBIS file does not "
           "have. The shape of the file's $K_u(t)$ is the shape of the map stretched by how fast the gate moved, "
           "and the two cannot be separated without the gate.", "FirstParagraph"))
    A(para("The method therefore does not obtain the map from the file. It offers three fixed shapes "
           f"({F('map')}(c)) and leaves the choice among them to the stressed measurement ({S('stress')}). The three "
           f"are built-in constants ({T('inputs')}): (0.50, 0.70) lies near the middle of the three measured maps; "
           "(0.40, 0.60) and (0.40, 0.90) were retained from an earlier search scored on the same twelve test "
           "buffers. Their generality is untested, and this is the least well founded element of the method."))
    A(heading("4) From the gate waveform to the conducting fraction", 3))
    A(para("With a map chosen, the model's $K_u(t)$ is obtained by evaluating the two relations one after the "
           f"other: (19)–(21) give $G_{{UP}}(t)$, and (22) is applied to each of its values. {T('worked')} does this "
           f"for a single stage after an input step; {F('gate_to_ku')} does it for the fitted three-stage chain of ex2.",
           "FirstParagraph"))
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
            f"{T('worked')}: Worked example: one stage ($s_{{up}} = 2$ per ns, $x_{{lin}} = 0.45$) read through the map "
            "($v_{t,map} = 0.57$, $a = 0.64$)"))
    A(para("The gate rises as a ramp of 2 per ns until it is within $x_{lin}$ of its rail and then approaches it "
           "exponentially. Nothing conducts until the gate passes 0.57, 0.29 ns after the step; the conducting "
           "fraction then rises quickly, because the map is steep just above its threshold.", "FirstParagraph"))
    A(fig("gate_to_ku", "Construction of the conducting fraction on ex2 ($K = 3$, map shape (0.57, 0.64)). Left: the "
                        "gate trajectory given by the stage law. Middle: the map (22); the dots are the gate values of the "
                        "left panel at six instants. Right: the resulting $K_u(t)$, normalized, with the same instants "
                        "marked. (a)–(c) Full transition, with the parameters of the fit (26); in (c) the model is "
                        f"compared with the $K_u(t)$ of the IBIS file, and this comparison is the fit of {S('fit')}. "
                        "(d)–(f) An 810 ps input pulse, after calibration: the gate turns back at 0.74, the map is read "
                        "only up to that level, and $K_u$ reaches 0.56.", 6.3))
    A(para(f"The top row of {F('gate_to_ku')} is the situation the file records. The gate sweeps its full range, the "
           "whole map is read, and the result in (c) can be compared with the file. The bottom row is the situation "
           "the file does not record. The input is cut short, the gate turns back before reaching its rail, and "
           "only the lower part of the map is read. The conducting fraction in (f) rises to 0.56 and returns to "
           "zero: a waveform that no table of the file contains, produced by the same two relations with no "
           "additional parameter."))
    A(heading("5) From the conducting fraction to the pad", 3))
    A(para("The current delivered to the die node is that of the existing converter:", "FirstParagraph"))
    A(equation("I_{die}(t) = K_u(t)~I_{PU}(V_{die}) + K_d(t)~I_{PD}(V_{die}) + I_{PC}(V_{die}) + I_{GC}(V_{die})", 24))
    A(para("where $I_{PU}$ and $I_{PD}$ are the pull-up and pull-down I–V tables of the file, held at their end "
           "values outside the tabulated range, and $I_{PC}$, $I_{GC}$ are the power- and ground-clamp tables, "
           "present only when the file contains them (io_buf does; ex2 and inv_chain do not). $C_{comp}$ loads the "
           "die node and the package $R$, $L$, $C$ of the file connect it to the pad. Equation (24) was checked "
           "against the generated subcircuits and is unchanged by the proposed method, which replaces only the "
           "source of $K_u(t)$ and $K_d(t)$; the converter's short first-order lag on the fractions (5 ps) and its "
           "residual correction term are also retained as they are.", "FirstParagraph"))

    # ================================================================ I. the target
    A(heading(f"{SEC['target']}. Step 0: the target, the file's own $K_u(t)$"))
    A(para("The fit of the next section needs a curve to fit to, and nothing else in the method is fitted to "
           "anything. That curve is the file's own conducting fraction through one complete transition. This "
           f"section shows where it comes from, on ex2 ({F('target')}).", "FirstParagraph"))
    A(para(f"*What the file holds.* ex2's file tabulates the pull-up and the pull-down current at {ti['n_iv']} pad "
           f"voltages each ({F('target')}(a)), and the pad voltage against time for a rising and for a falling "
           f"transition into two fixtures, {ti['rfix']:.0f} Ω to {ti['vfix'][0]:g} V and {ti['rfix']:.0f} Ω to "
           f"{ti['vfix'][1]:g} V, {ti['n_vt']} samples over {ti['t_vt']:.0f} ns each ({F('target')}(b)). The two "
           "fixtures are the point: the same transition recorded into two different loads."))
    A(para("*How the converter solves for the two fractions.* At each instant of the rising transition the current "
           "into the die node must balance in both fixtures. With the pull-up table scaled by $K_u$ and the "
           "pull-down table by $K_d$, and $V_i(t)$ the pad voltage recorded in fixture $i$,"))
    A(equation("K_u(t)~I_{PU}(V_i(t)) + K_d(t)~I_{PD}(V_i(t)) = \\frac{V_{fix,i} - V_i(t)}{R_{fix}} - C_{comp}\\frac{dV_i}{dt},\\quad i = 1, 2"))
    A(para("(the clamp currents join the right-hand side when the file has them). Two equations, two unknowns: the "
           "converter solves the pair at every sample and obtains $K_u(t)$ and $K_d(t)$ for the rising transition, "
           f"and in the same way for the falling one ({F('target')}(c)). This is the standard two-waveform "
           "solution; it is not part of the proposed method, which takes its result as given. Note what the "
           "solution contains: $K_u$ against time, for the one transition the file recorded, including the "
           "buffer's own delay.", "FirstParagraph"))
    A(para("*From the solution to the target.* The existing converter builds its circuit model so that, driven "
           "through one complete transition, it reproduces this solution; the model's internal node that carries "
           "the table value, before the converter's small residual correction, follows the solved $K_u(t)$ within "
           f"{ti['rms_r']:.3f} rms on ex2 once the two are aligned on the input edge ({F('target')}(c)). The target "
           "is that node, recorded in an ngspice run of the existing model through one 10 ns input pulse and "
           "normalised between its settled off level at $t_{rest}$ and its settled on level at $t_{on}$:"))
    A(equation("\\hat{K}_u(t) = \\clip\\left( \\frac{K_u(t) - K_u(t_{rest})}{K_u(t_{on}) - K_u(t_{rest})}, 0, 1 \\right),\\quad t_{rest} = 4.5~\\text{ns},~t_{on} = 12~\\text{ns}", 25))
    A(para(f"(the input edge is at 5 ns). {F('target')}(d) shows the result, sampled every 2 ps from 4 to 21 ns, "
           "together with the input that the model's chain receives during the fit: an ideal 10 ns pulse starting "
           "at the mid-point of the input edge, (20). Its rising edge constrains $s_{up}$ and its falling edge "
           "$s_{dn}$. Nothing in this curve says how many stages produced it or where their thresholds lie; that "
           f"is the subject of {S('ident')}.", "FirstParagraph"))
    A(fig("target", "The target, on ex2 (file-only run at the measured $C_{comp}$ of 1.7 pF). (a) The I–V tables of "
                    "the file. (b) Its V–T waveforms: one rising and one falling transition, each recorded into two "
                    "fixtures. (c) $K_u(t)$ and $K_d(t)$ solved from (b) by the existing converter (grey), and the "
                    "conducting fractions of the existing circuit model through a 10 ns input pulse (colour); the "
                    "solution is aligned on the input edge. (d) The normalised target (25) and the chain input (20) "
                    "used in the fit.", 6.3))

    # ================================================================ J. the fit
    A(heading(f"{SEC['fit']}. Step 1: fitting the stage law through an assumed map"))
    A(para("This is the step that gives the stage law its numbers, and it deserves to be seen slowly. The question, "
           "the score, what each number does, how the minimum is found, why several stages are needed, and what "
           "the fit leaves open are taken in turn, on ex2 with its measured map shape and $C_{comp}$ "
           f"({S('road')}.4).", "FirstParagraph"))
    A(heading("1) The question", 3))
    A(para(f"{T('fit_problem')} sorts the quantities of the model by their status in this step. Three numbers are "
           "unknown; everything else is given by the file, assumed for the candidate, or built in. The order "
           f"matters: the map is assumed first and its two numbers frozen ({S('map')}.3), and only then are the "
           "stage numbers adjusted. The map is an input to the fit, not a result of it.", "FirstParagraph"))
    A(table(["Quantity", "Status in step 1", "In the ex2 example"],
            [["target $\\hat{K}_u(t)$", f"given: the file, through the existing converter ({S('target')})", f"{F('target')}(d)"],
             ["map shape $(v_{t,map}, a)$", "assumed for the candidate; three shapes offered",
              "(0.57, 0.64) here; (0.5, 0.7), (0.4, 0.6), (0.4, 0.9) in the procedure"],
             ["stage count $K$", "assumed for the candidate; three counts from the band (27)", "3 here; 3, 4, 5 in the procedure"],
             ["$x_{lin}$, $p$", "built in", "0.45, 1"],
             ["$s_{up}$, $s_{dn}$", "fitted", f"{d['one_vs']['k3']['s_up'][:4]} and {d['one_vs']['k3']['s_dn'][:4]} per ns"],
             ["$v_t$", f"fitted here; replaced by the calibration of step 3 ({S('stress')})", f"{float(d['one_vs']['k3']['vt']):.3f} here; 0.487 after calibration"]],
            [2300, 3900, 3400], f"{T('fit_problem')}: The quantities of the model and their status in step 1"))
    A(para("For a given stage count $K$ and the assumed map shape, the stage parameters minimize the "
           "root-mean-square mismatch between the model's conducting fraction and the target:", "FirstParagraph"))
    A(equation("\\{ s_{up}, s_{dn}, v_t \\}^{\\star} = \\arg \\min~\\rms_t \\left[ M(v_K(t)) - \\hat{K}_u^{file}(t) \\right],\\quad x_{lin},~p~\\text{fixed}", 26))
    A(para("with $0 \\le v_t \\le 0.7$, over 4–21 ns sampled every 2 ps. For a buffer with a separate pull-down "
           "path, the pull-down chain is fitted in the same way to $K_d(t)$ through its own map; fitting it through "
           "the $K_u$ target leaves its onset unconstrained, because that target is zero wherever $K_d$ turns on "
           "(an onset 250 ps early was observed on an open-drain test buffer).", "FirstParagraph"))
    A(heading("2) The score: what the residual measures", 3))
    _trial = next(k for k in sc if k.startswith("a trial"))
    _thefit = next(k for k in sc if k.startswith("the fit"))
    A(para("For a trial set of the three numbers, the model's $K_u(t)$ is produced exactly as in "
           f"{F('gate_to_ku')}: the chain is run from the 10 ns input pulse, and the gate is read through the map "
           "at every sample. At each of the 8500 samples the model is subtracted from the target; the differences "
           "are squared, averaged, and the square root is taken. That one number is the residual of (26). "
           f"{F('fit_score')} shows it for a poor trial and for the fit: the shaded gap in (a) and (b) is what is "
           "being measured, and (c) shows the difference over the whole window. The residual is small only when "
           "the gap is small everywhere. Because the target is flat at 0 or 1 for almost all of the 17 ns, the "
           "residual is in practice accumulated within the two edges, each about 0.7 ns wide on ex2: a residual of "
           f"{sc[_thefit]:.3f} means that, averaged over the window, the model is {100 * sc[_thefit]:.1f} % of the "
           "full swing away from the file, and most of that is a small timing and shape difference at the edges.",
           "FirstParagraph"))
    A(fig("fit_score", "What the residual of (26) measures, on ex2 ($K = 3$, map shape (0.57, 0.64), "
                       f"$x_{{lin}} = 0.45$). (a) A poor trial: the shaded gap between the model and the file gives a "
                       f"residual of {sc[_trial]:.3f}. (b) The fit: residual {sc[_thefit]:.3f}. (c) The difference "
                       "model − file over the whole fit window for both; the residual is its root-mean-square, and "
                       "it lives at the two edges."))
    A(heading("3) What each number does", 3))
    A(para(f"{F('fit_knobs')}(a)–(c) varies one fitted number at a time around the fitted values. $s_{{up}}$ is "
           "the charging rate of every stage: a larger value brings the rising edge earlier and makes it steeper, "
           "a smaller one delays and flattens it. $s_{dn}$ does the same for the falling edge. $v_t$ is the level "
           "a stage's input must reach before the stage starts: at fixed rates it moves the edge later or earlier "
           "without changing its steepness, because the delay between stages is the time each stage's output "
           "takes to reach $v_t$. The three numbers therefore have distinct, visible jobs: two slopes and one "
           "delay.", "FirstParagraph"))
    _k = d["knobs"]
    A(para(f"{F('fit_knobs')}(d) builds a fit one number at a time from a poor first guess, which the real search "
           f"does not do but which shows what each number buys: from a first guess (residual "
           f"{_k['first guess']:.3f}) adjusting $s_{{up}}$ fixes the rising edge ({_k['$s_{up}$ adjusted']:.3f}), "
           f"adjusting $s_{{dn}}$ fixes the falling edge ({_k['$s_{dn}$ adjusted']:.3f}), and adjusting $v_t$ "
           f"places the edges in time ({_k['$v_t$ adjusted: the fit']:.3f})."))
    A(fig("fit_knobs", "The fit (26) seen as three knobs, on ex2 ($K = 3$, map shape (0.57, 0.64), "
                       "$x_{lin} = 0.45$). (a)–(c) The model's $K_u(t)$ as $s_{up}$, $s_{dn}$ and $v_t$ are varied "
                       "one at a time around the fitted values, against the file's $K_u(t)$; (b) shows the falling edge "
                       "at 10 ns. (d) A fit built one number at a time from a poor first guess; the real minimization "
                       "moves all three together."))
    A(heading("4) How the minimum is found", 3))
    A(para("The three numbers are found by Nelder–Mead minimization, chosen because the residual is not "
           "differentiable: the chain is a simulation with thresholds and clips. The method keeps a simplex of "
           "four trial points in the three-dimensional parameter space. At each iteration it evaluates the "
           "residual at the point reflected through the far side of the simplex from its worst corner; if that is "
           "better than the best corner it tries a further step in the same direction, if it is worse than the "
           "second-worst corner it tries a point halfway back, and if nothing helps it shrinks the whole simplex "
           "towards its best corner. The simplex therefore walks downhill and contracts around a minimum. The "
           "rates are searched on a logarithmic scale, so that 1 and 30 per ns are equally reachable; $v_t$ is "
           "searched linearly and confined to $[0, 0.7]$ by returning a large residual outside it. The search "
           "stops when the simplex has collapsed (corners within 0.001 of each other and residuals within "
           "0.00001) or after 800 iterations. It is run from three starting points, $s_{up} = s_{dn} = 2$, 8 and "
           "30 per ns with $v_t = 0.4$, and the best end point is kept.", "FirstParagraph"))
    A(para(f"{F('fit_search')} shows the search on ex2. Panels (a) and (b) are the residual over two planes "
           "through the fitted point. The valley is narrow in the rates: at the fitted $v_t$, a change of 27 % in "
           f"$s_{{up}}$ in either direction triples the residual. Along $v_t$ it is shallow on the low side, "
           f"{land['z0']:.3f} at $v_t = 0$ falling gently to {land['zmin']:.3f} at {land['vt_min']:.2f}, and steep "
           f"above, {land['z07']:.3f} at the 0.7 bound. The three runs (c) took {se[2]['n']}, {se[8]['n']} and "
           f"{se[30]['n']} evaluations of (26), each a 17 ns chain simulation, before their simplex collapsed. "
           f"Only the run from 2 per ns reached the minimum ({se[2]['end'][3]:.4f}); the run from 8 per ns stopped "
           f"at {se[8]['end'][3]:.3f} with $v_t$ on its bound, and the run from 30 per ns at {se[30]['end'][3]:.2f} "
           f"with $s_{{dn}}$ at {se[30]['end'][1]:.0f} per ns, both in side valleys of the landscape. The search "
           "is local, and this is why one start is not enough."))
    A(fig("fit_search", "The search, on ex2 ($K = 3$, map shape (0.57, 0.64), $x_{lin} = 0.45$). (a) The residual "
                        "of (26) over $s_{up}$ and $v_t$ at the fitted $s_{dn}$, and (b) over $s_{up}$ and $s_{dn}$ at "
                        "the fitted $v_t$; darker is lower. Squares: the three starting points; stars: where each run "
                        "ended; the red circle: the fit. The paths are the best point found so far, projected onto "
                        "each plane. (c) The best residual against the number of evaluations for the three runs."))
    A(heading("5) Why several stages", 3))
    _k1, _k3 = ov["k1"], ov["k3"]
    A(para("With a single stage, one number sets both the delay and the edge: $K_u$ starts when the gate passes "
           "$v_{t,map}$, at about $v_{t,map}/s_{up}$ after the input, and the edge takes about "
           f"$(1 - v_{{t,map}})/s_{{up}}$. On ex2 the file's $K_u(t)$ starts {ov['file_start']:.1f} ns after the input "
           "edge and rises in 0.66 ns, which no single value of $s_{up}$ can give: the best one-stage fit "
           f"({F('one_vs_chain')}(a)) is early and slow, with a residual of {float(_k1['rms']):.3f} against "
           f"{float(_k3['rms']):.3f} for three stages. With several identical stages the delay is spent in the "
           f"handovers ({F('one_vs_chain')}(b)) and the edge belongs to the last stage, so delay and edge are set "
           "separately. This is the reason for the chain, and it is also why the stage count cannot be read from "
           f"the fit: beyond the minimum number, more stages redistribute the same delay ({S('ident')}).",
           "FirstParagraph"))
    A(fig("one_vs_chain", "Why a chain, on ex2. (a) The file's $K_u(t)$ against the best single-stage fit "
                          f"($s_{{up}}$ = {float(_k1['s_up']):.2f}/ns, $v_t$ = {float(_k1['vt']):.2f}) and the best "
                          f"three-stage fit ($s_{{up}}$ = {float(_k3['s_up']):.2f}/ns, $v_t$ = {float(_k3['vt']):.3f}). "
                          "(b) The three stage outputs of the fitted chain: each stage starts when the one before it "
                          "passes $v_t$ (dashed), and $K_u$ leaves zero when the gate passes $v_{t,map}$ (dotted); the "
                          "times are marked.", 6.0))
    A(heading("6) The result", 3))
    A(para(f"On ex2 with $K = 3$, map shape (0.57, 0.64) and $x_{{lin}} = 0.45$, (26) gives "
           f"$s_{{up}} = {float(_k3['s_up']):.3f}$/ns, $s_{{dn}} = {float(_k3['s_dn']):.3f}$/ns and "
           f"$v_t = {float(_k3['vt']):.3f}$ at a residual of {float(_k3['rms']):.3f} ({F('ku_fit')}(a)); on "
           f"inv_chain with $K = 7$ and its measured shape (0.49, 0.60) the residual is 0.008 ({F('ku_fit')}(b)). "
           "Three numbers are fitted, to a curve that the file already contains; no stressed data is used in "
           "this step. The figure also shows the one curve the file does not contain and the fit produces as a "
           "by-product: the gate trajectory.", "FirstParagraph"))
    A(fig("ku_fit", "Result of the fit (26) with $x_{lin} = 0.45$: the file's normalized $K_u(t)$, the fitted "
                    "model, and the model's gate trajectory, which the file does not contain. (a) ex2, $K = 3$, map "
                    "shape (0.57, 0.64). (b) inv_chain, $K = 7$, map shape (0.49, 0.60).", 6.0))
    _bound = [r for r in fa if r["vt_fit"] > 0.699]
    _rmss = [r["rms"] for r in fa]
    A(para(f"{F('fit_all')} and {T('fit_all')} give the same fit on all twelve test buffers, now with the "
           f"file-only settings of the procedure: $C_{{comp}}$ estimated from the file, and the stage count and "
           f"map shape that the procedure finally selected ({S('verify')}). The residuals are "
           f"{min(_rmss):.3f}–{max(_rmss):.3f}, and on every buffer the model's $K_u(t)$ lies on the file's. Two "
           f"things in the table deserve notice. First, on {len(_bound)} of the twelve buffers the fitted $v_t$ "
           "sits on its upper bound of 0.7: with these map shapes the fit would place the handovers even later "
           "than the bound allows, and the calibration of step 3 then lowers $v_t$ on all eleven buffers calibrated through the threshold (last column). "
           f"This is the non-identifiability of the threshold, seen from the other side ({S('ident')}): the file "
           "pushes $v_t$ to wherever the assumed map lets the composition match, and the measurement puts it "
           "where the short pulse says. Second, io_buf's single-stage chain could not reach the measured peak by "
           "its threshold alone and was calibrated through the rate scale instead (28)."))
    _fa_rows = []
    for r in fa:
        cal = f"{r['vt_cal']:.3f}" if abs(r["rate_scale"] - 1) < 1e-3 else f"rates × {r['rate_scale']:.2f}"
        _fa_rows.append([r["dev"], f"{r['cc']:g}", str(r["K"]), f"({r['shape'][0]:g}, {r['shape'][1]:g})",
                         f"{r['s_up']:.2f}", f"{r['s_dn']:.2f}", f"{r['vt_fit']:.3f}", f"{r['rms']:.4f}", cal])
    A(table(["Buffer", "$C_{comp}$ (pF)", "$K$", "Map shape", "$s_{up}$ (/ns)", "$s_{dn}$ (/ns)", "$v_t$ fitted",
             "Residual", "$v_t$ calibrated"], _fa_rows, [1500, 1000, 600, 1200, 1050, 1050, 1000, 1000, 1200],
            f"{T('fit_all')}: The fit (26) on the twelve test buffers with the file-only settings, for the stage "
            "count and map shape the procedure selected; $x_{lin}$ = 0.45 except "
            + " and ".join(f"{r['dev']} ({r['x_lin']:.2f})" for r in fa if abs(r["x_lin"] - 0.45) > 1e-6)
            + ", where it was fitted. The last column is the threshold after step 3.", size=16))
    A(fig("fit_all", "The fit (26) on the twelve test buffers with the file-only settings, rising edge: the file's "
                     "normalized $K_u(t)$ and the model's, for the candidate the procedure selected. The residual in "
                     "each title is over the whole fit window.", 6.3))
    A(heading("7) The fit succeeds whichever map is assumed", 3))
    A(para("A good fit does not show that the assumed map was right. If the map is made to start earlier, the "
           "fit delays the gate to compensate, and the composition $M(G_{UP}(t))$ still lands on the file's curve. "
           f"{T('shapes')} gives the residual of (26) on ex2 and inv_chain for six different shapes.", "FirstParagraph"))
    _hdr = ["Map shape $(v_{t,map}, a)$"] + [f"({v:g}, {a_:g})" for v, a_ in d["shape_order"]]
    _tr = []
    for _dev in ("ex2", "inv_chain"):
        _tr.append([_dev] + [f"{d['shapes'][(_dev, v, a_)]['rms']:.4f}" for v, a_ in d["shape_order"]])
    A(table(_hdr, _tr, [2400] + [1200] * 6,
            f"{T('shapes')}: Residual of the fit (26) for six assumed map shapes ($x_{{lin}} = 0.45$; $K = 3$ for ex2, 7 for inv_chain)"))
    _e = [d["shapes"][("ex2", v, a_)]["rms"] for v, a_ in d["shape_order"]]
    _i = [d["shapes"][("inv_chain", v, a_)]["rms"] for v, a_ in d["shape_order"]]
    A(para(f"The residual varies by {100 * (max(_e) / min(_e) - 1):.0f} % on ex2 and "
           f"{100 * (max(_i) / min(_i) - 1):.0f} % on inv_chain across the six shapes, and its small preference "
           "does not point at the measured map: on ex2 the shape nearest the measured one, (0.6, 0.6), has the "
           "largest residual. The file cannot choose the map.", "FirstParagraph"))
    _la, _ea = d["shapes"][("ex2", 0.6, 0.6)], d["shapes"][("ex2", 0.4, 0.6)]
    A(fig("ambiguity", "Two assumed maps on ex2 ($K = 3$), each with the stage law fitted through it to the same "
                       "file. (a) The two maps. (b) The gate trajectory the fit produces for each: the earlier map is "
                       "paired with a later gate. (c) Full transition: both reproduce the file's $K_u(t)$. (d) The same "
                       "two models driven by an 810 ps pulse, before any calibration: one passes the pulse, the other "
                       "extinguishes it."))
    A(para(f"{F('ambiguity')} shows what this means. Through the later-starting map (0.6, 0.6) the fit gives "
           f"$v_t = {_la['vt']:.3f}$; through the earlier-starting map (0.4, 0.6) it gives $v_t = {_ea['vt']:.3f}$, "
           "a gate that leaves later. For a full transition the two models are indistinguishable (residuals "
           f"{_la['rms']:.4f} and {_ea['rms']:.4f}). Driven by an 810 ps pulse they are not: the first delivers a "
           "conducting fraction of 0.51, the second none at all, because its higher stage threshold extinguishes "
           "the pulse inside the chain. Two models that the file cannot tell apart give opposite answers for the "
           f"short pulse. This is why a measurement of a short pulse is required, and {S('ident')} shows that the "
           "same holds for the stage count and the other parameters that act only under partial drive."))
    A(heading("8) What the fit decides and what it leaves open", 3))
    A(para("The fit fixes the two rates and, for the assumed map and stage count, a threshold. It does not decide "
           "the map, the stage count or, as the next section shows, even the threshold in any absolute sense: "
           "each of those can be changed and compensated by the others without the file noticing.",
           "FirstParagraph"))

    # ================================================================ K. identifiability
    ex, iv = d["ku"][("ex2", "linear_const")], d["ku"][("inv_chain", "linear_const")]
    A(heading(f"{SEC['ident']}. What the file cannot determine"))
    A(para("In plain terms: a complete transition is two edges. Two edges fix two rates and one delay, and the "
           "fit has exactly those three numbers to spend. Anything that acts only when a transition is cut "
           "short, how many stages share the delay, where each hands over, how the output transistor turns on in "
           "between, leaves no mark on a complete transition and cannot be read from it. This section shows that "
           "in numbers.", "FirstParagraph"))
    A(para(f"The fit (26) determines the rates well and the structure poorly. {T('rms_vs_k')} and {F('rms_vs_k')} "
           "give its residual as a function of the stage count for three of the twelve test buffers, each $K$ "
           "fitted independently. The transistor netlists of the test buffers are available, so the true stage "
           "count is known."))
    hdr = ["Buffer"] + [f"$K$ = {k}" if k == 1 else str(k) for k in range(1, 11)] + ["Netlist"]
    rws = []
    for key, name in ((("ex2", "pull-up"), "ex2"), (("inv_chain", "pull-up"), "inv_chain"),
                      (("io_buf", "pull-up"), "io_buf (pull-up)")):
        r = d["rms"][key]
        rws.append([name] + [f"{float(x):.4f}"[1:] for x in r["rms_by_K"].split()] + [r["netlist_K"]])
    A(table(hdr, rws, [1500] + [720] * 10 + [800],
            f"{T('rms_vs_k')}: Residual of the fit (26) in the $K_u$ domain against the stage count $K$", size=16))
    A(fig("rms_vs_k", "Residual of (26) against stage count for the thirteen predriver chains of the twelve test "
                      "buffers (io_buf has two). Circles mark the netlist stage count; the thick segments mark the band "
                      "(27).", 5.6))
    A(para("Two features are evident. First, $K = 1$ fails on ex2 and inv_chain: a single stage cannot produce "
           "the required delay together with the required edge rate, so the full swing does constrain the rate. "
           "Second, beyond that the residual is flat: on ex2, $K = 3$ to 6 lie within 0.002 of each other and the "
           "minimum is at $K = 5$ although the netlist has three stages; on inv_chain, $K = 6$ to 9 differ in the "
           "fourth decimal. The margin between the best and the second-best $K$ is at most 0.0007 on twelve of the "
           "thirteen chains. Only io_buf's pull-up, which is a single stage, has a distinct minimum (margin "
           f"0.0088). This is the same degeneracy as that of the map in {S('fit')}.7, in numbers."))
    A(para("The same holds for the other quantities that act only under partial drive. *The threshold:* the "
           "fitted $v_t$ of ex2 is 0.029 in one fitting pass ($K = 6$) and 0.528 in another ($K = 3$) that differs "
           "in $C_{comp}$ and map shape, at residuals of 0.0202 and 0.0233. *The exponent:* at full swing each stage input dwells at "
           "the rail, where (17) does not depend on $p$; in fits of the individual probed stages every $p$ between 1 and 2 "
           f"reaches a residual of 0.002–0.007. *The saturation boundary:* if $x_{{lin}}$ is left free in (26) it settles at "
           f"{float(ex['x_lin']):.3f} on ex2 and {float(iv['x_lin']):.3f} on inv_chain, less than half the measured "
           "$x_0$ of Table III, and replacing (18) by the drive-dependent boundary of (15) changes the residual by "
           "about 1 % on ex2 and not at all on inv_chain. The file cannot distinguish these alternatives, which is "
           f"why $x_{{lin}}$ and $p$ are normally held fixed ({T('inputs')}) rather than fitted."))
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

    # ================================================================ L. the stressed measurement
    A(heading(f"{SEC['stress']}. Steps 2–4: the single stressed measurement"))
    A(heading("1) Why it is needed", 3))
    A(para("After step 1 there is not one model but several, and all of them reproduce the file. They differ in "
           f"what the file cannot see: the map shape ({S('fit')}.7), the stage count and the stage threshold "
           f"({S('ident')}). These are exactly the quantities that decide what happens when the input is cut "
           "short, because they set how far the gate has travelled when it turns back and how much of the pulse "
           "each stage passes on. The candidates therefore agree on a full transition and disagree on a short "
           "pulse, and one measured short pulse can tell them apart.", "FirstParagraph"))
    _lo, _hi, _pk = d["stress"]
    A(para(f"{F('stress_use')}(b) shows how large the disagreement is. For ex2, the nine candidates of step 2, each "
           "fitted to the same file, were driven by the same 810 ps pulse. Their pad peaks range from "
           f"{_lo:.2f} to {_hi:.2f} V; the measured peak is {_pk:.2f} V. Some overshoot it by more than half, "
           "others extinguish the pulse altogether. The file alone gives no means of knowing which is right."))
    A(heading("2) What is measured", 3))
    A(para(f"The measurement is the pad voltage for one short input pulse into a known load ({F('stress_use')}(a)). "
           "Nothing inside the buffer is observed. In the tests below the pulse is the one that reaches about 50 % "
           "of the buffer's settled swing into a 50 Ω, 2 pF load, and the measurement is a transistor-level "
           "simulation of the buffer; for a user of the method it would be a bench measurement or a simulation "
           "supplied by the vendor.", "FirstParagraph"))
    A(heading("3) How it is used", 3))
    A(para(f"*Candidates (step 2).* The band (27) supplies three stage counts and {F('map')}(c) three map shapes. "
           "Each of the nine combinations has its own fit (26).", "FirstParagraph"))
    A(para("*Calibration of the threshold (step 3).* The stage threshold $v_t$ decides how much of a short pulse "
           "survives each stage, and so sets the height of the model's pad pulse; it is also the parameter the "
           f"file determines worst ({S('ident')}). For each candidate, with $\\hat{{V}}$ the measured peak of the pad "
           "voltage, define the peak error"))
    A(equation("e(v_t) \\triangleq \\frac{\\max_t V_{pad}^{model}(t; v_t) - \\hat{V}}{\\hat{V}},\\quad e(v_t^{cal}) = 0", 28))
    A(para("and solve $e = 0$ for $v_t$ by bisection on $[0, 0.7]$, all other parameters held at their values "
           "from (26). Each evaluation is one circuit simulation of the complete model; three bracket the "
           "interval and seven bisect it. If the threshold cannot bracket the peak, $s_{up}$ and $s_{dn}$ are scaled "
           "together within $[0.5, 2]$ instead. The threshold is used, and not the rates, because the rates were "
           "fitted to reproduce the full swing and moving them degrades it, whereas $v_t$ changes when each stage "
           "hands over without changing how fast it runs. After this step every candidate reproduces the measured "
           f"peak ({F('stress_use')}(c)).", "FirstParagraph"))
    A(para(f"{F('calib_mech')} shows the calibration on ex2's selected candidate, built with the file-only "
           "settings. The peak error as a function of $v_t$ (a) is not monotonic: it is "
           f"{cb['err_lo']:+.0f} % at $v_t = 0$, rises to {cb['emax']:+.0f} % near {cb['vt_emax']:.2f}, and falls "
           f"steeply above 0.55 to {cb['err_hi']:+.0f} % at the bound, where the chain extinguishes the pulse. A "
           "higher threshold means that each stage passes less of a short pulse to the next, so the pad peak falls "
           "as $v_t$ rises, and the zero crossing is where the model's peak equals the measured one. The bisection "
           "(b) needs only the sign of the error: after the three bracketing runs ($v_t$ as fitted, 0 and 0.7) the "
           "interval $[0, 0.7]$ is halved seven times, each halving one ngspice run of the complete model, and the "
           f"midpoint of the final interval, {cb['vt_final']:.3f}, is kept. Panel (c) shows the pad waveform at four "
           "of the iterations: too early and too high at low thresholds, on the measured peak at the end. The fitted "
           f"threshold of this candidate was on its bound, {cb['vt0']:.3f}, with a peak error of {cb['err0']:+.0f} %; "
           f"calibration moved it to {cb['vt_final']:.3f}."))
    A(fig("calib_mech", "The calibration (28) on ex2's selected candidate ($K = 3$, map shape (0.5, 0.7), file-only "
                        "settings), for the 810 ps pulse. (a) The peak error against the stage threshold, from a dense "
                        "sweep (grey) with the ten iterations of the procedure numbered (orange: the three bracketing "
                        "runs; teal: the seven bisections). (b) The interval each bisection tested, with the sign it "
                        "found. (c) The pad waveform at four of the iterations against the measurement; the dashed line "
                        "is the measured peak."))
    A(para("*Selection of the stage count and map shape (step 4).* Because calibration has forced the peak to "
           "match, the peak can no longer distinguish the candidates. They still differ in the rest of the "
           f"waveform, in when the pulse arrives and how it returns: in {F('stress_use')}(c) the nine pulses arrive "
           "between 0.11 ns early and 0.30 ns late. The candidate is chosen by the waveform error over the pulse "
           "and its return,", "FirstParagraph"))
    A(equation("(K, v_{t,map}, a)^{\\star} = \\arg \\min~\\rms_{t \\in [t_f - 0.3~\\text{ns},~t_f + 1.5~\\text{ns}]} \\left[ V_{pad}^{model}(t) - V_{pad}^{meas}(t) \\right]", 29))
    A(para(f"where $t_f$ is the falling edge of the input pulse (the shaded interval of {F('stress_use')}(c)). The "
           "window was chosen once and was not tuned. On ex2 the selected candidate ($K = 3$, shape (0.5, 0.7)) "
           "arrives 7 ps early.", "FirstParagraph"))
    A(fig("stress_use", "Use of the stressed measurement on ex2. (a) The measurement: pad voltage for an 810 ps "
                        "input pulse. (b) The nine candidates as fitted to the IBIS file, driven by the same pulse, before "
                        "the measurement is used; the dashed line is the measured peak. (c) After the threshold of each "
                        "candidate is calibrated on the peak (28): all reach the measured peak and differ elsewhere; the "
                        "shaded interval is the window of (29), and the selected candidate is highlighted. (d) The "
                        f"selected model at the five pulse widths of {S('verify')} against the transistor-level reference. "
                        "Time is measured from the input edge."))
    A(heading("4) What it does and does not establish", 3))
    A(para("One waveform is thus used for two decisions, read from two different features of it: the threshold "
           "from its height, the stage count and map shape from its shape. Selecting on the peak instead of the "
           "waveform is markedly worse. Averaged over the twelve buffers, the pad-waveform error at all five "
           "stressed widths (the rms of (29) evaluated at each width) is 52.3 mV for the candidates chosen by "
           "(29), against 51.7 mV for the best candidate available in each grid and 217.3 mV for the candidates "
           "that minimize the worst peak error, which achieve their peak by arriving 155–300 ps late.",
           "FirstParagraph"))
    A(para("The measurement can only choose among the candidates it is offered. If the true map is unlike all "
           "three shapes, or the true stage count lies outside the band, it selects the least wrong candidate, "
           f"not the right one. {F('stress_use')}(d) and {S('verify')} test the outcome at pulse widths other than "
           "the one used here."))

    # ================================================================ M. the ledger
    A(heading(f"{SEC['ledger']}. The procedure end to end: ex2"))
    A(para("This section collects what the procedure did on ex2 with the file-only settings, so that the whole "
           "chain of decisions can be read in one place. The input was the IBIS file and one transistor-level pad "
           "waveform for the 810 ps pulse; everything else in the two tables was computed from those.",
           "FirstParagraph"))
    _rk = lg["rms_by_k"]
    _band = lg["band"]
    _cands = lg["cands"]
    _selr = next(r for r in _cands if r["selected"])
    _pk0 = [r["peak0"] for r in _cands]
    _pe = [abs(r["peak_err"]) for r in _cands]
    _pr = [r["pad_rms"] for r in _cands]
    A(table(["Step", "What was done", "Result on ex2"],
            [["0", "$C_{comp}$. The file declares 5.0 pF. The converter's $K_u$ solution cannot exceed 1 for a correct "
                   "$C_{comp}$, and with 5.0 pF it overshoots to 1.24; the value at the knee of that overshoot "
                   "against the assumed $C_{comp}$ is taken instead (the file's own estimate).",
              f"{lg['cc_knee']} pF (the netlist measurement, not used, gives 1.7 pF)"],
             ["0", f"Target: $K_u(t)$ solved from the V–T waveforms, replayed by the existing model, normalised (25).",
              f"as {F('target')}(d), at {lg['cc_knee']} pF"],
             ["1", "Fit (26) for $K$ = 1 … 10 at the default shape (0.5, 0.7); residuals",
              " ".join(f"{x:.4f}"[1:] for x in _rk)],
             ["2", "Band (27): the three smallest $K$ within 25 % of the best residual; × three map shapes",
              f"$K$ ∈ {{{', '.join(str(k) for k in _band)}}}; nine candidates ({T('ledger_cands')})"],
             ["3", f"Measured peak of the 810 ps pad pulse; candidates' peaks before calibration; bisection of $v_t$ (28), ten runs each",
              f"{lg['peak']:.2f} V measured; {min(_pk0):.2f}–{max(_pk0):.2f} V before; after calibration all within {max(_pe):.1f} % of the peak"],
             ["4", "Waveform rms (29) at the calibration width; the smallest wins",
              f"{min(_pr):.0f}–{max(_pr):.0f} mV across the nine; selected $K$ = {_selr['K']}, shape ({_selr['shape'][0]:g}, {_selr['shape'][1]:g}), {_selr['pad_rms']:.0f} mV, arriving {abs(_selr['lag']):.0f} ps {'early' if _selr['lag'] < 0 else 'late'}"],
             ["check", f"Worst peak error of the selected model over the five stressed widths ({S('verify')})",
              f"{_selr['worst']:.1f} %"]],
            [700, 5400, 3500], f"{T('ledger_steps')}: ex2 through the procedure, file-only settings"))
    _cr = []
    for r in sorted(_cands, key=lambda r: (r["shape"], r["K"])):
        _cr.append([str(r["K"]), f"({r['shape'][0]:g}, {r['shape'][1]:g})", f"{r['s_up']:.2f}", f"{r['s_dn']:.2f}",
                    f"{r['vt_fit']:.3f}", f"{r['rms']:.4f}", f"{r['peak0']:.2f}", f"{r['vt_cal']:.3f}",
                    f"{r['peak_err']:+.1f}", f"{r['pad_rms']:.0f}", f"{r['lag']:+.0f}", f"{r['worst']:.1f}",
                    "selected" if r["selected"] else ""])
    A(table(["$K$", "Shape", "$s_{up}$", "$s_{dn}$", "$v_t$ fit", "Residual (26)", "Peak before (V)", "$v_t$ cal.",
             "Peak err. (%)", "rms (29) (mV)", "Lag (ps)", "Worst 5 widths (%)", ""], _cr,
            [500, 1000, 750, 750, 800, 1000, 950, 800, 900, 950, 700, 1000, 900],
            f"{T('ledger_cands')}: The nine candidates of ex2 through steps 2–4. Columns 3–6: the fit (26) to the file. "
            "Peak before: the pad peak of the candidate as fitted, for the 810 ps pulse (measured "
            f"{lg['peak']:.2f} V). $v_t$ cal., peak error and rms (29): after calibration, at the calibration width. "
            "Lag: arrival of the model's pulse relative to the measurement. Worst: over the five stressed widths, "
            f"not available to the procedure.", size=15))
    A(para(f"Three things can be read off {T('ledger_cands')}. The fit residuals of the nine candidates lie within "
           f"{100 * (max(r['rms'] for r in _cands) / min(r['rms'] for r in _cands) - 1):.0f} % of each other, so "
           f"the file does not rank them. Their pad peaks before calibration run from {min(_pk0):.2f} to "
           f"{max(_pk0):.2f} V against {lg['peak']:.2f} V measured, so the short pulse does. And after calibration every "
           f"candidate matches the peak within {max(_pe):.1f} %, so the peak no longer ranks them and the waveform "
           "must: the selected candidate has the smallest rms (29) and arrives closest to the measured pulse; the "
           "candidates with the smallest worst-case error over five widths (last column) would have been the "
           "$K$ = 4 and 5 builds, which the procedure cannot know and which the selector did not pick, so the "
           f"selection costs {_selr['worst'] - min(r['worst'] for r in _cands):.0f} points of peak error on this "
           "buffer.", "FirstParagraph"))

    # ================================================================ N. verification
    A(heading(f"{SEC['verify']}. Verification"))
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
            [3100] + [1300] * 5, f"{T('gate_ex2')}: Peak of the stressed gate, ex2 (fitted at full swing only)"))
    r3 = [r for r in e if int(r["K"]) == 3]
    worst3 = max(abs(float(r["pred_max"]) - float(r["meas_max"])) for r in r3)
    lin0 = float(r3[0]["lin_max"]) - float(r3[0]["meas_max"])
    k2 = peaks(e, 2)
    A(para(f"On ex2 the stage law with the netlist stage count is within {worst3:.2f} of the measured peak at "
           f"every width, where linear superposition is off by {lin0:.2f} at the narrowest pulse ({T('gate_ex2')}, "
           f"{F('gate_verify')}(a)). The waveform error at the narrowest pulse is {float(r3[0]['rms']):.3f} for the stage law, "
           f"from a full-swing fit residual of {float(r3[0]['full_rms']):.4f}. The stage count matters as "
           f"{S('ident')} predicts: $K = 2$ gives {min(k2):.2f}–{max(k2):.2f}, far below the measurement."))
    iv_rows = d["inv"]
    wid = [r["width_ps"] for r in iv_rows if int(r["K"]) == 7]
    have = sorted({int(r["K"]) for r in iv_rows})
    A(table(["Pulse width (ps)"] + wid + ["Full-swing residual"],
            [["Measured"] + [f3(float(r["meas_max"])) for r in iv_rows if int(r["K"]) == 7] + [""]]
            + [[f"Stage law, $K$ = {k}"] + [f3(v) for v in peaks(iv_rows, k)]
               + [f"{float(next(r for r in iv_rows if int(r['K']) == k)['full_rms']):.4f}"] for k in (7, 5, 3, 9) if k in have]
            + [["Linear superposition"] + [f3(v) for v in peaks(iv_rows, 7, "lin_max")] + [""]],
            [2700] + [1050] * 5 + [1650], f"{T('gate_inv')}: Peak of the stressed gate, inv_chain (fitted at full swing only)"))
    A(fig("gate_verify", "Stressed gate of the transistor netlist against the stage law fitted at full swing only, "
                         "and against linear superposition, at the narrowest, middle and widest of the five pulse widths. "
                         "(a) ex2. (b) inv_chain."))
    k7 = [r for r in iv_rows if int(r["K"]) == 7]
    err7 = [float(r["pred_max"]) - float(r["meas_max"]) for r in k7]

    def swallowed(K):
        return sum(1 for v in peaks(iv_rows, K) if v < 0.05)

    txt = (f"On inv_chain ({T('gate_inv')}, {F('gate_verify')}(b)) the stage law with the netlist stage count follows the measurement "
           f"at the three widest pulses (within {max(abs(x) for x in err7[2:]):.2f}) and undershoots at the two "
           f"narrowest, by {abs(err7[0]):.2f} at 104 ps. This is the partial-drive regime in which approximation A2 "
           f"is active ({S('approx')}).")
    if 5 in have and 3 in have:
        f7 = float(k7[0]["full_rms"])
        f5 = float(next(r for r in iv_rows if int(r["K"]) == 5)["full_rms"])
        f3_ = float(next(r for r in iv_rows if int(r["K"]) == 3)["full_rms"])
        txt += (f" The other rows show the consequence of the flat residual of {S('ident')}. The full-swing "
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
    A(heading("2) The model's internal gate against the transistor's", 3))
    A(para("The file-only model is judged at the pad; its internal gate $G_{UP}$ is never fitted to anything "
           "and the method never observes a gate. On the two buffers whose gate was probed, the gate of the "
           f"selected file-only build can nevertheless be compared with the real one ({F('gate_internal')}, "
           f"{T('gate_internal')}).", "FirstParagraph"))
    _gi = d["gate_int"]
    _rows = []
    for _dev in ("ex2", "inv_chain"):
        _r = [r for r in _gi if r["device"] == _dev]
        _rows.append([_dev] + [f"{r['model'] - r['real']:+.3f}" for r in _r]
                     + [f"{min(r['rms'] for r in _r):.2f}–{max(r['rms'] for r in _r):.2f}"])
    _w = sorted({r["width_ps"] for r in _gi if r["device"] == "ex2"})
    _wi = sorted({r["width_ps"] for r in _gi if r["device"] == "inv_chain"})
    A(table(["Buffer", "narrowest", "2nd", "3rd", "4th", "widest", "Waveform rms"],
            _rows, [1500, 1400, 1100, 1100, 1100, 1400, 2000],
            f"{T('gate_internal')}: Peak of the model's internal gate minus the peak of the probed gate, at the five "
            f"stressed widths (ex2: {_w[0]}–{_w[-1]} ps; inv_chain: {_wi[0]}–{_wi[-1]} ps)"))
    A(fig("gate_internal", "The internal gate of the selected file-only model against the probed gate of the "
                           "transistor netlist, at full swing and at the narrowest and widest stressed pulse. (a) ex2. "
                           "(b) inv_chain. The model was fitted to the IBIS file and one pad waveform only."))
    A(para("The model's gate has the height and shape of the real one at every width, although nothing in the "
           "procedure aimed at the gate: its stressed peak is 0.03–0.05 low on ex2 and 0.01–0.08 low on "
           "inv_chain, and it leads the real gate by 56–74 ps on ex2 and 12–20 ps on inv_chain. It is not "
           "the same waveform: on ex2 it returns to zero faster than the real gate, and the map absorbs the "
           "difference at the pad. The structure of (19) therefore produces an internal gate that resembles the "
           "transistor's, while its numbers remain effective parameters and the internals remain approximate."))
    A(heading("3) Pad level: the complete method on twelve buffers", 3))
    A(para(f"The complete procedure of {T('procedure')} was applied to twelve test buffers: ex2, inv_chain and io_buf, and "
           "nine variants of the first two. For each buffer the model was built from its IBIS file and from one transistor-level pad waveform "
           "at the pulse width giving about 50 % of the settled swing; $C_{comp}$ was estimated from the file as in "
           f"{T('ledger_steps')}. The model was then simulated at five "
           "pulse widths (about 50 to 90 % of the settled swing) into the same load and compared with "
           "transistor-level simulation of the same buffer. The score is the worst peak error over the five widths, "
           "with the peak error defined as in (28). The calibration width is one of the five, so the score is not "
           "entirely held out. HSPICE's native IBIS element with the same file is given for comparison.",
           "FirstParagraph"))
    A(fig("pad_waveforms", "Pad voltage for the narrowest stressed pulse of three buffers: transistor-level reference, "
                           "HSPICE native IBIS, and the proposed model built from the IBIS file and one stressed measurement. "
                           "The percentages are peak errors against the reference. Time is measured from the input edge.", 6.3))
    rows = []
    for dev, nat, t1, dead in d["pad"]:
        k_sh = d["sel"][dev]["rms"].split()
        rows.append([dev, d["knet"][dev], k_sh[0][1:], "(" + k_sh[1].replace("/", ", ") + ")", f"{t1:.1f}",
                     "no valid run" if dead else f"{nat:.1f}"])
    t1s = [x[2] for x in d["pad"]]
    A(table(["Buffer", "Netlist $K$", "Selected $K$", "Selected map shape", "Proposed: worst peak error (%)",
             "Native IBIS: worst peak error (%)"], rows, [1700, 1100, 1200, 1700, 2000, 1900],
            f"{T('pad')}: Pad-level result on the twelve test buffers (worst of five stressed pulse widths)"))
    A(fig("pad_summary", "Worst stressed peak error at the pad for the twelve test buffers.", 6.3))
    live = [x[1] for x in d["pad"] if not x[3]]
    A(para(f"The proposed model is within 10 % on all twelve buffers (range {min(t1s):.1f}–{max(t1s):.1f} %, "
           f"mean {sum(t1s) / len(t1s):.1f} %). On the seven buffers for which the native IBIS element produced a "
           f"valid run, its worst peak error is {min(live):.0f}–{max(live):.0f} %; on the five ex2 variants it "
           "did not produce a valid waveform at any pulse width with the simulation settings used, and no number is "
           "reported. The selected stage count equals the netlist count on eleven buffers (inv_chain selects 6 "
           "against 7)."))
    A(heading("4) Limits of the evidence", 3))
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

    # ================================================================ O. approximations
    A(heading(f"{SEC['approx']}. Summary of approximations"))
    A(table(["Label", "Approximation", "Introduced at", "What it removes", "Evidence"],
            [["A0", "One $V_{TH}$, $\\alpha$, $V_{D0}$ for both devices of a stage", "(13)–(14)",
              "Per-device parameters", "As in [1, Sec. VI]. Table III: the N and P devices differ ($x_0$ 0.34 against 0.57 on inv_chain)"],
             ["A1", "$p$ in place of $\\alpha$, with $p = 1$", "(17)", "The measured $\\alpha$ (Table III)",
              f"Not identifiable from the file ({S('ident')})"],
             ["A2", "$x_0 g^{\\alpha/2} \\to x_{lin}$, with $x_{lin} = 0.45$", "(18)",
              "Drive dependence of the saturation boundary",
              f"Not identifiable from the file ({S('ident')}); candidate cause of the inv_chain undershoot in {T('gate_inv')}"],
             ["A3", "$K$ identical normalized stages", "(20)", "$4(K - 1)$ free parameters",
              f"Free fit fails ({S('ident')}); $K$ selected by (29)"],
             ["A4", "Map shape taken from a grid of three", "(22), (26)", "Trade-off between gate and map",
              "Selected by (29); grid chosen on the test buffers"]],
            [650, 2700, 1300, 2150, 2800], f"{T('approx')}: Approximations of the model", size=16))
    A(para("Everything else in (19) is inherited from (1) and (2)–(5): the threshold, the constant-current "
           "ramp, the straight-line resistive tail and the two-device structure. Equation (24) is the existing "
           "converter's and is unchanged."))

    # ================================================================ Table I: notation
    A(heading(f"{T('notation')}: Notation"))
    A(table(["Symbol", "Definition", "Origin"],
            [["$u$, $v$", "Normalized stage input and output, 0 → 1", "(8)"],
             ["$v_t$", "$V_{TH}/V_{DD}$; in the fitted model, the effective stage threshold", "(9)"],
             ["$x_0$", "$V_{D0}/V_{DD}$, saturation boundary at full drive", "(9)"],
             ["$x_{lin}$", "Effective constant replacing the drive-dependent boundary $x_0 g^{\\alpha/2}$; 0.45 unless fitted", "(18)"],
             ["$g(x)$", "Normalized gate drive with cutoff", "(11)"],
             ["$h(x)$", "Gate factor, $g^{p}$", "(17)"],
             ["$r(x)$", "Drain factor, $\\min(1, x/x_{lin})$", "(18)"],
             ["$s_{up}$, $s_{dn}$", "$I_{D0}/(C V_{DD})$ per device, swings per unit time", "(16)"],
             ["$p$", "Gate exponent, model counterpart of $\\alpha$", "(17)"],
             ["$K$", "Number of stages", "(20)"],
             ["$G_{UP}$, $G_{DN}$", "Normalized gate trajectories of the output pull-up and pull-down devices", "(21)"],
             ["$M$, $(v_{t,map}, a, g_s)$", "Static gate-to-fraction map and its shape parameters", "(22)"],
             ["$K_u$, $K_d$", "Conducting fractions of the output pull-up and pull-down devices", "(22), (23)"],
             ["$V_{fix}$, $R_{fix}$", "Voltage and resistance of the fixture a V–T waveform was recorded into", S("target")],
             ["$\\hat{K}_u$", "$K_u$ normalized from its settled off level to its settled on level", "(25)"],
             ["$e(v_t)$", "Relative error of the model's pad peak against the measured peak", "(28)"]],
            [2400, 5600, 1600]))

    # ================================================================ references, remarks
    A(heading("References"))
    A(para("[1] T. Sakurai and A. R. Newton, “Alpha-power law MOSFET model and its applications to CMOS "
           "inverter delay and other formulas,” IEEE J. Solid-State Circuits, vol. 25, no. 2, pp. 584–594, "
           "Apr. 1990.", "FirstParagraph"))
    A(para("[2] H. Shichman and D. A. Hodges, “Modeling and simulation of insulated-gate field-effect "
           "transistor switching circuits,” IEEE J. Solid-State Circuits, vol. SC-3, 1968."))
    A(para("[3] N. Hedenstierna and K. O. Jeppson, “CMOS circuit speed and buffer optimization,” IEEE "
           "Trans. Computer-Aided Design, vol. CAD-6, no. 2, pp. 270–280, Mar. 1987."))
    A(heading("Remarks for the manuscript"))
    A(para(f"*Sources.* Every statement in Sections II-{SEC['road']} to II-{SEC['approx']} was checked against the "
           "code and result files of the project; the builder script of this document lists the file behind each. "
           "Reference [1] was read in full: equations (2)–(5) here are its (2)–(4), the straight-line triode "
           "region of (6) is its own, the single-stage response of Fig. 3(c) is its Appendix B, and approximation "
           "A0 is its Section VI. Reference [3] is given as it appears in the reference list of [1]. Reference "
           "[2] is given as it appears in the bibliography of Leventhal and Green, *Semiconductor Modeling* "
           "(Springer, 2006); its issue and page numbers were not available for checking and are omitted.",
           "FirstParagraph"))
    A(para(f"*Regenerated numbers.* {T('gate_inv')} was regenerated for this document. The earlier committed table "
           "had been produced with an explicit-Euler integrator that was later replaced "
           f"({S('chain')}); ex2 ({T('gate_ex2')}) is unaffected to the third decimal for $K = 3$. The search of "
           f"{F('fit_search')} and the calibration sweep of {F('calib_mech')} were re-run for this document with "
           "the procedure's own code and settings."))
    A(para("*Open points.* (1) A drive-dependent boundary (15) in place of A2 reduces the inv_chain undershoot at "
           "the gate (mean peak error 0.077 to 0.016) but is neutral on ex2 and cannot be identified in the $K_u$ "
           "domain, so it has not been adopted; fixing $x_{lin}$ per buffer from a measured $x_0$ (Table III) is "
           "untested at the pad. (2) The pad-level score includes the calibration width. (3) Pulse trains, "
           f"low-going pulses and other loads and corners are not covered by {T('pad')}. (4) Two of the three "
           "Nelder–Mead starts stop in side minima on ex2; a search with more starts, or a global stage, would "
           "make step 1 more robust and has not been tried."))
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

    ins = build(pkg, d)
    # the inserts into Sections A-E were written against the old section letters and table numbers
    fix = {"Table XIII": T("pad"), "Sections II-F to II-M": f"Sections II-F to II-{SEC['approx']}",
           "from Section II-I onward": f"from {S('fit')} onward", "(Section II-J)": f"({S('ident')})",
           "Section II-J shows": f"{S('ident')} shows", "pad-level tests of Section II-L": f"pad-level tests of {S('verify')}"}
    for key in ("prelim", "a1a2", "after_eq19", "after_eq7", "min_form"):
        for a, b in fix.items():
            ins[key] = ins[key].replace(a, b)
    tail = build_sections(pkg, d)

    def insert_after(startswith: str, xml: str):
        el = next(k for k in body if text(k).startswith(startswith))
        pos = list(body).index(el)
        for j, new in enumerate(frag(xml), 1):
            body.insert(pos + j, new)

    # (5): the clip is ours. Rewrite the end of the paragraph that explains it.
    for k in body:
        for tnode in k.iter(f"{{{W}}}t"):
            if tnode.text and "The lower clip in (5)" in tnode.text:
                tnode.text = tnode.text[:tnode.text.index("The lower clip in (5)")] + (
                    "The clip is our notation and does not appear in [1]: its lower bound is the cutoff row "
                    "of (2) written into the drive, and its upper bound is a numerical guard for the chain of "
                    f"{S('chain')}, in which a stage output may overshoot its rail by a few percent for a few "
                    "time steps. In the paper's own setting the gate never exceeds the supply and the upper "
                    "bound is never reached.")
                run = tnode.getparent()
                for sib in list(run.itersiblings()):
                    run.getparent().remove(sib)
                break
    # (6): derive the min form instead of asserting it
    el = next(k for k in body if text(k).startswith("Because (2) is piecewise linear"))
    pos = list(body).index(el)
    body.remove(el)
    for j, new in enumerate(frag(ins["min_form"])):
        body.insert(pos + j, new)
    insert_after("Equation (7) is the device model", ins["after_eq7"])
    insert_after("Comparing (19) with (15) term by term", ins["after_eq19"])
    # Section E: A1 and A2 rewritten (from "A1 (gate exponent)" up to "Applying (17) and (18)")
    a1 = next(k for k in body if text(k).startswith("A1 (gate exponent)"))
    end = next(k for k in body if text(k).startswith("Applying (17) and (18)"))
    kids = list(body)
    i0, i1 = kids.index(a1), kids.index(end)
    assert 4 <= i1 - i0 <= 8, (i0, i1)
    for k in kids[i0:i1]:
        body.remove(k)
    for j, new in enumerate(frag(ins["a1a2"])):
        body.insert(i0 + j, new)

    def set_text(el, new):
        for r in list(el):
            if etree.QName(r).localname != "pPr":
                el.remove(r)
        for new_el in frag(f"<w:p>{new}</w:p>"):
            for child in list(new_el):
                if etree.QName(child).localname != "pPr":
                    el.append(child)

    from stage_law_docx import inline
    for k in body:
        st = k.find(f"{{{W}}}pPr/{{{W}}}pStyle")
        sid = st.get(f"{{{W}}}val") if st is not None else ""
        if sid == "Title":
            set_text(k, inline("A Stage-Law Model of the IBIS Predriver: Derivation, Fitting and Verification"))
        elif sid == "Date":
            set_text(k, inline("October 15, 2026"))
        elif sid == "Heading1" and text(k).startswith("II. Stage Model Derivation"):
            set_text(k, inline("II. The Stage-Law Buffer Model"))
        elif text(k).startswith("This section derives the stage law"):
            set_text(k, inline(
                "This section presents the stage law, the model of the predriver used in this work, derived from "
                "the α-power law MOSFET model [1], and the buffer model built on it. The preliminaries state "
                "the problem and the terms; Sections II-A to II-E derive the law; Sections II-F to "
                f"II-{SEC['approx']} build the buffer model, fit it to an IBIS file and one measurement, and verify "
                f"it. Equations are numbered consecutively, the approximations are summarized in {S('approx')}, "
                "and notation is collected in Table I."))
    head_a = next(k for k in body if text(k).startswith("A. Node dynamics"))
    for new in frag(ins["prelim"]):
        head_a.addprevious(new)
    # Section C: why u is measured downward, and that v_t changes meaning later
    for tnode in body.iter(f"{{{W}}}t"):
        if tnode.text and "fully turns on the working (pull-up) device" in tnode.text:
            tnode.text = tnode.text.replace(
                "fully turns on the working (pull-up) device",
                "fully turns on the working (pull-up) device: for a rising output the pull-up PMOS does the "
                "work, and it is driven harder as the input falls, so $u$ counts how far the input has come "
                "down from the supply".replace("$u$", "u"))
            break
    # the equation number is a delimiter object, so itertext gives "...x0...9" without the parentheses
    eq9 = next(k for k in body if "x0" in text(k).replace(" ", "") and text(k).rstrip().endswith("9"))
    pos = list(body).index(eq9)
    for j, new in enumerate(frag(para(
            "A note on $v_t$, because the symbol changes meaning. In (9) it is the device threshold as a fraction "
            f"of the supply, 0.14–0.33 for the devices of Table III. From {S('fit')} onward it is the "
            "threshold of a modeled stage, fitted to the file and then calibrated, and its fitted values "
            "(0.03–0.70 across the test buffers) are not device thresholds. The same symbol is kept because "
            "it plays the same role in (19).", "FirstParagraph")), 1):
        body.insert(pos + j, new)
    for new in frag("".join(tail)):
        sect.addprevious(new)

    tree.write(str(doc_xml), xml_declaration=True, encoding="UTF-8", standalone=True)
    pkg.finish(OUT)
    print(f"wrote {OUT}  ({OUT.stat().st_size / 1024:.0f} kB, {len(pkg.images)} figures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
