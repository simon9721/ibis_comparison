#!/usr/bin/env python3
"""Build the stage-law paper (Word, native equations, embedded figures).

IEEE-style layout: abstract, I introduction, II the stage law, III the buffer model, IV
identification from the file and one measurement, V verification, VI discussion, VII conclusion.
Sections II-A to II-E are the derivation of the stage law from the alpha-power law, kept from
`results/stage_law_doc_2026-10-01/source/stage_law_derivation_original.docx` with short inserts;
everything else is built here from the repository's own code and results, so that every statement
can be traced:

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

Figures come from scripts/build_stage_law_doc_figures.py (the data-bearing ones are called here).
Figures, tables and sections are numbered by the registries below, so a cross-reference in the
text cannot drift from the order in which the objects appear.

    py -3.14 scripts/build_stage_law_doc.py

Output: results/stage_law_doc_2026-10-01/stage_law_paper_v6_ieee.docx, IEEE Transactions layout (Letter,
two 3.5 in columns, Times 10 pt, double-column floating figures and wide tables, in-column figures),
and stage_law_paper_v6_draft.md, a markdown rendering of the same body for review. References are
numbered by first citation (REFS, C()); the kept derivation's literal [1]-[3] are renumbered with
them. The earlier stage_law_derivation_v2.docx (chapter), stage_law_paper_v3.docx (single column),
v4 and v5 (IEEE layout) stay as committed.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stage_law_docx import (Package, equation, heading, ieee_caption, ieee_sect_pr, ieee_styles, para,  # noqa: E402
                            section_break, table, table_height_pt)
from stage_law_doc_markdown import markdown_of_body  # noqa: E402

DOC = ROOT / "results" / "stage_law_doc_2026-10-01"
FIG = DOC / "figures"
SRC = DOC / "source" / "stage_law_derivation_original.docx"
OUT = DOC / "stage_law_paper_v6_ieee.docx"
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
    import numpy as np
    import build_stage_law_doc_figures as figs
    d["shape_order"] = [(0.3, 0.6), (0.4, 0.6), (0.4, 0.9), (0.5, 0.7), (0.6, 0.6), (0.6, 0.9)]
    d["shapes"] = {}
    for p in (DOC / "shape_from_file").glob("shape_*.json"):
        r = json.loads(p.read_text())
        d["shapes"][(r["dev"], r["vt_map"], r["a"])] = r
    d["knobs"] = figs.fig_fit_knobs()
    d["stress"] = figs.fig_stress_use()                     # (lowest, highest candidate peak, measured)
    # native on the five ex2 variants, revived by resampling the V-T tables (native_revived_variants.py)
    NAT = ROOT / "results" / "native_revived_variants_2026-10-18"
    revived: dict[str, float] = {}
    rows_rs = None
    if (NAT / "native_revived.csv").exists():
        for r in rows_of(NAT / "native_revived.csv"):
            rows_rs = int(r["rows_after"])
            if r["status"] == "ok" and r["valid"] == "1":
                revived[r["variant"]] = max(revived.get(r["variant"], 0.0), abs(float(r["peak_err_pct"])))
    d["rows_rs"] = rows_rs
    d["diag"] = rows_of(NAT / "diagnose" / "diagnose.csv") if (NAT / "diagnose" / "diagnose.csv").exists() else []
    devs, nat, t1, dead = figs.fig_pad_summary(revived)     # revived buffers come back alive, with their value
    # (buffer, native worst peak error, proposed worst peak error, native has no valid run, native revived)
    d["pad"] = [(dev, n, t, dd, dev in revived) for dev, n, t, dd in zip(devs, nat, t1, dead)]
    d["replay"] = figs.fig_replay_fails()
    figs.fig_stage()
    d["natfail"] = figs.fig_native_fail()
    d["cc_declared"] = {r["buffer"]: float(r["declared_pF"])
                        for r in rows_of(ROOT / "results/ccomp_from_file_2026-09-22/ccomp_from_file.csv")}
    import gate_ramp_prototype as gp
    d["widths"] = {}
    for dev in ("ex2", "inv_chain", "io_buf"):                # the five test widths, narrowest first
        gp.VARIANT_NAME = dev
        d["widths"][dev] = sorted(round(w * 1000) for _, w, _ in gp.cases(dev))
    d["target_info"] = figs.fig_target()
    d["search"] = figs.fig_fit_search()
    d["one_vs"] = figs.fig_one_vs_chain()                   # handover times of the fitted ex2 chain
    d["fa"] = figs.file_only_builds()
    d["calib"] = figs.fig_calib_mech()
    d["ledger"] = figs.ex2_ledger()
    L = np.load(DOC / "fit_search" / "landscape.npz")
    i = int(np.argmin(np.abs(np.log(L["s_up"]) - np.log(L["fit"][0]))))
    z = L["rms_sup_vt"][i]
    d["land"] = dict(z0=float(z[0]), zmin=float(z.min()), vt_min=float(L["vt"][int(np.argmin(z))]), z07=float(z[-1]))
    return d


def peaks(rows, K, col="pred_max"):
    return [float(r[col]) for r in rows if int(r["K"]) == K]


def f3(v):
    return f"{v:.3f}"


# ----------------------------------------------------------------------------- numbering
FIGS = ["replay_fails", "stage", "device", "stage_law", "blocks", "chain", "map", "gate_to_ku", "workflow", "target",
        "fit_knobs", "fit_search", "ambiguity", "rms_vs_k", "stress_use", "calib_mech", "gate_verify",
        "pad_summary", "pad_waveforms", "native_fail"]
COL_FIGS = {"stage": 3.2, "native_fail": 3.2}          # in-column figures and their width (in)
TABS = ["notation", "device", "procedure", "fit_all", "shapes", "ledger", "gate", "pad", "approx"]
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
SEC = dict(intro="I", law="II", model="III", ident="IV", verify="V", disc="VI", concl="VII")


def F(key: str) -> str:
    return f"Fig. {FIGS.index(key) + 1}"


def T(key: str) -> str:
    return "Table " + ROMAN[TABS.index(key)]


def S(key: str, sub: str | None = None) -> str:
    return f"Section {SEC[key]}" + (f"-{sub}" if sub else "")


# References, each verified against the source (the manual texts in hspice_manuals/, the publishers'
# pages, 2026-10-19). Numbered at assembly in order of first citation; C() writes a placeholder.
REFS = {
    "sakurai": "T. Sakurai and A. R. Newton, “Alpha-power law MOSFET model and its applications to CMOS inverter "
               "delay and other formulas,” *IEEE J. Solid-State Circuits*, vol. 25, no. 2, pp. 584–594, Apr. 1990.",
    "shichman": "H. Shichman and D. A. Hodges, “Modeling and simulation of insulated-gate field-effect transistor "
                "switching circuits,” *IEEE J. Solid-State Circuits*, vol. SC-3, 1968.",
    "hedenstierna": "N. Hedenstierna and K. O. Jeppson, “CMOS circuit speed and buffer optimization,” *IEEE Trans. "
                    "Computer-Aided Design*, vol. CAD-6, no. 2, pp. 270–280, Mar. 1987.",
    "ibis": "IBIS Open Forum, *I/O Buffer Information Specification (IBIS), Version 7.1*, Dec. 2021. [Online]. "
            "Available: https://ibis.org/ver7.1/",
    "cookbook": "IBIS Open Forum, *IBIS Modeling Cookbook for IBIS Version 4.0*, Sep. 2005. [Online]. Available: "
                "https://ibis.org/cookbook/",
    "wang": "Y. Wang and H. N. Tan, “The development of analog SPICE behavioral model based on IBIS model,” in "
            "*Proc. 9th Great Lakes Symp. VLSI*, 1999, pp. 101–104.",
    "hspice": "Synopsys, *PrimeSim HSPICE User Guide: Signal Integrity Modeling and Analysis*, Version T-2022.06, "
              "Jun. 2022, ch. 8.",
    "stievano": "I. S. Stievano, I. A. Maio, and F. G. Canavero, “Mπlog: Macromodeling via parametric identification "
                "of logic gates,” *IEEE Trans. Adv. Packag.*, vol. 27, no. 1, pp. 15–23, Feb. 2004.",
    "leventhal": "R. Leventhal and L. Green, *Semiconductor Modeling: For Simulating Signal, Power, and Electromagnetic "
                 "Integrity*. New York, NY, USA: Springer, 2006.",
    "hairer": "E. Hairer, S. P. Nørsett, and G. Wanner, *Solving Ordinary Differential Equations I: Nonstiff Problems*, "
              "2nd ed. Berlin, Germany: Springer, 1993.",
    "ngspice": "H. Vogt, G. Atkinson, D. Warning, and P. Nenzi, *Ngspice User’s Manual, Version 46*, Mar. 2026. "
               "[Online]. Available: https://ngspice.sourceforge.io/docs/",
    "nelder": "J. A. Nelder and R. Mead, “A simplex method for function minimization,” *Comput. J.*, vol. 7, no. 4, "
              "pp. 308–313, 1965.",
}


def C(*keys: str, suffix: str | None = None) -> str:
    """An inline citation: a placeholder that main() numbers by first appearance in the document."""
    for k in keys:
        assert k in REFS, k
    return "⟦cite:" + ",".join(keys) + (f"|{suffix}" if suffix else "") + "⟧"


COL = 5000                    # dxa: one IEEE column (3.5 in) less the cell padding
FIG_WIDTH = {"chain": 5.4, "gate_to_ku": 5.4, "fit_knobs": 5.0, "ambiguity": 4.8, "stress_use": 5.0,
             "gate_verify": 5.0, "fit_search": 6.0, "map": 6.4, "rms_vs_k": 5.0, "workflow": 6.4,
             "calib_mech": 5.6, "pad_summary": 5.6, "pad_waveforms": 5.4}     # inches; the rest span the text width
PAGE = 10300                  # dxa: a double-column (floating) table


def scaled(widths: list[int], total: int) -> list[int]:
    f = total / sum(widths)
    return [int(w * f) for w in widths]


def tab_col(key: str, title: str, header, rows, widths, size=16) -> str:
    """A table in the column, with its IEEE caption above."""
    return table(header, rows, scaled(widths, COL), size=size, caption_xml=ieee_caption(T(key).upper(), title))


FLOATS: list[dict] = []       # the double-column floats, placed at assembly time from the layout plan
_M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
_T: list[str] = []            # the block list of build_sections, for the mention paragraph of a wide table


def plain_prefix(xml_or_el, n: int = 40) -> str:
    """The first `n` characters of a paragraph's plain text before its first equation object, or ""
    if that is too short to identify the paragraph in a rendered page."""
    if isinstance(xml_or_el, str) and not xml_or_el.strip():     # a registered float leaves "" in the block list
        return ""
    el = etree.fromstring(f"<root {Package.NS}>{xml_or_el}</root>")[0] if isinstance(xml_or_el, str) else xml_or_el
    if etree.QName(el).localname != "p":
        return ""
    st = el.find(f"{{{W}}}pPr/{{{W}}}pStyle")
    if st is not None and st.get(f"{{{W}}}val") in ("ImageCaption", "CaptionedFigure", "TableCaption"):
        return ""                                         # a caption or a picture never anchors a float
    out = []
    for child in el:
        tag = etree.QName(child).localname
        if tag in ("oMath", "oMathPara"):
            break
        if tag == "r":                                   # direct text only: not a text box inside a drawing
            out += [t.text or "" for t in child.findall(f"{{{W}}}t")]
    s = " ".join("".join(out).split())
    return s[:n] if len(s) >= 20 else ""


SEEN: dict[str, list[str]] = {"fig": [], "tab": []}      # figures and tables in the order they are written


def note_order(key: str) -> None:
    """Every figure and table, wide or in the column, must be written in numbering order."""
    kind, order = ("fig", FIGS) if key in FIGS else ("tab", TABS)
    seen = SEEN[kind]
    assert not seen or order.index(seen[-1]) < order.index(key), f"{key} written out of numbering order, after {seen[-1]}"
    seen.append(key)


def register_float(key: str, xml: str, after: str, pkg: Package) -> str:
    note_order(key)
    FLOATS.append(dict(key=key, xml=xml, after=after[:40], height=pkg.float_heights.get(key, 3.0)))
    return ""


def fig_col(pkg: Package, key: str, caption: str) -> str:
    """An in-column figure: picture and caption in the text flow, numbered with the others."""
    note_order(key)
    return pkg.figure(FIG / f"fig_{key}.png", f"{F(key)}. {caption}", width_in=COL_FIGS[key])


def last_prefix(t: list[str]) -> str:
    for blk in reversed(t):
        p = plain_prefix(blk)
        if p:
            return p
    return ""


def tab_wide(pkg: Package, key: str, title: str, header, rows, widths, size=16, valign="auto",
             width=PAGE, jc=None) -> str:
    """A table spanning both columns: registered for placement, anchored after the last text
    paragraph written so far unless the layout plan says otherwise."""
    w = scaled(widths, width)
    xml = pkg.table_span(ieee_caption(T(key).upper(), title), table(header, rows, w, size=size, spacer=False, jc=jc),
                         table_height_pt(header, rows, w, size), key=key)
    return register_float(key, xml, last_prefix(_T), pkg)


# ----------------------------------------------------------------------------- front matter and inserts
def build_inserts(pkg: Package, d) -> dict:
    """The abstract and introduction (before Section II) and the short inserts into Sections II-A to II-E."""
    out = {}
    def fig(key, caption, width_in=7.1, valign="auto", after=""):
        xml = pkg.figure_span(FIG / f"fig_{key}.png", f"{F(key)}. {caption}", width_in=width_in, key=key)
        return register_float(key, xml, after, pkg)

    t1s = [x[2] for x in d["pad"]]
    live = [x[1] for x in d["pad"] if not x[3]]
    no_run = " where it produces a waveform at all" if any(x[3] for x in d["pad"]) else ""
    wd = d["widths"]
    al = [float(r["alpha"]) for r in d["dev"]]
    x0 = [float(r["vd0_over_vdd"]) for r in d["dev"]]
    rng = {"a": f"{min(al):.2f}–{max(al):.2f}", "x": f"{min(x0):.2f}–{max(x0):.2f}"}
    out["rng"] = rng
    rp = d["replay"]

    out["front"] = (
        para("*Abstract*—An IBIS model describes an output buffer by the I–V tables of its output devices and by the pad "
               "voltage of complete transitions, from which the conducting fractions $K_u(t)$ and $K_d(t)$ of the "
               "two devices are solved and replayed against time. When an input pulse is shorter than the buffer's "
               "own delay, the predriver interrupts the transition and the replay fails: on twelve test buffers "
               f"HSPICE's native IBIS element misses the stressed pad peak by {min(live):.0f}–{max(live):.0f} %{no_run}. "
               "This paper replaces the replay by a model of the predriver. Each "
               "predriver stage obeys a stage law derived from the α-power MOSFET model; $K$ identical stages drive "
               "the gate of the output device, and a static map turns the gate into $K_u$. The stage rates are "
               "fitted to the $K_u(t)$ that the IBIS file already contains. The file cannot determine the stage "
               "count, the map shape or the stage threshold, which act only under partial drive; one measured pad "
               "waveform for a short pulse calibrates the threshold on its peak and selects among nine candidates "
               "on its shape. Built from the file and that one measurement, the model reproduces the stressed pad "
               f"peak within 10 % (mean {sum(t1s) / len(t1s):.1f} %) on the twelve buffers at five pulse widths. "
               "The method relies on four built-in constants chosen on the test buffers, and was tested on single "
               "pulses into one load; both limits are stated.", "Abstract")
        + para("*Index Terms*—IBIS, I/O buffer modeling, predriver, short pulses, α-power law, behavioral "
               "modeling, signal integrity.", "Abstract")
        + heading(f"{SEC['intro']}. Introduction", 1)
        + para(f"An IBIS model {C('ibis')} describes an output buffer from its pins: the I–V tables of the pull-up and "
               "the pull-down device, the pad voltage of one complete rising and one complete falling transition "
               f"recorded into two fixtures {C('cookbook')}, the die capacitance $C_{{comp}}$ and the package. A "
               "simulator solves the two waveforms, instant by instant, for the conducting fractions $K_u(t)$ and "
               "$K_d(t)$, the multipliers on the two tables that reproduce the recorded pad voltage "
               f"{C('wang')}, and then replays them against time from the input edge. The IBIS-to-SPICE converter "
               "this work extends (the *converter* below) does this and writes the result as a SPICE subcircuit, "
               "the *existing model*. HSPICE's built-in IBIS element (the *native element*) derives its pull-up and "
               f"pull-down scaling coefficients from two V–T waveforms in the same way {C('hspice')} and is the "
               f"baseline of this paper; {S('ident', 'B')} lays its coefficient over the two-fixture solution. The "
               "proposed model is a subcircuit written by the same converter.",
               "FirstParagraph")
        + para("The coefficients describe complete transitions, which is all the file records. When an input "
               "pulse is shorter than the buffer's own delay and edge, the transition is interrupted inside the "
               "predriver, the chain of inverters between the input pin and the output devices: the gate of the "
               "output device turns back before it reaches its rail, and a coefficient replayed against time has "
               f"no representation of that. {F('replay_fails')} shows this on test buffer ex2, whose netlist can be probed. "
               f"Under a complete transition ({F('replay_fails')}(a)) the gate of the output device reaches its rail and "
               f"the replayed coefficient is the right one. For an 810 ps pulse ({F('replay_fails')}(b)) the gate turns "
               f"back at {rp['gate_peak']:.2f} of its swing; the conducting fraction solved from the transistor's own "
               f"fixture runs peaks at {rp['ku_si_peak']:.2f} and returns, while the native element replays the "
               f"coefficient of the complete transition up to {rp['ku_nat_peak']:.2f} ({F('replay_fails')}(c)), and its pad "
               f"overshoots the measured peak by {rp['native_peak_err']:.0f} % ({F('replay_fails')}(d)). Across the twelve "
               f"test buffers of this work its worst stressed peak error is {min(live):.0f}–{max(live):.0f} % "
               f"({S('verify')}).")
        + fig("replay_fails", "Where the replay fails, on test buffer ex2 at transistor level (the gate of the output device "
                        "is probed for this figure only). (a) A complete transition: input pin, gate and pad, "
                        f"normalized; the gate reaches its rail. (b) An 810 ps input pulse: the gate turns back at "
                        f"{rp['gate_peak']:.2f}. (c) The conducting fraction $K_u$ solved from the transistor's own two "
                        "fixture runs, against the native element's replayed coefficient; the solution is undefined "
                        "within about 90 ps of the reversal, where the two fixtures are not in the same state. (d) The "
                        "pad: transistor against the native element. Time is counted from the input edge.", 7.1, "auto",
             after="The coefficients describe complete transitions")
        + para("This paper replaces the replay by a model of the predriver. Each inverter of the predriver is "
               f"modeled by a stage law derived from the α-power MOSFET model {C('sakurai')}; $K$ identical stages drive the "
               "gate of the output device, and a static map turns the gate into $K_u$. The fractions then follow "
               "the gate rather than the clock: for a short pulse the gate turns back partway, and the model's "
               "$K_u$ does the same. The stage rates are fitted to the $K_u(t)$ that the file already contains, so "
               "the model needs nothing the file does not have, with one exception. A complete transition fixes "
               "the rates but not the quantities that act only under partial drive: the stage count, the shape of "
               "the map and the stage threshold. One measured pad waveform for a short pulse settles them.",
               "FirstParagraph")
        + para("The contributions are: (1) the stage law, a three-parameter normalized law of one predriver stage "
               f"derived from {C('sakurai')}, and the evidence that it extrapolates from a complete transition to truncated "
               "pulses; (2) an identification result, that the IBIS file determines the stage rates and leaves the "
               "stage count, the map shape and the threshold undetermined, shown in numbers; (3) a procedure that "
               "builds the model from the file and one stressed pad waveform, using the waveform's peak to "
               "calibrate the threshold and its shape to select among nine candidates; (4) verification at the pad "
               "on twelve test buffers, within 10 % of the transistor-level reference at five pulse widths, against "
               f"{min(live):.0f}–{max(live):.0f} % for the native element.")
        + para("Behavioral models of I/O buffers that go beyond the IBIS tables exist. Macromodels identified from "
               f"the buffer's port waveforms, such as Mπlog {C('stievano')}, represent the buffer as a black box and "
               "offer improved accuracy and numerical efficiency, but they are built from the buffer's transient "
               "responses rather than from the "
               f"IBIS file. Conversions of IBIS files into SPICE behavioral models {C('wang')} and the simulators' own "
               f"IBIS elements {C('hspice')} keep the file as the only input and replay its coefficients against "
               "time, which is the mechanism that fails here. This paper keeps the file as the primary input and "
               "inserts a model of the predriver between the input pin and the coefficients.")
        + para(f"The rest of the paper follows the construction of the model. {S('law')} derives the stage law from "
               f"the α-power MOSFET model {C('sakurai')}, because everything that follows rests on it. {S('model')} "
               "assembles the buffer model: the chain of stages, the map from the gate to the conducting fraction, "
               f"and the pad current. {S('ident')} asks what the IBIS file determines and what it cannot, and gives "
               f"the identification procedure step by step, with ex2 as the running example. {S('verify')} verifies "
               "the model, first at the gate, where the stage law is tested on its own, then at the pad on twelve "
               f"buffers against the transistor-level reference and the native element. {S('disc')} collects the "
               f"approximations and limits, and {S('concl')} concludes.")
        + heading("A. Terms and Test Set")
        + para("The test set is three buffers whose transistor netlists are available, ex2 (3.3 V, three "
               "predriver inverters), inv_chain (1.8 V, seven) and io_buf (3.3 V, separate pull-up and pull-down "
               "paths with one and three predriver stages), and nine variants of the first two, each changing one "
               "property of the silicon: ex2_base and inv_base8 are the two buffers rebuilt through the variant "
               "generator; ex2_weak and inv_weak halve the device widths (ex2: the output stage; inv_chain: every "
               "stage); ex2_skewp and inv_skewp halve the pull-up PMOS only; ex2_slowpre halves the predriver "
               "widths; ex2_nomiller removes the gate-to-drain capacitances of the output stage, the feedthrough "
               f"that puts the small bump before the edge of a V–T curve {C('leventhal', suffix='p. 64')}; inv_stage4 has "
               "three predriver inverters instead of seven. The input edge is 50 ps on the three base buffers and "
               "1 ps on the variants. Transistor-level HSPICE simulation is the reference, the model runs in "
               "ngspice, and the native element is the baseline. The method is not derived from the file alone: "
               "besides the one measurement it uses four built-in constants chosen on these buffers, which "
               f"{S('disc')} discusses.")
        + para("*Terms used throughout.* The *settled swing* of a buffer is the pad excursion of a complete "
               "transition into the test load (50 Ω and 2 pF), between the settled level before the input edge and "
               "the settled level after the transition; on ex2 it is 1.55 V. A pulse is *stressed* when it is too "
               "short for the transition to complete, so that the pad turns back before reaching the settled level; "
               "its *depth* is the fraction of the settled swing the pad reaches. Every buffer is tested at the five "
               "pulse widths at which the transistor-level pad reaches about 50, 60, 70, 80 and 90 % of its settled "
               f"swing, so a slower buffer is tested with longer pulses (ex2 {wd['ex2'][0]}–{wd['ex2'][-1]} ps, "
               f"inv_chain {wd['inv_chain'][0]}–{wd['inv_chain'][-1]} ps, io_buf {wd['io_buf'][0]}–{wd['io_buf'][-1]} ps); "
               "the *calibration width* is the shortest of the five, at which the one measurement is taken. A "
               "quantity is *probed* when it is read from an internal node of the transistor-level simulation; the "
               "method never does this, and probed data appear only in tests of the method and in the figures that "
               "explain it. *File-only* describes what the method itself uses: the IBIS file, one pad waveform and "
               "the built-in constants. In the chain, a *handover* is the instant at which a stage's output crosses "
               "the threshold of the stage after it, which then starts to move. "
               f"{T('notation')} lists the notation.")
        + tab_col("notation", "Notation", ["Symbol", "Definition", "Where"],
                [["$u$, $v$", "Normalized stage input and output, 0 → 1", "(8)"],
                 ["$v_t$", "Stage threshold: $V_{TH}/V_{DD}$ in the derivation, an effective fitted number in the model", "(9), (17)"],
                 ["$x_0$, $x_{lin}$", "Saturation boundary at full drive, $V_{D0}/V_{DD}$; the effective constant that replaces it (0.45)", "(9), (18)"],
                 ["$h$, $r$", "Gate factor and drain factor of the stage law", "(17), (18)"],
                 ["$s_{up}$, $s_{dn}$", "Charging and discharging rate of a stage, in swings per ns (one swing: the full excursion of $v$ from 0 to 1)", "(16)"],
                 ["$p$, $\\alpha$", "Gate exponent of the stage law (fixed at 1); the device's velocity-saturation index", "(17), (2)"],
                 ["$K$", "Number of stages in the chain", "(20)"],
                 ["$G_{UP}$, $G_{DN}$", "Gate of the output pull-up and pull-down device, 0 → 1", "(21)"],
                 ["$M$, $(v_{t,map}, a)$", "The map from the gate to the conducting fraction, and its shape", "(22)"],
                 ["$K_u$, $K_d$; $\\hat{K}_u$", "Conducting fractions of the output devices; $K_u$ normalized between its settled levels", "(22), (25)"],
                 ["$e(v_t)$", "Relative error of the model's pad peak against the measured peak", "(28)"],
                 ["$C_{comp}$", "Die capacitance: declared in the file, re-estimated from the file's own waveforms", f"(24), {S('ident', 'B').split()[1]}"]],
                [1300, 2750, 950]))

    # ---- Section II-A: the stage, drawn (an in-column figure after the paragraph that explains (1))
    out["stage_fig"] = (
        para(f"{F('stage')} draws the stage with these quantities: the two devices, the node, the load, the "
             f"currents, and the normalized variables defined in {S('law', 'C')}.")
        + fig_col(pkg, "stage", "One predriver stage: a CMOS inverter whose output node $V_o$ drives the lumped "
                                "capacitance $C$ and the gate of the next stage. $I_P$ and $I_N$ are the device "
                                "currents of (1); $u$ and $v$ are the normalized input and output of (8)."))

    # ---- Section II lead (replaces the original intro paragraph)
    out["law_lead"] = ("A predriver stage is a CMOS inverter driving the gate of the next. This section derives, from "
                       f"the α-power law MOSFET model {C('sakurai')}, a normalized law for its output with three parameters per "
                       "stage, (19). Equations are numbered consecutively. A reader willing to take (19) on trust may "
                       f"go to {S('model')}.")

    # ---- Section II-B: the min form, derived; the device check
    out["min_form"] = (
        para(f"Equation (2) has no single-expression form in {C('sakurai')}; the one used here follows from factoring $I'_{{D0}}$ "
             "out of the triode row, so that the two conducting rows read", "FirstParagraph")
        + equation("I_D = I'_{D0} \\cdot \\frac{V_{DS}}{V'_{D0}}~~(V_{DS} < V'_{D0}), \\\\ I_D = I'_{D0} \\cdot 1~~(V_{DS} \\ge V'_{D0})", size=18)
        + para("In each row the multiplier of $I'_{D0}$ is the smaller of 1 and $V_{DS}/V'_{D0}$, and the rows meet "
               "at $V_{DS} = V'_{D0}$. The conducting part of (2) is therefore", "FirstParagraph"))
    dev_rows = []
    for r in d["dev"]:
        card = "hspice.mod (BSIM3v3)" if "ex2" in r["device"] else "HL18G-S3.7S"
        dev_rows.append([r["device"], card, f"{float(r['L_m']) * 1e9:.0f} nm", f"{float(r['vdd']):.1f} V",
                         f"{float(r['vd0_over_vdd']):.3f}", f"{float(r['alpha']):.2f}"])
    out["after_eq7"] = (
        para("The device model (2)–(5) was checked against the transistors of the predrivers of two test buffers, "
             "simulated in HSPICE from their model cards at their drawn dimensions. $V_{TH}$ and $\\alpha$ are "
             f"extracted as in {C('sakurai', suffix='App. A')}; $V_{{D0}}$, for which {C('sakurai')} gives no procedure, "
             "is the breakpoint that best fits the piecewise form (6) to the output curve at full gate drive. "
             f"{T('device')} lists the result and {F('device')} shows the curves with the fit: $\\alpha$ is {rng['a']}, "
             f"between the short-channel limit of 1 and the long-channel value of 2 {C('shichman')}, and the "
             f"saturation voltage is {rng['x']} of the supply, comparable to the 0.5–0.55 used in {C('sakurai')}.")
        + tab_col("device", "Device parameters of (2)–(5), extracted in HSPICE from the predriver transistors "
                            "(ex2: the BSIM3v3 card hspice.mod; inv_chain: HL18G-S3.7S)",
                  ["Device", "$L$", "$V_{DD}$", "$x_0 = V_{D0}/V_{DD}$", "$\\alpha$"],
                  [[r[0].replace(" predriver", ""), r[2], r[3], r[4], r[5]] for r in dev_rows],
                  [1500, 750, 750, 1250, 750])
        + fig("device", "The device model (2)–(5) against HSPICE on the predriver transistors. (a) Output current at "
                        "full gate drive against $V_{DS}$, both normalized, with the breakpoint $x_0$ of each device. "
                        "(b) inv_chain NMOS: HSPICE output curves at five gate drives and the piecewise model (2). "
                        "(c) Saturation current against gate drive on log scales; the slope is $\\alpha$.", 7.1, "auto",
              after="The device model (2)–(5) was checked aga"))

    # ---- Section II-C: the two meanings of v_t
    out["vt_note"] = para(
        "A note on $v_t$, because the symbol changes meaning. In (9) it is the device threshold as a fraction of the "
        f"supply, 0.14–0.33 for the devices of {T('device')}. From {S('ident')} onward it is the threshold of a "
        "modeled stage, fitted to the file and then calibrated, and its fitted values (0.03–0.70 across the test "
        "buffers) are not device thresholds. The same symbol is kept because it plays the same role in (19).",
        "FirstParagraph")

    # ---- Section II-E: A1 and A2, said plainly
    out["a1a2"] = (
        para("*A1 (gate exponent).* In (15) the gate factor is $g(u)^{\\alpha}$ with the measured device exponent "
             f"$\\alpha$, {rng['a']} for the devices of {T('device')}. The model keeps the form but treats the "
             "exponent as a parameter $p$:", "FirstParagraph")
        + equation("h(x) \\triangleq g(x)^{p} = \\clip\\left(\\frac{x - v_t}{1 - v_t},~0,~1\\right)^{p}", 17)
        + para("A full-swing waveform cannot set $p$: the stage input dwells near $g = 1$, where $g^{p} = 1$ for every "
               f"$p$ ({S('ident', 'D')}). In this work $p = 1$ is adopted, so (17) reduces to $h(x) = g(x)$: A1 drops "
               "the measured exponent and makes the drive current linear in the gate above threshold, the "
               f"short-channel limit of {C('sakurai')}. The parameter $p$ is kept in the formula only so that the exponent can "
               "be restored if a measurement supplies it.", "FirstParagraph")
        + para("*A2 (fixed saturation boundary).* In (15) the boundary between the constant-current ramp and the "
               "resistive tail is $x_0 g^{\\alpha/2}$: it equals $x_0$ at full drive and shrinks when the gate is only "
               "partly on. The model replaces it by a constant that does not depend on the gate:", "FirstParagraph")
        + equation("r(x) \\triangleq \\min\\left(1,~\\frac{x}{x_{lin}}\\right)", 18)
        + para("For a known device the natural value is $x_{lin} = x_0$, and at $g = 1$ (18) then coincides with "
               "(15); the two differ only under partial drive. The model never knows the device, so the constant "
               "is given its own name: $x_{lin}$ is an effective number, set to 0.45 in this work for the reasons "
               f"given after {F('stage_law')}, and the measured $x_0$ of {T('device')} ({rng['x']}) is only a check "
               "on it.", "FirstParagraph"))

    # ---- Section II-E: the stage law, pictured; the value of x_lin
    out["after_eq19"] = (
        fig("stage_law", "The stage law (19). (a) Gate factor $h(u)$ of (17) for three exponents. (b) Drain factor "
                         "of the charging term: the fixed boundary of (18) against the drive-dependent boundary of "
                         "(15) at three gate drives ($\\alpha = 1$, $x_0 = 0.45$). (c) One stage's response to an "
                         "input step: a constant-slope ramp, then an exponential approach to the rail.",
            after="Comparing (19) with (15) term by term:")
        + para("The value $x_{lin} = 0.45$ is a built-in constant of the method, not a quantity read from the IBIS "
               "file. It was chosen during development from fits of (19) to the individual probed predriver stages "
               "of two test buffers (0.37–0.47 on ex2, 0.52–0.63 on inv_chain); fitted to the probed gate with "
               f"$x_{{lin}}$ free, the chain gives 0.41 and 0.48, the measured $x_0$ of {T('device')} is {rng['x']}, "
               f"and {C('sakurai')} uses 0.5–0.55. In the pad-level tests of {S('verify')} it is fixed at 0.45 on ten of the "
               f"twelve buffers and fitted on inv_chain and io_buf; {S('ident', 'D')} shows why the file constrains "
               f"it only weakly. As a check that (19) is the model of {C('sakurai')} and not merely similar to it, one stage with "
               f"$p = \\alpha$ driven by a linear input ramp reproduces the closed-form delay of {C('sakurai', suffix='eq. (5)')} within "
               "4 ps for input ramps of 0.05 to 0.8 ns.", "FirstParagraph"))
    return out


# ----------------------------------------------------------------------------- Sections III to VII
def build_sections(pkg: Package, d) -> list[str]:
    t: list[str] = []
    A = t.append
    global _T
    _T = t

    def fig(key, caption, width_in=None, valign="auto"):
        xml = pkg.figure_span(FIG / f"fig_{key}.png", f"{F(key)}. {caption}",
                              width_in=width_in or FIG_WIDTH.get(key, 7.1), key=key)
        return register_float(key, xml, last_prefix(t), pkg)

    ti, se, ov, fa, cb, lg, land = (d["target_info"], d["search"], d["one_vs"], d["fa"], d["calib"], d["ledger"], d["land"])
    wd = d["widths"]
    hand = ov["hand"]
    k1, k3 = ov["k1"], ov["k3"]

    # ================================================================ III. the buffer model
    A(heading(f"{SEC['model']}. The Buffer Model", 1))
    A(para(f"Equation (19) describes one stage. This section assembles the buffer: $K$ stages in a chain, the map "
           "from the gate of the output device to its conducting fraction, and the pad current, which is the "
           "existing model's and is unchanged.", "FirstParagraph"))
    A(heading("A. Signal path"))
    A(para(f"{F('blocks')}(a) shows the buffer as an IBIS file describes it. The input pin drives the predriver, "
           "a chain of inverters whose last node is the gate of the output stage; the output pull-up and pull-down "
           "devices drive the die node, which $C_{comp}$ loads and the package connects to the pad. The file "
           "records the output stage (its I–V tables), $C_{comp}$, the package and the pad voltage of complete "
           "transitions; it records nothing about the predriver, which is where a short pulse is interrupted.",
           "FirstParagraph"))
    A(para(f"{F('blocks')}(b) shows the signal path of the model. A comparator turns the input pin into a 0-or-1 command; $K$ "
           "identical stages obeying (19) pass it along, each adding delay and rounding the edge; the output of the "
           "last stage is the gate of the output pull-up device on a 0-to-1 scale; a static map $M$ turns the gate "
           "into $K_u$, and its complement into $K_d$; and the fractions scale the I–V tables of the file to give "
           "the current into the die node, which $C_{comp}$ and the package turn into the pad voltage. The proposed "
           "method replaces only how $K_u(t)$ and $K_d(t)$ are generated."))
    A(fig("blocks", "(a) The buffer as the IBIS file describes it: predriver, output stage, die node, package. (b) "
                    "Signal path of the model. The teal blocks replace the way $K_u(t)$ and $K_d(t)$ are generated; "
                    "the I–V tables, $C_{comp}$ and the package are those of the IBIS file. Numbers in parentheses "
                    "are equation numbers."))
    A(heading("B. The chain"))
    A(para("The predriver is modeled as $K$ stages, each obeying (19) with one shared parameter set "
           "$\\{s_{up}, s_{dn}, v_t, x_{lin}, p\\}$ (approximation A3, identical normalized stages). Because (8) "
           "expresses every node as its own progress from 0 to 1, an inverting stage needs no sign: each stage's "
           "output is the next stage's input. The first stage is driven by a comparator on the input pin at half "
           "the supply, and the output of the last stage is the gate of the output pull-up device, with the "
           "pull-down gate its complement:", "FirstParagraph"))
    A(equation("u_1(t) = 1~\\text{if}~V_{in}(t) > V_{DD}/2,~\\text{else}~0; \\\\ u_{k+1}(t) = v_k(t),\\quad k = 1,\\ldots,K-1", 20, size=18))
    A(equation("G_{UP}(t) \\triangleq v_K(t),\\quad G_{DN}(t) \\triangleq 1 - G_{UP}(t)", 21))
    A(para("The comparator in (20) plays the part of the existing model's input stage, which also turns the pin "
           "into a command; the input edges of the test set, 50 ps and 1 ps, are short against the chain delay "
           "(about 1 ns on ex2), so the input's own shape is not modeled. The complement in (21) corresponds to an "
           "output stage whose two devices are driven from one predriver node, the case for ex2 and inv_chain and "
           "their variants. Where the two devices have separate predriver paths, as in io_buf, a second chain with "
           "its own stage count and parameters is fitted for $G_{DN}$. An IBIS file does not state which structure "
           "a buffer has; in this work the choice was made from the netlists, and it is one input the user must "
           f"supply ({S('disc')}).", "FirstParagraph"))
    A(para("In words, a stage is a bucket: it fills at the rate $s_{up}$ once the bucket before it is more than "
           "$v_t$ full, drains at $s_{dn}$ once that bucket has emptied below $1 - v_t$, and the flow tapers off "
           "within $x_{lin}$ of the rim or the floor. A step at the input starts filling the first bucket at once; "
           "each later stage waits until the one before it passes $v_t$. The delay of the chain is spent in these "
           f"handovers, and the shape of its last edge is set by the rate. On the fitted ex2 chain ({F('chain')}) "
           f"the handovers come at {hand[0]:.2f} and {hand[1]:.2f} ns, the gate reaches the map's threshold at "
           f"{hand[2]:.2f} ns, and the file's own $K_u(t)$ leaves zero at {ov['file_start']:.2f} ns."))
    A(para(f"{F('chain')}(b) shows why the stage count is a first-order parameter. For a pulse shorter than the "
           "chain's own delay, the input reverses while the later stages are still rising: each stage turns back "
           "before reaching its rail, the gate reaches only part of its swing (0.74), and because a stage delivers "
           "no current until its input passes $v_t$, a pulse loses amplitude at every stage and is extinguished "
           "once its peak falls below $v_t$. The abrupt cutoff is a property of the hard threshold in (17); in a "
           "transistor chain the loss is gradual. For the fits below, (19)–(21) are integrated with Heun's method "
           f"{C('hairer')} at 1 ps steps, which agrees with the ngspice {C('ngspice')} circuit model where explicit Euler "
           "at 2 ps did not; in the circuit model each stage is a behavioral current source charging a capacitor."))
    A(fig("chain", "One chain, two inputs (ex2, probed-map setting: $K = 3$, $s_{up} = 2.19$/ns, $s_{dn} = 2.12$/ns, $v_t = 0.487$, "
                   "$x_{lin} = 0.45$). Top: the stage nodes of (19)–(21). Bottom: the conducting fraction obtained "
                   "from the gate through the map (22). (a) Full transition. (b) An 810 ps input pulse: the gate "
                   "turns back at 0.74 of its swing and $K_u$ reaches 0.56."))
    A(heading("C. The map: from the gate to the conducting fraction"))
    A(para("The stage law produces the gate trajectory $G_{UP}(t)$ and nothing else. An IBIS-based model needs "
           "at each instant the fraction $K_u$ of the pull-up table that is conducting. A second relation, "
           "separate from the stage law, connects the two: with the gate only partly on, the output transistor "
           "delivers less than its table, and the reduction is taken to be one multiplier at every pad voltage, "
           "$I(V_{pad}, g) = K_u(g)\\,I_{PU}(V_{pad})$, which is the assumption any $K_u$-based model already "
           "makes. The map is the function $K_u(g)$, a curve against the gate, not against time.", "FirstParagraph"))
    A(para("Where the gate node can be probed the curve can be measured: at each instant of a full transition the "
           f"gate level and the file's $K_u$ are read together and plotted against each other ({F('map')}(a), (b)). "
           "On the three buffers where this was done, the curve traced while the gate rises coincides with the one "
           "traced while it falls within 0.07–0.11, so $K_u$ depends on the gate alone. The curve is described by "
           "a two-parameter formula scaled between the settled off and on levels of the file's own $K_u$ and $K_d$:"))
    A(equation("K_u(t) = k_{off} + (k_{on} - k_{off})~M(G_{UP}(t)), \\\\ M(g) \\triangleq \\clip\\left( \\frac{g - v_{t,map}}{g_s - v_{t,map}}, 0, 1 \\right)^{a}", 22, size=18))
    A(equation("K_d(t) = d_{off} + (d_{on} - d_{off})~M(G_{DN}(t))", 23))
    A(para("$v_{t,map}$ is the gate level at which the output device starts to conduct, $a$ bends the curve between "
           "that point and $g_s = 1$ where the table is fully on (below 1, the curve rises steeply and then "
           "flattens), and $k_{off}$, $k_{on}$, $d_{off}$, $d_{on}$ are the settled levels, close to 0 and 1. The "
           "same function $M$, with the same shape, serves both devices in (22) and (23); only the levels differ. The "
           "form is borrowed from the gate factor (5), because the map describes how the output transistor turns "
           "on, but its parameters are empirical: fitted to the measured maps they are (0.57, 0.64) on ex2, "
           "(0.49, 0.60) on inv_chain and (0.50, 0.78) on io_buf, and they are distinct from the stage parameters "
           "$v_t$ and $p$, which describe the predriver.", "FirstParagraph"))
    A(para("The file does not contain the map. It gives $K_u$ against time; the map is $K_u$ against the gate; "
           "converting one into the other needs the gate against time, the one waveform an IBIS file does not "
           "have. The method therefore does not obtain the map from the file: it offers three fixed shapes "
           f"({F('map')}(c)) and leaves the choice among them to the stressed measurement ({S('ident', 'E')}). The "
           "three are built-in constants: (0.50, 0.70) lies near the middle of the three measured maps; "
           "(0.40, 0.60) and (0.40, 0.90) were retained from an earlier search scored on the same twelve test "
           "buffers. Their generality is untested, and this is the least well founded element of the method."))
    A(fig("map", "The map. (a) With the gate of ex2 probed, the gate level (squares) and the file's $K_u$ (circles) "
                 "are read at the same instants of a full transition. (b) $K_u$ against the gate: the measured map, "
                 "and the formula (22) fitted to it, $(v_{t,map}, a) = (0.57, 0.64)$. (c) The three shapes offered "
                 "when the gate cannot be probed, with the measured map of ex2 for reference."))
    A(para(f"{F('gate_to_ku')} shows the two relations evaluated one after the other on ex2: (19)–(21) give the gate, "
           "and (22) is applied to each of its values. For a full transition (top row) the gate sweeps its full "
           "range, the whole map is read, and the result can be compared with the file; this comparison is the fit "
           f"of {S('ident', 'C')}. For an 810 ps pulse (bottom row) the gate turns back at 0.74, only the lower part "
           "of the map is read, and $K_u$ rises to 0.56 and returns to zero: a waveform no table of the file "
           "contains, produced by the same two relations with no additional parameter.", "FirstParagraph"))
    A(fig("gate_to_ku", "From the gate to the conducting fraction on ex2 (probed-map setting; $K = 3$, map (0.57, 0.64)). Left: the gate "
                        "from the stage law. Middle: the map (22), with the gate values at six instants. Right: the "
                        "resulting $K_u(t)$. (a)–(c) Full transition, against the file's $K_u(t)$. (d)–(f) An 810 ps "
                        "pulse after calibration."))
    A(heading("D. The pad current"))
    A(para("The current delivered to the die node is that of the existing model,", "FirstParagraph"))
    A(equation("I_{die}(t) = K_u(t)~I_{PU}(V_{die}) + K_d(t)~I_{PD}(V_{die}) \\\\ + I_{PC}(V_{die}) + I_{GC}(V_{die})", 24, size=18))
    A(para("where $I_{PU}$, $I_{PD}$ are the pull-up and pull-down tables of the file, held at their end values "
           "outside the tabulated range, and $I_{PC}$, $I_{GC}$ are the clamp tables, present only when the file "
           "contains them (io_buf does; ex2 and inv_chain do not). $C_{comp}$ loads the die node and the package "
           "$R$, $L$, $C$ connect it to the pad. Two details of the existing model are kept unchanged: the fractions "
           "pass through a first-order lag of 5 ps before they scale the tables, and a tabulated correction of up to "
           "about 0.1, indexed by the time since the input edge and fitted so that the replayed complete transition "
           "reproduces the solved curve, is added to the map output. Both belong to the existing model and are not "
           "part of the proposed method.", "FirstParagraph"))

    # ================================================================ IV. identification
    A(heading(f"{SEC['ident']}. Identification from the File and One Measurement", 1))
    A(heading("A. Overview"))
    A(para(f"{F('workflow')} draws the procedure and {T('procedure')} lists it; the steps are numbered 0 to 4 "
           "throughout. The quantities of the model have four origins. The I–V tables and the package come from "
           "the file and are never changed; $C_{comp}$ is declared in the file but is re-estimated from the file's "
           f"own waveforms in step 0 ({S('ident', 'B')}), because the solved $K_u(t)$, $K_d(t)$ depend on it. The "
           "constants $x_{lin}$ and $p$ of the stage law and the three candidate map shapes are built in: their "
           "values were chosen during development with knowledge of the test buffers' transistors, and they are "
           "the method's assumptions. The stage rates $s_{up}$, $s_{dn}$ and a first value of the threshold $v_t$ "
           "are fitted to the file (step 1). The stage count $K$, the map shape and the final $v_t$ are settled by "
           "one measurement (steps 3 and 4). Applying the method to a new buffer needs the file, one pad "
           "measurement and one structural decision, whether the two output devices share a predriver node or "
           f"have separate paths ({S('model', 'B')}); it needs no other transistor-level information, but the "
           "method is not derived from the file alone.", "FirstParagraph"))
    A(para("Step 1 integrates (19)–(21) in Python, and a fit takes seconds. Steps 3 and 4 simulate the complete "
           "circuit model in ngspice, ten runs per candidate, about ninety per buffer. The result is a SPICE "
           "subcircuit written by the converter, in which each stage is a behavioral current source charging a "
           "capacitor and the map a piecewise-linear behavioral source, with the file's tables as in the existing "
           "model; it was run in ngspice and has not been tested in other simulators."))
    A(fig("workflow", "The procedure as a flow. Grey: from the IBIS file. Orange: assumed, built into the method. "
                      "Teal: fitted or computed. Red: the one measurement."))
    A(tab_col("procedure", "The procedure ($p = 1$ fixed; $x_{lin} = 0.45$ fixed on ten of the twelve buffers, fitted on two)",
              ["Step", "What is determined", "Data used", "Eq."],
              [["0", "I–V tables, package; $C_{comp}$ estimated; full-swing $K_u(t)$, $K_d(t)$ solved with it; the normalized target", "IBIS file, converter", "(24)–(25)"],
               ["1", "$s_{up}$, $s_{dn}$, initial $v_t$, per candidate stage count and map shape", "full-swing $K_u(t)$ of the file", "(26)"],
               ["2", "Candidates: three stage counts × three map shapes", "fit residuals of step 1", "(27)"],
               ["3", "$v_t$, for each candidate", "peak of one stressed pad waveform", "(28)"],
               ["4", "Stage count $K$ and map shape", "the same waveform, whole shape", "(29)"]],
              [560, 2250, 1490, 700]))
    _selr = next(r for r in lg["cands"] if r["selected"])
    A(para("ex2 is the running example, in two settings, and every figure and table names the one it uses. In the "
           f"*probed-map setting* ({F('chain')}, {F('gate_to_ku')}, {F('target')}–{F('rms_vs_k')}, {T('shapes')}) the "
           "map shape and $C_{comp}$ are those measured on its netlist, (0.57, 0.64) and 1.7 pF, so that the "
           "model's gate can be compared with the probed gate; these figures explain the fit and are not part of "
           f"the procedure. In the *file-only setting* ({T('fit_all')}, {T('ledger')}, {F('stress_use')}, "
           f"{F('calib_mech')} and {S('verify', 'B')}) only what the file and one measurement provide is used: "
           f"$C_{{comp}}$ estimated from the file ({lg['cc_knee']} pF) and the three candidate shapes. Numbers of the "
           f"same name differ between the settings: the one-stage residual is {float(k1['rms']):.3f} in the first and "
           f"{lg['rms_by_k'][0]:.3f} in the second, the fitted threshold {float(k3['vt']):.3f} and "
           f"{_selr['vt_fit']:.3f}.", "FirstParagraph"))

    A(heading("B. Step 0: the target"))
    A(para("The only curve the stage law is ever fitted to is the file's own conducting fraction through one "
           f"complete transition. The converter obtains it from the two fixtures the specification prescribes "
           f"{C('ibis', 'cookbook')}: at each instant of the "
           "rising transition the current into the die node must balance in both, with $V_i(t)$ the pad voltage "
           "recorded in fixture $i$,", "FirstParagraph"))
    A(equation("K_u(t)~I_{PU}(V_i(t)) + K_d(t)~I_{PD}(V_i(t)) \\\\ = \\frac{V_{fix,i} - V_i(t)}{R_{fix}} - C_{comp}\\frac{dV_i}{dt},\\quad i = 1, 2", size=18))
    A(para("(the clamp currents join the right-hand side when the file has them). Two equations in two unknowns "
           f"are solved at every sample, for the rising and for the falling transition ({F('target')}(a), (b)). This "
           f"is the standard two-waveform solution {C('wang')} and is not part of the proposed method.", "FirstParagraph"))
    A(para("*The die capacitance.* The right-hand side subtracts the displacement current of $C_{comp}$, so the solved "
           "fractions depend on the value assumed for it, and a value that is too large books capacitor current as "
           "device current: the solved $K_u$ then exceeds 1, which asks the pull-up device for more current than "
           f"its table holds. On ex2 the declared {ti['cc_declared']:.1f} pF gives a peak $K_u$ of "
           f"{ti['ku_at_declared']:.2f} ({F('target')}(c)). The method therefore re-estimates $C_{{comp}}$ from the "
           "file itself: the peak of the solved $K_u$ is computed for a range of assumed values, and the rising "
           "branch of that curve (between 1.05 and 1.35) is extrapolated back to $K_u = 1$, as a threshold voltage "
           f"is read from a transfer curve. The estimate, {ti['cc_knee']:.2f} pF on ex2, replaces the declared value "
           f"on every buffer, upward or downward ({T('fit_all')}, second column). A measurement on the netlist, "
           f"which the method never uses, gives {ti['cc_loop']:.2f} pF for ex2; the probed-map setting uses that "
           "value."))
    A(para(f"The native element derives its own coefficients from the same two waveforms {C('hspice')} and exposes "
           "them through its xv_pu and xv_pd outputs. Read through them during the same 10 ns transition, its $K_u$ "
           f"follows the solved curve within {ti['nat_rms']:.3f} rms ({F('target')}(b)), which is what {S('intro')} "
           "means by the same replay inside the simulator."))
    A(para("The existing model reproduces the solution: driven through one 10 ns input pulse, its internal node "
           f"carrying the table value follows the solved $K_u(t)$ within {ti['rms_r']:.3f} rms on ex2 once aligned "
           "on the input edge. The target is read from that node rather than from the solved curve directly, so "
           "that the fit sees $K_u$ exactly as the circuit replays it, with the converter's settled levels and lag, "
           "on the time base of the circuit's own input comparator, which also drives the chain, (20). The target "
           "is the node's value normalized between its settled off level at $t_{rest}$ and its settled on level at "
           "$t_{on}$:"))
    A(equation("\\hat{K}_u(t) = \\clip\\left( \\frac{K_u(t) - K_u(t_{rest})}{K_u(t_{on}) - K_u(t_{rest})}, 0, 1 \\right), \\\\ t_{rest} = 4.5~\\text{ns},\\quad t_{on} = 12~\\text{ns}", 25, size=18))
    A(para("with the input edge at 5 ns, sampled every 2 ps from 4 to 21 ns. During the fit the chain receives the "
           "same 10 ns pulse as an ideal step at the mid-point of the input edge, (20), so that the rising edge of "
           "the target constrains $s_{up}$ and the falling edge $s_{dn}$. Nothing in this curve says how many stages "
           f"produced it or where their thresholds lie; that is the subject of {S('ident', 'D')}.", "FirstParagraph"))
    A(fig("target", "The target on ex2 (probed-map setting, 1.7 pF). (a) The file's V–T waveforms: one rising and "
                    "one falling transition, each recorded into two fixtures (inset: the fixture, pad, $R_{fix}$, "
                    "$V_{fix}$). (b) $K_u(t)$, $K_d(t)$ solved from (a) by the converter (grey), the existing model's "
                    "$K_u$ through a 10 ns pulse (teal), the native element's own coefficient through the same pulse "
                    "(blue, dotted), and the normalized target (25) with the chain input (20). (c) The estimate of $C_{comp}$ from the file: "
                    "the peak of the solved $K_u$ against the assumed $C_{comp}$, with the declared value, the "
                    "estimate (the rising branch extrapolated to 1) and the value measured on the netlist."))

    A(heading("C. Step 1: fitting the stage law through an assumed map"))
    A(para("For an assumed stage count $K$ and an assumed map shape, one of the three of "
           f"{F('map')}(c), the stage parameters minimize the root-mean-square mismatch between the model's "
           "conducting fraction and the target:", "FirstParagraph"))
    A(equation("\\{ s_{up}, s_{dn}, v_t \\}^{\\star} = \\arg \\min~R,\\quad x_{lin},~p~\\text{fixed} \\\\ R = \\rms_t \\left[ M(v_K(t)) - \\hat{K}_u^{file}(t) \\right]", 26, size=18))
    A(para("with $0 \\le v_t \\le 0.7$; $R$ is the residual. The map is an input to the fit and not a result of it. The residual is "
           "accumulated almost entirely within the two edges of the target, each about 0.7 ns wide on ex2, because "
           "the curve is flat at 0 or 1 elsewhere; a residual of 0.023 means that, averaged over the window, the "
           "model is 2.3 % of the full swing away from the file, most of it a small timing and shape difference at "
           "the edges. For a buffer with a separate pull-down path, the pull-down chain is fitted in the same way to "
           "$K_d(t)$ through its own map.", "FirstParagraph"))
    _k = d["knobs"]
    A(para(f"*What each number does.* {F('fit_knobs')}(a)–(c) varies one fitted number at a time around the fitted "
           "values. $s_{up}$ is the charging rate of every stage: a larger value brings the rising edge earlier and "
           "makes it steeper. $s_{dn}$ does the same for the falling edge. $v_t$ is the level a stage's input must "
           "reach before the stage starts: at fixed rates it moves the edge in time without changing its "
           f"steepness. Panel (d) builds a fit one number at a time from a poor first guess: adjusting $s_{{up}}$ "
           f"takes the residual from {_k['first guess']:.3f} to {_k['$s_{up}$ adjusted']:.3f}, $s_{{dn}}$ to "
           f"{_k['$s_{dn}$ adjusted']:.3f}, and $v_t$ to {_k['$v_t$ adjusted: the fit']:.3f}."))
    A(fig("fit_knobs", "The fit (26) as three knobs, on ex2 (probed-map setting: $K = 3$, map (0.57, 0.64), $x_{lin} = 0.45$). (a)–(c) "
                       "The model's $K_u(t)$ as $s_{up}$, $s_{dn}$ and $v_t$ are varied one at a time around the "
                       "fitted values; (b) is the falling edge at 10 ns. (d) A fit built one number at a time."))
    A(para("*How the minimum is found.* The residual is not differentiable (the chain is a simulation with "
           f"thresholds and clips), so (26) is minimized by Nelder–Mead {C('nelder')}: a simplex of four trial points that is "
           "reflected away from its worst corner, extended when that helps, contracted when it does not, and shrunk "
           "towards its best corner when nothing helps. The rates are searched on a logarithmic scale, $v_t$ "
           "linearly within its bounds; the search stops when the simplex has collapsed or after 800 iterations, "
           f"and it is run from three starts, $s_{{up}} = s_{{dn}} = 2$, 8 and 30 per ns. {F('fit_search')} shows "
           "the search on ex2. The valley is narrow in the rates (a 27 % change in $s_{up}$ triples the residual) "
           f"and shallow along $v_t$ on the low side ({land['z0']:.3f} at $v_t = 0$, {land['zmin']:.3f} at "
           f"{land['vt_min']:.2f}, {land['z07']:.3f} at the 0.7 bound). The three runs took {se[2]['n']}, "
           f"{se[8]['n']} and {se[30]['n']} evaluations, and only the run from 2 per ns reached the minimum "
           f"({se[2]['end'][3]:.4f}); the others stopped in side valleys at {se[8]['end'][3]:.3f} and "
           f"{se[30]['end'][3]:.2f}. The procedure keeps the best of the three; the search is local, and one start "
           "is not enough.", "FirstParagraph"))
    A(fig("fit_search", "The search on ex2 (probed-map setting). (a) The residual of (26) over $s_{up}$ and $v_t$ at the fitted $s_{dn}$ "
                        "and (b) over $s_{up}$ and $s_{dn}$ at the fitted $v_t$; darker is lower. Squares: the three "
                        "starts; stars: where each run ended; red circle: the fit. (c) The best residual against the "
                        "number of evaluations."))
    A(para(f"*Why several stages.* With a single stage, one number sets both the delay and the edge. On ex2 the "
           f"file's $K_u(t)$ starts {ov['file_start']:.1f} ns after the input edge and rises in 0.66 ns, which no single "
           f"value of $s_{{up}}$ can give: the best one-stage fit has a residual of {float(k1['rms']):.3f} against "
           f"{float(k3['rms']):.3f} for three stages. With several identical stages the delay is spent in the "
           "handovers and the edge belongs to the last stage, so delay and edge are set separately. This is the "
           "reason for the chain, and also why the stage count cannot be read from the fit: beyond the minimum "
           f"number, more stages redistribute the same delay ({S('ident', 'D')}).", "FirstParagraph"))
    _bound = [r for r in fa if r["vt_fit"] > 0.698]          # at the 0.7 bound to the table's three decimals
    _rmss = [r["rms"] for r in fa]
    A(para(f"*Result.* On ex2 with $K = 3$ in the probed-map setting, (26) gives $s_{{up}} = {float(k3['s_up']):.2f}$/ns, "
           f"$s_{{dn}} = {float(k3['s_dn']):.2f}$/ns and $v_t = {float(k3['vt']):.3f}$ at a residual of "
           f"{float(k3['rms']):.3f} ({F('gate_to_ku')}(c)). {T('fit_all')} gives the fit on all twelve buffers in "
           "the file-only setting, for the stage count and map shape the procedure finally selected: residuals "
           f"{min(_rmss):.3f}–{max(_rmss):.3f}. On {len(_bound)} of the twelve the fitted $v_t$ sits on its upper "
           "bound: with these map shapes the fit would place the handovers even later than the bound allows, and "
           "the calibration of step 3 then lowers $v_t$ on every buffer calibrated through the threshold (last "
           f"column). This is the non-identifiability of the threshold seen from the other side ({S('ident', 'D')}): "
           "the file pushes $v_t$ to wherever the assumed map lets the composition match, and the measurement puts "
           "it where the short pulse says. io_buf's single-stage chain could not reach the measured peak by its "
           "threshold alone and was calibrated through the fallback of step 3, a common scale on its two rates "
           f"({S('ident', 'E')}).", "FirstParagraph"))
    _fa_rows = []
    for r in fa:
        cal = f"{r['vt_cal']:.3f}" if abs(r["rate_scale"] - 1) < 1e-3 else f"rates × {r['rate_scale']:.2f}"
        _fa_rows.append([r["dev"], f"{d['cc_declared'][r['dev']]:g} → {r['cc']:g}", str(r["K"]), f"({r['shape'][0]:g}, {r['shape'][1]:g})",
                         f"{r['s_up']:.2f}", f"{r['s_dn']:.2f}", f"{r['vt_fit']:.3f}", f"{r['rms']:.4f}", cal])
    A(tab_wide(pkg, "fit_all", "The fit (26) on the twelve test buffers in the file-only setting, for the selected "
               "stage count and map shape ($C_{comp}$: declared in the file → estimate used; $x_{lin}$ = 0.45 except "
               + " and ".join(f"{r['dev']} ({r['x_lin']:.2f})" for r in fa if abs(r["x_lin"] - 0.45) > 1e-6)
               + ", fitted; last column: after step 3)",
               ["Buffer", "$C_{comp}$ (pF)", "$K$", "Map shape", "$s_{up}$ (/ns)", "$s_{dn}$ (/ns)", "$v_t$ fitted",
                "Residual", "$v_t$ calibrated"], _fa_rows, [1400, 1400, 550, 1150, 1000, 1000, 950, 950, 1200]))

    A(heading("D. What the file cannot determine"))
    A(para("A complete transition is two edges. Two edges fix two rates and one delay, and the fit has exactly "
           "those three numbers to spend. Anything that acts only when a transition is cut short, how many stages "
           "share the delay, where each hands over, how the output transistor turns on in between, leaves no mark "
           "on a complete transition. This subsection shows it in numbers.", "FirstParagraph"))
    _hdr = ["Map shape $(v_{t,map}, a)$"] + [f"({v:g}, {a_:g})" for v, a_ in d["shape_order"]]
    _tr = []
    for _dev in ("ex2", "inv_chain"):
        _tr.append([_dev] + [f"{d['shapes'][(_dev, v, a_)]['rms']:.4f}" for v, a_ in d["shape_order"]])
    _e = [d["shapes"][("ex2", v, a_)]["rms"] for v, a_ in d["shape_order"]]
    _i = [d["shapes"][("inv_chain", v, a_)]["rms"] for v, a_ in d["shape_order"]]
    _la, _ea = d["shapes"][("ex2", 0.6, 0.6)], d["shapes"][("ex2", 0.4, 0.6)]
    A(para(f"*The map.* {T('shapes')} gives the residual of (26) on ex2 and inv_chain for six assumed shapes. It "
           f"varies by {100 * (max(_e) / min(_e) - 1):.0f} % and {100 * (max(_i) / min(_i) - 1):.0f} % across them, "
           "and its small preference does not point at the measured map: on ex2 the shape nearest the measured one, "
           f"(0.6, 0.6), has the largest residual. {F('ambiguity')} shows why. Through the later-starting map "
           f"(0.6, 0.6) the fit gives $v_t = {_la['vt']:.3f}$; through the earlier-starting map (0.4, 0.6) it gives "
           f"$v_t = {_ea['vt']:.3f}$, a gate that leaves later; for a full transition the two are indistinguishable "
           f"(residuals {_la['rms']:.4f} and {_ea['rms']:.4f}). Driven by an 810 ps pulse they are not: the first "
           "delivers a conducting fraction of 0.51, the second none at all, because its higher threshold "
           "extinguishes the pulse inside the chain. Two models that the file cannot tell apart give opposite "
           "answers for the short pulse."))
    _hdr = ["Shape $(v_{t,map}, a)$"] + [f"({v:g}, {a_:g})" for v, a_ in d["shape_order"]]
    A(tab_wide(pkg, "shapes", "Residual of (26) for six assumed map shapes (probed-map setting; $K = 3$ for ex2, 7 for inv_chain)",
               _hdr, _tr, [1300] + [950] * 6, size=16, width=7000, jc="center"))
    A(fig("ambiguity", "Two assumed maps on ex2 ($K = 3$, $C_{comp}$ 1.7 pF), each with the stage law fitted through it to the same "
                       "file. (a) The maps. (b) The gate each fit produces. (c) Full transition: both reproduce the "
                       "file. (d) An 810 ps pulse, before calibration: one passes it, the other extinguishes it."))
    ex, iv = d["ku"][("ex2", "linear_const")], d["ku"][("inv_chain", "linear_const")]
    r_ex = d["rms"][("ex2", "pull-up")]["rms_by_K"].split()
    r_iv = d["rms"][("inv_chain", "pull-up")]["rms_by_K"].split()
    A(para(f"*The stage count.* {F('rms_vs_k')} gives the residual of (26) against $K$ for the thirteen predriver "
           "chains of the twelve test buffers, each $K$ fitted independently; the netlists are available, so the "
           f"true count is known. $K = 1$ fails on ex2 and inv_chain ({float(r_ex[0]):.3f} and {float(r_iv[0]):.3f} "
           "against 0.02 and 0.007), so the full swing does constrain the rate. Beyond that the residual is flat: on "
           f"ex2, $K = 3$ to 6 lie within 0.002 of each other and the minimum is at $K = 5$ although the netlist has "
           "three stages; on inv_chain, $K = 6$ to 9 differ in the fourth decimal. The margin between the best and "
           "the second-best $K$ is at most 0.0007 on twelve of the thirteen chains; only io_buf's single-stage "
           "pull-up has a distinct minimum. The procedure therefore keeps a band of stage counts instead of a point "
           "estimate, the three smallest whose residual is within 25 % of the best:", "FirstParagraph"))
    A(equation("\\text{band} = \\text{the~three~smallest}~K \\\\ \\text{with}~\\rms(K) \\le 1.25~\\min_{K'}~\\rms(K')", 27, size=18))
    A(para("On the twelve test buffers the band contains the netlist stage count in every case. The tolerance and "
           "the band width were chosen on these same buffers, so this is a property of the rule as tuned and not "
           "an independent validation.", "FirstParagraph"))
    A(fig("rms_vs_k", "Residual of (26) against stage count for the thirteen predriver chains of the twelve test "
                      "buffers (probed-map setting; io_buf has two chains). Circles mark the netlist stage count; "
                      "the thick segments mark the band (27)."))
    _c5 = next(r for r in lg["cands"] if r["K"] == 5 and r["shape"] == (0.5, 0.7))
    _res = (f"at the same residual, {float(k3['rms']):.4f}" if abs(float(k3["rms"]) - _selr["rms"]) < 5e-5
            else f"at residuals of {float(k3['rms']):.4f} and {_selr['rms']:.4f}")
    A(para(f"*The threshold, the exponent, the boundary.* The fitted $v_t$ of ex2 is {float(k3['vt']):.3f} in the "
           f"probed-map setting and {_selr['vt_fit']:.3f}, on its bound, in the file-only setting, both with $K = 3$ "
           f"and {_res}; in the file-only setting with $K = 5$ "
           f"it is {_c5['vt_fit']:.3f} at {_c5['rms']:.4f}. The threshold slides with the map and the stage count "
           "while the residual barely moves. At full swing each stage input dwells at the rail, where (17) does not "
           "depend on $p$: in gate-domain fits of the individual probed stages of ex2 and inv_chain (the setting of "
           f"{S('verify', 'A')}) every $p$ between 1 and 2 reaches a residual of 0.002–0.007. If $x_{{lin}}$ is left "
           f"free in (26) it settles at {float(ex['x_lin']):.3f} on ex2 and {float(iv['x_lin']):.3f} on inv_chain, "
           f"less than half the measured $x_0$ of {T('device')}, and replacing (18) by the drive-dependent boundary "
           "of (15) changes the residual by about 1 % on ex2 and not at all on inv_chain. This is why $x_{lin}$ and "
           "$p$ are held fixed rather than fitted. A fit with every stage free is worse than uninformative: on ex2 "
           "with $K = 2$ and all eight parameters free (a gate-domain fit), the full-swing residual against the probed gate falls below "
           "that of the identical-stage fit with the correct $K = 3$, with one very slow stage and one fast one, and "
           "such a chain extinguishes short pulses (stressed gate peak 0.228 where 0.758 is measured). Sharing one "
           "parameter set (A3) removes this solution and leaves $K$ as the single structural unknown, chosen within "
           "the band (27) by the measurement.", "FirstParagraph"))

    A(heading("E. Steps 2–4: the single stressed measurement"))
    _lo, _hi, _pk = d["stress"]
    A(para("After step 1 there is not one model but several, and all of them reproduce the file. They differ in "
           "exactly the quantities that decide what happens when the input is cut short, so one measured short "
           f"pulse can tell them apart. {F('stress_use')}(b) shows how far they disagree: for ex2 the nine "
           "candidates of step 2, three stage counts from the band (27) × three map shapes, each fitted to the same "
           f"file, driven by the same 810 ps pulse, give pad peaks from {_lo:.2f} to {_hi:.2f} V against {_pk:.2f} V "
           "measured. The measurement is the pad voltage for one short input pulse into a known load "
           f"({F('stress_use')}(a)); nothing inside the buffer is observed. It is taken at the calibration width, the "
           "pulse width at which the pad reaches about 50 % of the settled swing into 50 Ω and 2 pF, the deepest of "
           "the five test depths; a user finds it by shortening the pulse until the pad peak is about half the "
           f"settled swing (deeper pulses were not tested, {S('verify', 'C')}). In the tests below it comes from a "
           "transistor-level simulation; for a user it would be a bench measurement or a waveform supplied by the "
           "vendor.", "FirstParagraph"))
    A(fig("stress_use", "Use of the stressed measurement on ex2 (file-only setting). (a) The measurement: pad voltage for an 810 ps "
                        "pulse. (b) The nine candidates as fitted to the file, driven by the same pulse; dashed: the "
                        "measured peak. (c) After calibration of each threshold on the peak; shaded: the window of (29); "
                        f"teal: the selected candidate. (d) The selected model at the five widths of {S('verify')}."))
    A(para("*Calibration (step 3).* The stage threshold decides how much of a short pulse survives each stage and "
           "so sets the height of the model's pad pulse; it is also the parameter the file determines worst. For "
           "each candidate, with $\\hat{V}$ the measured peak, the peak error", "FirstParagraph"))
    A(equation("e(v_t) \\triangleq \\frac{\\max_t V_{pad}^{model}(t; v_t) - \\hat{V}}{\\hat{V}},\\quad e(v_t^{cal}) = 0", 28))
    A(para("is driven to zero by bisection of $v_t$ on $[0, 0.7]$, all other parameters held at their values from "
           "(26); each evaluation is one circuit simulation of the complete model, three bracket the interval and "
           "seven bisect it. If the threshold cannot bracket the peak, $s_{up}$ and $s_{dn}$ are scaled together "
           "within $[0.5, 2]$ instead. The threshold is used rather than the rates because the rates were fitted to "
           f"reproduce the full swing and moving them degrades it. {F('calib_mech')} shows the calibration on ex2's "
           f"selected candidate: the peak error is {cb['err_lo']:+.0f} % at $v_t = 0$, rises to {cb['emax']:+.0f} % "
           f"near {cb['vt_emax']:.2f}, and falls steeply above 0.55 to {cb['err_hi']:+.0f} % at the bound, where the "
           "chain extinguishes the pulse; the bisection needs only the sign and ends at "
           f"$v_t = {cb['vt_final']:.3f}$, from a fitted value on the bound ({cb['err0']:+.0f} % before).",
           "FirstParagraph"))
    A(fig("calib_mech", "The calibration (28) on ex2's selected candidate ($K = 3$, map (0.5, 0.7), file-only "
                        "setting), 810 ps pulse. (a) The peak error against $v_t$ from a dense sweep, with the ten "
                        "runs of the procedure numbered (orange: bracketing; teal: bisection). (b) The pad waveform at "
                        "four of them against the measurement; dashed: the measured peak."))
    _lags = [r["lag"] for r in lg["cands"]]
    A(para("*Selection (step 4).* After calibration every candidate reproduces the measured peak "
           f"({F('stress_use')}(c)), so the peak can no longer distinguish them. They still differ in when the pulse "
           f"arrives and how it returns, between {-min(_lags) / 1000:.2f} ns early and {max(_lags) / 1000:.2f} ns late "
           "on ex2 (the lag of a candidate is the time shift of its waveform that best matches the measurement over "
           "the pulse, positive when the model is late). The candidate is chosen by the waveform error over the "
           "pulse and its return,", "FirstParagraph"))
    A(equation("(K, v_{t,map}, a)^{\\star} = \\arg \\min~E_W \\\\ E_W = \\rms_{t \\in W} \\left[ V_{pad}^{model}(t) - V_{pad}^{meas}(t) \\right] \\\\ W = [t_f - 0.3~\\text{ns},~t_f + 1.5~\\text{ns}]", 29, size=18))
    A(para(f"where $t_f$ is the falling edge of the input pulse (the shaded interval of {F('stress_use')}(c)); the "
           "window was chosen once and not tuned. One waveform is thus used for two decisions, read from two "
           "features of it: the threshold from its height, the stage count and map shape from its shape. The peak "
           "cannot serve for the second decision: at the calibration width every candidate now matches it, and the "
           "peaks at the other widths would need measurements the method does not have. They would also mislead. "
           "Over the twelve buffers, the mean pad-waveform error at the five test widths is 52.3 mV for the "
           "candidates chosen by (29), against 51.7 mV for the best candidate each grid contains (chosen with "
           "knowledge of all five widths, the floor of any selector) and 217.3 mV for the candidates with the "
           "smallest worst peak error over the five widths, which reach their peaks by arriving 155–300 ps late. A "
           "correct height reached at the wrong time is what the waveform error penalizes and the peak error cannot "
           "see. The measurement can only choose among the candidates it is offered: if the true map is unlike all "
           "three shapes, or the true stage count lies outside the band, it selects the least wrong candidate.",
           "FirstParagraph"))
    A(heading("F. The procedure end to end on ex2"))
    _cands = lg["cands"]
    _selr = next(r for r in _cands if r["selected"])
    _pk0 = [r["peak0"] for r in _cands]
    _pe = [abs(r["peak_err"]) for r in _cands]
    _pr = [r["pad_rms"] for r in _cands]
    _rk = lg["rms_by_k"]
    A(para(f"{T('ledger')} collects what the procedure did on ex2 in the file-only setting. Step 0: the file "
           f"declares $C_{{comp}}$ = {ti['cc_declared']:.1f} pF, with which the solved $K_u$ peaks at "
           f"{ti['ku_at_declared']:.2f}; the estimate of {S('ident', 'B')} gives {lg['cc_knee']} pF, used from here "
           "on. Step 1: the fit at the first candidate shape, (0.50, 0.70), with which the band is determined, gives residuals "
           + ", ".join(f"{x:.4f}"[1:] for x in _rk[:6]) + f" for $K$ = 1 to 6, so the band (27) is "
           f"$K$ ∈ {{{', '.join(str(k) for k in lg['band'])}}}. Step 2: nine candidates. Step 3: the measured peak is "
           f"{lg['peak']:.2f} V; the candidates' peaks before calibration run from {min(_pk0):.2f} to {max(_pk0):.2f} V, "
           f"and after it all are within {max(_pe):.1f} % of the peak. Step 4: the waveform rms (29) runs from "
           f"{min(_pr):.0f} to {max(_pr):.0f} mV across the nine; the selected candidate, $K$ = {_selr['K']} with "
           f"shape ({_selr['shape'][0]:g}, {_selr['shape'][1]:g}), has {_selr['pad_rms']:.0f} mV and arrives "
           f"{abs(_selr['lag']):.0f} ps {'early' if _selr['lag'] < 0 else 'late'}. Its worst peak error over the five "
           f"stressed widths, which the procedure cannot know, is {_selr['worst']:.1f} %.", "FirstParagraph"))
    _cr = []
    for r in sorted(_cands, key=lambda r: (r["shape"], r["K"])):
        _cr.append([str(r["K"]), f"({r['shape'][0]:g}, {r['shape'][1]:g})", f"{r['vt_fit']:.3f}", f"{r['rms']:.4f}",
                    f"{r['peak0']:.2f}", f"{r['vt_cal']:.3f}", f"{r['peak_err']:+.1f}", f"{r['pad_rms']:.0f}",
                    f"{r['lag']:+.0f}", f"{r['worst']:.1f}", "selected" if r["selected"] else ""])
    A(tab_wide(pkg, "ledger", "The nine candidates of ex2 through steps 2–4 (file-only setting). Columns 3–4: the fit (26). "
               f"Peak before: as fitted, 810 ps pulse (measured {lg['peak']:.2f} V). Then, after calibration at that width: "
               "$v_t$, peak error, rms (29) and lag (positive: late). Worst: peak error over the five widths, not available to the procedure",
               ["$K$", "Shape", "$v_t$ fit", "Residual (26)", "Peak before (V)", "$v_t$ cal.", "Peak err. (%)",
                "rms (29) (mV)", "Lag (ps)", "Worst (%)", ""], _cr,
               [500, 1000, 850, 1050, 1050, 850, 1000, 1050, 800, 900, 900], size=15))
    _k45 = [r for r in _cands if r["K"] in (4, 5)]
    A(para(f"Three things can be read off {T('ledger')}. The fit residuals of the nine candidates lie within "
           f"{100 * (max(r['rms'] for r in _cands) / min(r['rms'] for r in _cands) - 1):.0f} % of each other, so the "
           "file does not rank them; their peaks before calibration do. After calibration every candidate matches "
           "the peak, so the peak no longer ranks them and the waveform must. The $K$ = 4 and 5 candidates would "
           f"have scored {min(r['worst'] for r in _k45):.1f}–{max(r['worst'] for r in _k45):.1f} % on the worst peak over "
           f"the five widths against {_selr['worst']:.1f} % for the selected one, but they arrive "
           f"{min(r['lag'] for r in _k45):.0f}–{max(r['lag'] for r in _k45):.0f} ps late at the calibration width, where "
           f"the selected one is {abs(_selr['lag']):.0f} ps early. The waveform error (29) penalizes the late arrival "
           "and the peak score does not, so the two criteria disagree on ex2; the selector cannot know the peak "
           "errors at the other widths in any case, and (29) chooses timing.", "FirstParagraph"))

    # ================================================================ V. verification
    A(heading(f"{SEC['verify']}. Verification", 1))
    A(para("Two claims are verified separately: that the stage law, fitted to a complete transition only, "
           "predicts how the gate responds to a truncated pulse; and that the complete method, built from the file "
           "and one measurement, reproduces the pad voltage of stressed pulses. Both compare the model with the "
           "transistor-level netlist from which the IBIS file was extracted, the golden-waveform check of "
           f"{C('leventhal')}.", "FirstParagraph"))
    A(heading("A. Gate level: the stage law extrapolates from full swing to truncated pulses"))
    A(para("This test uses the internal gate node of the transistor netlist (n4 of ex2, vout7 of inv_chain) and is "
           "therefore not available to a user of the method; its purpose is to test (19). $K$ identical stages are "
           "fitted in the gate domain, that is, the chain output is compared directly with the probed full-swing "
           "gate and no map is involved (a third setting, used only here); the chain is then driven by the stressed "
           "input and compared with the probed stressed gate at the five test widths. No stressed data enters the "
           "fit. The comparison is linear superposition: the node's response to the short pulse predicted by adding "
           "its probed full-swing rising response and its full-swing falling response delayed by the pulse width, "
           "which is exactly what any linear model of the predriver would give.", "FirstParagraph"))
    e = d["ex2"]
    iv_rows = d["inv"]
    have = sorted({int(r["K"]) for r in iv_rows})
    rows = [["ex2, measured"] + [f3(float(r["meas_max"])) for r in e if int(r["K"]) == 3] + [""],
            ["ex2, stage law, $K$ = 3"] + [f3(v) for v in peaks(e, 3)] + [f"{float(next(r for r in e if int(r['K']) == 3)['full_rms']):.4f}"],
            ["ex2, stage law, $K$ = 2"] + [f3(v) for v in peaks(e, 2)] + [""],
            ["ex2, linear superposition"] + [f3(v) for v in peaks(e, 3, "lin_max")] + [""],
            ["inv_chain, measured"] + [f3(float(r["meas_max"])) for r in iv_rows if int(r["K"]) == 7] + [""]]
    for k in (7, 5, 3, 9):
        if k in have:
            rows.append([f"inv_chain, stage law, $K$ = {k}"] + [f3(v) for v in peaks(iv_rows, k)]
                        + [f"{float(next(r for r in iv_rows if int(r['K']) == k)['full_rms']):.4f}"])
    rows.append(["inv_chain, linear superposition"] + [f3(v) for v in peaks(iv_rows, 7, "lin_max")] + [""])
    wid_e = [r["width_ps"] for r in e if int(r["K"]) == 3]
    wid_i = [r["width_ps"] for r in iv_rows if int(r["K"]) == 7]
    A(tab_wide(pkg, "gate", "Peak of the stressed gate: measured, the stage law fitted at full swing only, and linear "
               f"superposition (pulse widths ex2 {wid_e[0]}–{wid_e[-1]} ps, inv_chain {wid_i[0]}–{wid_i[-1]} ps)",
               ["Buffer, model", "narrowest", "2nd", "3rd", "4th", "widest", "Full-swing residual"], rows,
               [2700, 1150, 900, 900, 900, 1050, 1700]))
    r3 = [r for r in e if int(r["K"]) == 3]
    worst3 = max(abs(float(r["pred_max"]) - float(r["meas_max"])) for r in r3)
    lin0 = float(r3[0]["lin_max"]) - float(r3[0]["meas_max"])
    k2 = peaks(e, 2)
    k7 = [r for r in iv_rows if int(r["K"]) == 7]
    err7 = [float(r["pred_max"]) - float(r["meas_max"]) for r in k7]

    def swallowed(K):
        return sum(1 for v in peaks(iv_rows, K) if v < 0.05)

    txt = (f"On ex2 the stage law with the netlist stage count is within {worst3:.2f} of the measured peak at every "
           f"width, where linear superposition is off by {lin0:.2f} at the narrowest pulse ({T('gate')}, "
           f"{F('gate_verify')}(a)); $K = 2$ gives {min(k2):.2f}–{max(k2):.2f}, far below the measurement. On "
           f"inv_chain the stage law follows the measurement at the three widest pulses (within "
           f"{max(abs(x) for x in err7[2:]):.2f}) and undershoots at the two narrowest, by {abs(err7[0]):.2f} at "
           f"104 ps, the partial-drive regime in which approximation A2 is active ({S('disc')}).")
    if 5 in have and 3 in have:
        txt += (f" The other rows show the consequence of the flat residual of {S('ident', 'D')}: with $K = 5$ the "
                f"chain extinguishes {swallowed(5)} of the five stressed pulses and with $K = 3$ it extinguishes "
                f"{swallowed(3)}, at full-swing residuals that the file cannot separate from that of $K = 7$; with "
                "$K = 9$ the pulse passes almost unattenuated.")
    txt += (" A control establishes that the nonlinearity is a property of the buffers and not of the fit: on io_buf, "
            f"at its five test widths ({wd['io_buf'][0]}–{wd['io_buf'][-1]} ps; its transition is slower), every "
            "probed predriver node and the pad follow linear superposition (pad "
            "peak 0.373 measured against 0.371 predicted), whereas the same test fails on the output gate of ex2 "
            "(0.758 against 0.926) and at the pad of inv_chain (0.490 against 0.853).")
    A(para(txt))
    A(fig("gate_verify", "Stressed gate of the transistor netlist against the stage law fitted at full swing only, "
                         "and against linear superposition, at the narrowest, middle and widest of the five pulse widths. "
                         "(a) ex2. (b) inv_chain."))
    A(para("The file-only model's internal gate, which is never fitted to anything, can also be compared with the "
           "probed gate on these two buffers. Its stressed peak is 0.03–0.05 low on ex2 and 0.01–0.08 low on "
           "inv_chain, and it leads the real gate by 56–74 ps and 12–20 ps; on ex2 it returns to zero faster than the "
           "real gate, and the map absorbs the difference at the pad. The structure of (19) produces an internal "
           "gate that resembles the transistor's, while its numbers remain effective parameters."))
    A(heading("B. Pad level: the complete method on twelve buffers"))
    A(para(f"The procedure of {T('procedure')} was applied to the twelve test buffers. For each buffer the model was "
           "built from its IBIS file and one transistor-level pad waveform at the pulse width giving about 50 % of "
           f"the settled swing, with $C_{{comp}}$ estimated from the file as in {S('ident', 'B')}. The model was then "
           "simulated at five pulse widths (about 50 to 90 % of the settled swing) into the same load and compared "
           "with transistor-level simulation. The score is the worst peak error over the five widths, with the peak "
           "error defined as in (28). The calibration width is one of the five, so the score is not entirely held "
           "out. HSPICE's native IBIS element with the same file is the baseline.", "FirstParagraph"))
    rows = []
    for dev, nat, t1, dead, star in d["pad"]:
        k_sh = d["sel"][dev]["rms"].split()
        rows.append([dev, d["knet"][dev], k_sh[0][1:], "(" + k_sh[1].replace("/", ", ") + ")", f"{t1:.1f}",
                     "no valid run" if dead else f"{nat:.1f}" + ("*" if star else "")])
    t1s = [x[2] for x in d["pad"]]
    live = [x[1] for x in d["pad"] if not x[3]]
    starred = [x for x in d["pad"] if x[4]]
    dead_ = [x for x in d["pad"] if x[3]]
    A(tab_wide(pkg, "pad", "Pad-level result on the twelve test buffers (worst of five stressed pulse widths, file-only setting"
               + (f"; *: native with its V–T tables resampled onto {d['rows_rs']} rows, see text)" if starred else ")"),
               ["Buffer", "Netlist $K$", "Selected $K$", "Selected map shape", "Proposed: worst peak error (%)",
                "Native IBIS: worst peak error (%)"], rows, [1700, 1100, 1200, 1700, 2000, 1900]))
    _nat = (f"The native element's worst peak error is {min(live):.0f}–{max(live):.0f} % on "
            + (f"the {len(live)} buffers for which it produced a valid run. " if dead_ else "the twelve buffers. "))
    A(para(f"The proposed model is within 10 % on all twelve buffers (range {min(t1s):.1f}–{max(t1s):.1f} %, mean "
           f"{sum(t1s) / len(t1s):.1f} %; {T('pad')}, {F('pad_summary')}, {F('pad_waveforms')}). " + _nat
           + "The selected stage count equals the netlist count on eleven buffers (inv_chain selects 6 against 7).",
           "FirstParagraph"))
    A(fig("pad_summary", "Worst stressed peak error over the five test widths on the twelve buffers: HSPICE's native "
                         "IBIS element against the proposed model built from the file and one stressed measurement. "
                         "Starred: native with its V–T tables resampled, as described in the text."))
    A(fig("pad_waveforms", "Pad voltage for the narrowest stressed pulse of three buffers: transistor-level reference, "
                           "HSPICE native IBIS, and the proposed model built from the file and one stressed measurement. "
                           "Percentages are peak errors against the reference."))
    _dg = d["diag"]
    _flat = [abs(float(r["peak_err_pct"])) for r in _dg if r["recipe"] == "flat300" and r["pulse"] != "10 ns" and r["valid"] == "1"]
    _rows = [abs(float(r["peak_err_pct"])) for r in _dg if r["recipe"] in ("rows100", "rows200") and r["pulse"] != "10 ns" and r["valid"] == "1"]
    _nf = d["natfail"]
    if starred and _flat and _rows:
        A(para(f"*The native element on the variant files.* On the five ex2 variants the native element produced no "
               f"waveform with the files as generated; the starred entries of {T('pad')} and {F('pad_summary')} come "
               f"from the same files with every V–T table resampled onto {d['rows_rs']} rows ({_nf['step_rs']:.0f} ps on "
               f"ex2_base) and nothing else changed. {F('native_fail')} shows the cause. The variant files sample their "
               f"tables at 2.2–2.7 ps, three times finer than the shipped ex2 file, and the resampled table is the same "
               f"waveform ({F('native_fail')}(a)); before the edge the variant file and the shipped file both carry "
               f"about {_nf['ripple_as_mV']:.1f} mV rms of ripple about their trend. The element's two-waveform solver "
               f"{C('hspice')} latches $K_u$ near {_nf['ku_dead_max']:.1f} when the reversal of a short pulse lands in "
               f"that lead-in and never recovers, without a warning ({F('native_fail')}(b)). Four observations locate "
               "the fault: every as-generated file runs under a 10 ns pulse; holding the first 300 ps of every table "
               "flat revives every variant; adding 0.3 mV rms of noise to the first nanosecond of the shipped ex2 "
               "tables resampled at 2.7 ps kills the element on the shipped file, where 0.1 mV does not and the same "
               "0.3 mV at 300 rows does not; and the converter's own solution of the same files is unaffected. The "
               "solver fails on sub-millivolt sample-to-sample variation when the samples are closer than a few "
               "picoseconds, which is not a property of the buffers or of the files' electrical content. The revived "
               "score depends on the edit (the flat lead-in, "
               "which also removes the feedthrough dip that precedes the edge, gives "
               f"{min(_flat):.0f}–{max(_flat):.0f} % on the three variants tested; 100 or 200 rows "
               f"{min(_rows):.0f}–{max(_rows):.0f} %), so {T('pad')} uses the least invasive edit, and the native "
               "element then fails on the variants as it does on the shipped ex2, by replaying the coefficients of a "
               "complete transition against a pulse that interrupts it. What the solver does with the ripple is not "
               "visible from outside; the runs above characterize it and nothing more is claimed."))
        A(fig_col(pkg, "native_fail", "Why the native element has no valid run on the variant files, on ex2_base. (a) The "
                                      f"lead-in of the rising V–T table into the 0 V fixture: as generated ({_nf['step_as']:.1f} ps), "
                                      f"resampled onto {d['rows_rs']} rows ({_nf['step_rs']:.0f} ps) and, for comparison, the "
                                      "shipped ex2 table (8 ps). (b) The element's $K_u$ under the 812 ps pulse on the "
                                      "as-generated and on the resampled file, against the $K_u$ solved from the "
                                      "transistor's own fixture runs (undefined within about 90 ps of the reversal)."))
    A(heading("C. Limits of the evidence"))
    A(para("The gate-level test establishes that the structure of (19) extrapolates from full swing to truncated "
           "pulses when fitted to the true gate; the pad-level test establishes the accuracy of the file-only "
           "procedure, in which the gate is never observed. Both have a narrow statistical base: the five pulse "
           "widths of a buffer sample one stressed trajectory and are strongly correlated, so the evidence rests on "
           "the number of buffers. The pad-level test covers single high-going pulses, one load and the typical "
           "corner; pulse trains, low-going pulses, other loads and other corners are outside it. The map-shape "
           "grid and the band rule (27) were chosen on these same twelve buffers.", "FirstParagraph"))

    # ================================================================ VI. discussion
    A(heading(f"{SEC['disc']}. Discussion: Approximations and Limits", 1))
    A(tab_wide(pkg, "approx", "Approximations of the model", ["Label", "Approximation", "Introduced at", "What it removes", "Evidence"],
            [["A0", "One $V_{TH}$, $\\alpha$, $V_{D0}$ for both devices of a stage", "(13)–(14)",
              "Per-device parameters", f"As in {C('sakurai', suffix='Sec. VI')}. {T('device')}: the N and P devices differ ($x_0$ 0.34 against 0.57 on inv_chain)"],
             ["A1", "$p$ in place of $\\alpha$, with $p = 1$", "(17)", f"The measured $\\alpha$ ({T('device')})",
              f"Not identifiable from the file ({S('ident', 'D')})"],
             ["A2", "$x_0 g^{\\alpha/2} \\to x_{lin}$, with $x_{lin} = 0.45$", "(18)",
              "Drive dependence of the saturation boundary",
              f"Not identifiable from the file; candidate cause of the inv_chain undershoot in {T('gate')}"],
             ["A3", "$K$ identical normalized stages", "(20)", "$4(K - 1)$ free parameters",
              f"Free fit fails ({S('ident', 'D')}); $K$ selected by (29)"],
             ["A4", "Map shape taken from a grid of three", "(22), (26)", "Trade-off between gate and map",
              "Selected by (29); grid chosen on the test buffers"]],
            [650, 2700, 1300, 2150, 2800]))
    A(para(f"{T('approx')} collects the approximations. Everything else in (19) is inherited from (1) and (2)–(5): "
           "the threshold, the constant-current ramp, the straight-line resistive tail and the two-device "
           "structure; (24) is the existing model's. Two limits deserve emphasis. First, the method has four "
           "built-in constants, $x_{lin}$, $p$, the three map shapes and the band rule, whose values were chosen with "
           "transistor-level knowledge of the twelve test buffers; whether they suit buffers outside the set has not "
           "been tested, and the map shapes are the least well founded element. Second, one limit is inherited "
           f"from the device model: {C('sakurai')} states that the α-power law does not reproduce the region near and below "
           f"threshold, and its delay analysis neglects the opposing device, justified for fast inputs {C('hedenstierna')}; a "
           "truncated pulse holds the stages near $v_t$ with both devices conducting, outside the regime for which "
           f"{C('sakurai')} validated the model, so the accuracy of (19) there rests on the tests of {S('verify')} and not on {C('sakurai')}.",
           "FirstParagraph"))
    A(para("Several points are open. A drive-dependent boundary (15) in place of A2 reduces the inv_chain undershoot "
           "at the gate (mean peak error 0.077 to 0.016) but is neutral on ex2 and cannot be identified in the $K_u$ "
           "domain, so it has not been adopted. The pad-level score includes the calibration width, and the "
           "selector costs about six points of peak error on ex2 against the best candidate in its grid. Two of the "
           "three Nelder–Mead starts stop in side minima on ex2; more starts, or a global stage, would make step 1 "
           "more robust and has not been tried. Two inputs are not yet given by a rule: whether $x_{lin}$ is fitted "
           "or fixed, decided per buffer here (fixed on ten, fitted on two) and not re-run uniformly; and the choice "
           f"between one chain and two ({S('model', 'B')}), made from the netlists."))

    # ================================================================ VII. conclusion
    A(heading(f"{SEC['concl']}. Conclusion", 1))
    A(para("An IBIS file records complete transitions, and a model that replays its coefficients against time "
           "cannot follow a pulse that the predriver cuts short. Modeling the predriver as a chain of stages "
           "obeying a law derived from the α-power MOSFET model, and reading the conducting fraction from the gate "
           "through a static map, gives a model whose coefficients follow the gate. The file fixes the stage rates "
           "and nothing else that matters under partial drive; one measured short pulse fixes the rest, its peak "
           "through the threshold and its shape through the choice among nine candidates. On twelve test buffers "
           f"the result is within 10 % of the transistor-level pad peak at five pulse widths, where the native "
           f"element is at {min(live):.0f}–{max(live):.0f} %. The cost is one measurement and four built-in constants; "
           "the next steps are a test outside the buffers those constants were chosen on, pulse trains and other "
           "loads, and a more robust search in step 1.", "FirstParagraph"))

    # ================================================================ references
    A(heading("References", 1))
    A(para("⟦reflist⟧", "Bibliography"))                 # replaced at assembly by the numbered list
    return t


# ----------------------------------------------------------------------------- assembly
PLAN = DOC / "layout_plan.json"


def load_data():
    """The document's data, cached between layout iterations (STAGE_LAW_FAST=1 reuses the cache)."""
    import os
    import pickle
    cache = DOC / "_build_data.pkl"
    if os.environ.get("STAGE_LAW_FAST") and cache.exists():
        return pickle.loads(cache.read_bytes())
    d = data()
    cache.write_bytes(pickle.dumps(d))
    return d


