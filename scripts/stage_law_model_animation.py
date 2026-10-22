#!/usr/bin/env python3
"""The stage-law model of the IBIS predriver, explained with manim (Community v0.22).

Where scripts/stage_law_flow_animation.py explained the fitting procedure, this one explains the
model itself, in seven parts: what the file knows and what a short pulse does; one stage and its
law, term by term, as a bucket that fills and drains; the chain, whose delay is spent in
handovers; the map from the gate to the conducting fraction; the pad; a compact recap of what the
file fixes, what it cannot, and what one measurement settles; the parameter set as a closing card.
Every curve is a stored result of the project, gathered into one file by
scripts/stage_law_model_animation_data.py; nothing is simulated here. The test buffer is ex2.

    py -3.14 scripts/stage_law_model_animation_data.py
    py -3.14 -m manim -qm --disable_caching --media_dir results/stage_law_model_animation_2026-10-22/media ^
        scripts/stage_law_model_animation.py StageLawModel

The drawing helpers (mtex, txt, axes, curve, box), the palette and the caption/heading/clear_stage
methods are those of stage_law_flow_animation, imported rather than copied; its mathtext cache is
pointed at this study's media folder right after the import (sla.CACHE), so the SVGs land here.
Formulas are typeset with matplotlib's mathtext (no LaTeX on this machine). The classes P1..P7
render one part each, for checking.

Output: results/stage_law_model_animation_2026-10-22/media/videos/stage_law_model_animation/720p30/StageLawModel.mp4
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath
from manim import (  # noqa: E402
    DOWN, LEFT, RIGHT, UP, UL, UR, DR, WHITE, AnimationGroup, Arrow, Circle, Create, DashedLine, Dot, FadeIn, FadeOut,
    GrowArrow, ImageMobject, Line, Rectangle, ReplacementTransform, RoundedRectangle, Transform, VGroup, VMobject,
    ValueTracker, Write, always_redraw, linear, config,
)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import stage_law_flow_animation as sla  # noqa: E402

STUDY = ROOT / "results" / "stage_law_model_animation_2026-10-22"
sla.CACHE = STUDY / "media" / "mtex"            # the mathtext SVGs of this study live in its own media tree
DATA = STUDY / "data" / "model_data.npz"

DARK, TEAL, BLUE, RED, GREY, ORANGE, SAND = sla.DARK, sla.TEAL, sla.BLUE, sla.RED, sla.GREY, sla.ORANGE, sla.SAND
AXIS = "#55606A"
LIGHT_TEAL = "#BFE3E1"
TEALS = ("#9CC8C6", TEAL, "#0B5F5C")
MARKS = ("#3B1F6E", "#3F4E9A", "#2A7F9E", "#1FA187", "#6CB94A", "#C9A227")
mtex, txt, axes, curve, box = sla.mtex, sla.txt, sla.axes, sla.curve, sla.box
config.background_color = WHITE


# ------------------------------------------------------------------ helpers added for this scene
def partial_curve(ax, x, y, tmax, color=DARK, width=4.0) -> VMobject:
    """The part of a curve up to x = tmax, for tracing with a ValueTracker (sla.curve draws it whole)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    keep = (x >= ax.x_range[0]) & (x <= min(tmax, ax.x_range[1]))
    xs, ys = x[keep], y[keep]
    m = VMobject()
    if len(xs) >= 2:
        lo, hi = ax.y_range[0], ax.y_range[1]
        ys = np.clip(ys, lo - 0.02 * (hi - lo), hi + 0.02 * (hi - lo))
        m.set_points_as_corners([ax.c2p(a, b) for a, b in zip(xs, ys)])
    return m.set_stroke(color, width=width)


def vline(ax, x, y0, y1, color=GREY, width=1.5) -> DashedLine:
    return DashedLine(ax.c2p(x, y0), ax.c2p(x, y1), color=color, stroke_width=width, dash_length=0.08)


def hline(ax, y, x0, x1, color=GREY, width=1.5) -> DashedLine:
    return DashedLine(ax.c2p(x0, y), ax.c2p(x1, y), color=color, stroke_width=width, dash_length=0.08)


def legend(items, fs=17, buff=0.1) -> VGroup:
    """Rows of (colour swatch, label); sla has no legend helper."""
    rows = VGroup()
    for color, label in items:
        sw = Line([0, 0, 0], [0.4, 0, 0], color=color, stroke_width=4)
        rows.add(VGroup(sw, txt(label, fs, color)).arrange(RIGHT, buff=0.12))
    return rows.arrange(DOWN, aligned_edge=LEFT, buff=buff)


def block(text: str, w: float, h: float, fs: int = 16, color=DARK) -> VGroup:
    """A plain rectangle with a label, no fill: the block-diagram style of the paper's Fig. 5(a)
    (sla.box is the rounded, filled box of the earlier animation)."""
    r = Rectangle(width=w, height=h).set_fill(WHITE, opacity=1).set_stroke(color, width=2)
    t = txt(text, fs, color).move_to(r)
    if t.width > w - 0.15:
        t.set(width=w - 0.15)
    return VGroup(r, t)


def arrow_between(a, b, color=DARK) -> Arrow:
    return Arrow(a.get_right(), b.get_left(), buff=0.04, color=color, stroke_width=2.5,
                 max_tip_length_to_length_ratio=0.35, max_stroke_width_to_length_ratio=8)


def logaxes(xr, yr, w, h, xt, yt, xlabel="", ylabel="", fs=18) -> VGroup:
    """Log-log axes: a linear Axes over log10 of the ranges, with the tick labels written as the
    values themselves. sla.axes labels ticks with their coordinate, which a log axis cannot use.
    The group's [0] is the Axes; plot with ax.c2p(log10(x), log10(y))."""
    from manim import Axes
    lx, ly = (np.log10(xr[0]), np.log10(xr[1])), (np.log10(yr[0]), np.log10(yr[1]))
    ax = Axes(x_range=[lx[0], lx[1], 1], y_range=[ly[0], ly[1], 1], x_length=w, y_length=h,
              axis_config={"color": AXIS, "include_numbers": False, "include_ticks": False, "stroke_width": 2,
                           "include_tip": False})
    g = VGroup(ax)
    for v in xt:
        p = ax.c2p(np.log10(v), ly[0])
        g.add(Line(p, p + 0.06 * DOWN, color=AXIS, stroke_width=2), txt(f"{v:g}", fs, AXIS).next_to(p, DOWN, buff=0.12))
    for v in yt:
        p = ax.c2p(lx[0], np.log10(v))
        g.add(Line(p, p + 0.06 * LEFT, color=AXIS, stroke_width=2), txt(f"{v:g}", fs, AXIS).next_to(p, LEFT, buff=0.12))
    if xlabel:
        g.add(txt(xlabel, fs + 1, AXIS).next_to(ax, DOWN, buff=0.45))
    if ylabel:
        g.add(txt(ylabel, fs + 1, AXIS).rotate(np.pi / 2).next_to(ax, LEFT, buff=0.7))
    return g


def _ink(s: str):
    bb = TextPath((0, 0), s, size=24, prop=FontProperties()).get_extents()
    return bb.x0, bb.x1


def term_box(eq, full: str, prefix: str, term: str, color=ORANGE) -> RoundedRectangle:
    """A highlight box around one term of a mathtext formula rendered by mtex. The term's position is
    found by measuring the ink width of the formula up to the term with matplotlib's TextPath, which
    uses the same mathtext layout as the SVG. `prefix` is the formula up to the term, opened with
    '$' but not closed; the closing '$' is added here."""
    x0, x1 = _ink(full)
    a = _ink(prefix + "$")[1] if prefix.strip("$ ") else x0
    b = _ink(prefix + term + "$")[1]
    left, wdt = eq.get_left()[0], eq.width
    xa = left + (a - x0) / (x1 - x0) * wdt
    xb = left + (b - x0) / (x1 - x0) * wdt
    r = RoundedRectangle(corner_radius=0.08, width=xb - xa + 0.18, height=eq.height + 0.25)
    r.set_fill(color, opacity=0.14).set_stroke(color, width=2)
    return r.move_to([(xa + xb) / 2 + 0.04, eq.get_center()[1], 0])


LAW = r"$\frac{dv}{dt} = s_{up}\,h(u)\,r(1-v) \;-\; s_{dn}\,h(1-u)\,r(v)$"
LAW_PRE = r"$\frac{dv}{dt} = "
LAW_UP = r"s_{up}\,h(u)\,r(1-v)"
LAW_DN = r"s_{dn}\,h(1-u)\,r(v)"


