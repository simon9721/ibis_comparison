"""Animation: how Ku(t) and Kd(t) are extracted from a transistor buffer.

Built on the real numbers in results/kukd_animation/data.json -- the two fixture
waveforms actually simulated for inv_chain, and the same 2x2 solve the study
runs. Nothing here is illustrative-only.

There is no LaTeX on this machine, so every equation is Text with unicode
rather than MathTex, which manim cannot render without a TeX install.

    py -3.13 -m manim -qh scripts/animate_kukd_extraction.py KuKdExtraction
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from manim import (
    Arrow, Axes, Create, DOWN, Dot, FadeIn, FadeOut, LEFT, Line, RIGHT, Rectangle,
    Scene, Text, UP, VGroup, ValueTracker, Write, always_redraw, config,
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


def small(s, size=22, color=INK, weight=None):
    if weight:
        return Text(s, font_size=size, color=color, weight=weight)
    return Text(s, font_size=size, color=color)


class KuKdExtraction(Scene):
    def construct(self):
        self.act1_problem()
        self.act2_one_fixture()
        self.act3_two_fixtures()
        self.act4_one_instant()
        self.act5_sweep()

    def act1_problem(self):
        title = Text("How Ku(t) and Kd(t) are extracted", font_size=44, color=INK, weight="BOLD")
        sub = small("the transistor has no Ku or Kd - they are derived", 24, FAINT)
        sub.next_to(title, DOWN, buff=0.35)
        self.play(Write(title), run_time=1.4)
        self.play(FadeIn(sub, shift=UP * 0.2), run_time=0.8)
        self.wait(1.0)
        self.play(FadeOut(sub), title.animate.scale(0.55).to_edge(UP, buff=0.4), run_time=0.9)

        eq = VGroup(
            small("I_pad  =  ", 30),
            small("Ku", 30, KU_C),
            small(" x I_pullup(V)   +   ", 30),
            small("Kd", 30, KD_C),
            small(" x I_pulldown(V)   +   clamps   +   C_comp x dV/dt", 30),
        ).arrange(RIGHT, buff=0.05)
        eq.scale(0.78).move_to([0, 0.6, 0])
        self.play(Write(eq), run_time=2.2)
        self.wait(0.6)

        note = small("everything but Ku and Kd is known: the I-V tables and C_comp come from the IBIS file",
                     22, FAINT)
        note.next_to(eq, DOWN, buff=0.7)
        self.play(FadeIn(note), run_time=0.8)
        self.wait(1.8)
        self.play(FadeOut(note), FadeOut(eq), FadeOut(title), run_time=0.7)

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
        self.play(VGroup(self.ax_pad, self.graph_lo, self.graph_hi).animate
                  .scale(0.9).move_to([-3.55, 0.75, 0]), run_time=0.9)

    def act4_one_instant(self):
        s = DATA["snapshot"]
        head = small("At one instant, both equations are just numbers", 30, INK, "BOLD")
        head.to_edge(UP, buff=0.45)
        self.play(Write(head), run_time=1.0)

        x = s["t_ns"]
        ax = self.ax_pad[0]
        cursor = Line(ax.c2p(x, -0.15), ax.c2p(x, 1.55), color=INK, stroke_width=3)
        cursor.set_opacity(0.85)
        d_lo = Dot(ax.c2p(x, s["v_lo"]), color=LOW_C, radius=0.07)
        d_hi = Dot(ax.c2p(x, s["v_hi"]), color=HIGH_C, radius=0.07)
        self.play(Create(cursor), run_time=0.7)
        self.play(FadeIn(d_lo), FadeIn(d_hi), run_time=0.5)

        read = VGroup(
            small("t = %.3f ns" % x, 22, INK),
            small("V = %.3f V" % s["v_lo"], 22, LOW_C),
            small("V = %.3f V" % s["v_hi"], 22, HIGH_C),
        ).arrange(DOWN, buff=0.14, aligned_edge=LEFT)
        read.next_to(self.ax_pad, DOWN, buff=0.45)
        self.play(FadeIn(read), run_time=0.6)
        self.wait(0.8)

        rows = VGroup(
            self.eq_row(s["pu_lo"], s["pd_lo"], s["rhs_lo"], LOW_C),
            self.eq_row(s["pu_hi"], s["pd_hi"], s["rhs_hi"], HIGH_C),
        ).arrange(DOWN, buff=0.5, aligned_edge=LEFT)
        rows.move_to([2.9, 1.4, 0])
        self.play(Write(rows[0]), run_time=1.5)
        self.play(Write(rows[1]), run_time=1.5)
        self.wait(1.0)

        note = small("two linear equations, two unknowns", 22, FAINT)
        note.next_to(rows, DOWN, buff=0.45)
        self.play(FadeIn(note), run_time=0.6)

        ans = VGroup(
            small("Ku = %.3f" % s["ku"], 34, KU_C, "BOLD"),
            small("Kd = %.3f" % s["kd"], 34, KD_C, "BOLD"),
        ).arrange(RIGHT, buff=0.9)
        ans.next_to(note, DOWN, buff=0.5)
        self.play(FadeIn(ans, shift=UP * 0.25), run_time=1.0)
        self.wait(2.2)

        self.play(FadeOut(rows), FadeOut(note), FadeOut(read), FadeOut(head),
                  FadeOut(d_lo), FadeOut(d_hi), FadeOut(cursor), FadeOut(ans), run_time=0.8)

    def act5_sweep(self):
        head = small("Repeat at every timestep", 30, INK, "BOLD")
        head.to_edge(UP, buff=0.45)
        self.play(Write(head), run_time=0.9)
        self.play(VGroup(self.ax_pad, self.graph_lo, self.graph_hi).animate
                  .scale(0.86).move_to([0, 1.45, 0]), run_time=0.8)

        kax = self.k_axes()
        kax.move_to([0, -1.95, 0])
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
            pad_ax.c2p(tracker.get_value(), -0.15),
            pad_ax.c2p(tracker.get_value(), 1.55),
            color=INK, stroke_width=2.5).set_opacity(0.55))
        self.add(gku, gkd, bar)

        lab = VGroup(small("Ku(t)", 24, KU_C), small("Kd(t)", 24, KD_C)).arrange(RIGHT, buff=0.7)
        lab.next_to(kax, UP, buff=0.1)
        self.play(FadeIn(lab), run_time=0.5)

        self.play(tracker.animate.set_value(float(t[-1])), run_time=5.5)
        self.wait(0.6)

        closing = small("the coefficients silicon actually requires", 26, GOLD)
        closing.next_to(kax, DOWN, buff=0.45)
        self.play(FadeIn(closing), run_time=0.8)
        self.wait(2.2)

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
        ax = Axes(x_range=[4.85, 5.85, 0.25], y_range=[-0.15, 1.55, 0.5],
                  x_length=6.2, y_length=3.1,
                  axis_config={"color": FAINT, "stroke_width": 2, "font_size": 16},
                  x_axis_config={"include_numbers": True, "label_constructor": Text, "decimal_number_config": {"num_decimal_places": 1}},
                  y_axis_config={"include_numbers": True, "label_constructor": Text, "decimal_number_config": {"num_decimal_places": 1}},
                  tips=False)
        xl = small("time (ns)", 18, FAINT).next_to(ax, DOWN, buff=0.2)
        yl = small("pad (V)", 18, FAINT).rotate(np.pi / 2).next_to(ax, LEFT, buff=0.2)
        return VGroup(ax, xl, yl)

    def k_axes(self):
        return Axes(x_range=[4.85, 5.85, 0.25], y_range=[-0.35, 1.35, 0.5],
                    x_length=9.0, y_length=2.5,
                    axis_config={"color": FAINT, "stroke_width": 2, "font_size": 16},
                    x_axis_config={"include_numbers": True, "label_constructor": Text, "decimal_number_config": {"num_decimal_places": 1}},
                    y_axis_config={"include_numbers": True, "label_constructor": Text, "decimal_number_config": {"num_decimal_places": 1}},
                    tips=False)

    def eq_row(self, pu, pd, rhs, colour):
        return VGroup(
            small("%+.4f" % pu, 23, colour),
            small("x", 23, FAINT),
            small("Ku", 23, KU_C),
            small("%+.4f" % pd, 23, colour),
            small("x", 23, FAINT),
            small("Kd", 23, KD_C),
            small("= %+.4f A" % rhs, 23, colour),
        ).arrange(RIGHT, buff=0.17)
