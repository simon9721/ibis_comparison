"""Track 1 and track 2, animated in manim, from the real exported runs.

No LaTeX anywhere: every label is Text (pango), and no Axes uses include_numbers, because
numbered axes render through MathTex and this machine has no working LaTeX. Tick labels are
drawn by hand as Text.

Layout note: labels are positioned against the Axes BOUNDING BOX, never against ax.x_axis or
ax.y_axis. Manim draws those axis lines through the data origin, so on a plot whose x range
starts below zero the x-axis line sits in the middle of the data and anything placed relative
to it lands on top of the curves.

Data comes from results/method_animations_2026-09-17/method_data.npz, exported by the project
interpreter, since this environment has none of the project's readers.

    manimenv/Scripts/python.exe -m manim -qm --disable_caching \
        --media_dir <scratch>/manim_media method_scenes.py FitSearch Bisection MapBuild
"""
from pathlib import Path

import numpy as np
from manim import (
    Axes, Create, Dot, FadeIn, Scene, Text, VGroup, VMobject, ValueTracker,
    always_redraw, config, BLACK, BLUE_D, GREY_B, ORANGE, DOWN, LEFT, RIGHT, UP,
)

DATA = Path(r"C:\Users\sh3qm\code\ibis_comparison\results\method_animations_2026-09-17\method_data.npz")
D = np.load(DATA)
config.background_color = "#F6F4EE"
INK, DIM = BLACK, GREY_B


def xticks(ax, xs, fmt="%g"):
    """Tick labels under the bottom edge of the plot, not under the y=0 line."""
    out = VGroup()
    y0 = ax.y_range[0]
    for v in xs:
        t = Text(fmt % v, font_size=18, color=INK)
        t.next_to(ax.c2p(v, y0), DOWN, buff=0.14)
        out.add(t)
    return out


def yticks(ax, ys, fmt="%g"):
    """Tick labels left of the left edge of the plot, not left of the x=0 line."""
    out = VGroup()
    x0 = ax.x_range[0]
    for v in ys:
        t = Text(fmt % v, font_size=18, color=INK)
        t.next_to(ax.c2p(x0, v), LEFT, buff=0.14)
        out.add(t)
    return out


def axis_labels(ax, xtext, ytext):
    """Axis names outside everything, measured from the axes bounding box."""
    x = Text(xtext, font_size=22, color=INK).next_to(ax, DOWN, buff=0.55)
    y = Text(ytext, font_size=22, color=INK).rotate(np.pi / 2).next_to(ax, LEFT, buff=0.95)
    return VGroup(x, y)


def as_curve(ax, xs, ys, color, width=5):
    m = VMobject(color=color, stroke_width=width)
    m.set_points_as_corners([ax.c2p(x, y) for x, y in zip(xs, ys)])
    return m


class FitSearch(Scene):
    """Track 1, step 1: four numbers searched until the chain lands on one recording."""

    def construct(self):
        t, tgt = D["fit_t"], D["fit_target"]
        curves, rms, prm = D["fit_curves"], D["fit_rms"], D["fit_params"]
        head = Text("Track 1, step 1: fit four numbers to one full-swing recording",
                    font_size=30, color=INK).to_edge(UP, buff=0.3)
        ax = Axes(x_range=[-0.3, 4.0, 1.0], y_range=[-0.08, 1.16, 0.5],
                  x_length=8.8, y_length=3.9, tips=False,
                  axis_config={"color": INK, "stroke_width": 2}).shift(DOWN * 0.3 + RIGHT * 0.4)
        self.add(head, ax, xticks(ax, [0, 1, 2, 3, 4]), yticks(ax, [0.0, 0.5, 1.0]),
                 axis_labels(ax, "time from the input rising edge (ns)", "gate node, 0 to 1"))

        target = as_curve(ax, t, tgt, INK, 6)
        cap = Text("measured gate node n4 (the target)", font_size=21, color=INK)
        cap.next_to(head, DOWN, buff=0.22)
        self.play(Create(target), FadeIn(cap), run_time=1.2)

        k = ValueTracker(0.0)
        trial = always_redraw(
            lambda: as_curve(ax, t, curves[int(round(k.get_value()))], ORANGE, 5)
        )
        readout = always_redraw(lambda: Text(
            "s_up %5.2f   s_dn %5.2f\nvt %5.2f   x_lin %5.2f\nrms %.4f" % (
                prm[int(round(k.get_value()))][0], prm[int(round(k.get_value()))][1],
                prm[int(round(k.get_value()))][2], prm[int(round(k.get_value()))][3],
                rms[int(round(k.get_value()))]),
            font_size=22, color=INK, line_spacing=0.75,
        ).move_to(ax.c2p(3.0, 0.30)))
        self.add(trial, readout)
        self.play(k.animate.set_value(len(curves) - 1), run_time=6.0, rate_func=lambda a: a)
        self.wait(1.2)


