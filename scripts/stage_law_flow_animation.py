#!/usr/bin/env python3
"""The stage-law flow, animated with manim (Community v0.22).

Seven parts, in the order of the document (results/stage_law_doc_2026-10-01): the problem, the
model, the target, the fit, what the file cannot tell, the one stressed measurement, the result.
Every curve is a stored result of the project, gathered into one file by
scripts/stage_law_flow_animation_data.py; nothing is simulated here.

    py -3.14 scripts/stage_law_flow_animation_data.py
    py -3.14 -m manim -qm --media_dir results/stage_law_flow_animation_2026-10-15/media ^
        scripts/stage_law_flow_animation.py StageLawFlow

Formulas are typeset with matplotlib's mathtext (no LaTeX on this machine) and loaded as SVG.
The classes P1..P7 render one part each, for checking.

Output: results/stage_law_flow_animation_2026-10-15/media/videos/stage_law_flow_animation/720p30/StageLawFlow.mp4
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from manim import (  # noqa: E402
    DOWN, LEFT, RIGHT, UP, ORIGIN, UL, UR, DL, DR, WHITE, Arrow, Axes, Create, DashedLine, Dot, FadeIn, FadeOut,
    ImageMobject, Line, MoveAlongPath, Rectangle, RoundedRectangle, SVGMobject, Scene, Text, TracedPath,
    Transform, VGroup, VMobject, Write, config, rate_functions, ReplacementTransform, Indicate, GrowArrow,
    GrowFromCenter, Succession, AnimationGroup, Circle, Polygon,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "results" / "stage_law_flow_animation_2026-10-15" / "data" / "flow_data.npz"
CACHE = ROOT / "results" / "stage_law_flow_animation_2026-10-15" / "media" / "mtex"

DARK, TEAL, BLUE, RED, GREY, ORANGE, SAND = "#1B1F22", "#0E9F9A", "#2B6CA3", "#B0563C", "#8A9499", "#C9862B", "#E8E1D3"
FONT = "Arial"
config.background_color = WHITE


# ------------------------------------------------------------------ helpers
def mtex(s: str, color=DARK, height: float = 0.5) -> SVGMobject:
    """A formula typeset by matplotlib's mathtext, as a vector mobject."""
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / (hashlib.md5(s.encode()).hexdigest()[:12] + ".svg")
    if not p.exists():
        fig = plt.figure(figsize=(0.1, 0.1))
        fig.text(0, 0, s, fontsize=24)
        fig.savefig(p, format="svg", bbox_inches="tight", pad_inches=0.02, transparent=True)
        plt.close(fig)
    m = SVGMobject(str(p)).set_color(color)
    m.set_stroke(width=0)
    return m.set(height=height)


def txt(s: str, size: float = 26, color=DARK, weight="NORMAL") -> Text:
    return Text(s, font=FONT, font_size=size, color=color, weight=weight)


def axes(xr, yr, w=5.0, h=3.0, xt=None, yt=None, xlabel="", ylabel="", fs=18) -> VGroup:
    """Axes with Text tick labels (no LaTeX), returned as a group whose [0] is the Axes."""
    ax = Axes(x_range=[xr[0], xr[1], xr[2]], y_range=[yr[0], yr[1], yr[2]], x_length=w, y_length=h,
              axis_config={"color": "#55606A", "include_numbers": False, "include_ticks": True,
                           "stroke_width": 2, "tick_size": 0.06, "include_tip": False})
    g = VGroup(ax)
    for v in (xt if xt is not None else np.arange(xr[0], xr[1] + 1e-9, xr[2])):
        g.add(txt(f"{v:g}", fs, "#55606A").next_to(ax.x_axis.n2p(v), DOWN, buff=0.12))
    for v in (yt if yt is not None else np.arange(yr[0], yr[1] + 1e-9, yr[2])):
        g.add(txt(f"{v:g}", fs, "#55606A").next_to(ax.y_axis.n2p(v), LEFT, buff=0.12))
    if xlabel:
        g.add(txt(xlabel, fs + 1, "#55606A").next_to(ax, DOWN, buff=0.45))
    if ylabel:
        g.add(txt(ylabel, fs + 1, "#55606A").rotate(np.pi / 2).next_to(ax, LEFT, buff=0.7))
    return g


def curve(ax: Axes, x, y, color=DARK, width: float = 4.0, n: int = 400) -> VMobject:
    x, y = np.asarray(x, float), np.asarray(y, float)
    keep = (x >= ax.x_range[0]) & (x <= ax.x_range[1])
    x, y = x[keep], y[keep]
    if len(x) > n:
        g = np.linspace(x[0], x[-1], n)
        y = np.interp(g, x, y)
        x = g
    lo, hi = ax.y_range[0], ax.y_range[1]
    y = np.clip(y, lo - 0.02 * (hi - lo), hi + 0.02 * (hi - lo))
    m = VMobject().set_points_as_corners([ax.c2p(a, b) for a, b in zip(x, y)])
    return m.set_stroke(color, width=width)


