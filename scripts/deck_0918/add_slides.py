"""Append the new slides to Simon's 0918 deck copy, after slide 17, on his own layout.

Runs place_figures.py first (fresh from the original), so this is safe to re-run.
Order: inv_chain explained (2), three buffers side by side, How to reproduce: the question,
four attempts after looking inside and their table (reused from the 09-17 deck), the method
(track 1, track 2, result), and one backup slide on inv_chain's input threshold.
"""
import runpy
import sys
from pathlib import Path

sys.path.insert(0, r"C:/Users/sh3qm/code/ibis_comparison/.codex_deps/presentation/python")
from pptx import Presentation  # noqa: E402
from pptx.dml.color import RGBColor  # noqa: E402
from pptx.util import Pt  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).parent
runpy.run_path(str(HERE / "place_figures.py"))

ROOT = Path(r"C:/Users/sh3qm/code/ibis_comparison")
F18 = ROOT / "results/meeting_deck_2026-09-18/figures"
F17 = ROOT / "results/meeting_deck_2026-09-17/figures"
OUT = ROOT / "results/meeting_deck_2026-09-18/0918_Simon_IBIS_figures_v3.pptx"
E = 914400
GREEN = RGBColor(43, 122, 67)
PALE = RGBColor(241, 248, 242)
ORANGE = RGBColor(192, 86, 33)

# numbers the inv_chain slides quote, from build_0918_deck_figures.py's output
# (inv_why_111 / inv_fixed_111, C_comp 0.6 pF, 111 ps)
N = dict(inv_file="-41.4 %", inv_fix="+4.5 %", sw_file_on="0.96", sw_file_off="0.49",
         sw_tr_on="0.98", sw_tr_off="0.93", sw_gate="0.95")

prs = Presentation(OUT)
LAYOUT = prs.slides[2].slide_layout      # content_1, the layout of Simon's slides
FIRST_NEW = len(prs.slides._sldIdLst)    # 17: Simon's slides are left exactly as they are