# ------------------------------------------------------------------ the scene
class StageLawModel(sla.StageLawFlow):
    """Subclassed for caption(), heading() and clear_stage(); setup and construct are replaced."""

    def setup(self):
        self.camera.background_color = WHITE
        self.d = dict(np.load(DATA, allow_pickle=True))
        self._cap = None
        self._head = None

    def caption_with(self, s: str, anims, wait: float = 0.8, size: float = 27):
        """A caption that fades in while other animations run (the bucket keeps filling)."""
        new = txt(s, size, DARK).to_edge(DOWN, buff=0.45)
        if new.width > 12.8:
            new.set(width=12.8)
        group = [FadeIn(new, shift=0.2 * UP, run_time=0.6)]
        if self._cap is not None:
            group.append(FadeOut(self._cap, run_time=0.3))
        self._cap = new
        self.play(AnimationGroup(*group, *anims, lag_ratio=0))
        if wait:
            self.wait(wait)

    # ---- 0. title
    def part_title(self):
        self.next_section("title")
        t1 = txt("The stage-law model of the IBIS predriver", 44, DARK, weight="BOLD").shift(0.6 * UP)
        t2 = txt("one stage, its law, the chain, the map, the pad", 28, "#55606A").next_to(t1, DOWN, buff=0.4)
        t3 = txt("every curve is a stored result on the test buffer ex2", 22, GREY).next_to(t2, DOWN, buff=0.8)
        self.play(Write(t1), run_time=1.6)
        self.play(FadeIn(t2, shift=0.2 * UP), run_time=0.8)
        self.play(FadeIn(t3), run_time=0.6)
        self.wait(1.8)
        self.play(FadeOut(t1), FadeOut(t2), FadeOut(t3), run_time=0.6)

    # ---- 1. what the file knows, and what a short pulse does
    def part_file(self):
        d = self.d
        self.next_section("file")
        self.heading("1 · What the file knows, and what a short pulse does")
        pin = txt("input\npin", 16)
        inv = [block("inverter\n1", 1.05, 0.9), block("inverter\n2", 1.05, 0.9), txt("…", 26), block("inverter\nK", 1.05, 0.9)]
        outs = block("output stage:\npull-up device,\npull-down device", 2.2, 1.1, 14)
        cc = block("C_comp", 1.0, 0.9)
        pkg = block("package\nR, L, C", 1.2, 0.9)
        pad = txt("pad", 17)
        items = [pin, *inv, outs, cc, pkg, pad]
        row = VGroup(*items).arrange(RIGHT, buff=0.7).move_to(1.3 * UP)
        if row.width > 13.4:
            row.set(width=13.4)
        arrows = VGroup(*[arrow_between(a, b) for a, b in zip(items[:-1], items[1:])])
        lab_g = txt("gate", 14).next_to(arrows[4], UP, buff=0.08)
        lab_d = txt("die", 14).next_to(arrows[5], UP, buff=0.08)
        self.play(FadeIn(pin), run_time=0.3)
        for a, b in zip(arrows, items[1:]):
            self.play(GrowArrow(a), FadeIn(b), run_time=0.3)
        self.play(FadeIn(lab_g), FadeIn(lab_d), run_time=0.3)
        self.caption("A buffer: the input pin drives a chain of inverters, the predriver, whose last node is the gate of the output stage.")
        y_lo = outs.get_bottom()[1] - 0.25
        br2 = VGroup(Line([outs.get_left()[0], y_lo, 0], [pkg.get_right()[0], y_lo, 0], color=DARK, stroke_width=1.5),
                     Line([outs.get_left()[0], y_lo, 0], [outs.get_left()[0], y_lo + 0.12, 0], color=DARK, stroke_width=1.5),
                     Line([pkg.get_right()[0], y_lo, 0], [pkg.get_right()[0], y_lo + 0.12, 0], color=DARK, stroke_width=1.5))
        l2 = txt("described in the file: I–V tables, V–T waveforms of complete transitions, C_comp, package", 17, DARK).next_to(br2, DOWN, buff=0.08)
        if l2.get_right()[0] > 6.9:
            l2.shift((6.9 - l2.get_right()[0]) * RIGHT)
        self.play(Create(br2), FadeIn(l2), run_time=0.7)
        self.caption("The file describes the output stage (I–V tables), C_comp, the package, and the pad voltage of complete transitions.")
        y_hi = inv[0].get_top()[1] + 0.25
        br1 = VGroup(Line([inv[0].get_left()[0], y_hi, 0], [inv[3].get_right()[0], y_hi, 0], color=GREY, stroke_width=1.5),
                     Line([inv[0].get_left()[0], y_hi, 0], [inv[0].get_left()[0], y_hi - 0.12, 0], color=GREY, stroke_width=1.5),
                     Line([inv[3].get_right()[0], y_hi, 0], [inv[3].get_right()[0], y_hi - 0.12, 0], color=GREY, stroke_width=1.5))
        l1 = txt("predriver: not described in the file", 17, GREY).next_to(br1, UP, buff=0.08)
        grey_anims = []
        for m in inv:
            if isinstance(m, VGroup):
                grey_anims += [m[0].animate.set_stroke(GREY), m[1].animate.set_color(GREY)]
            else:
                grey_anims.append(m.animate.set_color(GREY))
        self.play(*grey_anims, Create(br1), FadeIn(l1), run_time=0.8)
        self.caption("It says nothing about the predriver, which is where a short pulse is interrupted.", wait=2.8)
        self.clear_stage()
        # ex2's complete transition and the 810 ps pulse, normalised
        A = axes((-0.5, 4.0, 1), (-0.1, 1.2, 0.5), 5.4, 3.0, xt=[0, 1, 2, 3, 4], yt=[0, 0.5, 1],
                 xlabel="time from the input edge (ns)", ylabel="normalised").shift(3.3 * LEFT + 0.2 * UP)
        ax = A[0]
        self.play(Create(A), run_time=0.7)
        c_in = curve(ax, d["p1_t"], d["p1_in"], GREY, 2.5)
        c_g = curve(ax, d["p1_t"], d["p1_gate"], TEAL, 4.5)
        c_p = curve(ax, d["p1_t"], d["p1_pad"], DARK, 3.5)
        self.play(Create(c_in), run_time=0.6)
        self.play(Create(c_g), run_time=1.0)
        self.play(Create(c_p), run_time=1.0)
        lg = legend([(GREY, "input pin"), (TEAL, "gate of the output device (probed)"), (DARK, "pad")], 15, 0.06)
        lg.next_to(ax.c2p(1.9, 0.08), RIGHT, buff=0.0).align_to(ax.c2p(0, 0.55), UP)
        tA = txt("complete transition", 18, DARK).next_to(ax, UP, buff=0.15)
        self.play(FadeIn(lg), FadeIn(tA), run_time=0.5)
        self.caption("ex2's complete transition: input pin, probed gate of the output device and pad, each on its own 0-to-1 scale. The gate reaches its rail.", wait=3.0)
        B = axes((-0.5, 3.0, 1), (-0.1, 1.2, 0.5), 5.4, 3.0, xt=[0, 1, 2, 3], yt=[0, 0.5, 1],
                 xlabel="time from the input edge (ns)").shift(3.6 * RIGHT + 0.2 * UP)
        bx = B[0]
        self.play(Create(B), run_time=0.6)
        s_in = curve(bx, d["p1s_t"], d["p1s_in"], GREY, 2.5)
        s_g = curve(bx, d["p1s_t"], d["p1s_gate"], TEAL, 4.5)
        s_p = curve(bx, d["p1s_t"], d["p1s_pad"], DARK, 3.5)
        tB = txt("810 ps input pulse", 18, DARK).next_to(bx, UP, buff=0.15)
        self.play(Create(s_in), FadeIn(tB), run_time=0.6)
        self.play(Create(s_g), Create(s_p), run_time=1.2)
        gpk = float(d["p1_gate_peak"])
        pl = hline(bx, gpk, -0.5, 3.0, TEAL)
        pt = txt(f"gate turns back at {gpk:.2f}", 17, TEAL).next_to(bx.c2p(1.6, gpk), UP, buff=0.08)
        self.play(Create(pl), FadeIn(pt), run_time=0.5)
        self.caption(f"An 810 ps pulse: the input returns before the chain has finished, and the gate turns back at {gpk:.2f} of its swing.", wait=3.0)
        self.play(FadeOut(s_in), FadeOut(s_g), FadeOut(s_p), FadeOut(pl), FadeOut(pt), FadeOut(B), FadeOut(tB), run_time=0.5)
        C = axes((-0.5, 3.0, 1), (-0.3, 1.5, 0.5), 5.4, 3.0, xt=[0, 1, 2, 3], yt=[0, 0.5, 1, 1.5],
                 xlabel="time from the input edge (ns)").shift(3.6 * RIGHT + 0.2 * UP)
        cx = C[0]
        tC = txt("810 ps input pulse: pad voltage (V)", 18, DARK).next_to(cx, UP, buff=0.15)
        self.play(Create(C), FadeIn(tC), run_time=0.6)
        v_si = curve(cx, d["p1_pad_t"], d["p1_pad_si"], DARK, 4.5)
        v_nat = curve(cx, d["p1_pad_t"], d["p1_pad_nat"], BLUE, 4).set_stroke(opacity=0.9)
        self.play(Create(v_si), run_time=1.0)
        self.play(Create(v_nat), run_time=1.0)
        lgc = legend([(DARK, f"transistor, peak {float(d['p1_pad_peak']):.2f} V"),
                      (BLUE, f"native IBIS: {float(d['p1_nat_err']):+.0f} %")], 15, 0.06)
        lgc.next_to(cx.c2p(0.0, 1.5), DOWN, buff=0.02).align_to(cx.c2p(0.05, 1.45), LEFT)
        self.play(FadeIn(lgc), run_time=0.5)
        self.caption(f"The native IBIS element replays the coefficient of a complete transition against time: its pad overshoots the measured peak by {float(d['p1_nat_err']):+.0f} %.", wait=3.2)
        self.clear_stage()

    # ---- 2. one stage and its law
    def _schematic(self) -> dict:
        """The inverter of the paper's Fig. 3: PMOS above, NMOS below, the output node into a lumped C."""
        s = 0.052
        X, YP, YN = 38, 46, 20

        def P(x, y):
            return np.array([(x - 50) * s, (y - 33) * s, 0])

        def L(x0, y0, x1, y1, color=DARK, w=2.5):
            return Line(P(x0, y0), P(x1, y1), color=color, stroke_width=w)

        g = VGroup()

        def mos(x, y, pmos):
            g.add(L(x, y - 7, x, y + 7), L(x - 4, y - 5, x - 4, y + 5), L(x, y + 6, x + 8, y + 6), L(x, y - 6, x + 8, y - 6),
                  L(x + 8, y + 6, x + 8, y + 13), L(x + 8, y - 13, x + 8, y - 6))
            if pmos:
                g.add(Circle(radius=1.6 * s, color=DARK, stroke_width=2.5).move_to(P(x - 6, y)), L(x - 14, y, x - 8, y))
            else:
                g.add(L(x - 14, y, x - 4, y))

        mos(X, YP, True)
        mos(X, YN, False)
        g.add(L(X + 8, YP + 13, X + 8, 62), L(X + 2, 62, X + 14, 62), L(X + 8, 4, X + 8, YN - 13), L(X + 2, 4, X + 14, 4),
              L(X + 8, YN + 13, X + 8, YP - 13), L(X - 14, YN, X - 14, YP), L(X - 30, 33, X - 14, 33), L(X + 8, 33, X + 40, 33))
        g.add(Dot(P(X + 8, 33), radius=0.05, color=DARK))
        cx = X + 28
        g.add(L(cx, 33, cx, 24), L(cx - 4, 24, cx + 4, 24), L(cx - 4, 20.5, cx + 4, 20.5), L(cx, 20.5, cx, 4), L(X + 2, 4, cx + 6, 4))
        nxt = Arrow(P(X + 40, 33), P(X + 47, 33), buff=0, color=DARK, stroke_width=2.5, max_tip_length_to_length_ratio=0.5)
        out = {"body": g, "next": nxt,
               "vdd": mtex(r"$V_{DD}$", DARK, 0.3).next_to(P(X + 8, 62), UP, buff=0.08),
               "vin": mtex(r"$V_{in}$", DARK, 0.3).next_to(P(X - 30, 33), LEFT, buff=0.1),
               "vo": mtex(r"$V_o$", DARK, 0.28).next_to(P(X + 8, 33), UL, buff=0.06),
               "C": mtex(r"$C$", DARK, 0.26).next_to(P(cx + 4, 22.2), RIGHT, buff=0.08),
               "next_t": txt("next\nstage", 15).next_to(P(X + 47, 33), RIGHT, buff=0.08),
               "ip": Arrow(P(X + 8, YP - 6), P(X + 8, YP - 11.5), buff=0, color=TEAL, stroke_width=4, max_tip_length_to_length_ratio=0.5),
               "in": Arrow(P(X + 8, YN + 11.5), P(X + 8, YN + 6), buff=0, color=RED, stroke_width=4, max_tip_length_to_length_ratio=0.5),
               "ip_t": mtex(r"$I_P$", TEAL, 0.3).next_to(P(X + 10, YP - 8.5), RIGHT, buff=0.05),
               "in_t": mtex(r"$I_N$", RED, 0.3).next_to(P(X + 10, YN + 8.5), RIGHT, buff=0.05),
               "gnd": txt("0", 15).next_to(P(X + 8, 4), DOWN, buff=0.06)}
        return out

    def part_stage(self):
        d = self.d
        self.next_section("stage")
        self.heading("2 · One stage and its law")
        # (a) the inverter
        sc = self._schematic()
        all_sc = VGroup(*sc.values()).shift(3.4 * LEFT + 0.1 * UP)
        self.play(Create(sc["body"]), FadeIn(sc["vdd"]), FadeIn(sc["gnd"]), FadeIn(sc["vin"]), FadeIn(sc["vo"]), FadeIn(sc["C"]),
                  GrowArrow(sc["next"]), FadeIn(sc["next_t"]), run_time=1.4)
        self.play(GrowArrow(sc["ip"]), FadeIn(sc["ip_t"]), GrowArrow(sc["in"]), FadeIn(sc["in_t"]), run_time=0.6)
        eq1 = mtex(r"$C\,\frac{dV_o}{dt} = I_P - I_N$", DARK, 0.7).move_to(3.2 * RIGHT + 1.9 * UP)
        self.play(FadeIn(eq1, shift=0.2 * UP), run_time=0.6)
        self.caption("A predriver stage is a CMOS inverter: its output node charges through the PMOS and discharges through the NMOS, into a lumped capacitance C.")
        du = VGroup(mtex(r"$u = (V_{DD} - V_{in})/V_{DD}$", DARK, 0.42), txt("the input, 0 to 1; u = 1 means 'charge the node'", 19, AXIS)).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        dv = VGroup(mtex(r"$v = V_o/V_{DD}$", DARK, 0.42), txt("the output, 0 to 1; 1 is the rail it charges to", 19, AXIS)).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        defs = VGroup(du, dv).arrange(DOWN, aligned_edge=LEFT, buff=0.4).move_to(3.3 * RIGHT + 0.1 * DOWN)
        self.play(FadeIn(du, shift=0.15 * RIGHT), run_time=0.6)
        self.play(FadeIn(dv, shift=0.15 * RIGHT), run_time=0.6)
        self.caption("u is the input and v the output, both counted from 0 to 1 so that u = 1 means 'charge': every stage, inverting or not, then reads the same way.", wait=3.2)
        self.clear_stage()
        # (b) the bucket
        self.heading("2 · One stage and its law: the bucket")
        self._bucket()
        self.clear_stage()
        # (c) where the law comes from
        self.heading("2 · One stage and its law: where it comes from")
        self._device()
        self.clear_stage()
        # (d) the three knobs
        self.heading("2 · One stage and its law: the three numbers")
        self._knobs()
        self.clear_stage()

    def _bucket(self):
        d = self.d
        VT, XL, S = (float(x) for x in d["b_prm"])
        t_tap, t_on, t_taper, t_drain, t_taper_dn = (float(x) for x in d["b_events"])
        step = 5
        bt, bu, bv = d["b_t"][::step], d["b_u"][::step], d["b_v"][::step]
        b_up, b_dn = d["b_up"], d["b_dn"]
        t_all = d["b_t"]
        law = mtex(LAW, DARK, 0.62).set(width=5.6).move_to(1.2 * RIGHT + 2.85 * UP)
        self.play(FadeIn(law, shift=0.2 * UP), run_time=0.7)
        # the bucket
        BW, BH = 1.7, 2.6
        bx0, by0 = -5.0, -1.9
        bucket = VGroup(Line([bx0 - BW / 2, by0 + BH, 0], [bx0 - BW / 2, by0, 0], color=DARK, stroke_width=3),
                        Line([bx0 - BW / 2, by0, 0], [bx0 + BW / 2, by0, 0], color=DARK, stroke_width=3),
                        Line([bx0 + BW / 2, by0, 0], [bx0 + BW / 2, by0 + BH, 0], color=DARK, stroke_width=3))
        brim = hline_plain = Line([bx0 - BW / 2 - 0.15, by0 + BH, 0], [bx0 - BW / 2, by0 + BH, 0], color=DARK, stroke_width=2)
        l_brim = txt("1", 16).next_to(brim, LEFT, buff=0.06)
        l_floor = txt("0", 16).next_to([bx0 - BW / 2 - 0.15, by0, 0], LEFT, buff=0.06)
        z_up = DashedLine([bx0 - BW / 2, by0 + (1 - XL) * BH, 0], [bx0 + BW / 2, by0 + (1 - XL) * BH, 0], color=RED, stroke_width=1.5, dash_length=0.08)
        z_dn = DashedLine([bx0 - BW / 2, by0 + XL * BH, 0], [bx0 + BW / 2, by0 + XL * BH, 0], color=RED, stroke_width=1.5, dash_length=0.08)
        l_zup = txt("1 − x_lin", 14, RED).next_to(z_up, LEFT, buff=0.06)
        l_zdn = txt("x_lin", 14, RED).next_to(z_dn, LEFT, buff=0.06)
        tap_y = by0 + BH + 0.55
        tap = VGroup(Line([bx0 - 0.9, tap_y, 0], [bx0, tap_y, 0], color=DARK, stroke_width=3),
                     Line([bx0, tap_y, 0], [bx0, tap_y - 0.3, 0], color=DARK, stroke_width=3))
        l_tap = txt("tap: charging", 15, TEAL).next_to(tap, UP, buff=0.05).shift(0.2 * LEFT)
        dx = bx0 + 0.45                                   # the drain: a short channel through the floor
        drain = VGroup(Line([dx - 0.09, by0, 0], [dx - 0.09, by0 - 0.25, 0], color=DARK, stroke_width=3),
                       Line([dx + 0.09, by0, 0], [dx + 0.09, by0 - 0.25, 0], color=DARK, stroke_width=3))
        l_drain = txt("drain: discharging", 15, RED).next_to([dx + 0.12, by0 - 0.42, 0], RIGHT, buff=0.1)
        T = ValueTracker(float(bt[0]))

        def val(arr, t):
            return float(np.interp(t, t_all, arr))

        def fill():
            v = max(val(d["b_v"], T.get_value()), 0.0)
            r = Rectangle(width=BW - 0.04, height=max(v * BH, 0.002)).set_fill(LIGHT_TEAL, opacity=1).set_stroke(width=0)
            return r.move_to([bx0, by0 + v * BH / 2 + 0.002, 0])

        def stream_up():
            rate = val(b_up, T.get_value()) / S
            v = max(val(d["b_v"], T.get_value()), 0.0)
            top, bot = tap_y - 0.3, by0 + v * BH
            r = Rectangle(width=0.03 + 0.2 * rate, height=max(top - bot, 0.01)).set_stroke(width=0)
            r.set_fill(TEAL, opacity=0.75 if rate > 0.01 else 0.0)
            return r.move_to([bx0, (top + bot) / 2, 0])

        def stream_dn():
            rate = val(b_dn, T.get_value()) / S
            r = Rectangle(width=0.03 + 0.14 * rate, height=0.5).set_stroke(width=0)
            r.set_fill(RED, opacity=0.7 if rate > 0.01 else 0.0)
            return r.move_to([dx, by0 - 0.02 - 0.25, 0])

        def level_label():
            v = val(d["b_v"], T.get_value())
            return txt(f"v = {v:.2f}", 17, TEAL).next_to([bx0 + BW / 2, by0 + max(v, 0) * BH, 0], RIGHT, buff=0.1)

        self.play(Create(bucket), FadeIn(brim), FadeIn(l_brim), FadeIn(l_floor), Create(tap), FadeIn(l_tap), Create(drain), FadeIn(l_drain), run_time=0.9)
        # the time axes
        AU = axes((-0.2, 3.4, 1), (0, 1, 1), 5.0, 0.9, xt=[0, 1, 2, 3], yt=[0, 1], ylabel="input u").shift(1.9 * RIGHT + 1.35 * UP)
        AV = axes((-0.2, 3.4, 1), (0, 1, 0.5), 5.0, 2.1, xt=[0, 1, 2, 3], yt=[0, 0.5, 1], xlabel="time (ns)", ylabel="output v").shift(1.9 * RIGHT + 0.95 * DOWN)
        au, av = AU[0], AV[0]
        self.play(FadeIn(AU), FadeIn(AV), run_time=0.6)
        hv = hline(av, 1 - XL, -0.2, 3.4, RED)
        hvd = hline(av, XL, -0.2, 3.4, RED)
        self.play(Create(z_up), Create(z_dn), FadeIn(l_zup), FadeIn(l_zdn), Create(hv), Create(hvd), run_time=0.5)
        # insets: h and r
        HI = axes((0, 1, 0.5), (0, 1, 1), 1.5, 0.95, xt=[0, 1], yt=[0, 1], fs=13).shift(5.35 * RIGHT + 1.35 * UP)
        RI = axes((0, 1, 0.5), (0, 1, 1), 1.5, 0.95, xt=[0, 1], yt=[0, 1], fs=13).shift(5.35 * RIGHT + 0.65 * DOWN)
        h_c = curve(HI[0], d["hr_x"], d["hr_h"], TEAL, 3)
        r_c = curve(RI[0], d["hr_x"], d["hr_r"], RED, 3)
        h_l = txt("h(x): 0 below v_t,\nthen linear to 1", 13, TEAL).next_to(HI[0], UP, buff=0.08)
        r_l = txt("r(x): 1, then down to 0\nwithin x_lin of the rail", 13, RED).next_to(RI[0], UP, buff=0.08)
        h_vt = vline(HI[0], VT, 0, 1, GREY, 1)
        r_xl = vline(RI[0], XL, 0, 1, GREY, 1)
        self.play(FadeIn(HI), FadeIn(RI), Create(h_c), Create(r_c), FadeIn(h_l), FadeIn(r_l), Create(h_vt), Create(r_xl), run_time=0.8)
        self.caption("The stage as a bucket: the node is the bucket and its level is v; a tap above fills it, a drain below empties it.", wait=2.6)
        self.caption(f"Illustrative values: v_t = {VT:g}, x_lin = {XL:g}, s_up = s_dn = {S:g} per ns. The input u rises over 0.4 ns, as a previous stage's output would.", wait=2.8)
        fill_m = always_redraw(fill)
        su_m = always_redraw(stream_up)
        sd_m = always_redraw(stream_dn)
        lev_m = always_redraw(level_label)
        cu_m = always_redraw(lambda: partial_curve(au, bt, bu, T.get_value(), GREY, 3.5))
        cv_m = always_redraw(lambda: partial_curve(av, bt, bv, T.get_value(), TEAL, 4.5))
        du_m = always_redraw(lambda: Dot(au.c2p(T.get_value(), val(d["b_u"], T.get_value())), radius=0.06, color=GREY))
        dv_m = always_redraw(lambda: Dot(av.c2p(T.get_value(), val(d["b_v"], T.get_value())), radius=0.06, color=TEAL))
        self.add(fill_m, su_m, sd_m, lev_m, cu_m, cv_m, du_m, dv_m)

        def run_to(t1, seconds):
            return [T.animate(run_time=seconds, rate_func=linear).set_value(t1)]

        box_h = term_box(law, LAW, LAW_PRE + r"s_{up}\,", r"h(u)")
        box_s = term_box(law, LAW, LAW_PRE, r"s_{up}")
        box_r = term_box(law, LAW, LAW_PRE + r"s_{up}\,h(u)\,", r"r(1-v)")
        box_d = term_box(law, LAW, LAW_PRE + LAW_UP + r" \;-\; ", LAW_DN)
        self.caption_with(f"The input u (grey) starts to rise at t = 0; below v_t = {VT:g} the tap stays closed and nothing happens.", run_to(t_tap, 1.2), wait=1.2)
        self.caption_with(f"At {t_tap:.2f} ns u passes v_t: the tap opens, and its flow grows with u − v_t. This is the gate factor h(u).",
                          run_to(t_on, 2.0) + [FadeIn(box_h, run_time=0.4)], wait=1.4)
        self.caption_with(f"The input is fully on: the level rises at the constant slope s_up = {S:g} per ns, a constant current. The device is in saturation.",
                          run_to(t_taper, 1.2) + [FadeOut(box_h, run_time=0.3), FadeIn(box_s, run_time=0.4)], wait=1.6)
        self.caption_with(f"Within x_lin = {XL:g} of the brim the flow tapers off: the resistive tail, the device now in its linear region.",
                          run_to(1.0, 1.6) + [FadeOut(box_s, run_time=0.3), FadeIn(box_r, run_time=0.4)], wait=1.0)
        self.caption_with("The drain factor r(1 − v) shrinks as the bucket fills, and the level approaches the rail exponentially.",
                          run_to(1.8, 1.8), wait=1.0)
        self.caption_with("The input falls back.", run_to(t_drain, 0.8) + [FadeOut(box_r, run_time=0.3)], wait=0.4)
        self.caption_with(f"Once 1 − u passes v_t, at {t_drain:.2f} ns, the drain opens: the second term. The level falls at s_dn = {S:g} per ns.",
                          run_to(t_taper_dn, 1.6) + [FadeIn(box_d, run_time=0.4)], wait=1.0)
        self.caption_with("And the same taper within x_lin of the floor: the law is symmetric, one term for each device of the inverter.",
                          run_to(float(bt[-1]), 2.4), wait=2.0)
        self.play(FadeOut(box_d), run_time=0.3)
        self.caption("The whole stage law: a charging term and a discharging term, each a rate times a gate factor times a drain factor.", wait=3.0)
        self.remove(fill_m, su_m, sd_m, lev_m, cu_m, cv_m, du_m, dv_m)
        self.add(fill(), partial_curve(au, bt, bu, 9, GREY, 3.5), partial_curve(av, bt, bv, 9, TEAL, 4.5))

    def _device(self):
        d = self.d
        f1 = mtex(r"$I_D = I'_{D0}\,\min\!\left(1,\;V_{DS}/V'_{D0}\right),\qquad I'_{D0} \propto (V_{GS}-V_{TH})^{\alpha}$", DARK, 0.5)
        f1.set(width=7.6).move_to(0.6 * RIGHT + 2.85 * UP)
        self.play(FadeIn(f1, shift=0.2 * UP), run_time=0.7)
        self.caption("Behind the law is the α-power law of a MOSFET: constant current beyond V'_D0, a resistance below it, both growing with the gate drive.")
        A = axes((0, 1.25, 0.5), (0, 1.3, 0.5), 4.2, 3.0, xt=[0, 0.5, 1], yt=[0, 0.5, 1],
                 xlabel="V_DS / V_DD", ylabel="I_D / I_D0").shift(3.2 * LEFT + 0.1 * DOWN)
        ax = A[0]
        self.play(Create(A), run_time=0.6)
        fam = VGroup()
        for i in range(len(d["dev_D"])):
            fam.add(curve(ax, d["dev_x"], d["dev_y"][i], RED, 3))
        self.play(*[Create(c) for c in fam], run_time=1.2)
        dl = txt("D =", 13, AXIS).next_to(ax.c2p(1.02, 1.12), RIGHT, buff=0.05)
        dls = VGroup(*[txt(f"{D:.2f}", 13, AXIS).next_to(ax.c2p(1.02, float(d["dev_y"][i][-1])), RIGHT, buff=0.05) for i, D in enumerate(d["dev_D"])])
        self.play(FadeIn(dl), FadeIn(dls), run_time=0.4)
        pw = VGroup()
        for i in range(len(d["dev_D"])):
            k, lv = float(d["dev_knee"][i]), float(d["dev_level"][i])
            pw.add(VMobject().set_points_as_corners([ax.c2p(0, 0), ax.c2p(k, lv), ax.c2p(1.0, lv)]).set_stroke(DARK, 2.0))
            pw.add(Dot(ax.c2p(k, lv), radius=0.05, color=DARK))
        self.play(Create(pw), run_time=1.0)
        lgA = legend([(RED, "inv_chain NMOS, HSPICE"), (DARK, "α-power law, piecewise")], 14).next_to(ax.c2p(0.02, 1.3), DOWN, buff=0.05).align_to(ax.c2p(0.04, 1), LEFT)
        self.play(FadeIn(lgA), run_time=0.4)
        self.caption(f"The inv_chain NMOS from HSPICE at five gate drives D: constant current, then resistive, the knee at V'_D0 = {float(d['dev_x0']):.2f} V_DD. This is the drain factor r.", wait=3.2)
        B = logaxes((0.09, 1.1), (0.045, 1.2), 3.8, 3.0, xt=[0.1, 0.3, 1], yt=[0.1, 0.3, 1],
                    xlabel="gate drive D = (V_GS − V_TH)/(V_DD − V_TH)", ylabel="I'_D0 / I_D0").shift(3.4 * RIGHT + 0.1 * DOWN)
        bx = B[0]
        self.play(Create(B), run_time=0.6)
        pts = VGroup(*[Dot(bx.c2p(np.log10(x), np.log10(y)), radius=0.06, color=RED) for x, y in zip(d["dev_ll_x"], d["dev_ll_y"])])
        self.play(FadeIn(pts), run_time=0.6)
        al = float(d["dev_alpha"])
        xs = np.linspace(0.1, 1.0, 50)
        fitl = VMobject().set_points_as_corners([bx.c2p(np.log10(x), np.log10(x ** al)) for x in xs]).set_stroke(DARK, 2.5)
        p1l = VMobject().set_points_as_corners([bx.c2p(np.log10(x), np.log10(x)) for x in xs]).set_stroke(TEAL, 4)
        self.play(Create(fitl), run_time=0.8)
        lo, hi = float(d["dev_alphas"].min()), float(d["dev_alphas"].max())
        la = txt(f"slope α = {al:.2f}\n({lo:.2f} to {hi:.2f} on the four\npredriver devices)", 14, DARK).next_to(bx.c2p(np.log10(0.1), np.log10(0.5)), RIGHT, buff=0.1)
        self.play(FadeIn(la), run_time=0.4)
        self.caption(f"The saturation current against the gate drive above threshold, on log axes: a straight line of slope α = {al:.2f}. This is the gate factor h.", wait=3.0)
        self.play(Create(p1l), run_time=0.7)
        lp = txt("p = 1 (used)", 14, TEAL).next_to(bx.c2p(np.log10(0.4), np.log10(0.4)), DR, buff=0.08)
        self.play(FadeIn(lp), run_time=0.3)
        self.caption("The model uses p = 1, the short-channel limit: a complete transition cannot set the exponent, because the stage inputs dwell at the rail.", wait=3.4)
        self.clear_stage(keep=())
        # the step response of one stage
        VT, XL, S = (float(x) for x in d["b_prm"])
        C = axes((-0.1, 2.0, 0.5), (0, 1.2, 0.5), 6.0, 3.3, xt=[0, 0.5, 1, 1.5, 2], yt=[0, 0.5, 1],
                 xlabel="time (ns)", ylabel="normalised node").shift(1.0 * LEFT + 0.1 * DOWN)
        cx = C[0]
        self.play(Create(C), run_time=0.6)
        su = curve(cx, d["sr_t"], d["sr_u"], GREY, 2.5)
        sv = curve(cx, d["sr_t"], d["sr_v"], TEAL, 4.5)
        self.play(Create(su), run_time=0.4)
        self.play(Create(sv), run_time=1.2)
        kx, ky = (float(x) for x in d["sr_knee"])
        ramp = DashedLine(cx.c2p(0, 0), cx.c2p(1 / S, 1), color=DARK, stroke_width=2, dash_length=0.08)
        kd = Dot(cx.c2p(kx, ky), radius=0.07, color=DARK)
        self.play(Create(ramp), FadeIn(kd), run_time=0.6)
        l1 = txt(f"ramp, slope s_up = {S:g}/ns", 17, DARK).next_to(cx.c2p(0.45, 0.35), RIGHT, buff=0.05)
        l2 = txt(f"exponential, τ = x_lin / s_up = {float(d['sr_tau']):.3f} ns", 17, TEAL).next_to(cx.c2p(0.75, 0.86), RIGHT, buff=0.05)
        lgC = legend([(GREY, "input u, a step"), (TEAL, "output v")], 16).next_to(cx.c2p(2.0, 0.0), RIGHT, buff=0.4).align_to(cx.c2p(2, 0.5), DOWN)
        self.play(FadeIn(l1), FadeIn(l2), FadeIn(lgC), run_time=0.5)
        self.caption(f"One stage under a step: a ramp at s_up until the node is within x_lin of the rail, then an exponential with time constant x_lin / s_up = {float(d['sr_tau']):.3f} ns.", wait=3.4)

    def _knobs(self):
        d = self.d
        panels = []
        for i, (title, xlabel) in enumerate((("s_up: the charging rate", "time (ns)"), ("v_t: the threshold", "time (ns)"), ("s_dn: the discharging rate", "time (ns)"))):
            A = axes((-0.1, 2.0, 1), (0, 1.1, 0.5), 3.6, 2.4, xt=[0, 1, 2], yt=[0, 0.5, 1], xlabel=xlabel, fs=15).shift((i - 1) * 4.5 * RIGHT + 0.1 * DOWN)
            tl = txt(title, 18, DARK).next_to(A[0], UP, buff=0.4)
            panels.append((A, tl))
        a1, a2, a3 = (p[0][0] for p in panels)
        self.play(*[Create(p[0]) for p in panels], *[FadeIn(p[1]) for p in panels], run_time=0.8)
        u1 = curve(a1, d["kn_t"], d["kn_step"], GREY, 2.5)
        self.play(Create(u1), run_time=0.4)
        lg1 = VGroup()
        for s, c in zip((1, 2, 4), TEALS):
            cv = curve(a1, d["kn_t"], d[f"kn_sup{s}"], c, 3.5)
            lab = txt(f"s_up = {s}/ns", 14, c)
            lg1.add(lab)
            self.play(Create(cv), run_time=0.5)
        lg1.arrange(DOWN, aligned_edge=LEFT, buff=0.06).next_to(a1.c2p(1.0, 0.1), RIGHT, buff=0.1).align_to(a1.c2p(1, 0.42), UP)
        self.play(FadeIn(lg1), run_time=0.3)
        self.caption("s_up: a larger charging rate fills the node faster, 1, 2 and 4 per ns. v_t = 0.3 here, and the input is a step.", wait=2.8)
        u2 = curve(a2, d["kn_t"], d["kn_ramp"], GREY, 2.5)
        self.play(Create(u2), run_time=0.4)
        lg2 = VGroup()
        for vt, c in zip((0.1, 0.3, 0.5), (ORANGE, TEAL, RED)):
            cv = curve(a2, d["kn_t"], d[f"kn_vt{vt:g}"], c, 3.5)
            lab = txt(f"v_t = {vt:g}", 14, c)
            lg2.add(lab)
            self.play(Create(cv), run_time=0.5)
        lg2.arrange(DOWN, aligned_edge=LEFT, buff=0.06).next_to(a2.c2p(1.0, 0.1), RIGHT, buff=0.1).align_to(a2.c2p(1, 0.42), UP)
        self.play(FadeIn(lg2), run_time=0.3)
        self.caption("v_t, with an input that rises over 0.5 ns, as a previous stage's output would: the stage starts when its input passes v_t.", wait=2.6)
        self.caption("The threshold sets when a stage starts, not how fast it moves.", wait=2.4)
        u3 = curve(a3, d["kn_t"], d["kn_fall"], GREY, 2.5)
        self.play(Create(u3), run_time=0.4)
        lg3 = VGroup()
        for s, c in zip((1, 2, 4), TEALS):
            cv = curve(a3, d["kn_t"], d[f"kn_sdn{s}"], c, 3.5)
            lab = txt(f"s_dn = {s}/ns", 14, c)
            lg3.add(lab)
            self.play(Create(cv), run_time=0.5)
        lg3.arrange(DOWN, aligned_edge=LEFT, buff=0.06).next_to(a3.c2p(1.0, 1.0), RIGHT, buff=0.1).align_to(a3.c2p(1, 1.05), UP)
        self.play(FadeIn(lg3), run_time=0.3)
        self.caption("s_dn does the same for the falling edge: the input steps back to 0 and the drain empties the node at 1, 2 or 4 per ns.", wait=3.0)

    # ---- 3. the chain
    def part_chain(self):
        d = self.d
        self.next_section("chain")
        self.heading("3 · The chain: delay is spent in handovers")
        s_up, s_dn, vt, xl, K = (float(x) for x in d["ch_prm"])
        vin = txt("V_in", 17)
        cmp_ = block("comparator\nV_DD / 2", 1.5, 0.75, 15)
        stg = [block(f"stage {k}", 1.15, 0.75, 16) for k in (1, 2, 3)]
        gate = txt("gate G_UP", 17, TEAL)
        items = [vin, cmp_, *stg, gate]
        row = VGroup(*items).arrange(RIGHT, buff=0.5).move_to(2.75 * UP)
        arrows = VGroup(*[arrow_between(a, b) for a, b in zip(items[:-1], items[1:])])
        labs = VGroup(txt("u1", 14).next_to(arrows[1], UP, buff=0.04), txt("v1", 14).next_to(arrows[2], UP, buff=0.04),
                      txt("v2", 14).next_to(arrows[3], UP, buff=0.04), txt("v3", 14).next_to(arrows[4], UP, buff=0.04))
        self.play(FadeIn(vin), run_time=0.2)
        for a, b in zip(arrows, items[1:]):
            self.play(GrowArrow(a), FadeIn(b), run_time=0.3)
        self.play(FadeIn(labs), run_time=0.3)
        prm = txt(f"ex2, selected model: K = {K:g} identical stages, s_up = {s_up:.2f}/ns, s_dn = {s_dn:.2f}/ns, v_t = {vt:.3f}, x_lin = {xl:g}, p = 1", 17, AXIS).move_to(2.1 * UP)
        self.play(FadeIn(prm), run_time=0.4)
        self.caption("The input pin is turned into a 0-or-1 command by a comparator at V_DD/2; three identical stages pass it along; the last node is the gate of the output pull-up device.")
        A = axes((-0.3, 4.2, 1), (0, 1.1, 0.5), 5.6, 2.9, xt=[0, 1, 2, 3, 4], yt=[0, 0.5, 1],
                 xlabel="time from the input edge (ns)", ylabel="stage nodes").shift(3.4 * LEFT + 0.55 * DOWN)
        ax = A[0]
        tA = txt("complete transition", 17, DARK).next_to(ax, UP, buff=0.1)
        self.play(Create(A), FadeIn(tA), run_time=0.6)
        t, uf, vf = d["ch_t"], d["ch_u_full"], d["ch_v_full"]
        cu = curve(ax, t, uf, GREY, 2.5)
        hv = hline(ax, vt, -0.3, 4.2, DARK, 1.2)
        lv = txt("v_t", 14).next_to(ax.c2p(4.2, vt), RIGHT, buff=0.05)
        self.play(Create(cu), Create(hv), FadeIn(lv), run_time=0.5)
        c1 = curve(ax, t, vf[0], TEALS[0], 3.5)
        self.play(Create(c1), run_time=0.8)
        self.caption("A complete transition: u1 steps to 1 at t = 0 and stage 1 starts filling at once.", wait=2.2)
        h1, h2 = (float(x) for x in d["ch_handover"])
        m1 = vline(ax, h1, 0, vt, DARK, 1.2)
        d1 = Dot(ax.c2p(h1, vt), radius=0.06, color=DARK)
        l1 = txt(f"{h1:.2f} ns", 14, DARK).next_to(d1, UL, buff=0.04)
        l1.add_background_rectangle(color=WHITE, opacity=0.85, buff=0.03)
        c2 = curve(ax, t, vf[1], TEALS[1], 3.5)
        self.play(Create(m1), FadeIn(d1), FadeIn(l1), run_time=0.4)
        self.play(Create(c2), run_time=0.8)
        m2 = vline(ax, h2, 0, vt, DARK, 1.2)
        d2 = Dot(ax.c2p(h2, vt), radius=0.06, color=DARK)
        l2 = txt(f"{h2:.2f} ns", 14, DARK).next_to(d2, DR, buff=0.04)
        l2.add_background_rectangle(color=WHITE, opacity=0.85, buff=0.03)
        c3 = curve(ax, t, vf[2], TEALS[2], 4.5)
        self.play(Create(m2), FadeIn(d2), FadeIn(l2), run_time=0.4)
        self.play(Create(c3), run_time=0.8)
        self.caption(f"Stage 2 waits until v1 passes v_t = {vt:.3f}, at {h1:.2f} ns; stage 3 waits for v2, at {h2:.2f} ns. These are the handovers.", wait=2.8)
        tr = float(d["ch_t_rail"])
        lr = txt(f"gate at 0.99: {tr:.2f} ns", 14, TEALS[2]).next_to(ax.c2p(tr, 1.0), DR, buff=0.08)
        dr = Dot(ax.c2p(tr, 0.99), radius=0.06, color=TEALS[2])
        lgA = legend([(GREY, "u1"), (TEALS[0], "v1"), (TEALS[1], "v2"), (TEALS[2], "v3 = gate")], 14, 0.05).next_to(ax.c2p(2.6, 0.1), RIGHT, buff=0.1).align_to(ax.c2p(2.6, 0.62), UP)
        self.play(FadeIn(dr), FadeIn(lr), FadeIn(lgA), run_time=0.4)
        self.caption(f"The gate reaches its rail at about {tr:.1f} ns. The chain's delay is the sum of the handovers; the shape of the final edge belongs to the last stage alone.", wait=3.2)
        # the 810 ps pulse
        B = axes((-0.3, 4.2, 1), (0, 1.1, 0.5), 5.6, 2.9, xt=[0, 1, 2, 3, 4], yt=[0, 0.5, 1],
                 xlabel="time from the input edge (ns)").shift(3.6 * RIGHT + 0.55 * DOWN)
        bx = B[0]
        tB = txt("810 ps input pulse", 17, DARK).next_to(bx, UP, buff=0.1)
        self.play(Create(B), FadeIn(tB), run_time=0.6)
        up, vp = d["ch_u_810"], d["ch_v_810"]
        hvb = hline(bx, vt, -0.3, 4.2, DARK, 1.2)
        self.play(Create(curve(bx, t, up, GREY, 2.5)), Create(hvb), run_time=0.5)
        pk, tpk = d["ch_peak_810"], d["ch_tpeak_810"]
        for k, (c, w) in enumerate(zip(TEALS, (3.5, 3.5, 4.5))):
            self.play(Create(curve(bx, t, vp[k], c, w)), run_time=0.7)
            self.add(txt(f"{float(pk[k]):.2f}", 14, c).next_to(bx.c2p(float(tpk[k]), float(pk[k])), UP if k < 2 else UR, buff=0.06))
        self.caption(f"An 810 ps pulse: u1 returns at 0.81 ns. v1 turns back at once; v2 peaks at {float(pk[1]):.2f}; the gate peaks at {float(pk[2]):.2f} and turns back.", wait=3.0)
        self.caption("Every stage loses amplitude, because a stage delivers nothing until its input passes v_t. A pulse whose peak falls below v_t is extinguished in the chain.", wait=3.2)
        cr = curve(bx, d["ch_real_t"], d["ch_real_g"], RED, 3.5)
        self.play(Create(cr), run_time=0.9)
        lgB = legend([(TEALS[2], "model gate"), (RED, f"probed gate of ex2, peak {float(d['ch_real_peak']):.2f}")], 14, 0.05).next_to(bx.c2p(2.0, 0.1), RIGHT, buff=0.1).align_to(bx.c2p(2, 0.62), UP)
        self.play(FadeIn(lgB), run_time=0.3)
        lead, ret = float(d["ch_lead_ps"]), float(d["ch_return_ps"])
        self.caption(f"The real gate, probed at 810 ps, peaks at {float(d['ch_real_peak']):.2f}. The model's gate is an effective one: it leads the real gate by {lead:.0f} ps and returns {ret:.0f} ps earlier.", wait=3.4)
        self.clear_stage()

    # ---- 4. the map
    def part_map(self):
        d = self.d
        self.next_section("map")
        self.heading("4 · The map: from the gate to the conducting fraction")
        self.caption("The output pull-up device conducts a fraction K_u of its I–V table. How much depends on its gate.", wait=2.4)
        t_end = float(d["mp_t"][-1])
        A = axes((0.2, t_end, 0.5), (-0.1, 1.3, 0.5), 5.2, 3.0, xt=[0.5, 1, 1.5, 2], yt=[0, 0.5, 1],
                 xlabel="time from the input edge (ns)", ylabel="normalised").shift(3.5 * LEFT + 0.1 * DOWN)
        ax = A[0]
        self.play(Create(A), run_time=0.6)
        cg = curve(ax, d["mp_t"], d["mp_g"], TEAL, 4)
        ck = curve(ax, d["mp_t"], d["mp_ku"], DARK, 4)
        self.play(Create(cg), Create(ck), run_time=1.2)
        lgA = legend([(TEAL, "probed gate g(t)"), (DARK, "K_u(t) of the file")], 15, 0.05).next_to(ax.c2p(0.25, 1.3), DOWN, buff=0.02).align_to(ax.c2p(0.28, 1), LEFT)
        self.play(FadeIn(lgA), run_time=0.3)
        marks = d["mp_marks"]
        pairs = []
        for m, c in zip(marks, MARKS):
            gi, ki = float(np.interp(m, d["mp_t"], d["mp_g"])), float(np.interp(m, d["mp_t"], d["mp_ku"]))
            ln = DashedLine(ax.c2p(m, gi), ax.c2p(m, ki), color=c, stroke_width=1.5, dash_length=0.06)
            sq = Rectangle(width=0.14, height=0.14).set_fill(c, 1).set_stroke(WHITE, 1).move_to(ax.c2p(m, gi))
            do = Dot(ax.c2p(m, ki), radius=0.08, color=c).set_stroke(WHITE, 1)
            pairs.append((m, gi, ki, c, ln, sq, do))
            self.play(Create(ln), FadeIn(sq), FadeIn(do), run_time=0.3)
        self.caption("ex2's complete transition with the gate probed: the gate g(t) in teal, the file's K_u(t) in black, read together at five instants.", wait=2.8)
        B = axes((0, 1, 0.5), (-0.1, 1.3, 0.5), 3.4, 3.0, xt=[0, 0.5, 1], yt=[0, 0.5, 1], xlabel="gate g", ylabel="K_u").shift(3.6 * RIGHT + 0.1 * DOWN)
        bx = B[0]
        self.play(Create(B), run_time=0.6)
        for m, gi, ki, c, ln, sq, do in pairs:
            target = Dot(bx.c2p(gi, ki), radius=0.09, color=c).set_stroke(WHITE, 1)
            self.play(ReplacementTransform(VGroup(sq, do), target), FadeOut(ln), run_time=0.45)
        cm = curve(bx, d["mp_curve_g"], d["mp_curve_ku"], DARK, 4)
        self.play(Create(cm), run_time=1.0)
        self.caption("Moved to a plane of K_u against g, the pairs trace one curve: the map, K_u as a function of the gate and not of time.", wait=2.8)
        hy = d["mp_hyst"]
        self.caption(f"On three probed buffers the curve traced while the gate rises coincides with the one traced while it falls, within {hy.min():.2f} to {hy.max():.2f}: K_u depends on the gate alone.", wait=3.2)
        # (b) the formula and the candidate shapes
        self.play(FadeOut(A), FadeOut(cg), FadeOut(ck), FadeOut(lgA), run_time=0.5)
        fm = mtex(r"$M(g) = \mathrm{clip}\!\left(\frac{g - v_{t,map}}{1 - v_{t,map}},\,0,\,1\right)^{a}$", DARK, 0.75).move_to(3.5 * LEFT + 1.6 * UP)
        self.play(FadeIn(fm, shift=0.2 * UP), run_time=0.7)
        vm, am = (float(x) for x in d["mp_fit_prm"])
        cf = curve(bx, d["mp_gg"], d["mp_fit"], RED, 3.5)
        self.play(Create(cf), run_time=0.8)
        lf = legend([(DARK, "measured map"), (RED, f"formula fitted: ({vm:.2f}, {am:.2f})")], 15, 0.05).next_to(bx.c2p(0.02, 1.3), DOWN, buff=0.02).align_to(bx.c2p(0.04, 1), LEFT)
        self.play(FadeIn(lf), run_time=0.3)
        e1 = VGroup(txt("v_t,map: the gate level at which the device starts to conduct", 18, DARK),
                    txt("a: bends the curve between that level and the rail", 18, DARK)).arrange(DOWN, aligned_edge=LEFT, buff=0.2).next_to(fm, DOWN, buff=0.5).align_to(fm, LEFT)
        self.play(FadeIn(e1, shift=0.15 * RIGHT), run_time=0.6)
        self.caption(f"A two-parameter formula describes it: v_t,map is the gate level at which the device starts to conduct, a bends the curve. Fitted to ex2's measured map: ({vm:.2f}, {am:.2f}).", wait=3.2)
        self.caption("The file gives K_u against time; the map is K_u against the gate. Converting one into the other needs the gate against time, which the file does not have.", wait=3.2)
        self.play(FadeOut(cf), FadeOut(lf), cm.animate.set_stroke("#BBBBBB", 3), run_time=0.4)
        cols = (TEAL, BLUE, ORANGE)
        items = [("#BBBBBB", "measured (ex2)")]
        for i, ((v, a), c) in enumerate(zip(d["mp_shapes"], cols)):
            self.play(Create(curve(bx, d["mp_gg"], d["mp_cand"][i], c, 3.5)), run_time=0.5)
            items.append((c, f"({float(v):.2f}, {float(a):.2f})"))
        lc = legend(items, 15, 0.05).next_to(bx.c2p(0.02, 1.3), DOWN, buff=0.02).align_to(bx.c2p(0.04, 1), LEFT)
        self.play(FadeIn(lc), run_time=0.3)
        self.caption("So the map cannot be read from the file. The method offers three built-in shapes, (0.50, 0.70), (0.40, 0.60) and (0.40, 0.90), and lets the measurement choose among them.", wait=3.4)
        self.clear_stage()
        # (c) the two relations in series
        self.heading("4 · The map: the two relations in series")
        self._gate_to_ku()
        self.clear_stage()

    def _gate_to_ku(self):
        d = self.d
        vm, am = (float(x) for x in d["mp_shapes"][0])
        A = axes((0, 3, 1), (0, 1.1, 0.5), 3.5, 2.4, xt=[0, 1, 2, 3], yt=[0, 0.5, 1], xlabel="time (ns)", ylabel="gate g", fs=15).shift(4.1 * LEFT + 0.0 * UP)
        B = axes((0, 1, 0.5), (0, 1.1, 0.5), 3.5, 2.4, xt=[0, 0.5, 1], yt=[0, 0.5, 1], xlabel="gate g", ylabel="M(g)", fs=15).shift(0.35 * RIGHT + 0.0 * UP)
        C = axes((0, 4, 1), (0, 1.1, 0.5), 3.5, 2.4, xt=[0, 1, 2, 3, 4], yt=[0, 0.5, 1], xlabel="time (ns)", ylabel="K_u", fs=15).shift(4.8 * RIGHT + 0.0 * UP)
        ax, bx, cx = A[0], B[0], C[0]
        tA = txt("1  the chain: the gate", 17, DARK).next_to(ax, UP, buff=0.35)
        tB = txt("2  the map, read at each gate value", 17, DARK).next_to(bx, UP, buff=0.35)
        tC = txt("3  the result: K_u against time", 17, DARK).next_to(cx, UP, buff=0.35)
        self.play(Create(A), Create(B), Create(C), FadeIn(tA), FadeIn(tB), FadeIn(tC), run_time=0.8)
        mp = curve(bx, d["mp_gg"], d["mp_cand"][0], RED, 3.5)
        hvm = vline(bx, vm, 0, 1.1, GREY, 1.2)
        lvm = txt("v_t,map", 13, AXIS).next_to(bx.c2p(vm, 1.08), UP, buff=0.03)
        self.play(Create(mp), Create(hvm), FadeIn(lvm), run_time=0.6)
        self.caption("The two relations in series: the chain gives the gate against time; the map turns each value of the gate into K_u; the result is K_u against time.", wait=2.4)
        t = d["gk_t"]
        tgt = curve(cx, t, d["gk_target"], "#9A9A9A", 7)
        self.play(Create(tgt), run_time=0.7)
        lt = txt("K_u(t) of the file", 14, "#777777").next_to(cx.c2p(2.3, 1.0), DOWN, buff=0.1)
        self.add(lt)

        def row(g, ku, marks, label, col=TEALS[2]):
            cg = curve(ax, t, g, col, 4)
            self.play(Create(cg), run_time=0.8)
            dots = VGroup()
            for m, c in zip(marks, MARKS):
                gi = float(np.interp(m, t, g))
                ki = float(np.interp(m, t, ku))
                da = Dot(ax.c2p(m, gi), radius=0.075, color=c).set_stroke(WHITE, 1)
                db = Dot(bx.c2p(gi, ki), radius=0.075, color=c).set_stroke(WHITE, 1)
                dc = Dot(cx.c2p(m, ki), radius=0.075, color=c).set_stroke(WHITE, 1)
                dots.add(da, db, dc)
                self.play(FadeIn(da), run_time=0.12)
                self.play(ReplacementTransform(da.copy(), db), run_time=0.3)
                self.play(ReplacementTransform(db.copy(), dc), run_time=0.3)
            ck = curve(cx, t, ku, RED, 4)
            self.play(Create(ck), run_time=0.8)
            return cg, dots, ck

        cg, dots, ck = row(d["gk_g_cal"], d["gk_ku_cal"], d["gk_marks_full"], "full")
        lA = txt("complete transition", 14, DARK).next_to(ax.c2p(1.7, 0.3), RIGHT, buff=0.05)
        self.add(lA)
        rms_c, rms_f = float(d["gk_rms_cal"]), float(d["gk_rms_fit"])
        lr = txt(f"model, rms {rms_c:.3f}", 14, RED).next_to(cx.c2p(2.3, 0.82), DOWN, buff=0.08)
        self.play(FadeIn(lr), run_time=0.3)
        self.caption(f"A complete transition: the gate sweeps its whole range, the whole map is read, and the model's K_u(t) lands on the file's own, rms {rms_c:.3f}.", wait=3.0)
        self.caption(f"Part 6 shows how the numbers were fitted to this curve: rms {rms_f:.3f} at the fit, {rms_c:.3f} here, after the calibration moved v_t.", wait=3.0)
        self.play(FadeOut(cg), FadeOut(dots), FadeOut(ck), FadeOut(lA), FadeOut(lr), tgt.animate.set_stroke("#DDDDDD", 5), lt.animate.set_color("#BBBBBB"), run_time=0.5)
        gpk, kpk = float(d["gk_gate_peak_cut"]), float(d["gk_ku_peak_cut"])
        cut_mask = d["mp_gg"] <= gpk
        self.play(mp.animate.set_stroke("#BBBBBB", 2.5), run_time=0.3)
        mp2 = curve(bx, d["mp_gg"][cut_mask], d["mp_cand"][0][cut_mask], RED, 4.5)
        hgp = vline(bx, gpk, 0, 1.1, GREY, 1.2)
        lgp = txt(f"gate turns back at {gpk:.2f};\nabove it the map is not read", 11, AXIS).next_to(bx.c2p(0.08, 1.0), DR, buff=0.02)
        self.play(Create(mp2), Create(hgp), FadeIn(lgp), run_time=0.5)
        cg, dots, ck = row(d["gk_g_cut"], d["gk_ku_cut"], d["gk_marks_cut"], "cut")
        lB = txt("810 ps pulse", 14, DARK).next_to(ax.c2p(1.7, 0.3), RIGHT, buff=0.05)
        lk = txt(f"K_u peaks at {kpk:.2f}", 14, RED).next_to(cx.c2p(1.6, kpk), UR, buff=0.06)
        self.play(FadeIn(lB), FadeIn(lk), run_time=0.3)
        self.caption(f"The 810 ps pulse: the gate turns back at {gpk:.2f}, only the lower part of the map is read, and K_u rises to {kpk:.2f} and returns.", wait=2.8)
        self.caption("A waveform no table of the file contains, produced by the same two relations with no additional parameter.", wait=3.0)

    # ---- 5. from Ku to the pad
    def part_pad(self):
        d = self.d
        self.next_section("pad")
        self.heading("5 · From K_u to the pad")
        eq = mtex(r"$I_{die} = K_u\,I_{PU}(V_{die}) + K_d\,I_{PD}(V_{die})$", DARK, 0.6).move_to(2.8 * UP)
        self.play(FadeIn(eq, shift=0.2 * UP), run_time=0.7)
        self.caption("The current into the die node is the file's pull-up table scaled by K_u plus its pull-down table scaled by K_d.", wait=2.8)
        self.caption("C_comp loads the die node and the package connects it to the pad: tables, C_comp and package are the file's, unchanged.", wait=2.8)
        A = axes((-0.5, 4.3, 1), (-30, 60, 30), 5.0, 3.0, xt=[0, 1, 2, 3, 4], yt=[-30, 0, 30, 60],
                 xlabel="die voltage (V)", ylabel="current (mA)").shift(3.6 * LEFT + 0.2 * DOWN)
        ax = A[0]
        self.play(Create(A), run_time=0.6)
        pu = curve(ax, d["iv_v"], d["iv_pu"], TEAL, 4)
        pd = curve(ax, d["iv_v"], d["iv_pd"], BLUE, 4)
        self.play(Create(pu), Create(pd), run_time=1.0)
        lg = legend([(TEAL, "pull-up table I_PU"), (BLUE, "pull-down table I_PD")], 15, 0.05).next_to(ax.c2p(4.3, 60), UP, buff=0.15).align_to(ax.c2p(4.3, 60), RIGHT)
        self.play(FadeIn(lg), run_time=0.3)
        kpk = float(d["gk_ku_peak_cut"])
        kl = txt("K_u = 1.00", 20, ORANGE).next_to(ax, UP, buff=0.3).align_to(ax.c2p(-0.3, 0), LEFT)
        self.play(FadeIn(kl), run_time=0.3)
        self.caption(f"ex2's tables from the file, C_comp {float(d['cc_estimated']):.2f} pF. With the gate fully on, K_u = 1, the pull-up delivers its whole table.", wait=2.0)
        pu2 = curve(ax, d["iv_v"], kpk * d["iv_pu"], TEAL, 4)
        kl2 = txt(f"K_u = {kpk:.2f}", 20, ORANGE).move_to(kl)
        self.play(Transform(pu, pu2), Transform(kl, kl2), run_time=1.4)
        self.caption(f"With the gate partly on, K_u = {kpk:.2f} at the peak of the 810 ps pulse, the pull-up delivers {kpk:.2f} of its table at every die voltage.", wait=2.8)
        B = axes((-0.5, 3.0, 1), (-0.3, 1.5, 0.5), 5.2, 3.0, xt=[0, 1, 2, 3], yt=[0, 0.5, 1, 1.5],
                 xlabel="time from the input edge (ns)", ylabel="pad voltage (V)").shift(3.6 * RIGHT + 0.2 * DOWN)
        bx = B[0]
        self.play(Create(B), run_time=0.6)
        si = curve(bx, d["pd_t"], d["pd_si"], DARK, 4.5)
        nat = curve(bx, d["pd_t"], d["pd_nat"], BLUE, 3.5).set_stroke(opacity=0.9)
        mo = curve(bx, d["pd_t"], d["pd_mo"], TEAL, 4)
        self.play(Create(si), run_time=0.9)
        self.play(Create(nat), run_time=0.9)
        self.play(Create(mo), run_time=0.9)
        lgB = legend([(DARK, "transistor netlist"), (BLUE, f"native IBIS: {float(d['pd_err_nat']):+.0f} %"),
                      (TEAL, f"the model: {float(d['pd_err_mo']):+.0f} %")], 15, 0.05).next_to(bx.c2p(0.0, 1.5), DOWN, buff=0.02).align_to(bx.c2p(0.05, 1.4), LEFT)
        self.play(FadeIn(lgB), run_time=0.4)
        self.caption(f"The pad at 810 ps: transistor netlist, native element ({float(d['pd_err_nat']):+.0f} % on the peak) and the model ({float(d['pd_err_mo']):+.0f} %), whose K_u came from the chain and the map.", wait=3.4)
        self.clear_stage()

    # ---- 6. what the file fixes, what it cannot, what one measurement settles
    def part_fix(self):
        d = self.d
        self.next_section("fix")
        self.heading("6 · What the file fixes")
        A = axes((0, 3.0, 1), (0, 1.1, 0.5), 5.8, 3.2, xt=[0, 1, 2, 3], yt=[0, 0.5, 1],
                 xlabel="time from the input edge (ns)", ylabel="K_u").shift(3.1 * LEFT + 0.1 * UP)
        ax = A[0]
        t = d["gk_t"]
        tgt = curve(ax, t, d["gk_target"], "#9A9A9A", 7)
        self.play(Create(A), run_time=0.6)
        self.play(Create(tgt), run_time=0.8)
        lt = txt("the file's own K_u(t): the target", 17, "#777777").next_to(ax.c2p(1.6, 1.0), DOWN, buff=0.12)
        self.add(lt)
        self.caption("The fit: s_up, s_dn and v_t are the only numbers fitted, and the file's own K_u(t) of the complete transition is the only thing they are fitted to.", wait=3.0)
        labels = VGroup(*[txt(n, 21, DARK) for n in ("s_up", "s_dn", "v_t", "rms")]).arrange(DOWN, aligned_edge=LEFT, buff=0.32).shift(2.4 * RIGHT + 0.4 * UP)
        self.play(FadeIn(labels), run_time=0.4)

        def show(prm, rms, color):
            vals = VGroup(txt(f"{prm[0]:.2f} /ns", 21, color), txt(f"{prm[1]:.2f} /ns", 21, color), txt(f"{prm[2]:.3f}", 21, color),
                          txt(f"{rms:.3f}", 21, RED if rms > 0.05 else TEAL))
            for lab, v in zip(labels, vals):
                v.next_to(lab, RIGHT, buff=0.45)
            return vals

        steps, prms, rmss = d["ft_steps"], d["ft_steps_prm"], d["ft_steps_rms"]
        cur = curve(ax, t, steps[0], ORANGE, 4)
        vals = show(prms[0], float(rmss[0]), ORANGE)
        self.play(Create(cur), FadeIn(vals), run_time=0.8)
        self.caption(f"A first guess, s_up = s_dn = 8 per ns and v_t = 0.4: far too early. The residual is the rms gap to the target, {float(rmss[0]):.3f}.", wait=2.2)
        caps = (f"s_up adjusted to {prms[1][0]:.2f}: the rising edge takes the file's slope, rms {float(rmss[1]):.3f}.",
                f"s_dn adjusted to {prms[2][1]:.2f}: the falling edge, at 10 ns, out of this window, rms {float(rmss[2]):.3f}.",
                f"v_t adjusted to {prms[3][2]:.3f}: the edge moves to the file's delay. The fit: rms {float(rmss[3]):.3f}, with v_t on its bound {float(d['ft_vt_bound']):g}.")
        for j in (1, 2, 3):
            col = TEAL if j == 3 else ORANGE
            new = curve(ax, t, steps[j], col, 4)
            nv = show(prms[j], float(rmss[j]), col)
            self.play(Transform(cur, new), Transform(vals, nv), run_time=1.0)
            self.caption(caps[j - 1], wait=2.2 if j < 3 else 3.0)
        self.clear_stage()
        # the ambiguity
        self.heading("6 · What the file cannot fix")
        A = axes((0, 1, 0.5), (0, 1.1, 0.5), 3.3, 2.4, xt=[0, 0.5, 1], yt=[0, 0.5, 1], xlabel="gate g", ylabel="map M(g)", fs=15).shift(4.4 * LEFT + 0.75 * UP)
        B = axes((0, 3, 1), (0, 1.1, 0.5), 3.3, 2.4, xt=[0, 1, 2, 3], yt=[0, 0.5, 1], xlabel="time (ns)", ylabel="K_u", fs=15).shift(0.0 * RIGHT + 0.75 * UP)
        C = axes((0, 3, 1), (0, 1.1, 0.5), 3.3, 2.4, xt=[0, 1, 2, 3], yt=[0, 0.5, 1], xlabel="time (ns)", ylabel="K_u", fs=15).shift(4.4 * RIGHT + 0.75 * UP)
        titles = VGroup(txt("two assumed maps", 17).next_to(A[0], UP, buff=0.3), txt("complete transition", 17).next_to(B[0], UP, buff=0.3),
                        txt("810 ps pulse", 17).next_to(C[0], UP, buff=0.3))
        self.play(Create(A), Create(B), Create(C), FadeIn(titles), run_time=0.8)
        tgt = curve(B[0], t, d["gk_target"], "#9A9A9A", 7)
        self.play(Create(tgt), run_time=0.6)
        rows = VGroup()
        for tag, col in (("late", BLUE), ("early", RED)):
            vm, am = (float(x) for x in d[f"am_{tag}_shape"])
            m = curve(A[0], d["am_g"], d[f"am_{tag}_map"], col, 4)
            k = curve(B[0], t, d[f"am_{tag}_ku"], col, 3.5)
            lab = txt(f"map ({vm:g}, {am:g}): fitted v_t = {float(d[f'am_{tag}_vt']):.3f}, rms {float(d[f'am_{tag}_rms']):.4f}", 18, col)
            rows.add(lab)
            self.play(Create(m), run_time=0.6)
            self.play(Create(k), run_time=0.8)
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.12).move_to(2.5 * LEFT + 1.55 * DOWN)
        self.play(FadeIn(rows), run_time=0.4)
        self.caption("Assume a map that starts at 0.6 and the fit puts v_t at 0.649; assume one that starts at 0.4 and it puts v_t at 0.700. Both land on the file.", wait=3.0)
        for tag, col in (("late", BLUE), ("early", RED)):
            self.play(Create(curve(C[0], t, d[f"am_{tag}_ku810"], col, 4)), run_time=0.8)
        pk = txt(f"810 ps: K_u peaks at {float(d['am_late_peak810']):.2f} and {float(d['am_early_peak810']):.2f}", 18, DARK).move_to(4.0 * RIGHT + 1.55 * DOWN)
        self.play(FadeIn(pk), run_time=0.4)
        self.caption("Under the 810 ps pulse they differ: K_u peaks at 0.26 with one map and at 0 with the other. The file cannot choose the map.", wait=3.0)
        r = d["rms_by_K"]
        kt = txt(f"stage count: K = 3, 4, 5 fit the file with rms {r[2]:.4f}, {r[3]:.4f}, {r[4]:.4f}", 18, DARK).move_to(2.25 * DOWN)
        self.play(FadeIn(kt), run_time=0.4)
        self.caption(f"Nor the stage count: K = 3, 4 and 5 fit the file with rms {r[2]:.4f}, {r[3]:.4f} and {r[4]:.4f}. Three counts and three shapes: nine candidates.", wait=3.2)
        self.clear_stage()
        # the one measurement
        self.heading("6 · What one measurement settles")
        A = axes((0.2, 3, 1), (-0.4, 1.5, 0.5), 6.2, 3.5, xt=[1, 2, 3], yt=[0, 0.5, 1.0, 1.5],
                 xlabel="time from the input edge (ns)", ylabel="pad voltage (V)").shift(2.7 * LEFT + 0.2 * UP)
        ax = A[0]
        self.play(Create(A), run_time=0.6)
        meas = curve(ax, d["w_t"], d["w_si"][0], DARK, 6)
        self.play(Create(meas), run_time=1.0)
        pkv = float(d["p1_pad_peak"])
        pl = hline(ax, pkv, 0.2, 3.0, DARK, 1.5)
        pt = txt(f"measured peak {pkv:.2f} V", 18, DARK).next_to(ax.c2p(2.3, pkv), UP, buff=0.08)
        self.play(Create(pl), FadeIn(pt), run_time=0.5)
        self.caption(f"The one measurement: ex2's pad for the 810 ps pulse, peak {pkv:.2f} V. Nothing inside the buffer is observed.", wait=2.6)
        pre = VGroup(*[curve(ax, d["c_t"], y, GREY, 2.5).set_stroke(opacity=0.8) for y in d["c_pre"]])
        self.play(*[Create(c) for c in pre], run_time=1.4)
        lo, hi = float(d["c_pre"].max(axis=1).min()), float(d["c_pre"].max(axis=1).max())
        self.caption(f"The nine candidates as fitted to the file, driven by the same pulse: peaks from {lo:.2f} to {hi:.2f} V. Some overshoot, some extinguish the pulse in the chain.", wait=3.0)
        self.play(*[c.animate.set_stroke(opacity=0.15) for c in pre], run_time=0.4)
        names = [str(n) for n in d["bi_names"]]
        show_its = [names.index(n) for n in ("it00", "it01", "it03", "it05", "it09")]
        i0 = show_its[0]
        cur = curve(ax, d["bi_t"], d["bi_pads"][i0], TEAL, 4)
        lab = txt(f"v_t = {float(d['bi_vt'][i0]):.3f}: peak error {float(d['bi_err'][i0]):+.0f} %", 20, TEAL).shift(3.9 * RIGHT + 1.6 * UP)
        self.play(Create(cur), FadeIn(lab), run_time=0.7)
        self.caption("Calibration: v_t of each candidate is bisected until its peak matches the measured one. The selected candidate, five of its ten iterations:", wait=1.2)
        for i in show_its[1:]:
            new = curve(ax, d["bi_t"], d["bi_pads"][i], TEAL, 4)
            nl = txt(f"v_t = {float(d['bi_vt'][i]):.3f}: peak error {float(d['bi_err'][i]):+.0f} %", 20, TEAL).move_to(lab)
            self.play(Transform(cur, new), Transform(lab, nl), run_time=0.8)
            self.wait(0.5)
        self.wait(0.6)
        self.play(FadeOut(cur), FadeOut(lab), run_time=0.4)
        post = VGroup(*[curve(ax, d["c_t"], y, GREY, 2.5).set_stroke(opacity=0.85) for y in d["c_post"]])
        self.play(*[Transform(a, b) for a, b in zip(pre, post)], run_time=1.4)
        self.caption("After calibration all nine reach the measured peak. They still differ in when the pulse arrives and how it returns.", wait=2.6)
        rms = d["c_rms"]
        order = np.argsort(rms)
        table = VGroup()
        for i in order:
            nm = str(d["c_names"][i])
            col = TEAL if i == int(d["c_pick"]) else AXIS
            table.add(txt(f"{nm:12s} {rms[i]:4.0f} mV", 18, col))
        table.arrange(DOWN, aligned_edge=LEFT, buff=0.1).shift(4.0 * RIGHT + 0.1 * DOWN)
        th = txt("waveform rms over the pulse", 18, DARK, weight="BOLD").next_to(table, UP, buff=0.2)
        self.play(FadeIn(th), FadeIn(table), run_time=0.7)
        sel = curve(ax, d["c_t"], d["c_post"][int(d["c_pick"])], TEAL, 5)
        self.play(Create(sel), run_time=0.8)
        nm = str(d["c_names"][int(d["c_pick"])])
        self.caption(f"The waveform rms over the pulse and its return selects {nm.split()[0].replace('K', 'K = ')} with the map ({nm.split()[1].replace('/', ', ')}): {rms[int(d['c_pick'])]:.0f} mV against {np.sort(rms)[1]:.0f} to {rms.max():.0f} mV.", wait=3.2)
        self.play(FadeOut(pre), FadeOut(sel), FadeOut(table), FadeOut(th), FadeOut(pl), FadeOut(pt), FadeOut(meas), run_time=0.5)
        for i, w in enumerate(d["w_widths"]):
            s_ = curve(ax, d["w_t"], d["w_si"][i], DARK, 4)
            m_ = curve(ax, d["w_t"], d["w_mo"][i], TEAL, 3)
            self.play(Create(s_), Create(m_), run_time=0.6)
        lg = legend([(DARK, "transistor netlist"), (TEAL, "selected model")], 18).shift(4.0 * RIGHT + 0.6 * UP)
        wl = txt(f"{int(d['w_widths'][0])} to {int(d['w_widths'][-1])} ps", 18, AXIS).next_to(lg, DOWN, buff=0.2).align_to(lg, LEFT)
        self.play(FadeIn(lg), FadeIn(wl), run_time=0.4)
        self.caption(f"The selected model at the five stressed widths, {int(d['w_widths'][0])} to {int(d['w_widths'][-1])} ps, against the transistor: within {float(d['cl_worst']):.1f} % on the peak. One measurement, five widths predicted.", wait=3.4)
        self.clear_stage()

    # ---- 7. closing card
    def part_close(self):
        d = self.d
        self.next_section("close")
        self.heading("7 · The parameter set, and where each number comes from")
        p = d["ft_prm"]
        vt_cal = float(d["ch_prm"][2])
        rows = [("s_up, s_dn", f"fitted to the file's K_u(t): {p[0]:.2f}, {p[1]:.2f} per ns", TEAL),
                ("v_t", f"fitted to the file ({p[2]:.3f}), then calibrated on the measured peak ({vt_cal:.3f})", RED),
                ("K and the map (v_t,map, a)", "chosen by the measured waveform among nine candidates: K = 3, (0.50, 0.70)", RED),
                ("x_lin = 0.45, p = 1", "built-in constants", ORANGE),
                ("I–V tables, package", "from the file, unchanged", GREY),
                ("C_comp", f"declared {float(d['cc_declared']):.1f} pF; re-estimated from the file's own waveforms: {float(d['cc_estimated']):.2f} pF", GREY)]
        left = VGroup(*[txt(a, 22, DARK, weight="BOLD") for a, _, _ in rows]).arrange(DOWN, aligned_edge=LEFT, buff=0.42)
        right = VGroup(*[txt(b, 22, c) for _, b, c in rows])
        for l, r in zip(left, right):
            r.next_to(l, RIGHT, buff=0.5).align_to(l, DOWN)
        for r in right:
            r.align_to(max(left, key=lambda m: m.get_right()[0]).get_right() + 0.5 * RIGHT, LEFT)
        g = VGroup(left, right).move_to(0.5 * UP)
        if g.width > 13.4:
            g.set(width=13.4)
        g.move_to(0.5 * UP)
        for l, r in zip(left, right):
            self.play(FadeIn(l, shift=0.15 * RIGHT), FadeIn(r, shift=0.15 * RIGHT), run_time=0.5)
        self.wait(1.5)
        res = txt(f"ex2, five stressed widths: within {float(d['cl_worst']):.1f} % of the transistor-level pad peak; native IBIS {float(d['p1_nat_err']):+.0f} %.", 26, TEAL, weight="BOLD")
        res.to_edge(DOWN, buff=0.7)
        if res.width > 13.0:
            res.set(width=13.0)
        self.play(FadeIn(res, shift=0.2 * UP), run_time=0.8)
        self.wait(4.0)
        self.play(FadeOut(g), FadeOut(res), FadeOut(self._head), run_time=0.8)
        self._head = None

    def construct(self):
        self.part_title()
        self.part_file()
        self.part_stage()
        self.part_chain()
        self.part_map()
        self.part_pad()
        self.part_fix()
        self.part_close()


class P1(StageLawModel):
    def construct(self):
        self.part_file()


class P2(StageLawModel):
    def construct(self):
        self.part_stage()


class P3(StageLawModel):
    def construct(self):
        self.part_chain()


class P4(StageLawModel):
    def construct(self):
        self.part_map()


class P5(StageLawModel):
    def construct(self):
        self.part_pad()


class P6(StageLawModel):
    def construct(self):
        self.part_fix()


class P7(StageLawModel):
    def construct(self):
        self.part_close()