def box(text: str, w: float, h: float, fc, ec, fs: int = 22) -> VGroup:
    r = RoundedRectangle(corner_radius=0.12, width=w, height=h).set_fill(fc, opacity=1).set_stroke(ec, width=2.5)
    t = txt(text, fs).move_to(r)
    return VGroup(r, t)


# ------------------------------------------------------------------ the scene
class StageLawFlow(Scene):
    def setup(self):
        self.camera.background_color = WHITE
        self.d = dict(np.load(DATA, allow_pickle=True))
        self._cap = None
        self._head = None

    # ---- caption and section heading
    def caption(self, s: str, size: float = 27, wait: float = 2.6, color=DARK):
        new = txt(s, size, color).to_edge(DOWN, buff=0.45)
        if new.width > 12.8:
            new.set(width=12.8)
        if self._cap is None:
            self.play(FadeIn(new, shift=0.2 * UP), run_time=0.6)
        else:
            self.play(FadeOut(self._cap, run_time=0.3), FadeIn(new, shift=0.2 * UP, run_time=0.6))
        self._cap = new
        self.wait(wait)

    def heading(self, s: str):
        new = txt(s, 24, TEAL, weight="BOLD").to_corner(UL, buff=0.35)
        if self._head is None:
            self.play(FadeIn(new), run_time=0.5)
        else:
            self.play(ReplacementTransform(self._head, new), run_time=0.5)
        self._head = new

    def clear_stage(self, keep=()):
        mobs = [m for m in self.mobjects if m is not self._head and m is not self._cap and m not in keep]
        if mobs:
            self.play(*[FadeOut(m) for m in mobs], run_time=0.6)
        if self._cap is not None:
            self.play(FadeOut(self._cap), run_time=0.3)
            self._cap = None

    # ---- 0. title
    def part_title(self):
        self.next_section("title")
        t1 = txt("A stage-law model of the IBIS predriver", 44, DARK, weight="BOLD").shift(0.6 * UP)
        t2 = txt("how the model is built from the IBIS file and one stressed measurement", 28, "#55606A").next_to(t1, DOWN, buff=0.4)
        t3 = txt("every curve is a stored result on the test buffer ex2", 22, GREY).next_to(t2, DOWN, buff=0.8)
        self.play(Write(t1), run_time=1.6)
        self.play(FadeIn(t2, shift=0.2 * UP), run_time=0.8)
        self.play(FadeIn(t3), run_time=0.6)
        self.wait(1.8)
        self.play(FadeOut(t1), FadeOut(t2), FadeOut(t3), run_time=0.6)

    # ---- 1. the problem
    def part_problem(self):
        d = self.d
        self.next_section("problem")
        self.heading("1 · The problem")
        A = axes((-0.5, 6, 2), (0, 3.5, 1), 5.4, 3.0, xt=[0, 2, 4, 6], yt=[0, 1, 2, 3],
                 xlabel="time from the input edge (ns)", ylabel="voltage (V)").shift(3.1 * LEFT + 0.3 * UP)
        ax = A[0]
        c_in = curve(ax, d["p_t"], d["p_in"], GREY, 3)
        c_pad = curve(ax, d["p_t"], d["p_pad"], DARK, 5)
        self.play(Create(A), run_time=0.8)
        self.play(Create(c_in), run_time=0.8)
        l1 = txt("input pin", 20, GREY).next_to(ax.c2p(3.0, 3.3), DOWN, buff=0.1)
        self.add(l1)
        self.play(Create(c_pad), run_time=1.6)
        l2 = txt("pad, transistor netlist", 20, DARK).next_to(ax.c2p(3.5, 1.55), DOWN, buff=0.15)
        self.add(l2)
        self.caption("An IBIS file records complete transitions: I–V tables, and the pad voltage for one full rise and one full fall.")
        B = axes((-0.5, 3, 1), (-0.5, 1.5, 0.5), 5.4, 3.0, xt=[0, 1, 2, 3], yt=[0, 0.5, 1.0, 1.5],
                 xlabel="time from the input edge (ns)").shift(3.4 * RIGHT + 0.3 * UP)
        bx = B[0]
        s_si = curve(bx, d["s_t"], d["s_si"], DARK, 5)
        self.play(Create(B), run_time=0.8)
        pulse = Line(bx.c2p(0, 1.25), bx.c2p(0.81, 1.25), color="#55606A", stroke_width=2)
        pl = txt("810 ps input pulse", 18, "#55606A").next_to(pulse, UP, buff=0.08)
        self.play(Create(pulse), FadeIn(pl), run_time=0.6)
        self.play(Create(s_si), run_time=1.4)
        self.caption("A pulse shorter than the buffer's own delay is cut short inside the predriver: the pad reaches only part of its swing.")
        s_nat = curve(bx, d["s_t"], d["s_nat"], BLUE, 4).set_stroke(opacity=0.9)
        nat_l = txt(f"native IBIS: {d['s_nat_err']:+.0f} % on the peak", 20, BLUE).next_to(bx.c2p(1.7, 1.3), RIGHT, buff=0.1)
        self.play(Create(s_nat), run_time=1.4)
        self.play(FadeIn(nat_l), run_time=0.5)
        self.caption("The file's coefficients, replayed against time, cannot represent a gate that turns back partway.", wait=3.0)
        self.clear_stage()

    # ---- 2. the model
    def part_model(self):
        d = self.d
        self.next_section("model")
        self.heading("2 · The idea: a chain of stages drives the output gate")
        FILE, NEW = "#F1F3F4", "#DDF1F0"
        stages = VGroup(*[box(f"stage {k}", 1.3, 0.9, NEW, TEAL, 20) for k in (1, 2, 3)]).arrange(RIGHT, buff=0.8)
        cmp_ = box("comparator\nat V_DD/2", 1.55, 0.9, NEW, TEAL, 17)
        mp = box("map M", 1.2, 0.9, NEW, TEAL, 20)
        iv = box("I–V tables\n+ C_comp", 1.55, 0.9, FILE, "#55606A", 17)
        row = VGroup(cmp_, stages, mp, iv).arrange(RIGHT, buff=0.8).shift(1.2 * UP)
        arrows = VGroup()
        items = [cmp_, *stages, mp, iv]
        for a, b in zip(items[:-1], items[1:]):
            arrows.add(Arrow(a.get_right(), b.get_left(), buff=0.05, color="#55606A", stroke_width=3, max_tip_length_to_length_ratio=0.3))
        lab_g = txt("gate g", 16, TEAL).next_to(arrows[3], UP, buff=0.03)
        lab_k = txt("Ku", 16, TEAL).next_to(arrows[4], UP, buff=0.03)
        vin = txt("V_in", 20).next_to(cmp_, LEFT, buff=0.3)
        pad = txt("pad", 20).next_to(iv, RIGHT, buff=0.3)
        self.play(FadeIn(vin), FadeIn(cmp_), run_time=0.5)
        for a, b in zip(arrows[:3], stages):
            self.play(GrowArrow(a), FadeIn(b), run_time=0.45)
        self.play(GrowArrow(arrows[3]), FadeIn(mp), FadeIn(lab_g), run_time=0.5)
        self.play(GrowArrow(arrows[4]), FadeIn(iv), FadeIn(lab_k), FadeIn(pad), run_time=0.5)
        brace = Line(stages.get_left() + 0.65 * UP, mp.get_right() + 0.65 * UP, color=TEAL, stroke_width=2)
        bl = txt("added by the method: fitted to the file, one measurement to settle", 19, TEAL).next_to(brace, UP, buff=0.08)
        self.play(Create(brace), FadeIn(bl), run_time=0.6)
        self.caption("The predriver becomes K identical stages. The last one is the gate of the output transistor; a static map turns the gate into K_u.")
        law = mtex(r"$\frac{dv}{dt} = s_{up}\,h(u)\,r(1-v) \;-\; s_{dn}\,h(1-u)\,r(v)$", DARK, 0.62)
        law.set(width=5.4).move_to(3.6 * LEFT + 0.9 * DOWN)
        self.play(FadeIn(law, shift=0.2 * UP), run_time=0.8)
        self.caption("Each stage obeys the stage law, derived from the α-power law of the transistor: a charging term and a discharging term.")
        A = axes((-0.1, 2.0, 0.5), (0, 1.0, 0.5), 3.8, 2.0, xt=[0, 0.5, 1, 1.5, 2], yt=[0, 0.5, 1],
                 xlabel="time (ns)", ylabel="stage output v").shift(2.2 * RIGHT + 0.95 * DOWN)
        ax = A[0]
        self.play(FadeIn(A), run_time=0.6)
        u = curve(ax, d["st_t"], d["st_u"], GREY, 2.5)
        self.play(Create(u), run_time=0.5)
        cols = {1: "#9CC8C6", 2: TEAL, 4: "#0B5F5C"}
        shown = {}
        legend = VGroup(txt("input step", 17, GREY))
        legend.next_to(ax, RIGHT, buff=0.35).align_to(ax, UP)
        self.add(legend[0])
        for s in (1, 2, 4):
            c = curve(ax, d["st_t"], d[f"st_sup{s}"], cols[s], 4)
            lab = txt(f"s_up = {s}/ns, v_t = 0.3", 17, cols[s]).next_to(legend[-1], DOWN, aligned_edge=LEFT, buff=0.15)
            legend.add(lab)
            self.play(Create(c), FadeIn(lab), run_time=0.7)
            shown[s] = (c, lab)
        self.caption("A step at the input: the stage fills like a bucket at the rate s_up, and the last part tapers off as it nears the rail.")
        for s in (1, 4):
            self.play(FadeOut(shown[s][0]), FadeOut(shown[s][1]), run_time=0.3)
        c_vt = {}
        anchor = shown[2][1]
        for vt, col in ((0.1, ORANGE), (0.5, RED)):
            c = curve(ax, d["st_t"], d[f"st_vt{vt}"], col, 4)
            lab = txt(f"s_up = 2/ns, v_t = {vt}", 17, col).next_to(anchor, DOWN, aligned_edge=LEFT, buff=0.15)
            anchor = lab
            self.play(Create(c), FadeIn(lab), run_time=0.7)
            c_vt[vt] = (c, lab)
        self.caption("The threshold v_t is the level the input must reach before the stage starts: it sets the delay between stages without changing the slope.", wait=3.2)
        self.clear_stage()

    # ---- 3. the target
    def part_target(self):
        d = self.d
        self.next_section("target")
        self.heading("3 · Step 0: the target, the file's own K_u(t)")
        A = axes((0, 8, 2), (0, 3.5, 1), 4.6, 2.6, xt=[0, 2, 4, 6, 8], yt=[0, 1, 2, 3],
                 xlabel="table time (ns)", ylabel="pad voltage (V)").shift(3.6 * LEFT + 0.6 * UP)
        ax = A[0]
        self.play(Create(A), run_time=0.7)
        r0 = curve(ax, d["vt_t"], d["vt_r0"], TEAL, 4)
        r1 = curve(ax, d["vt_t"], d["vt_r1"], "#0B5F5C", 4)
        self.play(Create(r0), run_time=0.9)
        l0 = txt("rising, fixture 0 V", 17, TEAL).next_to(ax.c2p(4, 1.55), UP, buff=0.05)
        self.play(FadeIn(l0), Create(r1), run_time=0.9)
        l1 = txt("rising, fixture 3.3 V", 17, "#0B5F5C").next_to(ax.c2p(4, 3.3), DOWN, buff=0.05)
        self.add(l1)
        self.caption("The file holds the same rising transition recorded into two fixtures, 50 Ω to 0 V and 50 Ω to 3.3 V.")
        eq = mtex(r"$K_u\,I_{PU}(V_i) + K_d\,I_{PD}(V_i) = \frac{V_{fix,i}-V_i}{R_{fix}} - C_{comp}\frac{dV_i}{dt},\quad i=1,2$", DARK, 0.62)
        eq.set(width=6.3).move_to(3.3 * RIGHT + 0.6 * UP)
        self.play(FadeIn(eq, shift=0.2 * UP), run_time=0.8)
        self.caption("At every instant the current must balance in both fixtures: two equations, two unknowns. The converter solves them for K_u(t) and K_d(t).")
        B = axes((-1, 16, 5), (0, 1.0, 0.5), 4.6, 2.3, xt=[0, 5, 10, 15], yt=[0, 0.5, 1],
                 xlabel="time from the input edge (ns)", ylabel="conducting fraction").shift(3.3 * RIGHT + 1.0 * DOWN)
        bx = B[0]
        self.play(FadeOut(eq), FadeIn(B), run_time=0.7)
        ku = curve(bx, d["m_t"], d["m_ku"], TEAL, 4)
        kd = curve(bx, d["m_t"], d["m_kd"], BLUE, 3).set_stroke(opacity=0.7)
        lk = txt("K_u(t)", 18, TEAL).next_to(bx.c2p(5.5, 1.0), UP, buff=0.05)
        ld = txt("K_d(t)", 18, BLUE).next_to(bx.c2p(14, 1.0), UP, buff=0.05)
        self.play(Create(ku), Create(kd), run_time=1.5)
        self.play(FadeIn(lk), FadeIn(ld), run_time=0.4)
        self.caption("K_u(t) is the fraction of the pull-up table that conducts, against time, for the one complete transition the file recorded.")
        tgt = curve(bx, d["g_t"], d["g_target"], DARK, 5)
        uu = curve(bx, d["g_t"], d["g_u"], GREY, 2.5)
        self.play(FadeOut(kd), FadeOut(ld), ReplacementTransform(ku, tgt), FadeOut(lk), run_time=1.0)
        self.play(Create(uu), run_time=0.6)
        lt = txt("target: normalised K_u(t)", 18, DARK).next_to(bx.c2p(5.5, 1.0), UP, buff=0.05)
        lu = txt("chain input:\n10 ns pulse", 16, GREY).next_to(bx.c2p(12.3, 0.5), RIGHT, buff=0.05)
        self.play(FadeIn(lt), FadeIn(lu), run_time=0.4)
        self.caption("Normalised between its settled levels, this curve is the target: the only thing the stage law is ever fitted to.", wait=3.0)
        self.clear_stage()

    # ---- 4. the fit
    def part_fit(self):
        d = self.d
        self.next_section("fit")
        self.heading("4 · Step 1: fit the stage numbers to the target")
        A = axes((-0.3, 3.0, 1), (0, 1.0, 0.5), 5.6, 3.2, xt=[0, 1, 2, 3], yt=[0, 0.5, 1],
                 xlabel="time from the input edge (ns)", ylabel="K_u").shift(3.0 * LEFT + 0.2 * UP)
        ax = A[0]
        tgt = curve(ax, d["g_t"], d["g_target"], "#9A9A9A", 7)
        self.play(Create(A), run_time=0.7)
        self.play(Create(tgt), run_time=1.0)
        lt = txt("file: target", 18, "#777777").next_to(ax.c2p(2.2, 1.0), DOWN, buff=0.12)
        self.add(lt)
        chain_eq = mtex(r"$K_u(t) = M(v_K(t)),\qquad \{s_{up}, s_{dn}, v_t\}^\star = \arg\min\ \mathrm{rms}_t[M(v_K(t)) - \hat K_u(t)]$", DARK, 0.5).shift(3.0 * UP)
        self.play(FadeIn(chain_eq, shift=0.2 * UP), run_time=0.8)
        panel = VGroup()
        rows = [("s_up", 0.0), ("s_dn", 0.0), ("v_t", 0.0), ("residual", 0.0)]
        labels = VGroup(*[txt(n, 22, DARK) for n, _ in rows]).arrange(DOWN, aligned_edge=LEFT, buff=0.35).shift(2.2 * RIGHT + 0.4 * UP)
        vals = VGroup(*[txt("", 22, TEAL) for _ in rows])
        for lab, v in zip(labels, vals):
            v.next_to(lab, RIGHT, buff=0.4)
        self.play(FadeIn(labels), run_time=0.5)

        def show(prm, rms, color=TEAL):
            new = VGroup(*[txt(f"{prm[0]:.2f} /ns", 22, color), txt(f"{prm[1]:.2f} /ns", 22, color),
                           txt(f"{prm[2]:.3f}", 22, color), txt(f"{rms:.3f}", 22, RED if rms > 0.05 else TEAL)])
            for lab, v in zip(labels, new):
                v.next_to(lab, RIGHT, buff=0.4)
            return new

        cur = curve(ax, d["g_t"], d["guess_ku"], RED, 4)
        v = show((8.0, 8.0, 0.4), d["guess_rms"], RED)
        self.play(Create(cur), FadeIn(v), run_time=0.9)
        vals = v
        self.caption("A trial set of the three numbers gives a model curve. The residual is the root-mean-square gap to the target over the whole window.")
        seq = [("s_up", 0), ("s_up", 1), ("s_dn", 0), ("s_dn", 1), ("vt", 0), ("vt", 1)]
        caps = {"s_up": "s_up is the charging rate: it sets how early and how steep the rising edge is.",
                "s_dn": "s_dn does the same for the falling edge, at 10 ns, out of this window.",
                "vt": "v_t moves the edge in time without changing its steepness: it is the delay between stages."}
        last = None
        for name, j in seq:
            y = d[f"knob_{name}_{j}"]
            prm = d[f"knob_{name}_{j}_prm"]
            rms = float(d[f"knob_{name}_{j}_rms"])
            new = curve(ax, d["g_t"], y, ORANGE, 4)
            nv = show(prm, rms, ORANGE)
            self.play(Transform(cur, new), Transform(vals, nv), run_time=1.1)
            if last != name:
                self.caption(caps[name], wait=1.8)
                last = name
        fit = curve(ax, d["g_t"], d["fit_ku"], TEAL, 4)
        fv = show(d["fit_prm"], float(d["fit_rms"]), TEAL)
        self.play(Transform(cur, fit), Transform(vals, fv), run_time=1.2)
        self.caption(f"The fit: s_up = {d['fit_prm'][0]:.2f}/ns, s_dn = {d['fit_prm'][1]:.2f}/ns, v_t = {d['fit_prm'][2]:.3f}, residual {float(d['fit_rms']):.3f}.", wait=2.4)
        # the search
        self.clear_stage()
        self.heading("4 · Step 1: how the minimum is found")
        img_path = CACHE / "landscape.png"
        L_sup, L_vt, Z = d["land_s_up"], d["land_vt"], d["land_rms_sup_vt"]
        if not img_path.exists():
            fig, a = plt.subplots(figsize=(5.2, 3.6), dpi=200)
            a.contourf(np.log(L_sup), L_vt, np.log10(Z).T, levels=np.linspace(np.log10(0.02), np.log10(0.5), 15), cmap="Greys_r", extend="both")
            a.set_xlim(np.log(L_sup[0]), np.log(L_sup[-1])); a.set_ylim(L_vt[0], L_vt[-1])
            a.axis("off")
            fig.subplots_adjust(0, 0, 1, 1)
            fig.savefig(img_path, dpi=200)
            plt.close(fig)
        img = ImageMobject(str(img_path)).set(width=6.0).shift(2.8 * LEFT + 0.1 * UP)
        self.play(FadeIn(img), run_time=0.8)
        x0, x1 = np.log(L_sup[0]), np.log(L_sup[-1])
        y0, y1 = L_vt[0], L_vt[-1]
        left, right = img.get_left()[0], img.get_right()[0]
        bot, top = img.get_bottom()[1], img.get_top()[1]

        def lp(s_up, vt):
            fx = (np.log(np.clip(s_up, L_sup[0], L_sup[-1])) - x0) / (x1 - x0)
            fy = (np.clip(vt, y0, y1) - y0) / (y1 - y0)
            return np.array([left + fx * (right - left), bot + fy * (top - bot), 0])

        xl = txt("s_up (log scale) →", 18, "#55606A").next_to(img, DOWN, buff=0.15)
        yl = txt("v_t →", 18, "#55606A").rotate(np.pi / 2).next_to(img, LEFT, buff=0.15)
        self.play(FadeIn(xl), FadeIn(yl), run_time=0.4)
        self.caption("The residual over two of the three numbers, s_up and v_t: darker is lower. A narrow valley in the rate, a shallow one in the threshold.")
        cols = {2: TEAL, 8: ORANGE, 30: BLUE}
        legend = VGroup()
        for s0 in (2, 8, 30):
            path = d[f"path_{s0}"]
            end = d[f"end_{s0}"]
            pts = [lp(p[0], p[2]) for p in path]
            vm = VMobject().set_points_as_corners(pts)
            dot = Dot(pts[0], radius=0.08, color=cols[s0])
            trace = TracedPath(dot.get_center, stroke_color=cols[s0], stroke_width=3)
            self.add(trace, dot)
            self.play(MoveAlongPath(dot, vm), run_time=2.2, rate_func=rate_functions.linear)
            lab = txt(f"start {s0}/ns → residual {end[3]:.3f}", 20, cols[s0])
            legend.add(lab)
        legend.arrange(DOWN, aligned_edge=LEFT, buff=0.3).shift(3.6 * RIGHT + 0.6 * UP)
        self.play(FadeIn(legend), run_time=0.5)
        fitdot = Dot(lp(d["fit_prm"][0], d["fit_prm"][2]), radius=0.1, color=RED).set_fill(opacity=0).set_stroke(RED, 3)
        self.play(GrowFromCenter(fitdot), run_time=0.4)
        self.caption("Nelder–Mead walks downhill from three starts. Only one of the three reaches the minimum; the others stop in side valleys, so the best of the three is kept.", wait=3.4)
        self.clear_stage()

    # ---- 5. what the file cannot tell
    def part_ambiguity(self):
        d = self.d
        self.next_section("ambiguity")
        self.heading("5 · What the file cannot tell: several models fit it equally well")
        A = axes((0, 1, 0.5), (0, 1, 0.5), 3.3, 2.4, xt=[0, 0.5, 1], yt=[0, 0.5, 1], xlabel="gate g", ylabel="map M(g)").shift(3.9 * LEFT + 0.8 * UP)
        B = axes((-0.3, 3, 1), (0, 1, 0.5), 3.3, 2.4, xt=[0, 1, 2, 3], yt=[0, 0.5, 1], xlabel="time (ns)", ylabel="K_u, full transition").shift(0.4 * RIGHT + 0.8 * UP)
        C = axes((-0.3, 3, 1), (0, 1, 0.5), 3.3, 2.4, xt=[0, 1, 2, 3], yt=[0, 0.5, 1], xlabel="time (ns)", ylabel="K_u, 810 ps pulse").shift(4.7 * RIGHT + 0.8 * UP)
        self.play(Create(A), Create(B), Create(C), run_time=0.8)
        tgt = curve(B[0], d["g_t"], d["g_target"], "#9A9A9A", 7)
        self.play(Create(tgt), run_time=0.7)
        for tag, col, name in (("late", BLUE, "map starts at 0.6"), ("early", RED, "map starts at 0.4")):
            m = curve(A[0], d["amb_g"], d[f"amb_{tag}_map"], col, 4)
            k = curve(B[0], d["g_t"], d[f"amb_{tag}_ku"], col, 3.5)
            lab = txt(f"{name}: fitted v_t = {float(d[f'amb_{tag}_vt']):.2f}, residual {float(d[f'amb_{tag}_rms']):.4f}", 19, col)
            lab.move_to([-3.0, -1.7 if tag == "late" else -2.1, 0])
            self.play(Create(m), run_time=0.7)
            self.play(Create(k), FadeIn(lab), run_time=0.9)
        self.caption("Assume a map that starts later, and the fit makes the gate leave earlier; assume an earlier map, and the gate leaves later. Both land on the file.")
        for tag, col in (("late", BLUE), ("early", RED)):
            k = curve(C[0], d["g_t"], d[f"amb_{tag}_ku810"], col, 4)
            self.play(Create(k), run_time=0.9)
        pk = txt("peaks 0.51 and 0.00", 20, DARK).move_to([4.4, -1.7, 0])
        self.play(FadeIn(pk), run_time=0.4)
        self.caption("For an 810 ps pulse they give opposite answers: one passes the pulse, the other extinguishes it inside the chain. The file cannot choose.", wait=3.0)
        self.caption("The same holds for the stage count: on ex2, K = 3, 4 and 5 fit the file within 0.002 of each other. Three counts × three map shapes = nine candidates.", wait=3.4)
        self.clear_stage()

    # ---- 6. the measurement
    def part_measurement(self):
        d = self.d
        self.next_section("measurement")
        self.heading("6 · Steps 2–4: one stressed measurement decides")
        A = axes((0.2, 3, 1), (-0.4, 1.5, 0.5), 6.2, 3.6, xt=[1, 2, 3], yt=[0, 0.5, 1.0, 1.5],
                 xlabel="time from the input edge (ns)", ylabel="pad voltage (V)").shift(2.7 * LEFT + 0.2 * UP)
        ax = A[0]
        self.play(Create(A), run_time=0.7)
        meas = curve(ax, d["w_t"], d["w_si"][0], DARK, 6)
        self.play(Create(meas), run_time=1.2)
        pk = float(d["s_peak"])
        pl = DashedLine(ax.c2p(0.2, pk), ax.c2p(3, pk), color=DARK, stroke_width=1.5)
        pt = txt(f"measured peak {pk:.2f} V", 19, DARK).next_to(ax.c2p(2.3, pk), UP, buff=0.08)
        self.play(Create(pl), FadeIn(pt), run_time=0.5)
        self.caption("The one measurement: the pad voltage for a pulse that reaches about half the swing. Nothing inside the buffer is observed.")
        pre = VGroup(*[curve(ax, d["c_t"], y, GREY, 2.5).set_stroke(opacity=0.8) for y in d["c_pre"]])
        self.play(*[Create(c) for c in pre], run_time=1.6)
        self.caption(f"The nine candidates, as fitted to the file, driven by the same pulse: peaks from {d['c_pre'].max(axis=1).min():.2f} to {d['c_pre'].max(axis=1).max():.2f} V. Some overshoot, some extinguish the pulse.")
        # calibration of one candidate: the bisection
        self.play(*[c.animate.set_stroke(opacity=0.15) for c in pre], run_time=0.5)
        bt, bpads, bvt, berr = d["b_t"], d["b_pads"], d["b_vt"], d["b_err"]
        cur = curve(ax, bt, bpads[0], TEAL, 4)
        lab = txt(f"v_t = {bvt[0]:.3f}: peak error {berr[0]:+.0f} %", 21, TEAL).shift(3.9 * RIGHT + 1.6 * UP)
        self.play(Create(cur), FadeIn(lab), run_time=0.8)
        self.caption("Step 3, calibration: for each candidate the stage threshold v_t is bisected until the model's peak matches the measured one.", wait=1.6)
        for i in (1, 3, 4, 5, 6, 7, 8, 9):
            new = curve(ax, bt, bpads[i], TEAL, 4)
            nl = txt(f"v_t = {bvt[i]:.3f}: peak error {berr[i]:+.0f} %", 21, TEAL).move_to(lab)
            self.play(Transform(cur, new), Transform(lab, nl), run_time=0.7 if i < 6 else 0.5)
        self.wait(0.8)
        self.play(FadeOut(cur), FadeOut(lab), run_time=0.4)
        post = VGroup(*[curve(ax, d["c_t"], y, GREY, 2.5).set_stroke(opacity=0.85) for y in d["c_post"]])
        self.play(*[Transform(a, b) for a, b in zip(pre, post)], run_time=1.4)
        self.caption("After calibration all nine reach the measured peak. They still differ in when the pulse arrives and how it returns.")
        rms = d["c_rms29"]
        order = np.argsort(rms)
        table = VGroup()
        for i in order:
            nm = str(d["c_names"][i])
            col = TEAL if i == int(d["c_pick"]) else "#55606A"
            table.add(txt(f"{nm:12s} {rms[i]:4.0f} mV", 19, col))
        table.arrange(DOWN, aligned_edge=LEFT, buff=0.12).shift(4.0 * RIGHT + 0.0 * UP)
        th = txt("waveform rms, step 4", 20, DARK, weight="BOLD").next_to(table, UP, buff=0.2)
        self.play(FadeIn(th), FadeIn(table), run_time=0.8)
        win = Rectangle(width=ax.c2p(0.81 + 1.5, 0)[0] - ax.c2p(0.81 - 0.3, 0)[0], height=3.6).set_fill(SAND, opacity=0.35).set_stroke(width=0)
        win.move_to(ax.c2p(0.81 + 0.6, 0.55))
        self.play(FadeIn(win), run_time=0.4)
        sel = curve(ax, d["c_t"], d["c_post"][int(d["c_pick"])], TEAL, 5)
        self.play(Create(sel), run_time=0.8)
        self.caption("Step 4, selection: the candidate whose whole waveform is closest over the pulse and its return is kept. Here K = 3 with the map (0.5, 0.7).", wait=3.2)
        self.clear_stage()

    # ---- 7. the result
    def part_result(self):
        d = self.d
        self.next_section("result")
        self.heading("7 · The result")
        A = axes((0.2, 3, 1), (-0.3, 1.5, 0.5), 5.6, 3.3, xt=[1, 2, 3], yt=[0, 0.5, 1.0, 1.5],
                 xlabel="time from the input edge (ns)", ylabel="pad voltage (V)").shift(3.2 * LEFT + 0.2 * UP)
        ax = A[0]
        self.play(Create(A), run_time=0.6)
        for i, w in enumerate(d["w_widths"]):
            si = curve(ax, d["w_t"], d["w_si"][i], DARK, 4)
            mo = curve(ax, d["w_t"], d["w_mo"][i], TEAL, 3)
            self.play(Create(si), Create(mo), run_time=0.7)
        lg = VGroup(txt("transistor netlist", 19, DARK), txt("selected model", 19, TEAL)).arrange(DOWN, aligned_edge=LEFT, buff=0.1).next_to(ax.c2p(2.1, 1.4), RIGHT, buff=0.1)
        self.play(FadeIn(lg), run_time=0.4)
        self.caption("The selected model at five pulse widths, 50 to 90 % of the swing, against the transistor netlist: one measurement, five widths predicted.")
        # bar chart of twelve buffers
        devs, nat, prop, dead = d["r_devs"], d["r_native"], d["r_proposed"], d["r_dead"]
        base = 3.3 * RIGHT + 1.2 * DOWN
        bw, gap = 0.18, 0.44
        scale = 2.6 / 100.0
        bars = VGroup()
        labs = VGroup()
        x0 = base[0] - 0.5 * gap * (len(devs) - 1)
        for i, dev in enumerate(devs):
            x = x0 + i * gap
            h_p = max(float(prop[i]) * scale, 0.02)
            bp = Rectangle(width=bw, height=h_p).set_fill(TEAL, opacity=1).set_stroke(width=0)
            bp.move_to([x + bw / 2, base[1] + h_p / 2, 0])
            if dead[i]:
                bn = Rectangle(width=bw, height=100 * scale).set_fill(WHITE, opacity=1).set_stroke(BLUE, 1.2)
            else:
                bn = Rectangle(width=bw, height=float(nat[i]) * scale).set_fill(BLUE, opacity=1).set_stroke(width=0)
            bn.move_to([x - bw / 2, base[1] + bn.height / 2, 0])
            bars.add(bn, bp)
            labs.add(txt(str(dev), 13, "#55606A").rotate(np.pi / 4).move_to([x, base[1] - 0.45, 0]))
        axis = Line([x0 - 0.3, base[1], 0], [x0 + gap * len(devs), base[1], 0], color="#55606A", stroke_width=2)
        ten = DashedLine([x0 - 0.3, base[1] + 10 * scale, 0], [x0 + gap * len(devs), base[1] + 10 * scale, 0], color=TEAL, stroke_width=1.5)
        tl = txt("10 %", 16, TEAL).next_to(ten, RIGHT, buff=0.05)
        hundred = txt("100 %", 16, "#55606A").move_to([x0 - 0.45, base[1] + 100 * scale, 0])
        self.play(Create(axis), run_time=0.3)
        self.play(FadeIn(bars), FadeIn(labs), Create(ten), FadeIn(tl), FadeIn(hundred), run_time=1.2)
        key = VGroup(VGroup(Rectangle(width=0.25, height=0.25).set_fill(BLUE, 1).set_stroke(width=0), txt("HSPICE native IBIS", 17, DARK)).arrange(RIGHT, buff=0.15),
                     VGroup(Rectangle(width=0.25, height=0.25).set_fill(TEAL, 1).set_stroke(width=0), txt("proposed: file + one measurement", 17, DARK)).arrange(RIGHT, buff=0.15),
                     VGroup(Rectangle(width=0.25, height=0.25).set_fill(WHITE, 1).set_stroke(BLUE, 1.2), txt("native: no valid run", 17, DARK)).arrange(RIGHT, buff=0.15)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.1).next_to(axis, UP, buff=2.9).shift(0.6 * RIGHT)
        self.play(FadeIn(key), run_time=0.5)
        self.caption(f"Worst stressed peak error on the twelve test buffers: {prop.min():.1f}–{prop.max():.1f} % for the proposed model, 20–100 % for native IBIS where it ran at all.", wait=3.4)
        self.clear_stage()
        # closing card
        steps = ["0  the file → target K̂u(t)", "1  fit s_up, s_dn, v_t for each candidate (K, map shape)",
                 "2  keep the stage counts within 25 % of the best residual: nine candidates",
                 "3  one stressed pad waveform: bisect v_t of each candidate on the peak",
                 "4  keep the candidate whose whole waveform is closest", "→  verified at five widths, twelve buffers"]
        g = VGroup(*[txt(s, 24, DARK if not s.startswith("→") else TEAL) for s in steps]).arrange(DOWN, aligned_edge=LEFT, buff=0.32).shift(0.3 * UP)
        self.play(*[FadeIn(m, shift=0.15 * RIGHT) for m in g], lag_ratio=0.25, run_time=2.4)
        self.wait(3.5)
        self.play(FadeOut(g), run_time=0.6)

    def construct(self):
        self.part_title()
        self.part_problem()
        self.part_model()
        self.part_target()
        self.part_fit()
        self.part_ambiguity()
        self.part_measurement()
        self.part_result()


class P1(StageLawFlow):
    def construct(self):
        self.part_problem()


class P2(StageLawFlow):
    def construct(self):
        self.part_model()


class P3(StageLawFlow):
    def construct(self):
        self.part_target()


class P4(StageLawFlow):
    def construct(self):
        self.part_fit()


class P5(StageLawFlow):
    def construct(self):
        self.part_ambiguity()


class P6(StageLawFlow):
    def construct(self):
        self.part_measurement()


class P7(StageLawFlow):
    def construct(self):
        self.part_result()