class Bisection(Scene):
    """Track 1, step 2: one stressed run places the threshold."""

    def construct(self):
        t, tgt = D["bis_t"], D["bis_target"]
        curves, vts = D["bis_curves"], D["bis_vt"]
        peak = float(tgt.max())
        head = Text("Track 1, step 2: one stressed run places the threshold",
                    font_size=30, color=INK).to_edge(UP, buff=0.3)
        ax = Axes(x_range=[-0.3, 2.6, 1.0], y_range=[-0.12, 1.55, 0.5],
                  x_length=8.8, y_length=3.9, tips=False,
                  axis_config={"color": INK, "stroke_width": 2}).shift(DOWN * 0.3 + RIGHT * 0.4)
        self.add(head, ax, xticks(ax, [0, 1, 2]), yticks(ax, [0.0, 0.5, 1.0, 1.5]),
                 axis_labels(ax, "time from the input reversal (ns)", "pad (V)"))

        target = as_curve(ax, t, tgt, INK, 6)
        cap = Text("transistor, one 810 ps run: peak %.3f V" % peak, font_size=21, color=INK)
        cap.next_to(head, DOWN, buff=0.22)
        self.play(Create(target), FadeIn(cap), run_time=1.0)

        k = ValueTracker(0.0)
        tried = always_redraw(lambda: VGroup(*[
            as_curve(ax, t, curves[i], DIM, 2)
            for i in range(min(int(round(k.get_value())) + 1, len(curves)))
        ]))
        now = always_redraw(
            lambda: as_curve(ax, t, curves[int(round(k.get_value()))], ORANGE, 5)
        )
        readout = always_redraw(lambda: Text(
            "iteration %2d\nthreshold %.3f\npeak error %+5.1f %%" % (
                int(round(k.get_value())), vts[int(round(k.get_value()))],
                100.0 * (curves[int(round(k.get_value()))].max() - peak) / peak),
            font_size=22, color=INK, line_spacing=0.75,
        ).move_to(ax.c2p(1.75, 1.30)))
        self.add(tried, now, readout)
        self.play(k.animate.set_value(len(curves) - 1), run_time=5.0, rate_func=lambda a: a)
        self.wait(1.4)


class MapBuild(Scene):
    """Track 2: two fixture runs become the Ku map."""

    def construct(self):
        ts, ku, gate = D["map_t"], D["map_ku"], D["map_gate"]
        head = Text("Track 2: two extra runs become the Ku map", font_size=30, color=INK)
        head.to_edge(UP, buff=0.3)
        left = Axes(x_range=[4.9, 7.6, 1.0], y_range=[-0.15, 1.15, 0.5],
                    x_length=4.7, y_length=3.4, tips=False,
                    axis_config={"color": INK, "stroke_width": 2}).shift(LEFT * 3.4 + DOWN * 0.45)
        right = Axes(x_range=[-0.05, 1.05, 0.5], y_range=[-0.15, 1.15, 0.5],
                     x_length=4.7, y_length=3.4, tips=False,
                     axis_config={"color": INK, "stroke_width": 2}).shift(RIGHT * 3.4 + DOWN * 0.45)
        self.add(head, left, right,
                 xticks(left, [5, 6, 7]), yticks(left, [0.0, 0.5, 1.0]),
                 xticks(right, [0.0, 0.5, 1.0]), yticks(right, [0.0, 0.5, 1.0]),
                 axis_labels(left, "time (ns)", "Ku"),
                 axis_labels(right, "gate node n4, 0 to 1", "Ku"))
        self.add(Text("a. Ku solved at each instant", font_size=21, color=INK)
                 .next_to(left, UP, buff=0.3))
        self.add(Text("b. the same points against the gate", font_size=21, color=INK)
                 .next_to(right, UP, buff=0.3))

        self.play(Create(as_curve(left, ts, ku, DIM, 3)), run_time=1.2)

        k = ValueTracker(0.0)

        def idx():
            return int(round(k.get_value()))

        cursor = always_redraw(lambda: Dot(left.c2p(ts[idx()], ku[idx()]), color=ORANGE, radius=0.08))
        trail = always_redraw(
            lambda: as_curve(right, gate[:idx() + 1], ku[:idx() + 1], BLUE_D, 4)
            if idx() > 1 else VMobject()
        )
        headdot = always_redraw(lambda: Dot(right.c2p(gate[idx()], ku[idx()]), color=ORANGE, radius=0.08))
        self.add(cursor, trail, headdot)
        self.play(k.animate.set_value(len(ts) - 1), run_time=7.0, rate_func=lambda a: a)
        self.wait(1.4)