def main(d=None, plan: dict | None = None, out_path: Path | None = None, limit: int | None = None):
    """Build the paper. `plan` maps a float key to {"before": prefix} or {"after": prefix}, the plain-text
    prefix of the paragraph it is anchored to (scripts/stage_law_doc_layout.py writes it); without a plan,
    or for a key it lacks, the float is anchored after the paragraph that first mentions it. Returns the
    float registry and the ordered paragraph prefixes of the built document."""
    import json
    if d is None:
        d = load_data()
    if plan is None:
        plan = json.loads(PLAN.read_text(encoding="utf-8")) if PLAN.exists() else {}
    out_path = out_path or OUT
    FLOATS.clear()
    SEEN["fig"].clear()
    SEEN["tab"].clear()
    Package._boxes = 0
    pkg = Package(SRC, DOC / "_build")
    pkg.float_heights = {}
    ieee_styles(pkg.dir / "word" / "styles.xml")
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
    # the page: Letter, IEEE margins, two columns
    new_sect = etree.fromstring(f"<root {Package.NS}>{ieee_sect_pr(2, continuous=True)}</root>")[0]
    body.replace(sect, new_sect)
    sect = new_sect

    def frag(xml: str):
        return list(etree.fromstring(f"<root {Package.NS}>{xml}</root>"))

    # the kept derivation cites [1] Sakurai, [2] Shichman-Hodges and [3] Hedenstierna-Jeppson literally; they
    # become placeholders here so that the whole paper is numbered by first citation
    kept = {"1": "sakurai", "2": "shichman", "3": "hedenstierna"}
    n_kept = 0
    for tnode in body.iter(f"{{{W}}}t"):
        if tnode.text and "[" in tnode.text:
            tnode.text, n = re.subn(r"\[([123])(?:,\s*([^\]]+))?\]",
                                    lambda m: C(kept[m.group(1)], suffix=m.group(2)), tnode.text)
            n_kept += n
    assert n_kept >= 3, f"only {n_kept} literal citations found in the kept derivation"

    ins = build_inserts(pkg, d)
    tail = build_sections(pkg, d)

    def insert_after(startswith: str, xml: str):
        el = next(k for k in body if text(k).startswith(startswith))
        pos = list(body).index(el)
        for j, new in enumerate(frag(xml), 1):
            body.insert(pos + j, new)

    def replace_from_to(start: str, end: str, xml: str, lo=1, hi=12):
        a = next(k for k in body if text(k).startswith(start))
        b = next(k for k in body if text(k).startswith(end))
        kids_ = list(body)
        i0, i1 = kids_.index(a), kids_.index(b)
        assert lo <= i1 - i0 <= hi, (start, i0, i1)
        for k in kids_[i0:i1]:
            body.remove(k)
        for j, new in enumerate(frag(xml)):
            body.insert(i0 + j, new)

    # (5): the clip is ours. Rewrite the end of the paragraph that explains it.
    for k in body:
        for tnode in k.iter(f"{{{W}}}t"):
            if tnode.text and "The lower clip in (5)" in tnode.text:
                tnode.text = tnode.text[:tnode.text.index("The lower clip in (5)")] + (
                    f"The clip is our notation and does not appear in {C('sakurai')}: its lower bound is the cutoff row "
                    "of (2) written into the drive, and its upper bound is a numerical guard for the chain of "
                    f"{S('model', 'B')}, in which a stage output may overshoot its rail by a few percent for a few "
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
    el = next(k for k in body if text(k).startswith("where") and "pull-up (PMOS) current" in text(k))
    pos = list(body).index(el)
    for j, new in enumerate(frag(ins["stage_fig"]), 1):
        body.insert(pos + j, new)
    insert_after("Comparing (19) with (15) term by term", ins["after_eq19"])
    replace_from_to("A1 (gate exponent)", "Applying (17) and (18)", ins["a1a2"], 4, 8)

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
            set_text(k, inline("A Stage-Law Model of the IBIS Predriver for Short and Stressed Pulses"))
        elif sid == "Date":
            set_text(k, inline("Author names and affiliations"))
            # the title block spans the page: end a one-column section after it
            for new in frag(section_break(1)):
                k.addnext(new)
        elif sid == "Heading1" and text(k).startswith("II. Stage Model Derivation"):
            set_text(k, inline(f"{SEC['law']}. The Stage Law"))
        elif text(k).startswith("This section derives the stage law"):
            set_text(k, inline(ins["law_lead"]))
    # the abstract and the introduction go before Section II
    head_ii = next(k for k in body if (k.find(f"{{{W}}}pPr/{{{W}}}pStyle") is not None
                                       and k.find(f"{{{W}}}pPr/{{{W}}}pStyle").get(f"{{{W}}}val") == "Heading1"))
    for new in frag(ins["front"]):
        head_ii.addprevious(new)
    # equations of the kept derivation that are too wide for a column: (10) and (15), two lines each
    for ends, has, latex, num in (
            ("10", "GS", "|V_{GS,P}| = u\\,V_{DD},\\quad |V_{DS,P}| = (1 - v)\\,V_{DD} \\\\ V_{GS,N} = (1 - u)\\,V_{DD},\\quad V_{DS,N} = v\\,V_{DD}", 10),
            ("15", "min", "\\frac{dv}{dt} = s_{up}\\,g(u)^{\\alpha}\\min\\left(1, \\frac{1 - v}{x_0\\,g(u)^{\\alpha/2}}\\right) \\\\ \\quad - s_{dn}\\,g(1 - u)^{\\alpha}\\min\\left(1, \\frac{v}{x_0\\,g(1 - u)^{\\alpha/2}}\\right)", 15)):
        el = next(k for k in body if text(k).rstrip().endswith(ends) and has in text(k).replace(" ", "")
                  and k.find(f"{{{W}}}pPr/{{{W}}}pStyle") is not None)
        news = frag(equation(latex, num, size=18))
        body.replace(el, news[0])
        for extra in news[1:]:
            news[0].addnext(extra) if extra is news[1] else news[-2].addnext(extra)
    # Section II-C: why u is measured downward, and that v_t changes meaning later
    for tnode in body.iter(f"{{{W}}}t"):
        if tnode.text and "fully turns on the working (pull-up) device" in tnode.text:
            tnode.text = tnode.text.replace(
                "fully turns on the working (pull-up) device",
                "fully turns on the working (pull-up) device: for a rising output the pull-up PMOS does the "
                "work, and it is driven harder as the input falls, so u counts how far the input has come "
                "down from the supply")
            break
    hit = False
    for tnode in body.iter(f"{{{W}}}t"):
        if tnode.text and "swings per second" in tnode.text:
            tnode.text = tnode.text.replace(
                "swings per second",
                "swings per unit time, one swing being the full excursion of the stage output from 0 to 1 (the "
                "fitted values below are quoted per nanosecond)")
            hit = True
            break
    assert hit, "the rate-unit sentence of Section II-D was not found in the kept text"
    eq9 = next(k for k in body if "x0" in text(k).replace(" ", "") and text(k).rstrip().endswith("9"))
    pos = list(body).index(eq9)
    for j, new in enumerate(frag(ins["vt_note"]), 1):
        body.insert(pos + j, new)
    for new in frag("".join(tail)):
        sect.addprevious(new)
    # IEEE subsection heads in title case
    small = {"a", "an", "and", "the", "of", "to", "from", "for", "on", "in", "with", "by", "at", "or", "against"}
    for k in body:
        st = k.find(f"{{{W}}}pPr/{{{W}}}pStyle")
        if st is not None and st.get(f"{{{W}}}val") == "Heading2":
            for tnode in k.iter(f"{{{W}}}t"):
                if tnode.text:
                    words = tnode.text.split(" ")
                    out = []
                    for i, w in enumerate(words):
                        first = i == 0 or words[i - 1].endswith(":")
                        out.append(w if (not first and w.lower() in small) or not w else w[0].upper() + w[1:])
                    tnode.text = " ".join(out)

    # a paragraph followed by a display equation keeps with it (page and column breaks alike)
    kids = list(body)
    for a, b in zip(kids, kids[1:]):
        if (etree.QName(a).localname == "p" and etree.QName(b).localname == "p"
                and b.find(f".//{{{_M}}}oMathPara") is not None):
            ppr = a.find(f"{{{W}}}pPr")
            if ppr is None:
                ppr = etree.Element(f"{{{W}}}pPr")
                a.insert(0, ppr)
            if ppr.find(f"{{{W}}}keepNext") is None:
                kn = etree.Element(f"{{{W}}}keepNext")
                st = ppr.find(f"{{{W}}}pStyle")
                st.addnext(kn) if st is not None else ppr.insert(0, kn)

    def style_of(el) -> str:
        st = el.find(f"{{{W}}}pPr/{{{W}}}pStyle")
        return st.get(f"{{{W}}}val") if st is not None else ""

    # citations: numbered by first appearance in the document (the floats in their mention order);
    # the reference list follows that order
    order: list[str] = []

    def cite_text(m):
        keys, suffix = m.group(1).split(","), m.group(2)
        nums = []
        for k in keys:
            if k not in order:
                order.append(k)
            nums.append(order.index(k) + 1)
        if suffix:
            return f"[{nums[0]}, {suffix}]"
        nums.sort()
        if len(nums) >= 3 and nums == list(range(nums[0], nums[-1] + 1)):
            return f"[{nums[0]}]–[{nums[-1]}]"
        return ", ".join(f"[{n}]" for n in nums)

    cite_re = r"⟦cite:([^|⟧]+)(?:\|([^⟧]+))?⟧"
    for tnode in body.iter(f"{{{W}}}t"):
        if tnode.text and "⟦cite:" in tnode.text:
            tnode.text = re.sub(cite_re, cite_text, tnode.text)
    for f in FLOATS:
        f["xml"] = re.sub(cite_re, cite_text, f["xml"])
    ref_par = next(k for k in body if text(k).strip() == "⟦reflist⟧")
    for i, k in enumerate(order, 1):
        ref_par.addprevious(frag(para(f"[{i}] {REFS[k]}", "Bibliography"))[0])
    body.remove(ref_par)
    unused = sorted(set(REFS) - set(order))
    assert not unused, f"references never cited: {unused}"

    # the double-column floats, each anchored where the plan says (default: after its mention)
    def place_floats(body_el, plan_, limit_):
        paras = [k for k in body_el if etree.QName(k).localname == "p"]
        prefixes = [plain_prefix(k) for k in paras]
        inserted_ = []                                  # the blocks' own paragraphs: never anchors
        for f in FLOATS[:limit_]:
            spec = plan_.get(f["key"]) or {"after": f["after"]}
            how, pre = next(iter(spec.items()))
            if pre not in prefixes:
                how, pre = "after", f["after"]
            anchor = paras[prefixes.index(pre)]
            if how == "before":                         # a heading stays with its first paragraph
                prev = anchor.getprevious()
                while prev is not None and etree.QName(prev).localname == "p" and style_of(prev).startswith("Heading"):
                    anchor, prev = prev, prev.getprevious()
            cur = anchor
            while how == "after" and cur.getnext() is not None and cur.getnext() in inserted_:
                cur = cur.getnext()                     # a second float after the same paragraph follows the first
            for new in frag(f["xml"]):
                inserted_.append(new)
                if how == "before":
                    anchor.addprevious(new)
                else:
                    cur.addnext(new)
                    cur = new
        return inserted_

    # the markdown preview: the same body, every float right after its first mention
    if out_path == OUT:
        import copy
        md_body = copy.deepcopy(body)
        place_floats(md_body, {}, None)
        images = {rid: f"figures/{png.name}" for rid, png in pkg.images}
        md_path = out_path.with_name(out_path.stem.replace("_ieee", "") + "_draft.md")
        md_path.write_text(markdown_of_body(md_body, images), encoding="utf-8")
        print(f"wrote {md_path}")

    inserted = place_floats(body, plan, limit)

    # no stale pointers: every section reference must name a section that exists
    refs = sorted(set(re.findall(r"Section (?:I|II|III|IV|V|VI|VII)(?:-[A-F])?\b", "".join(text(k) for k in body))))
    bad = [r for r in refs if r.split()[1].split("-")[0] not in SEC.values()]
    assert not bad, bad
    tree.write(str(doc_xml), xml_declaration=True, encoding="UTF-8", standalone=True)
    pkg.finish(out_path)
    print(f"wrote {out_path}  ({out_path.stat().st_size / 1024:.0f} kB, {len(pkg.images)} figures); section refs: {refs}")
    return ([dict(key=f["key"], after=f["after"], height=f["height"]) for f in FLOATS],
            ["" if k in inserted else plain_prefix(k) for k in body if etree.QName(k).localname == "p"])


if __name__ == "__main__":
    main()
