"""Animation: how Ku(t) and Kd(t) are extracted from a transistor buffer.

Built on the real numbers in results/kukd_animation/data.json -- the two fixture
waveforms actually simulated for inv_chain, and the same 2x2 solve the study
runs. Nothing here is illustrative-only, including the two multipliers in each
equation, which are read off the IBIS I-V tables on screen, and each right-hand
side, which is assembled from the fixture resistor and C_comp terms.

Currents are shown in mA. The solve is identical either way, and four-decimal
amps are unreadable at projector distance.

Equations render through LaTeX when a TeX install is on PATH, and fall back to
unicode Text when it is not, so the scene builds on a bare machine. The template
is deliberately minimal -- amsmath and amssymb only -- because manim's default
preamble pulls in a dozen packages a small TeX distribution does not ship.

    py -3.13 -m manim -qh scripts/animate_kukd_extraction.py KuKdExtraction
    KUKD_NO_TEX=1 py -3.13 -m manim ...      # force the unicode fallback
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil

import numpy as np
from manim import (
    Arrow, Axes, Create, DOWN, DashedLine, Dot, FadeIn, FadeOut, LEFT, Line, MathTex,
    RIGHT, Rectangle, Scene, Text, UP, VGroup, ValueTracker, Write, always_redraw,
    config,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "results" / "kukd_animation" / "data.json").read_text(encoding="utf-8"))

BG = "#0F151B"
INK = "#E3E9EF"
FAINT = "#8695A2"
LOW_C = "#D97706"
HIGH_C = "#0E9F9F"
KU_C = "#E4564A"
KD_C = "#3FBF87"
GOLD = "#E0B341"

config.background_color = BG

# The fixture-to-VCC pad peaks at 1.863 V, so an axis topping out at 1.55 leaves
# the trace drawn outside its own box -- which in the last act runs into the
# title. The range is a constant because the cursor and sweep bar have to span
# exactly the same interval.
PAD_Y = (-0.15, 2.0)

# TinyTeX installs outside the system PATH, so look there before giving up on
# LaTeX -- otherwise a perfectly good install is invisible to this process.
# LOCALAPPDATA first: this machine's APPDATA is a redirected network share, and
# tlmgr against 300 MB of TeX over the wire is hours rather than minutes, so the
# working install is the local copy.
for _base in (os.environ.get("LOCALAPPDATA", ""), os.environ.get("APPDATA", "")):
    _bin = Path(_base) / "TinyTeX" / "bin" / "windows"
    if _base and _bin.is_dir():
        os.environ["PATH"] = str(_bin) + os.pathsep + os.environ.get("PATH", "")
        break

USE_TEX = not os.environ.get("KUKD_NO_TEX") and bool(
    shutil.which("latex") and shutil.which("dvisvgm"))

if USE_TEX:
    from manim import TexTemplate

    TEX = TexTemplate(preamble="\\usepackage{amsmath}\n\\usepackage{amssymb}")
else:
    TEX = None


def small(s, size=22, color=INK, weight=None):
    if weight:
        return Text(s, font_size=size, color=color, weight=weight)
    return Text(s, font_size=size, color=color)


def eq(tex, plain, size=30, color=INK):
    """One equation, LaTeX where available and unicode where not.

    Ku and Kd are recoloured wherever they appear so a term can be followed from
    the schematic into the equation and out into the solved curves.
    """
    if not USE_TEX:
        return small(plain, size, color)
    # tex_to_color_map, not set_color_by_tex: on a single-string MathTex there is
    # only one submobject, so set_color_by_tex would recolour the whole equation.
    # The map isolates the substrings into their own submobjects first.
    return MathTex(tex, font_size=size * 1.6, color=color, tex_template=TEX,
                   tex_to_color_map={"K_u": KU_C, "K_d": KD_C})


def ma(x):
    """Amps to milliamps, signed, two decimals."""
    return "%+.2f" % (x * 1000.0)


class KuKdExtraction(Scene):
    def construct(self):
        self.act1_problem()
        self.act2_one_fixture()
        self.act3_two_fixtures()
        self.act4_where_numbers_come_from()
        self.act5_solve()
        self.act6_sweep()

    # ------------------------------------------------------------------ act 1
    def act1_problem(self):
        title = Text("How Ku(t) and Kd(t) are extracted", font_size=44, color=INK, weight="BOLD")
        self.play(Write(title), run_time=1.3)
        self.play(title.animate.scale(0.55).to_edge(UP, buff=0.4), run_time=0.8)

        schematic, _pad_node = self.ibis_schematic()
        schematic.scale(0.86).move_to([0, 0.75, 0])
        self.play(Create(schematic), run_time=2.2)
        self.wait(0.8)

        e = eq("I_{pad} \\;=\\; K_u\\, I_{pu}(V) \\;+\\; K_d\\, I_{pd}(V) \\;+\\; I_{clamp}(V)"
               " \\;+\\; C_{comp}\\,\\frac{dV}{dt}",
               "I_pad  =  Ku x I_pu(V)  +  Kd x I_pd(V)  +  clamps  +  C_comp x dV/dt", 28)
        e.scale(0.82).to_edge(DOWN, buff=1.1)
        self.play(Write(e), run_time=2.0)
        self.wait(0.6)

        note = small("the I-V curves and C_comp come from the IBIS file - "
                     "Ku and Kd are the only unknowns", 21, FAINT)
        note.next_to(e, DOWN, buff=0.35)
        self.play(FadeIn(note), run_time=0.8)
        self.wait(2.2)
        self.play(FadeOut(note), FadeOut(e), FadeOut(schematic), FadeOut(title), run_time=0.8)

    # ------------------------------------------------------------------ act 2
    def act2_one_fixture(self):
        head = small("Drive the buffer through a known load and record the pad", 30, INK, "BOLD")
        head.to_edge(UP, buff=0.5)
        self.play(Write(head), run_time=1.1)

        buf, pad_dot = self.buffer_block()
        grp = VGroup(buf, pad_dot)
        grp.move_to([-4.2, 0.4, 0])
        self.play(Create(grp), run_time=1.0)

        fix_a = self.fixture(pad_dot.get_center(), "50 ohm", "0 V", LOW_C, down=True)
        self.play(Create(fix_a), run_time=0.9)

        ax = self.pad_axes()
        ax.move_to([2.7, 0.4, 0])
        self.play(Create(ax), run_time=0.8)
        gl = ax[0].plot_line_graph(DATA["t"], DATA["pad_lo"], add_vertex_dots=False,
                                   line_color=LOW_C, stroke_width=4)
        self.play(Create(gl), run_time=1.8)

        one = small("one measurement  ->  one equation, two unknowns", 26, GOLD)
        one.next_to(ax, DOWN, buff=0.55)
        self.play(FadeIn(one), run_time=0.7)
        self.wait(1.4)

        self.head2 = head
        self.circuit = grp
        self.fix_a = fix_a
        self.pad_dot = pad_dot
        self.ax_pad = ax
        self.graph_lo = gl
        self.play(FadeOut(one), run_time=0.4)

    # ------------------------------------------------------------------ act 3
    def act3_two_fixtures(self):
        fix_b = self.fixture(self.pad_dot.get_center(), "50 ohm", "VCC", HIGH_C, down=False)
        self.play(Create(fix_b), run_time=0.9)
        gh = self.ax_pad[0].plot_line_graph(DATA["t"], DATA["pad_hi"], add_vertex_dots=False,
                                            line_color=HIGH_C, stroke_width=4)
        self.play(Create(gh), run_time=1.8)
        self.graph_hi = gh

        lab = VGroup(
            small("pad with fixture to 0 V", 20, LOW_C),
            small("pad with fixture to VCC", 20, HIGH_C),
        ).arrange(DOWN, buff=0.16, aligned_edge=LEFT)
        lab.next_to(self.ax_pad, DOWN, buff=0.35)
        self.play(FadeIn(lab), run_time=0.6)

        two = small("two measurements  ->  two equations, two unknowns", 26, GOLD)
        two.next_to(lab, DOWN, buff=0.35)
        self.play(FadeIn(two), run_time=0.7)
        self.wait(1.6)
        self.play(FadeOut(two), FadeOut(lab), FadeOut(self.circuit), FadeOut(self.fix_a),
                  FadeOut(fix_b), FadeOut(self.head2), run_time=0.8)

    # ------------------------------------------------------------------ act 4
    def act4_where_numbers_come_from(self):
        """Every number in the two equations, shown being read or computed.

        This act exists because the equations on their own look like four
        decimals arriving from nowhere. Each multiplier is a table lookup at the
        measured pad voltage; each right-hand side is the part of the pad current
        that is already known.
        """
        head = small("Every number is read off something known", 30, INK, "BOLD")
        head.to_edge(UP, buff=0.35)
        self.play(Write(head), run_time=1.0)
        self.head4 = head

        self.play(VGroup(self.ax_pad, self.graph_lo, self.graph_hi).animate
                  .scale(0.58).move_to([-4.7, 1.75, 0]), run_time=0.9)

        ivax = self.iv_axes()
        ivax.scale(0.82).move_to([0.4, 1.75, 0])
        self.play(Create(ivax), run_time=0.8)
        v = DATA["iv"]["v"]
        gpu = ivax[0].plot_line_graph(v, [x * 1000 for x in DATA["iv"]["pu"]],
                                      add_vertex_dots=False, line_color=KU_C, stroke_width=4)
        gpd = ivax[0].plot_line_graph(v, [x * 1000 for x in DATA["iv"]["pd"]],
                                      add_vertex_dots=False, line_color=KD_C, stroke_width=4)
        # Labels ride on the curve ends rather than above the axes, which is
        # where the act title lives.
        lab_pd = small("I_pd(V)", 19, KD_C).move_to(ivax[0].c2p(0.85, 93))
        lab_pu = small("I_pu(V)", 19, KU_C).move_to(ivax[0].c2p(1.05, -66))
        ivlab = VGroup(lab_pd, lab_pu)
        self.play(Create(gpu), Create(gpd), FadeIn(ivlab), run_time=1.4)
        self.iv = VGroup(ivax, gpu, gpd, ivlab)

        s = DATA["snapshot"]
        cursor = Line(self.ax_pad[0].c2p(s["t_ns"], PAD_Y[0]),
                      self.ax_pad[0].c2p(s["t_ns"], PAD_Y[1]), color=INK, stroke_width=2.5)
        tlab = small("t = %.3f ns" % s["t_ns"], 17, INK).next_to(self.ax_pad, DOWN, buff=0.22)
        self.play(Create(cursor), FadeIn(tlab), run_time=0.8)
        self.cursor = VGroup(cursor, tlab)

        self.row_lo = self.detail_row("lo", LOW_C, "fixture to 0 V", 0.0)
        self.row_hi = self.detail_row("hi", HIGH_C, "fixture to VCC", DATA["vcc"], brisk=True)

    def detail_row(self, which, colour, caption, v_fix, brisk=False):
        """One fixture, worked end to end: lookup, right-hand side, equation."""
        s = DATA["snapshot"]
        vpad = s["v_%s" % which]
        i_pu, i_pd, rhs = s["pu_%s" % which], s["pd_%s" % which], s["rhs_%s" % which]
        terms = s["terms_%s" % which]
        rate = 0.62 if brisk else 1.0

        # 1. the pad voltage at this instant
        dot = Dot(self.ax_pad[0].c2p(s["t_ns"], vpad), color=colour, radius=0.06)
        # Under the time label rather than beside the dot: at 1.2 V the dot sits
        # on top of the other trace and the text lands on the waveform.
        vtag = small("V = %.3f V" % vpad, 18, colour)
        vtag.next_to(self.cursor[1], DOWN, buff=0.14)
        self.play(FadeIn(dot), FadeIn(vtag), run_time=0.55 * rate)

        # 2. carry it across to the tables and read both currents there
        ivax = self.iv[0][0]
        bridge = DashedLine(dot.get_center(), ivax.c2p(vpad, 0), color=colour,
                            stroke_width=2, dash_length=0.09).set_opacity(0.7)
        vline = Line(ivax.c2p(vpad, -80), ivax.c2p(vpad, 100), color=colour, stroke_width=2.5)
        d_pu = Dot(ivax.c2p(vpad, i_pu * 1000), color=KU_C, radius=0.07)
        d_pd = Dot(ivax.c2p(vpad, i_pd * 1000), color=KD_C, radius=0.07)
        self.play(Create(bridge), run_time=0.6 * rate)
        self.play(Create(vline), FadeIn(d_pu), FadeIn(d_pd), run_time=0.6 * rate)

        reads = VGroup(
            small("I_pu = %s mA" % ma(i_pu), 19, KU_C),
            small("I_pd = %s mA" % ma(i_pd), 19, KD_C),
        ).arrange(DOWN, buff=0.14, aligned_edge=LEFT)
        reads.next_to(self.iv[0], RIGHT, buff=0.35)
        self.play(FadeIn(reads), run_time=0.5 * rate)

        # 3. the right-hand side: the pad current we already know
        dvdt = terms["c_comp"] / DATA["c_comp"] / 1e9
        title = small("known pad current, %s" % caption, 20, colour)
        line_r = eq("(V_{fix} - V)/R \\;=\\; (%.3f - %.3f)/50 \\;=\\; %s\\ \\mathrm{mA}"
                    % (v_fix, vpad, ma(terms["rfix"])),
                    "(V_fix - V)/R = (%.3f - %.3f)/50 = %s mA"
                    % (v_fix, vpad, ma(terms["rfix"])), 18)
        line_c = eq("C_{comp}\\,dV/dt \\;=\\; 0.468\\,\\mathrm{pF} \\times %.1f\\ \\mathrm{V/ns}"
                    " \\;=\\; %s\\ \\mathrm{mA}" % (dvdt, ma(terms["c_comp"])),
                    "C_comp x dV/dt = 0.468 pF x %.1f V/ns = %s mA"
                    % (dvdt, ma(terms["c_comp"])), 18)
        total = eq("%s - %s \\;=\\; %s\\ \\mathrm{mA}"
                   % (ma(terms["rfix"]), ma(terms["c_comp"]).lstrip("+"), ma(rhs)),
                   "%s  -  %s  =  %s mA"
                   % (ma(terms["rfix"]), ma(terms["c_comp"]).lstrip("+"), ma(rhs)), 20, colour)
        block = VGroup(title, line_r, line_c, total).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        # Typeset maths runs wider than the unicode fallback -- wide enough that
        # block and equation would collide -- so both are capped rather than
        # sized by trial, which would only hold for whichever mode was tried.
        if block.width > 6.2:
            block.scale(6.2 / block.width)
        block.move_to([-3.7, -1.35, 0])
        for part in block:
            self.play(FadeIn(part), run_time=0.45 * rate)
        self.wait(0.6 * rate)

        # 4. and the equation those three numbers make
        row = eq("%s\\,K_u \\;%s\\,K_d \\;=\\; %s\\ \\mathrm{mA}" % (ma(i_pu), ma(i_pd), ma(rhs)),
                 "%s Ku   %s Kd  =  %s mA" % (ma(i_pu), ma(i_pd), ma(rhs)), 24, colour)
        if row.width > 5.4:
            row.scale(5.4 / row.width)
        row.move_to([3.7, -1.35, 0])
        arrow = Arrow(block.get_right() + RIGHT * 0.1, row.get_left() + LEFT * 0.15,
                      color=FAINT, buff=0.1, stroke_width=3,
                      max_tip_length_to_length_ratio=0.18)
        self.play(Create(arrow), run_time=0.4 * rate)
        self.play(Write(row), run_time=1.0 * rate)
        self.wait(0.9 * rate)

        self.play(FadeOut(bridge), FadeOut(vline), FadeOut(d_pu), FadeOut(d_pd),
                  FadeOut(reads), FadeOut(block), FadeOut(vtag), FadeOut(dot),
                  FadeOut(arrow), FadeOut(row), run_time=0.5)
        return row

    # ------------------------------------------------------------------ act 5
    def act5_solve(self):
        self.play(FadeOut(self.iv), FadeOut(self.cursor), FadeOut(self.head4),
                  FadeOut(self.ax_pad), FadeOut(self.graph_lo), FadeOut(self.graph_hi),
                  run_time=0.8)

        head = small("Two equations, two unknowns", 32, INK, "BOLD")
        head.to_edge(UP, buff=0.7)
        rows = VGroup(self.row_lo, self.row_hi)
        rows.arrange(DOWN, buff=0.6, aligned_edge=LEFT).scale(1.4).move_to([0, 0.95, 0])
        self.play(Write(head), run_time=0.9)
        self.play(FadeIn(rows), run_time=1.0)
        self.wait(1.4)

        s = DATA["snapshot"]
        ans = VGroup(
            eq("K_u = %.3f" % s["ku"], "Ku = %.3f" % s["ku"], 34),
            eq("K_d = %.3f" % s["kd"], "Kd = %.3f" % s["kd"], 34),
        ).arrange(RIGHT, buff=1.2)
        ans.move_to([0, -1.5, 0])
        self.play(FadeIn(ans, shift=UP * 0.25), run_time=1.1)
        self.wait(2.4)
        self.play(FadeOut(rows), FadeOut(ans), FadeOut(head), run_time=0.7)

    # ------------------------------------------------------------------ act 6
    def act6_sweep(self):
        head = small("Repeat at every timestep", 30, INK, "BOLD")
        head.to_edge(UP, buff=0.45)
        pads = VGroup(self.ax_pad, self.graph_lo, self.graph_hi)
        pads.scale(0.86 / 0.58).move_to([0, 1.45, 0])
        self.play(Write(head), FadeIn(pads), run_time=1.0)

        kax = self.k_axes()
        kax.move_to([-0.5, -1.95, 0])
        kyl = small("coefficient", 18, FAINT).rotate(np.pi / 2).next_to(kax, LEFT, buff=0.22)
        self.play(Create(kax), FadeIn(kyl), run_time=0.8)

        t = np.asarray(DATA["t"])
        ku = np.nan_to_num(np.asarray(DATA["ku"]), nan=0.0)
        kd = np.nan_to_num(np.asarray(DATA["kd"]), nan=0.0)
        tracker = ValueTracker(float(t[0]))
        pad_ax = self.ax_pad[0]

        def partial(vals, colour):
            def make():
                m = t <= tracker.get_value()
                if int(m.sum()) < 2:
                    return VGroup()
                return kax.plot_line_graph(
                    list(t[m]), list(np.clip(vals[m], -0.35, 1.35)),
                    add_vertex_dots=False, line_color=colour, stroke_width=4)
            return make

        gku = always_redraw(partial(ku, KU_C))
        gkd = always_redraw(partial(kd, KD_C))
        bar = always_redraw(lambda: Line(
            pad_ax.c2p(tracker.get_value(), PAD_Y[0]),
            pad_ax.c2p(tracker.get_value(), PAD_Y[1]),
            color=INK, stroke_width=2.5).set_opacity(0.55))
        self.add(gku, gkd, bar)

        # Beside the panel, not above it: above lands on the pad plot's axis label.
        lab = VGroup(small("Ku(t)", 24, KU_C), small("Kd(t)", 24, KD_C)).arrange(DOWN, buff=0.3)
        lab.next_to(kax, RIGHT, buff=0.35)
        self.play(FadeIn(lab), run_time=0.5)

        self.play(tracker.animate.set_value(float(t[-1])), run_time=5.5)
        self.wait(0.6)

        closing = small("Ku and Kd say how much of each device is on, at every instant",
                        26, GOLD)
        closing.next_to(kax, DOWN, buff=0.42).set_x(0)
        self.play(FadeIn(closing), run_time=0.8)
        self.wait(2.4)

    # ---------------------------------------------------------------- pieces
    def ibis_schematic(self):
        """The IBIS output stage: two scaled devices and C_comp onto one pad.

        Drawn rather than described because the equation's terms are only
        obvious once you can see they are parallel branches on a single node.
        """
        vcc = Line([-1.7, 2.1, 0], [1.7, 2.1, 0], color=FAINT, stroke_width=4)
        gnd = Line([-1.7, -1.9, 0], [1.7, -1.9, 0], color=FAINT, stroke_width=4)
        vlab = small("VCC", 18, FAINT).next_to(vcc, UP, buff=0.12)
        glab = small("GND", 18, FAINT).next_to(gnd, DOWN, buff=0.12)

        pu = Rectangle(width=1.9, height=0.72, color=KU_C, stroke_width=3).move_to([-0.55, 1.2, 0])
        pu_t = small("pullup I-V", 18, KU_C).move_to(pu.get_center())
        pd = Rectangle(width=1.9, height=0.72, color=KD_C, stroke_width=3).move_to([-0.55, -1.0, 0])
        pd_t = small("pulldown I-V", 17, KD_C).move_to(pd.get_center())

        node = np.array([-0.55, 0.15, 0])
        w1 = Line([-0.55, 2.1, 0], pu.get_top(), color=INK, stroke_width=3)
        w2 = Line(pu.get_bottom(), node, color=INK, stroke_width=3)
        w3 = Line(node, pd.get_top(), color=INK, stroke_width=3)
        w4 = Line(pd.get_bottom(), [-0.55, -1.9, 0], color=INK, stroke_width=3)

        ku_t = small("x Ku", 22, KU_C).next_to(pu, RIGHT, buff=0.24)
        kd_t = small("x Kd", 22, KD_C).next_to(pd, RIGHT, buff=0.24)

        lead = Line(node, node + RIGHT * 3.0, color=INK, stroke_width=3)
        dot = Dot(lead.get_end(), color=INK, radius=0.07)
        plab = small("pad", 19, INK).next_to(dot, UP, buff=0.16)

        cx = 1.95
        cwire = Line([cx, 0.15, 0], [cx, -0.4, 0], color=FAINT, stroke_width=3)
        p1 = Line([cx - 0.3, -0.4, 0], [cx + 0.3, -0.4, 0], color=FAINT, stroke_width=4)
        p2 = Line([cx - 0.3, -0.62, 0], [cx + 0.3, -0.62, 0], color=FAINT, stroke_width=4)
        cwire2 = Line([cx, -0.62, 0], [cx, -1.9, 0], color=FAINT, stroke_width=3)
        cgnd = Line([cx - 0.5, -1.9, 0], [cx + 0.5, -1.9, 0], color=FAINT, stroke_width=4)
        clab = small("C_comp", 17, FAINT).next_to(p1, RIGHT, buff=0.22).shift(DOWN * 0.11)

        inp = Arrow([-3.5, 0.15, 0], [-2.0, 0.15, 0], color=FAINT, buff=0,
                    stroke_width=3, max_tip_length_to_length_ratio=0.16)
        ilab = small("input", 18, FAINT).next_to(inp, UP, buff=0.12)
        gate = Line([-1.95, 1.2, 0], [-1.95, -1.0, 0], color=FAINT, stroke_width=2)
        g1 = Line([-2.0, 0.15, 0], [-1.95, 0.15, 0], color=FAINT, stroke_width=2)
        g2 = Line([-1.95, 1.2, 0], pu.get_left(), color=FAINT, stroke_width=2)
        g3 = Line([-1.95, -1.0, 0], pd.get_left(), color=FAINT, stroke_width=2)

        return VGroup(vcc, gnd, vlab, glab, w1, w2, w3, w4, pu, pu_t, pd, pd_t,
                      ku_t, kd_t, lead, dot, plab, cwire, p1, p2, cwire2, cgnd, clab,
                      inp, ilab, gate, g1, g2, g3), dot

    def buffer_block(self):
        box = Rectangle(width=2.0, height=1.3, color=INK, stroke_width=3)
        txt = small("buffer", 22, INK).move_to(box.get_center())
        inp = Arrow(box.get_left() + LEFT * 0.9, box.get_left(), color=FAINT,
                    buff=0, stroke_width=3, max_tip_length_to_length_ratio=0.25)
        lead = Line(box.get_right(), box.get_right() + RIGHT * 0.9, color=INK, stroke_width=3)
        dot = Dot(lead.get_end(), color=INK, radius=0.06)
        plab = small("pad", 18, FAINT).next_to(dot, UP, buff=0.15)
        return VGroup(box, txt, inp, lead, plab), dot

    def fixture(self, anchor, r_label, v_label, colour, down=True):
        sign = -1.0 if down else 1.0
        v = Line(anchor, anchor + np.array([0.0, sign * 0.7, 0.0]), color=colour, stroke_width=3)
        res = Rectangle(width=0.32, height=0.7, color=colour, stroke_width=3)
        res.move_to(v.get_end() + np.array([0.0, sign * 0.42, 0.0]))
        tail = Line(res.get_center() + np.array([0.0, sign * 0.35, 0.0]),
                    res.get_center() + np.array([0.0, sign * 0.9, 0.0]),
                    color=colour, stroke_width=3)
        rail = Line(tail.get_end() + LEFT * 0.4, tail.get_end() + RIGHT * 0.4,
                    color=colour, stroke_width=5)
        rl = small(r_label, 18, colour).next_to(res, RIGHT, buff=0.14)
        vl = small(v_label, 18, colour).next_to(rail, DOWN if down else UP, buff=0.1)
        return VGroup(v, res, tail, rail, rl, vl)

    def pad_axes(self):
        ax = Axes(x_range=[4.85, 5.85, 0.25], y_range=[PAD_Y[0], PAD_Y[1], 0.5],
                  x_length=6.2, y_length=3.1,
                  axis_config={"color": FAINT, "stroke_width": 2, "font_size": 16},
                  x_axis_config={"include_numbers": True, "label_constructor": Text,
                                 "decimal_number_config": {"num_decimal_places": 1}},
                  y_axis_config={"include_numbers": True, "label_constructor": Text,
                                 "decimal_number_config": {"num_decimal_places": 1}},
                  tips=False)
        xl = small("time (ns)", 18, FAINT).next_to(ax, DOWN, buff=0.2)
        yl = small("pad (V)", 18, FAINT).rotate(np.pi / 2).next_to(ax, LEFT, buff=0.2)
        return VGroup(ax, xl, yl)

    def iv_axes(self):
        # Top out at 100 rather than 80: the pulldown curve reaches 76 mA, and the
        # curve label needs somewhere to sit that is not on top of it.
        ax = Axes(x_range=[0, 1.8, 0.5], y_range=[-80, 100, 40],
                  x_length=4.6, y_length=3.0,
                  axis_config={"color": FAINT, "stroke_width": 2, "font_size": 15},
                  x_axis_config={"include_numbers": True, "label_constructor": Text,
                                 "decimal_number_config": {"num_decimal_places": 1}},
                  y_axis_config={"include_numbers": True, "label_constructor": Text,
                                 "decimal_number_config": {"num_decimal_places": 0}},
                  tips=False)
        xl = small("pad voltage (V)", 17, FAINT).next_to(ax, DOWN, buff=0.18)
        yl = small("current (mA)", 17, FAINT).rotate(np.pi / 2).next_to(ax, LEFT, buff=0.18)
        return VGroup(ax, xl, yl)

    def k_axes(self):
        return Axes(x_range=[4.85, 5.85, 0.25], y_range=[-0.35, 1.35, 0.5],
                    x_length=9.0, y_length=2.5,
                    axis_config={"color": FAINT, "stroke_width": 2, "font_size": 16},
                    x_axis_config={"include_numbers": True, "label_constructor": Text,
                                   "decimal_number_config": {"num_decimal_places": 1}},
                    y_axis_config={"include_numbers": True, "label_constructor": Text,
                                   "decimal_number_config": {"num_decimal_places": 1}},
                    tips=False)