def bullets(slide, items, size=18):
    """Bullets in the layout's own content placeholder, resized to a band under the title.
    Returns the y (EMU) where the band ends."""
    ph = next(sh for sh in slide.placeholders if sh.placeholder_format.idx == 10)
    lines = sum(max(1, -(-len(t) // 108)) for t in items)
    h = int((0.33 * lines + 0.12 * len(items) + 0.1) * E)
    ph.left, ph.top, ph.width, ph.height = int(0.45 * E), int(1.08 * E), int(12.45 * E), h
    tf = ph.text_frame
    tf.clear()
    for k, t in enumerate(items):
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        r = p.add_run()
        r.text = t
        r.font.size = Pt(size)
        p.space_after = Pt(4)
    return ph.top + h


def picture(slide, png, top, bottom=7.15 * E, left=0.45 * E, width=12.45 * E):
    w, h = Image.open(png).size
    a = w / h
    avail_h = bottom - top - 0.1 * E
    pw, ph_ = (width, width / a) if width / a <= avail_h else (avail_h * a, avail_h)
    x = left + (width - pw) / 2
    slide.shapes.add_picture(str(png), int(x), int(top + 0.08 * E), int(pw), int(ph_))


def new_slide(title, items, png=None, notes="", size=18):
    s = prs.slides.add_slide(LAYOUT)
    s.shapes.title.text = title
    y = bullets(s, items, size) if items else int(1.1 * E)
    if png is not None:
        picture(s, png, y)
    if not items:
        ph = next((sh for sh in s.placeholders if sh.placeholder_format.idx == 10), None)
        if ph is not None:
            ph._element.getparent().remove(ph._element)
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def table(slide, rows, top, col_w, size=14, first_col_bold=True, foot=None):
    nr, nc = len(rows), len(rows[0])
    x = int((13.333 - sum(col_w)) / 2 * E)
    row_h = 0.42
    shape = slide.shapes.add_table(nr, nc, x, int(top), int(sum(col_w) * E), int(row_h * nr * E))
    t = shape.table
    for j, w in enumerate(col_w):
        t.columns[j].width = int(w * E)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.text = val
            para = c.text_frame.paragraphs[0]
            for r in para.runs:
                r.font.size = Pt(size)
                r.font.bold = i == 0 or (j == 0 and first_col_bold)
                r.font.color.rgb = RGBColor(255, 255, 255) if i == 0 else RGBColor(25, 31, 28)
            c.fill.solid()
            c.fill.fore_color.rgb = GREEN if i == 0 else (PALE if i % 2 else RGBColor(255, 255, 255))
            c.margin_left = c.margin_right = int(0.08 * E)
    if foot:
        tb = slide.shapes.add_textbox(x, int(top + row_h * nr * E + 0.15 * E), int(sum(col_w) * E), int(0.5 * E))
        tb.text_frame.word_wrap = True
        r = tb.text_frame.paragraphs[0].add_run()
        r.text = foot
        r.font.size = Pt(14)
        r.font.italic = True
    return shape


# ------------------------------------------------------------------ inv_chain, explained
new_slide("inv_chain: why the real gate makes it worse", [
    "Our model reads ku_rise(g) while the gate rises and ku_fall(g) while it falls, built from the file's "
    "Ku_rising(t) and Ku_falling(t). A full swing switches only at gate = 1, where both give 1; the file's "
    "curves being a few ps off (7 late, 19 early) is only a small timing error.",
    f"A short pulse switches part-way. At gate {N['sw_gate']} the file's ku_rise gives {N['sw_file_on']} and "
    f"its ku_fall {N['sw_file_off']}, so Ku halves in a few ps; the transistor's give {N['sw_tr_on']} and "
    f"{N['sw_tr_off']}.",
], F18 / "inv_why_111.png", notes=(
    "Same real gate in both runs; only the curves differ. Teal: ku_rise / ku_fall built from the file's "
    "Ku_rising(t) / Ku_falling(t) (the netlist's KUGATE_ON / KUGATE_OFF). Green: the same pairing done with "
    "the transistor's own Ku(t), solved from its two fixture runs. Full swing (left, middle): the file's Ku "
    "crosses 0.5 6.9 ps after the transistor's on the rise and 18.9 ps before it on the fall; the pad's 50 % "
    "crossing is +14 / -12 ps against the transistor. inv_chain's gate falls from 0.95 to about 0.6 in "
    "roughly 19 ps, which is why a 19 ps early ku_fall already reads 0.49 at gate 0.95. 111 ps pulse "
    f"(right): the model switches to ku_fall with the gate at {N['sw_gate']}, just before its peak (the "
    "direction selector leads the gate by a few ps). 111 ps is the width of slides 16-17; C_comp 0.6 pF, "
    "see the next slide. Runs: gate_cascade_prototype_2026-09-09/inv_chain_c0.6/gate_replay and "
    "gate_replay_silicon_full."))

new_slide("Why only inv_chain: the same handoff, three gate speeds", [
    "Same 400 ps window for all. inv_chain's gate falls in 73 ps; ex2's in 800 ps, io_buf's in 449 ps.",
    "The file's Ku is a few ps off on each; only on inv_chain's fast gate does that halve Ku at the handoff.",
], F18 / "three_handoffs.png", notes=(
    "Top row: the full-swing falling edge, where ku_fall is built. Bottom row: the 70 % short pulse around the "
    "ku_rise -> ku_fall switch. The file's Ku is off by 9 ps on ex2 and 19 ps on inv_chain; in gate terms that "
    "is 0.01 of ex2's swing and 0.22 of inv_chain's, so only inv_chain's handoff halves Ku (0.96 -> 0.49; "
    "ex2 0.80 -> 0.74; io_buf 0.70 -> 0.73, no drop). "
    "Each buffer at its measured C_comp where the transistor-curve run exists (ex2 1.7 pF, inv_chain 0.6 pF); "
    "io_buf at the declared value, and it has no transistor-curve run, so only the file's Ku is drawn. "
    "Offsets: where Ku crosses 0.5 on the full-swing edge, file against transistor: ex2 +5 ps rise / +9 ps "
    "fall; inv_chain +7 ps rise / -19 ps fall. Gate speed near the top of the swing: ex2 0.0006-0.0009 per "
    "ps, inv_chain 0.006-0.012 per ps. The jump is timing error x gate speed; with zero timing error there "
    "is no jump even on a fast gate - inv_chain's transistor curves hand over 0.98 -> 0.93. inv_chain's pad "
    "pulse is also only ~70 ps wide at half height (ex2 ~380 ps), so a 25-40 ps early cut is a third to a "
    "half of it. io_buf's file Ku rising after its switch is the residual table, not the curves. "
    "At the declared 5 pF (slide 14) ex2's file curves do show a cliff at the switch, 1.16 -> 0.59: the "
    "wrong C_comp distorts them. The pad still lands at -6 %; not decomposed."))

new_slide("inv_chain: the real gate with the transistor's own Ku curves", [
    f"Keep the real gate, take the Ku curves from the transistor instead of the file: {N['inv_file']} becomes "
    f"{N['inv_fix']}.",
    "So inv_chain needs both: the gate's motion, and a Ku curve that is the same going up and coming down.",
], F18 / "inv_fixed_111.png", notes=(
    "At C_comp 0.6 pF, the value at which the transistor's Ku against its gate forms one curve (the loop "
    "method); measuring the curve needs the right C_comp. At the declared 0.47 pF, slide 17's case, the real "
    "gate with the file's curves is -32.9 %; the measured-curve replay at 0.47 pF was tried on 09-18, ran "
    "with a collapsing timestep (500 MB of output in 9 minutes on its first full-swing pass) and was stopped. "
    "The measured curves come from the same two fixture runs IBIS characterisation already uses "
    "(pad forced to 0 and to VDD), solved for Ku and Kd at every instant and plotted against the "
    "transistor's gate. They are evidence of what the transistor knows; how a converter gets them "
    "is part of 'How to reproduce'."))

# ------------------------------------------------------------------ three buffers, side by side
s = new_slide("Three buffers, side by side", [], None, notes=(
    "Every number is on slides 9-20, at 70 % stress and the declared C_comp except the dagger row "
    "(0.6 pF, slide 20). Late-by is measured "
    "between the two gates' peaks on slides 10 / 13 / 16; the rise is the real gate's 10-90 at full "
    "swing. The inv_chain peak of -0.8 % is flattered by the input threshold (backup slide)."))
table(s, [
    ["", "ex2  (858 ps)", "inv_chain  (111 ps)", "io_buf  (2090 ps)"],
    ["where the pulse is lost", "in the predriver", "at the output stage", "nowhere: a slow ramp cut short"],
    ["our gate turns round late by", "105 ps  (16 % of its rise)", "22 ps  (42 %)", "51 ps  (2 %)"],
    ["our model, pad peak", "+22.3 %", "-0.8 % *", "+1.6 %"],
    ["real gate as GUP", "-6.1 %", "-32.9 %", "+1.4 %, lag 67 -> 37 ps"],
    ["+ the transistor's Ku curves", "-", N["inv_fix"] + " †", "-"],
    ["still missing", "nothing", "one Ku curve, going up and down", "when the pull-down comes back"],
], int(1.3 * E), [3.3, 2.8, 3.1, 3.3], size=15,
    foot="* flattered by the file's input threshold: see the backup slide.   † at C_comp 0.6 pF, where the "
         f"file's curves give {N['inv_file']}.   On all three the output stage follows the gate; what differs "
         "is how the gate moves.")

# ------------------------------------------------------------------ how to reproduce: the question
s = prs.slides.add_slide(LAYOUT)
s.shapes.title.text = "How to reproduce: the question"
ph = next(sh for sh in s.placeholders if sh.placeholder_format.idx == 10)
ph._element.getparent().remove(ph._element)
for txt, y, h, size, bold, col in (
        ("The output stage follows the gate.\nThe gate comes from the predriver.\n"
         "Driven by the real gate, the model is right (ex2 -6 %, io_buf +1 %; inv_chain with its measured curve).",
         1.45, 2.0, 24, False, None),
        ("The IBIS file has no gate, and its V-T tables pin Ku(t) only at full swing.\n"
         "Native fails for the same reason with no gate at all: its Ku is a clock.", 3.6, 1.3, 20, False, None),
        ("What information would reproduce the gate's motion - for any input, including one cut short - "
         "without the transistor?", 5.1, 1.3, 24, True, ORANGE)):
    tb = s.shapes.add_textbox(int(0.7 * E), int(y * E), int(12.0 * E), int(h * E))
    tb.text_frame.word_wrap = True
    for k, line in enumerate(txt.split("\n")):
        p = tb.text_frame.paragraphs[0] if k == 0 else tb.text_frame.add_paragraph()
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.bold = bold
        if col is not None:
            r.font.color.rgb = col
s.notes_slide.notes_text_frame.text = (
    "Two halves: how the gate moves, and how the pad follows it. Next, what we tried once we could see "
    "the gate (four attempts, in the order tried), then the method that works on ex2.")

# ------------------------------------------------------------------ what we tried (from 0917)
new_slide("Tried 1: correct C_comp to the measured value", [
    "The first thing the probed gate gave us: Ku against the real gate only forms one curve at one C_comp - "
    "1.5-1.75 pF on ex2, at all five widths. The file declares 5.0.",
    "Put the measured 1.7 pF into our model at 858 ps, the 70 % case: +22.3 % becomes +26.4 %. Native gets "
    "worse too. The declared 5 pF was hiding part of the gate error.",
], F17 / "ccomp_ex2.png", notes=(
    "results/ex2_ccomp_correction_2026-09-08. Peak / lag / RMSE at 858 ps: ours +244 mV / +236 ps / 336 mV "
    "at 5.0 pF, +289 / +268 / 382 at 1.7; native +263 -> +342 mV. The full-swing control does not move. "
    "Lesson: fix the gate first; a single-parameter improvement can be a compensating error moving."))

new_slide("Tried 2: slow the gate", [
    "Slow our gate's ramp to match how slowly the probed gate moves. ex2 at 810 ps (50 %): +66.6 % becomes "
    "+48.7 % - a quarter off, not a fix. The gate-ramp form does no better, 70.9 to 66.9 %.",
    "At 810 ps our pad is already 46 % too tall at +600 ps, before our model's turn-off even begins at "
    "+733 ps: nothing done to the ramp can act before the schedule does.",
], F18 / "slew_ex2.png", notes=(
    "gate_cascade_prototype_2026-09-09/ex2/slew500ps and gate_ramp_prototype_2026-09-09. The gate-ramp "
    "form did fix io_buf's pedestal (+63...+69 ps to +10...-20) and took the 8-stage chain from 65 to 49 %."))

new_slide("Tried 3: an RC cascade in place of the schedule", [
    "The probe showed ex2's gate is slow and smooth, so replace our fixed delay with 5 RC stages - a gate "
    "that moves by itself. ex2 at 810 ps: -2.6 %, where our model is +66.6 %. It looked like the answer.",
    "On an inverter chain the same idea is dead: a 102 ps pulse cannot get through 4 RC stages (-98 %); real "
    "inverters regenerate. Delay plus one 60 ps stage only halves it, +65 to +22 %.",
], F17 / "cascade_pair.png", notes=(
    "gate_cascade_prototype_2026-09-09. Right panel: inv_base8, the 8-stage variant (the cascade was not "
    "run on inv_chain itself), at 50 % depth. Next slide: why the ex2 result is a fit - no linear "
    "structure reproduces ex2's gate. io_buf: neutral."))

new_slide("Tried 4: derive the gate from the file, then superpose", [
    "Assume the output stage's Ku curve has a MOSFET shape, ((g - vt)/(1 - vt))^a, and invert the file's "
    "Ku(t) through it: the gate comes out of the file, no transistor (left).",
    "Then treat the predriver as linear: a cut pulse is the rising step plus the falling step. ex2: 0.99 "
    "where the real gate stops at 0.76 (right). inv_chain 0.99 against 0.88; io_buf within 0.035.",
], F17 / "superpose_ex2.png", notes=(
    "physics_map_gate_2026-09-10. The three measured curves share the shape: vt 0.57 / 0.49 / 0.50, "
    "alpha 0.64 / 0.60 / 0.78. The tables can give the gate at full swing; a linear predriver cannot give "
    "ex2's, whose three stages each return less than the sum of their steps. That is what the method's "
    "current-limited stages add."))

s = new_slide("What we tried, in one table", [], None, notes=(
    "In order, 09-08 to 09-10. The inverter-chain column is the 8-stage variant for rows 2-3. Each attempt "
    "fixes the buffer whose mechanism it matches and misses the others."))
table(s, [
    ["attempt, in order", "on ex2", "on inv_chain family", "on io_buf", "verdict"],
    ["1  measured C_comp, 1.7 pF", "every metric worse", "-", "-", "was hiding gate error"],
    ["2  slow the gate", "+67 -> +49 % best", "65 -> 49 %", "pedestal fixed", "cannot beat the schedule"],
    ["3  RC cascade, 5 stages", "+67 -> -3 %", "-98 % (dead)", "neutral", "a fit, not physics"],
    ["    delay + one RC stage", "-", "+65 -> +22 %", "-", "halves it"],
    ["    residual scaled by depth", "no effect", "no effect", "bump height back", "io_buf only"],
    ["    one gate for both sides", "peak < 1.5 %", "peak < 1.5 %", "-", "not the lever"],
    ["4  gate from the file, superposed", "0.99 vs real 0.76", "0.99 vs 0.88", "within 0.035", "no non-linearity"],
], int(1.3 * E), [3.6, 2.2, 2.3, 2.1, 2.6], size=14)

# ------------------------------------------------------------------ the method (ex2)
new_slide("The method, track 1: rebuild how the gate moves - from the file", [
    "No internal node. Three identical stages drive a MOSFET-shaped Ku curve; their numbers (two drive rates, "
    "a threshold) are fitted so the model's Ku matches the file's own full-swing Ku(t), both edges (left).",
    "A full swing pins the threshold only loosely; one stressed pad run pins it: bisect at 810 ps until the "
    "pad peak lands, vt 0.53 -> 0.49 (right).",
], F18 / "method_track1.png", notes=(
    "Build: gate_chain_prototype_2026-09-10/ex2_c1.7/ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad810, "
    "C_comp 1.7 pF. Fitted in the Ku domain (fit_chain_ku): s_up 2.190, s_dn 2.124, vt 0.528, resistive "
    "fraction fixed at 0.45, rms 0.023; the pad-peak calibration then sets vt 0.489. Correction: the 09-17 "
    "animation's fit step showed a different fit - four numbers (2.590 / 2.375 / 0.512 / 0.658) to the probed "
    "gate n4 - which belongs to a build that needs the transistor; its threshold bisection was this build's. "
    "One caveat on 'file only': the curve's shape (vt 0.57, alpha 0.64) was fitted to ex2's measured Ku curve "
    "(physics_map_gate_2026-09-10). The universal shape (0.5, 0.7) needs no transistor; it has not been run "
    "through the pad calibration on ex2."))

new_slide("The method, track 2: measure how the pad follows the gate", [
    "The output stage only follows the gate, so Ku against the gate is one fixed curve: solve Ku from the two "
    "fixture runs IBIS already uses (a), record the gate (b), plot one against the other (c).",
    "Keep track 1's stages, swap in the measured curve: ex2 goes from -7 / -9 / -7 / -5 / 0 % to 0 / 0 / -1 / "
    "-2 / 0 % across the five widths (975 -> 810 ps). This needs the transistor's gate probed.",
], F17 / "static_map_ex2.png", notes=(
    "Build: ibis_silicon_K3_xlin0.45_calibpad810 (the 09-13 study's track 2): track 1's file-fitted stages "
    "and pad calibration, with the measured curves in place of the MOSFET-shaped one. Four curves in all: Ku "
    "rising and falling against the gate, Kd on and off against 1 - gate. With the real gate instead of the "
    "stages, the same swap takes ex2 from -3.3...-5.8 % to +1.2...-4.7 %, and inv_chain from -41.4 to +4.5 % "
    "(slide 20). On inv_chain inside the method the measured curve is worth only ~2 % (track 1 -10...+2 %, "
    "track 2 -7...+4 %), because track 1 already uses one curve both ways. C_comp 1.7 pF here."))

new_slide("The method on ex2: both tracks", [
    "At 810 ps, where the threshold was placed: our model +73.7 %, track 1 -0.1 %, tracks 1 + 2 +0.2 %. "
    "At 895 ps, never used in any fit: +13.3 %, -8.6 %, -0.0 %.",
    "Track 1 needs the IBIS file and one stressed pad run. Track 2 adds the measured curve, which needs the "
    "transistor's gate. ex2 here; inv_chain: track 1 -10...+2 %, track 2 -7...+4 %.",
], F18 / "method_result.png", notes=(
    "C_comp 1.7 pF (measured) throughout this section, so our model reads +73.7 % at 810 ps here against "
    "+66.8 % at the declared 5 pF on slide 4. Builds: track 1 ibis_prior_K3_prior0.57_0.64_xlin0.45_calibpad810; "
    "tracks 1 + 2 ibis_silicon_K3_xlin0.45_calibpad810 (the same stages, the measured curve). Correction: the "
    "09-17 animation and page showed +0.9 / -3.1 % for 'both tracks', from real_silicon_K3_calibpad810, whose "
    "stages were fitted to the probed gate - not track 1's stages. Track 1's gate reaches 0.74 against the real "
    "0.76 at 810 ps; its -8.6 % at 895 ps is the MOSFET-shaped curve, which track 2 replaces. inv_chain from "
    "the 09-13 table (ibis_prior_K7_prior0.49_0.6_calibpad104 / ibis_silicon_K7_calibpad104). The 09-10 "
    "review's file-only recipe put eleven of twelve buffers within 10 %; io_buf was the exception."))

# ------------------------------------------------------------------ backup
new_slide("Backup: why our model beats native on inv_chain", [
    "The IBIS file declares Vinh 2.0 V on a 1.8 V part, so our input comparator switches at 1.4 V. With 50 ps "
    "edges it sees the 111 ps pulse as 83 ps (left).",
    "That trims most of the overshoot. At mid-supply, 0.9 V, our model is +18.1 % instead of -1.9 %; native "
    "+31.7 %. Both our builds here are at C_comp 0.6 pF, the one folder with the mid-supply build.",
], F18 / "vinh_inv.png", notes=(
    "review_2026-09-09 claim 12B and input_threshold_check_2026-09-10.txt. The converter now clamps input "
    "thresholds to the supply (inv_chain 1.4 -> 0.9 V); slides 5 and 16 use the matrix build from before "
    "that change. This is also why slide 17's real-gate replay reads so low: the replay bypasses the "
    "comparator, so it loses the 28 ps the threshold was removing."))

# The template allows Latin words to wrap mid-word (an East Asian line-break default), which
# splits "swing" into "sw / ing" at a line end. Turn it off on every paragraph of the new slides.
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
for s in list(prs.slides)[FIRST_NEW:]:
    for p in s.shapes._spTree.iter(f"{A}p"):
        ppr = p.find(f"{A}pPr")
        if ppr is None:
            from lxml import etree
            ppr = etree.SubElement(p, f"{A}pPr")
            p.insert(0, ppr)
        ppr.set("latinLnBrk", "0")

prs.save(OUT)
print("wrote", OUT, len(prs.slides._sldIdLst), "slides")
