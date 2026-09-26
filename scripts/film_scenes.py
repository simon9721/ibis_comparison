"""One continuous film: how an IBIS buffer becomes a gate-state ngspice model.

Single Scene, so manim emits a single mp4. Every beat is driven by real exported runs
(method_data.npz) except the opening schematic, which is drawn from primitives.

Teaching happens through motion, not prose: on-screen text is limited to short labels, the
act rail, and numeric readouts. Nothing here relies on an accompanying page.

No LaTeX anywhere - numbered manim axes render through MathTex and this machine has none.
Labels are positioned against the Axes BOUNDING BOX, never against ax.x_axis / ax.y_axis,
because manim draws those lines through the DATA ORIGIN, which on a plot whose range does not
start at zero sits in the middle of the data.

    manimenv/Scripts/python.exe -m manim -qm --disable_caching \
        --media_dir <scratch>/manim_media film_scenes.py Method
"""
from pathlib import Path

import numpy as np
from manim import (
    Axes, Circle, Create, Dot, FadeIn, FadeOut, Line, Rectangle, Scene, Transform,
    VGroup, VMobject, ValueTracker, always_redraw, config,
    BLACK, BLUE_D, GREY_B, ORANGE, DOWN, LEFT, ORIGIN, RIGHT, UP,
)
from manim import Text as _Text


class Text(_Text):
    """Lay out at twice the size, then halve.

    manim's Text rounds glyph advances at small sizes and collapses word spaces below about
    20 pt - "the buffer" rendered as "thebuffer", "probing gate node n4" as one word. Every
    installed font did it (Georgia, Times, Cambria, Palatino, Segoe), and neither
    disable_ligatures nor MarkupText helped; rendering at 2x and scaling back does. Captions
    at 27 pt were never affected, which is what pointed at size rounding rather than metrics.
    """

    def __init__(self, text, font_size=48, **kwargs):
        super().__init__(text, font_size=font_size * 2, **kwargs)
        self.scale(0.5)


DATA = Path(r"C:\Users\sh3qm\code\ibis_comparison\results\method_animations_2026-09-17\method_data.npz")
BGM = DATA.parent / "bgm.wav"   # a quiet generated pad, scripts/make_film_bgm.py
D = np.load(DATA)

config.background_color = "#F6F4EE"
INK = BLACK
DIM = GREY_B
HOT = ORANGE
COOL = BLUE_D
CRIMSON = "#B03060"
PLUM = "#7B4B9E"      # HSPICE's own native IBIS buffer: the industry model, "the bar"
PAPER = "#F6F4EE"

ACTS = ["the buffer", "track 1", "track 2"]


# --------------------------------------------------------------------------- helpers
def xticks(ax, xs, fmt="%g", size=18):
    """Tick labels under the BOTTOM EDGE of the plot, not under the y=0 line."""
    out = VGroup()
    y0 = ax.y_range[0]
    for v in xs:
        t = Text(fmt % v, font_size=size, color=INK)
        t.next_to(ax.c2p(v, y0), DOWN, buff=0.14)
        out.add(t)
    return out


def yticks(ax, ys, fmt="%g", size=18):
    """Tick labels left of the LEFT EDGE of the plot, not left of the x=0 line."""
    out = VGroup()
    x0 = ax.x_range[0]
    for v in ys:
        t = Text(fmt % v, font_size=size, color=INK)
        t.next_to(ax.c2p(x0, v), LEFT, buff=0.14)
        out.add(t)
    return out


def axis_labels(ax, xtext, ytext, size=21):
    """Axis names outside the ticks, measured from the axes bounding box."""
    g = VGroup()
    if xtext:
        g.add(Text(xtext, font_size=size, color=INK).next_to(ax, DOWN, buff=0.55))
    if ytext:
        g.add(Text(ytext, font_size=size, color=INK).rotate(np.pi / 2).next_to(ax, LEFT, buff=0.95))
    return g


def nice_ticks(lo, hi, n=4):
    """Rounded ticks spanning [lo, hi]. Beat 6's current axis is scaled from the IBIS
    tables rather than from a constant, so its ticks cannot be hard-coded."""
    lo, hi = float(lo), float(hi)
    span = hi - lo
    if span <= 0:
        return [lo]
    step = 10.0 ** np.floor(np.log10(span / max(n, 1)))
    for mult in (1.0, 2.0, 2.5, 5.0, 10.0):
        if span / (step * mult) <= n:
            step *= mult
            break
    first = np.ceil(lo / step) * step
    return [float(x) for x in np.arange(first, hi + step * 0.5, step)]


def curve(ax, xs, ys, color, width=5):
    m = VMobject(color=color, stroke_width=width)
    m.set_points_as_corners([ax.c2p(x, y) for x, y in zip(xs, ys)])
    return m


def box(w, h, label, size=20, color=INK, fill=PAPER, opacity=1.0):
    """VGroup whose [0] is always the rectangle; an empty label adds no Text at all,
    because Text("") is a reliable way to get a degenerate mobject out of pango."""
    r = Rectangle(width=w, height=h, color=color, stroke_width=2.5,
                  fill_color=fill, fill_opacity=opacity)
    if not label:
        return VGroup(r)
    t = Text(label, font_size=size, color=color).move_to(r)
    return VGroup(r, t)


def link(a, b, color=INK, width=2.5):
    return Line(a, b, color=color, stroke_width=width)


class Method(Scene):
    # ----------------------------------------------------------------- scaffolding
    def build_rail(self):
        """A three-segment act rail: a visual table of contents, three words total."""
        segs, labels = VGroup(), VGroup()
        w, h, gap = 2.6, 0.13, 0.25
        x0 = -(3 * w + 2 * gap) / 2
        for i, name in enumerate(ACTS):
            x = x0 + i * (w + gap) + w / 2
            bar = Rectangle(width=w, height=h, color=DIM, stroke_width=0,
                            fill_color=DIM, fill_opacity=1.0)
            bar.move_to([x, 3.72, 0])
            lab = Text(name, font_size=17, color=DIM).next_to(bar, DOWN, buff=0.13)
            segs.add(bar)
            labels.add(lab)
        self.segs, self.labels = segs, labels
        return VGroup(segs, labels)

    def act(self, i):
        """Light the current act, dim the others."""
        anims = []
        for j in range(len(ACTS)):
            on = j == i
            anims.append(self.segs[j].animate.set_fill(INK if on else DIM, 1.0))
            anims.append(self.labels[j].animate.set_color(INK if on else DIM))
        self.play(*anims, run_time=0.5)

    def caption(self, text, size=27):
        t = Text(text, font_size=size, color=INK)
        t.move_to([0, 2.95, 0])
        return t

    def subcap(self, text, size=17):
        """The bench, stated under the caption. A viewer cannot judge a black curve without
        knowing the supply, the load, the stimulus and which node is being probed."""
        t = Text(text, font_size=size, color=DIM)
        t.move_to([0, 2.50, 0])
        return t

    def wipe(self, run_time=0.5):
        """Clear updaters BEFORE fading: an always_redraw mobject re-asserts full opacity
        every frame, so FadeOut on one does nothing and it survives into the next beat."""
        keep = {self.rail}
        gone = [m for m in self.mobjects if m not in keep]
        for m in gone:
            m.clear_updaters()
        if gone:
            self.play(*[FadeOut(m) for m in gone], run_time=run_time)
            self.remove(*gone)

    # ----------------------------------------------------------------- beat 1
    def beat_buffer(self):
        """What a buffer is, and which half of it the IBIS file describes."""
        self.act(0)
        cap = self.caption("a buffer: input in, pad out")
        self.play(FadeIn(cap), run_time=0.6)

        # Geometry note: the gate wire needs real length, or the label sitting above it
        # overruns the output stage and renders as "ga". Predriver right edge -0.4,
        # output stage left edge 1.5, so the wire is 1.9 units long.
        pin = box(1.15, 0.62, "in", 19).move_to([-5.0, 0, 0])
        pre = Rectangle(width=3.6, height=1.5, color=INK, stroke_width=2.5,
                        fill_color=PAPER, fill_opacity=1.0).move_to([-2.2, 0, 0])
        pre_lab = Text("predriver", font_size=19, color=INK).next_to(pre, UP, buff=0.16)
        stages = VGroup()
        for i in range(4):
            s = box(0.6, 0.66, "", 1).move_to([-3.55 + i * 0.9, 0, 0])
            stages.add(s)
        out = box(1.9, 1.5, "output\nstage", 19).move_to([2.45, 0, 0])
        pad = Circle(radius=0.11, color=INK, stroke_width=2.5,
                     fill_color=INK, fill_opacity=1.0).move_to([4.9, 0, 0])
        pad_lab = Text("pad", font_size=19, color=INK).next_to(pad, UP, buff=0.22)

        w1 = link(pin[0].get_right(), pre.get_left())
        w2 = link(pre.get_right(), out[0].get_left())
        w3 = link(out[0].get_right(), pad.get_center())
        gate_lab = Text("gate", font_size=18, color=INK).next_to(w2, UP, buff=0.14)

        self.play(FadeIn(pin), Create(w1), run_time=0.5)
        self.play(Create(pre), FadeIn(pre_lab), run_time=0.5)
        self.play(FadeIn(stages, lag_ratio=0.25), run_time=0.9)
        self.play(Create(w2), FadeIn(gate_lab), FadeIn(out), run_time=0.7)
        self.play(Create(w3), FadeIn(pad), FadeIn(pad_lab), run_time=0.5)

        # Walk a probe along the chain and draw the REAL waveform at each node as it is
        # reached. An abstract dot travelling between boxes shows position but not shape,
        # and the shape is the whole point: the edge arrives later and softer each time.
        sch = VGroup(pin, pre, pre_lab, stages, out, pad, pad_lab, w1, w2, w3, gate_lab)
        self.play(sch.animate.shift(UP * 1.35), run_time=0.7)

        st, sv = D["stage_t"], D["stage_v"]
        names = [str(x) for x in D["stage_names"]]
        nice = {"v(in_dig)": "in", "v(xdut.n2)": "n2", "v(xdut.n3)": "n3",
                "v(xdut.n4)": "n4  the gate", "v(pad_sp)": "pad"}
        where = [pin[0].get_center(), stages[1][0].get_center(), stages[2][0].get_center(),
                 stages[3][0].get_center(), pad.get_center()]

        inset = Axes(x_range=[-0.25, 3.5, 1.0], y_range=[-0.12, 1.18, 0.5],
                     x_length=7.4, y_length=2.1, tips=False,
                     axis_config={"color": INK, "stroke_width": 2}).move_to([0.3, -2.0, 0])
        self.add(inset, xticks(inset, [0, 1, 2, 3], "%g", 15),
                 yticks(inset, [0.0, 1.0], "%g", 15),
                 axis_labels(inset, "time from the input edge (ns)", "each node, 0 to 1", 17))

        probe = Dot(where[0], color=HOT, radius=0.13)
        self.play(FadeIn(probe), run_time=0.3)
        drawn = VGroup()
        for i, nm in enumerate(names):
            tag = Text(nice.get(nm, nm), font_size=20, color=HOT)
            tag.next_to(inset, UP, buff=0.18)
            if i:
                self.play(probe.animate.move_to(where[i]),
                          drawn.animate.set_stroke(DIM, 2), run_time=0.45)
            trace = curve(inset, st, sv[i], HOT, 4)
            self.play(FadeIn(tag), Create(trace), run_time=0.85)
            drawn.add(trace)
            if i < len(names) - 1:
                self.remove(tag)
        self.wait(1.4)
        self.play(FadeOut(probe), FadeOut(drawn), FadeOut(inset),
                  sch.animate.shift(DOWN * 1.35), run_time=0.7)

        # the point of the whole method: the file describes only the right-hand half
        cap2 = self.caption("the IBIS file describes only this half")
        self.play(Transform(cap, cap2), run_time=0.6)
        # The stage boxes leave entirely rather than dimming: a "?" laid over four
        # surviving rectangles reads as clutter, not as an unknown.
        self.play(
            pre.animate.set_stroke(DIM).set_fill(PAPER, 1.0),
            pre_lab.animate.set_color(DIM),
            FadeOut(stages),
            w1.animate.set_stroke(DIM),
            pin[0].animate.set_stroke(DIM), pin[1].animate.set_color(DIM),
            out[0].animate.set_fill(PAPER, 1.0).set_stroke(INK, 4.0),
            run_time=1.0,
        )
        q = Text("?", font_size=60, color=DIM).move_to(pre.get_center())
        self.play(FadeIn(q), run_time=0.5)
        self.wait(1.2)

        # A QUESTION, not a conclusion. The next three beats answer it - asserting the answer
        # here is exactly the jump that made the opening unconvincing.
        cap3 = self.caption("is that enough?")
        self.play(Transform(cap, cap3), run_time=0.6)
        self.wait(1.4)
        self.wipe()

    # ----------------------------------------------------------------- beat 2b
    def beat_knobs(self):
        """Why FOUR numbers: each one moves the stage in a way the other three cannot.

        Every panel sweeps one number with the other three held at their fitted values, and
        the fitted curve is drawn over the fan. Shown across both edges on purpose - s_dn
        does nothing visible on the rise, which is the whole reason the fit spans the fall.
        """
        self.act(1)
        cap = self.caption("the four numbers, one at a time")
        sub = self.subcap("orange is the fitted stage  -  grey is that one number turned, the other three held")
        self.play(FadeIn(cap), FadeIn(sub), run_time=0.6)

        t = D["knob_t"]
        names = [str(x) for x in D["knob_names"]]
        # The gloss names the VISIBLE effect, not the parameter's role - that is what a viewer
        # can check against the fan in front of them.
        what = {"s_up": "how fast it rises",
                "s_dn": "how fast it falls  -  the rise does not move",
                "vt": "when it starts to move",
                "x_lin": "the shape of the knee"}
        pos = ((-3.45, 0.85), (3.45, 0.85), (-3.45, -2.25), (3.45, -2.25))
        for i, nm in enumerate(names):
            cx, cy = pos[i]
            ys = D["knob_%s_y" % nm]
            ax = Axes(x_range=[-0.4, 13.0, 4.0], y_range=[-0.12, 1.15, 0.5],
                      x_length=4.4, y_length=1.75, tips=False,
                      axis_config={"color": INK, "stroke_width": 2}).move_to([cx, cy, 0])
            self.add(ax, xticks(ax, [0, 4, 8, 12], "%g", 14), yticks(ax, [0.0, 1.0], "%g", 14))
            lab = Text("%s:  %s" % (nm, what.get(nm, "")), font_size=16, color=INK)
            lab.next_to(ax, UP, buff=0.16)
            # fitted curve first, THEN the fan: "here is the fit - now watch this one number"
            self.play(FadeIn(lab), Create(curve(ax, t, ys[2], HOT, 3.5)), run_time=0.7)
            fan = VGroup(*[curve(ax, t, ys[j], DIM, 2)
                           for j in range(len(ys)) if j != 2])
            self.play(Create(fan), run_time=1.3)
            # Bring the fitted curve back to the front. Drawn first for the narrative, it
            # otherwise sits UNDER the grey fan wherever the two share a path - on s_dn's
            # rise the orange read as a grey-orange blend.
            self.add(curve(ax, t, ys[2], HOT, 3.5))
            self.wait(0.6)
        gl = Text("time from the input edge (ns)", font_size=17, color=INK).move_to([0, -3.62, 0])
        self.play(FadeIn(gl), run_time=0.4)
        self.wait(2.4)
        self.wipe()

    # ----------------------------------------------------------------- beat 3
    def beat_fit(self):
        """Four numbers, shared by every stage, searched against one recording."""
        self.act(1)
        cap = self.caption("fit four numbers to one full-swing recording")
        sub = self.subcap("ex2 transistor  |  3.3 V  |  50 ohm and 2 pF load  |  "
                          "10 ns pulse, 50 ps edges  |  probing gate node n4")
        self.play(FadeIn(cap), FadeIn(sub), run_time=0.6)

        t, tgt = D["fit_t"], D["fit_target"]
        curves, rms, prm = D["fit_curves"], D["fit_rms"], D["fit_params"]
        ax = Axes(x_range=[-0.4, 13.0, 2.0], y_range=[-0.08, 1.16, 0.5],
                  x_length=8.6, y_length=3.6, tips=False,
                  axis_config={"color": INK, "stroke_width": 2}).shift(DOWN * 0.55 + RIGHT * 0.4)
        self.add(ax, xticks(ax, [0, 2, 4, 6, 8, 10, 12]), yticks(ax, [0.0, 0.5, 1.0]),
                 axis_labels(ax, "time from the input edge (ns)", "gate node, 0 to 1"))
        # Faint rules where the stimulus moves. The fit spans BOTH edges - the residual is
        # taken over the whole window - and the falling edge is the only thing constraining
        # s_dn, so showing only the rise would misrepresent the fit.
        for xv in D["fit_on_ns"]:
            self.add(Line(ax.c2p(float(xv), -0.08), ax.c2p(float(xv), 1.16),
                          color=DIM, stroke_width=2))

        target = curve(ax, t, tgt, INK, 6)
        self.play(Create(target), run_time=1.4)

        k = ValueTracker(0.0)

        def i():
            return int(round(k.get_value()))

        trial = always_redraw(lambda: curve(ax, t, curves[i()], HOT, 5))
        readout = always_redraw(lambda: Text(
            "s_up %5.2f   s_dn %5.2f\nvt %5.2f   x_lin %5.2f\nrms %.4f"
            % (prm[i()][0], prm[i()][1], prm[i()][2], prm[i()][3], rms[i()]),
            font_size=21, color=INK, line_spacing=0.75).move_to(ax.c2p(5.6, 0.32)))
        self.add(trial, readout)
        self.play(k.animate.set_value(len(curves) - 1), run_time=6.0, rate_func=lambda a: a)
        self.wait(1.3)
        self.wipe()

    # ----------------------------------------------------------------- beat 3b
    def beat_why_stress(self):
        """Why the fourth number needs a pulse cut short.

        Not "the full swing cannot see vt" - it can, as a timing shift (rms 0.276 between the
        extremes). But s_up shifts the timing too, so the two trade off and the full swing
        pins vt only loosely. On 810 ps the same five vt values give gate peaks of 0.81 down
        to 0.00: vt decides whether the gate moves at all. That pins it hard.
        """
        self.act(1)
        cap = self.caption("why the fourth number needs a pulse cut short")
        sub = self.subcap("gate node, 0 to 1  -  the same five values of vt on both  -  orange is the fitted value")
        self.play(FadeIn(cap), FadeIn(sub), run_time=0.6)

        tf, yf = D["knob_t"], D["knob_vt_y"]
        ts, ys = D["stress_t"], D["stress_vt_y"]
        L = Axes(x_range=[-0.4, 13.0, 4.0], y_range=[-0.1, 1.15, 0.5],
                 x_length=5.4, y_length=2.9, tips=False,
                 axis_config={"color": INK, "stroke_width": 2}).move_to([-3.45, -0.85, 0])
        R = Axes(x_range=[-0.4, 3.0, 1.0], y_range=[-0.1, 1.15, 0.5],
                 x_length=5.4, y_length=2.9, tips=False,
                 axis_config={"color": INK, "stroke_width": 2}).move_to([3.45, -0.85, 0])
        self.add(L, R, xticks(L, [0, 4, 8, 12], "%g", 15), yticks(L, [0.0, 1.0], "%g", 15),
                 xticks(R, [0, 1, 2, 3], "%g", 15), yticks(R, [0.0, 1.0], "%g", 15),
                 # no rotated y label on either: at this panel width the left one lands past
                 # the frame edge. The quantity is named in the subcaption instead.
                 axis_labels(L, "time (ns)", "", 17), axis_labels(R, "time (ns)", "", 17))
        tl = Text("full swing:  vt only shifts the timing", font_size=18, color=INK).next_to(L, UP, buff=0.25)
        tr = Text("810 ps:  vt decides how far the gate gets", font_size=18, color=INK).next_to(R, UP, buff=0.25)

        for ax, t, Y, title in ((L, tf, yf, tl), (R, ts, ys, tr)):
            self.play(FadeIn(title), Create(curve(ax, t, Y[2], HOT, 3.5)), run_time=0.7)
            fan = VGroup(*[curve(ax, t, Y[j], DIM, 2) for j in range(len(Y)) if j != 2])
            self.play(Create(fan), run_time=1.3)
            self.add(curve(ax, t, Y[2], HOT, 3.5))
            self.wait(0.5)

        pk = ys.max(axis=1)
        note = Text("peaks from %.2f down to %.2f" % (float(pk.max()), float(pk.min())),
                    font_size=17, color=INK).move_to(R.c2p(1.9, 0.95))
        self.play(FadeIn(note), run_time=0.5)
        close = Text("so: fit three on the full swing, then pin vt on the short pulse",
                     font_size=18, color=INK).move_to([0, -3.35, 0])
        self.play(FadeIn(close), run_time=0.5)
        self.wait(2.4)
        self.wipe()

    # ----------------------------------------------------------------- beat 4
    def beat_bisect(self):
        """One short pulse pins the threshold the full swing could not."""
        self.act(1)
        cap = self.caption("one stressed run places the threshold")
        sub = self.subcap("the very same bench  |  810 ps pulse instead of 10 ns  |  "
                          "probing the pad")
        self.play(FadeIn(cap), FadeIn(sub), run_time=0.6)

        t, tgt = D["bis_t"], D["bis_target"]
        curves, vts = D["bis_curves"], D["bis_vt"]
        peak = float(tgt.max())
        ax = Axes(x_range=[-0.3, 2.6, 1.0], y_range=[-0.12, 1.55, 0.5],
                  x_length=8.6, y_length=3.6, tips=False,
                  axis_config={"color": INK, "stroke_width": 2}).shift(DOWN * 0.55 + RIGHT * 0.4)
        self.add(ax, xticks(ax, [0, 1, 2]), yticks(ax, [0.0, 0.5, 1.0, 1.5]),
                 axis_labels(ax, "time from the input reversal (ns)", "pad (V)"))

        target = curve(ax, t, tgt, INK, 6)
        self.play(Create(target), run_time=1.0)
        mark = Dot(ax.c2p(t[int(np.argmax(tgt))], peak), color=INK, radius=0.075)
        peak_lab = Text("%.3f V" % peak, font_size=20, color=INK).next_to(mark, UP, buff=0.15)
        self.play(FadeIn(mark), FadeIn(peak_lab), run_time=0.6)

        k = ValueTracker(0.0)

        def i():
            return int(round(k.get_value()))

        tried = always_redraw(lambda: VGroup(*[
            curve(ax, t, curves[j], DIM, 2) for j in range(min(i() + 1, len(curves)))]))
        now = always_redraw(lambda: curve(ax, t, curves[i()], HOT, 5))
        readout = always_redraw(lambda: Text(
            "iteration %2d\nthreshold %.3f\npeak error %+5.1f %%"
            % (i(), vts[i()], 100.0 * (curves[i()].max() - peak) / peak),
            font_size=21, color=INK, line_spacing=0.75).move_to(ax.c2p(1.75, 1.30)))
        self.add(tried, now, readout)
        self.play(k.animate.set_value(len(curves) - 1), run_time=5.2, rate_func=lambda a: a)
        self.wait(1.4)
        self.wipe()


    # ----------------------------------------------------------------- beat 7
    def beat_map(self):
        """Ku against time becomes Ku against the gate: a static map."""
        self.act(2)
        cap = self.caption("tie Ku to the gate, instant by instant")
        sub = self.subcap("the gate is node n4, probed on the transistor "
                          "-  the same node from the opening")
        self.play(FadeIn(cap), FadeIn(sub), run_time=0.6)

        ts, ku, gate = D["map_t"], D["map_ku"], D["map_gate"]
        # THREE panels, not two. The two-panel version plotted Ku against "the gate" without
        # ever saying where that gate came from, which is what made track 2 opaque: it is a
        # THIRD measurement, node n4 probed on the transistor - the trace from the opening.
        A = Axes(x_range=[4.9, 7.6, 1.0], y_range=[-0.15, 1.15, 0.5],
                 x_length=3.4, y_length=2.8, tips=False,
                 axis_config={"color": INK, "stroke_width": 2}).move_to([-4.8, -0.95, 0])
        B = Axes(x_range=[4.9, 7.6, 1.0], y_range=[-0.15, 1.15, 0.5],
                 x_length=3.4, y_length=2.8, tips=False,
                 axis_config={"color": INK, "stroke_width": 2}).move_to([0.0, -0.95, 0])
        C = Axes(x_range=[-0.05, 1.05, 0.5], y_range=[-0.15, 1.15, 0.5],
                 x_length=3.4, y_length=2.8, tips=False,
                 axis_config={"color": INK, "stroke_width": 2}).move_to([4.8, -0.95, 0])
        self.add(A, B, C,
                 xticks(A, [5, 6, 7], "%g", 15), yticks(A, [0.0, 0.5, 1.0], "%g", 15),
                 xticks(B, [5, 6, 7], "%g", 15), yticks(B, [0.0, 0.5, 1.0], "%g", 15),
                 xticks(C, [0.0, 0.5, 1.0], "%g", 15), yticks(C, [0.0, 0.5, 1.0], "%g", 15),
                 # No y label on A or B. Three panels wide there is no room: A's lands at
                 # about x = -7.45 in a frame that stops at -7.11, so it renders off-screen,
                 # and shifting it in pushes B's into A. The panel titles already name the
                 # quantity, so only C - whose title does not - keeps one.
                 axis_labels(A, "time (ns)", "", 17),
                 axis_labels(B, "time (ns)", "", 17),
                 axis_labels(C, "gate, 0 to 1", "Ku", 17))
        ta = Text("a.  Ku from the fixtures", font_size=17, color=COOL).next_to(A, UP, buff=0.22)
        tb = Text("b.  the gate, on the transistor", font_size=17, color=INK).next_to(B, UP, buff=0.22)
        tc = Text("c.  one against the other", font_size=17, color=HOT).next_to(C, UP, buff=0.22)

        self.play(Create(curve(A, ts, ku, COOL, 3)), FadeIn(ta), run_time=1.1)
        self.play(Create(curve(B, ts, gate, INK, 3)), FadeIn(tb), run_time=1.1)
        self.play(FadeIn(tc), run_time=0.4)

        k = ValueTracker(0.0)

        def i():
            return int(round(k.get_value()))

        ca = always_redraw(lambda: Dot(A.c2p(ts[i()], ku[i()]), color=HOT, radius=0.075))
        cb = always_redraw(lambda: Dot(B.c2p(ts[i()], gate[i()]), color=HOT, radius=0.075))
        trail = always_redraw(
            lambda: curve(C, gate[:i() + 1], ku[:i() + 1], COOL, 4) if i() > 1 else VMobject())
        headd = always_redraw(lambda: Dot(C.c2p(gate[i()], ku[i()]), color=HOT, radius=0.075))
        self.add(ca, cb, trail, headd)
        self.play(k.animate.set_value(len(ts) - 1), run_time=6.5, rate_func=lambda a: a)
        self.wait(1.6)
        self.wipe()

    # ----------------------------------------------------------------- beat 1b
    def beat_works(self):
        """Show the file working before showing it fail - otherwise the fix has no motive."""
        self.act(0)
        cap = self.caption("on a full transition, the file alone is enough")
        sub = self.subcap("the last gate-state model, laid over the transistor, 10 ns pulse")
        self.play(FadeIn(cap), FadeIn(sub), run_time=0.6)

        t, si, mo = D["why_pt"], D["why_pad_si"], D["why_pad_mo"]
        hi = float(max(si.max(), mo.max()))
        yt = nice_ticks(0.0, hi, 4)
        ax = Axes(x_range=[-0.3, 13.2, 2.0], y_range=[-0.08 * hi, 1.22 * hi, yt[1] - yt[0]],
                  x_length=8.4, y_length=3.5, tips=False,
                  axis_config={"color": INK, "stroke_width": 2}).shift(DOWN * 0.6 + RIGHT * 0.4)
        self.add(ax, xticks(ax, [0, 2, 4, 6, 8, 10, 12]), yticks(ax, yt),
                 axis_labels(ax, "time from the input edge (ns)", "pad (V)"))
        self.play(Create(curve(ax, t, si, INK, 6)), run_time=1.6)
        l1 = Text("transistor", font_size=20, color=INK).move_to(ax.c2p(6.5, 0.46 * hi))
        self.play(FadeIn(l1), run_time=0.4)
        self.play(Create(curve(ax, t, mo, CRIMSON, 4)), run_time=1.6)
        l2 = Text("the last gate-state", font_size=20, color=CRIMSON).move_to(ax.c2p(6.5, 0.28 * hi))
        self.play(FadeIn(l2), run_time=0.4)
        # The number is the point of this beat: two curves you cannot tell apart is an
        # impression, "1 mV" is a measurement.
        note = Text("peaks agree to %.0f mV" % (abs(float(si.max()) - float(mo.max())) * 1e3),
                    font_size=20, color=INK).move_to(ax.c2p(6.5, 0.66 * hi))
        self.play(FadeIn(note), run_time=0.5)
        self.wait(2.2)
        self.wipe()

    # ----------------------------------------------------------------- beat 1c
    def beat_breaks(self):
        """The same model, the same bench, a pulse cut short - and it comes apart."""
        self.act(0)
        cap = self.caption("cut the pulse short, and it comes apart")
        sub = self.subcap("the same bench, an 810 ps pulse  -  and HSPICE's own IBIS buffer fails the same way")
        self.play(FadeIn(cap), FadeIn(sub), run_time=0.6)

        t, si = D["pay_t"], D["pay_si"]
        peak = float(si.max())
        ax = Axes(x_range=[-0.3, 2.6, 1.0], y_range=[-0.15, 1.55, 0.5],
                  x_length=8.4, y_length=3.5, tips=False,
                  axis_config={"color": INK, "stroke_width": 2}).shift(DOWN * 0.6 + RIGHT * 0.4)
        self.add(ax, xticks(ax, [0, 1, 2]), yticks(ax, [0.0, 0.5, 1.0, 1.5]),
                 axis_labels(ax, "time from the input reversal (ns)", "pad (V)"))
        self.play(Create(curve(ax, t, si, INK, 6)), run_time=1.2)
        l1 = Text("transistor", font_size=20, color=INK).move_to(ax.c2p(1.75, 1.42))
        self.play(FadeIn(l1), run_time=0.4)
        # Two models that ship, not one: HSPICE's own IBIS buffer and the pybis build. They
        # fail together, which is the point - it is the approach, not a bug in either.
        for key, col, tag, yy in (("pay_native", PLUM, "HSPICE native IBIS", 1.18),
                                  ("pay_ship", CRIMSON, "the last gate-state", 0.94)):
            if key not in D.files:
                continue
            y = D[key]
            err = 100.0 * (float(y.max()) - peak) / peak
            self.play(Create(curve(ax, t, y, col, 4)), run_time=1.2)
            lab = Text("%s   %+.1f %%" % (tag, err), font_size=20, color=col)
            lab.move_to(ax.c2p(1.75, yy))
            self.play(FadeIn(lab), run_time=0.5)
            self.wait(0.5)
        self.wait(2.2)
        self.wipe()

    # ----------------------------------------------------------------- beat 1d
    def beat_why(self):
        """The reason, on the node the viewer has already watched propagate.

        The real gate is a state: cut the pulse and it stops partway and turns round. The
        shipped model's gate is driven by a schedule, so it runs on regardless - which is
        exactly why the predriver has to be rebuilt rather than ignored.
        """
        self.act(0)
        cap = self.caption("why: the real gate never finished")
        sub = self.subcap("the gate node on both pulses, against the model's own internal gate")
        self.play(FadeIn(cap), FadeIn(sub), run_time=0.6)

        t = D["why_gt"]
        # y to 1.50 so there is a band ABOVE every trace. No gate here exceeds 1.0, so a
        # caption parked at 1.12-1.42 is guaranteed clear - hunting for gaps BETWEEN the
        # curves failed twice, because a centred caption reaches back into the decay.
        ax = Axes(x_range=[-0.2, 3.0, 1.0], y_range=[-0.08, 1.50, 0.5],
                  x_length=8.4, y_length=3.5, tips=False,
                  axis_config={"color": INK, "stroke_width": 2}).shift(DOWN * 0.6 + RIGHT * 0.4)
        self.add(ax, xticks(ax, [0, 1, 2, 3]), yticks(ax, [0.0, 0.5, 1.0]),
                 axis_labels(ax, "time from the input edge (ns)", "gate, 0 to 1"))

        self.play(Create(curve(ax, t, D["why_g_si_full"], DIM, 3)), run_time=0.9)
        lf = Text("the real gate, full pulse", font_size=19, color=DIM).move_to(ax.c2p(2.0, 1.42))
        self.play(FadeIn(lf), run_time=0.4)

        for key, col, tag, yy in (("why_g_si_short", INK, "the real gate, 810 ps", 1.27),
                                  ("why_g_mo_short", CRIMSON, "the last gate-state's gate, 810 ps", 1.12)):
            y = D[key]
            self.play(Create(curve(ax, t, y, col, 5 if col is INK else 4)), run_time=1.1)
            lab = Text("%s:  stops at %.2f" % (tag, float(y.max())), font_size=19, color=col)
            lab.move_to(ax.c2p(2.0, yy))
            self.play(FadeIn(lab), run_time=0.5)
            self.wait(0.7)
        self.wait(2.4)
        self.wipe()

    # ----------------------------------------------------------------- beat 1e
    def beat_plan(self):
        """What it would TAKE - named before any bench or solver appears.

        Going straight from the failure to a bench is a jump to solutions. Exactly two things
        are missing, and naming them here is also what defines the two tracks.
        """
        self.act(0)
        cap = self.caption("so: two things are missing")
        self.play(FadeIn(cap), run_time=0.6)

        pin = box(1.15, 0.60, "in", 18, color=DIM).move_to([-5.0, 1.30, 0])
        pre = Rectangle(width=3.6, height=1.25, color=DIM, stroke_width=2.5,
                        fill_color=PAPER, fill_opacity=1.0).move_to([-2.2, 1.30, 0])
        q = Text("?", font_size=50, color=DIM).move_to(pre.get_center())
        out = box(1.9, 1.25, "output\nstage", 18).move_to([2.45, 1.30, 0])
        pad = Circle(radius=0.10, color=INK, stroke_width=2.5,
                     fill_color=INK, fill_opacity=1.0).move_to([4.9, 1.30, 0])
        pl = Text("pad", font_size=17, color=INK).next_to(pad, UP, buff=0.16)
        w1 = link(pin[0].get_right(), pre.get_left(), DIM)
        w2 = link(pre.get_right(), out[0].get_left())
        w3 = link(out[0].get_right(), pad.get_center())
        gl = Text("gate", font_size=17, color=INK).next_to(w2, UP, buff=0.12)
        self.play(FadeIn(VGroup(pin, pre, q, out, pad, pl, w1, w2, w3, gl)), run_time=0.9)

        # Leaders run diagonally so the two captions can sit far enough apart not to collide.
        # Name the GAPS, not the solutions. "track 1 / track 2" here confused the two: the
        # tracks are what supply these, and each gets its own opening when it arrives.
        for xa, xb, col, tag, body in (
                (-2.2, -3.5, HOT, "1.  how the gate moves",
                 "for any input,\nincluding one cut short"),
                (2.45, 3.5, COOL, "2.  how the pad follows it",
                 "wherever the gate happens\nto be at that instant")):
            tip = Line([xa, 0.62, 0], [xb, -0.28, 0], color=col, stroke_width=3)
            name = Text(tag, font_size=22, color=col).move_to([xb, -0.62, 0])
            txt = Text(body, font_size=18, color=INK, line_spacing=0.8).move_to([xb, -1.45, 0])
            self.play(Create(tip), FadeIn(name), run_time=0.45)
            self.play(FadeIn(txt), run_time=0.6)
            self.wait(0.9)
        self.wait(2.2)
        self.wipe()

    # ----------------------------------------------------------------- beat 1e2
    def beat_gatestate(self):
        """The idea behind the whole method, as architecture: carry a state, not a clock.

        What ships replays a table indexed by elapsed time; the gate-state model carries a
        node that moves, and reads Ku off where that node IS. Cut the pulse and the clock runs
        on regardless, while the gate turns round from wherever it has got to.
        """
        self.act(0)
        cap = self.caption("two ways to build the missing half")
        sub = self.subcap("replay a schedule  -  or carry a state")
        self.play(FadeIn(cap), FadeIn(sub), run_time=0.6)

        # The right column is the LAST method, not this one: pybis as it shipped already
        # carried a gate node and read Ku off a map of it - the right idea. Its flaw was
        # upstream: that node was driven by a fixed delay and a fixed ramp, i.e. still a
        # clock, so it ran on when the pulse was cut short. This method keeps the node and
        # changes what drives it, which is what the closing line hands to track 1.
        cols = (
            (-3.4, PLUM, "replay  -  HSPICE native",
             [("the input edge", INK),
              ("elapsed time since the edge   (a clock)", PLUM),
              ("Ku looked up in a table, by time", INK),
              ("pad", INK)]),
            (3.4, CRIMSON, "gate-state  -  the last method",
             [("the input", INK),
              ("a fixed delay and a fixed ramp  -  a clock", CRIMSON),
              ("the gate: a node that moves, 0 to 1", HOT),
              ("Ku read off a map, by where the gate is", INK),
              ("pad", INK)]),
        )
        for cx, col, title, steps in cols:
            self.play(FadeIn(Text(title, font_size=19, color=col).move_to([cx, 1.9, 0])), run_time=0.4)
            prev = None
            for k, (s, sc) in enumerate(steps):
                b = box(5.2, 0.52, s, 16, color=sc)
                b.move_to([cx, 1.28 - k * 0.76, 0])
                anims = [FadeIn(b)]
                if prev is not None:
                    anims.append(Create(link(prev.get_bottom(), b[0].get_top(), INK, 2)))
                self.play(*anims, run_time=0.38)
                prev = b[0]
            self.wait(0.4)

        pl = Text("cut the pulse short:  the clock runs on regardless", font_size=17, color=PLUM)
        pr = Text("the right idea  -  but its gate was still a clock, so it ran on too", font_size=17, color=CRIMSON)
        pl.move_to([-3.4, -2.72, 0])
        pr.move_to([3.4, -2.72, 0])
        self.play(FadeIn(pl), FadeIn(pr), run_time=0.6)
        self.wait(1.0)
        close = Text("this method keeps the gate node  -  and drives it with a chain of stages fitted to the real gate",
                     font_size=17, color=HOT).move_to([0, -3.4, 0])
        self.play(FadeIn(close), run_time=0.5)
        self.wait(2.4)
        self.wipe()

    # ----------------------------------------------------------------- track 1 opening
    def beat_t1_open(self):
        """Track 1's motivation and method at a glance, before any bench or solver.

        The gap is "how the gate moves". The stand-in is a chain of identical stages, each
        obeying one law with four numbers; the next four beats record, explain, fit, place.
        """
        self.act(1)
        cap = self.caption("track 1: rebuild how the gate moves")
        sub = self.subcap("a compact stand-in for the predriver, fitted to the real gate")
        self.play(FadeIn(cap), FadeIn(sub), run_time=0.6)

        pin = box(1.15, 0.60, "in", 18, color=DIM).move_to([-5.0, 1.55, 0])
        pre = Rectangle(width=3.6, height=1.25, color=DIM, stroke_width=2.5,
                        fill_color=PAPER, fill_opacity=1.0).move_to([-2.2, 1.55, 0])
        q = Text("?", font_size=50, color=DIM).move_to(pre.get_center())
        out = box(1.9, 1.25, "output\nstage", 18, color=DIM).move_to([2.45, 1.55, 0])
        pad = Circle(radius=0.10, color=DIM, stroke_width=2.5,
                     fill_color=DIM, fill_opacity=1.0).move_to([4.9, 1.55, 0])
        w1 = link(pin[0].get_right(), pre.get_left(), DIM)
        w2 = link(pre.get_right(), out[0].get_left(), DIM)
        w3 = link(out[0].get_right(), pad.get_center(), DIM)
        gl = Text("gate", font_size=17, color=INK).next_to(w2, UP, buff=0.12)
        self.play(FadeIn(VGroup(pin, pre, q, out, pad, w1, w2, w3, gl)), run_time=0.7)

        # the ? becomes a chain of identical stages
        stages = VGroup(*[box(0.82, 0.72, "stage", 15, color=HOT).move_to([-3.1 + i * 0.9, 1.55, 0])
                          for i in range(3)])
        self.play(FadeOut(q), pre.animate.set_stroke(HOT), FadeIn(stages, lag_ratio=0.3),
                  run_time=0.9)
        t1 = Text("a chain of identical stages", font_size=19, color=HOT).next_to(pre, DOWN, buff=0.22)
        self.play(FadeIn(t1), run_time=0.4)
        self.wait(0.6)

        law = Text("each stage charges toward its input, at a limited rate  -  four numbers set how",
                   font_size=19, color=INK).move_to([0, -0.15, 0])
        self.play(FadeIn(law), run_time=0.5)
        knobs = (("s_up", "how hard it pulls up"), ("s_dn", "how hard it pulls down"),
                 ("vt", "where it starts to respond"), ("x_lin", "how much of the swing is resistive"))
        for j, (nm, gloss) in enumerate(knobs):
            r = Text("%s     %s" % (nm, gloss), font_size=18, color=INK).move_to([0, -0.85 - j * 0.42, 0])
            self.play(FadeIn(r), run_time=0.35)
        self.wait(0.7)
        road = Text("record the real gate   >   see what each number does   >   fit three of them   >"
                    "   place the fourth", font_size=16, color=DIM).move_to([0, -3.15, 0])
        self.play(FadeIn(road), run_time=0.5)
        self.wait(2.4)
        self.wipe()

    # ----------------------------------------------------------------- track 1 result
    def beat_t1_result(self):
        """Track 1's own result, and what is not good enough about it.

        Calibrated at 810 ps, so that column proves nothing; the other four widths are the
        test, and there it runs 5-9 % low - while tracking the GATE well (0.74 against 0.76).
        The gate's motion is right; the map from gate to pad is still the file's guess.
        """
        self.act(1)
        cap = self.caption("track 1's result")
        sub = self.subcap("the threshold was placed at 810 ps  -  so 895 ps, which it never saw, is the test")
        self.play(FadeIn(cap), FadeIn(sub), run_time=0.6)

        self.result_panels([("t1", HOT, "track 1")])
        gate = D["t1_file_gate"]
        g_note = Text("and the gate itself is tracked well:  %.2f against the real %.2f at 810 ps"
                      % (gate[-1][0], gate[-1][1]), font_size=17, color=INK).move_to([0, -3.45, 0])
        self.play(FadeIn(g_note), run_time=0.5)
        self.wait(0.9)
        cap2 = self.caption("the gate's motion is right  -  the map from gate to pad is still the file's guess")
        self.play(Transform(cap, cap2), run_time=0.6)
        self.wait(2.4)
        self.wipe()

    def result_panels(self, rows):
        """Two pulse widths side by side, each model in `rows` drawn over the transistor.

        Shared by track 1's result and the payoff so the two beats are a direct comparison:
        same panels, same widths, same layout - track 1 alone, then everything. 810 ps is
        where the threshold was placed; 895 ps was never calibrated.
        """
        for cx, w, title in ((-3.3, 810, "810 ps  -  where the threshold was placed"),
                             (3.3, 895, "895 ps  -  never calibrated")):
            t, si = D["rw_t_%d" % w], D["rw_si_%d" % w]
            peak = float(si.max())
            ax = Axes(x_range=[-0.3, 2.6, 1.0], y_range=[-0.15, 1.55, 0.5],
                      x_length=5.0, y_length=3.0, tips=False,
                      axis_config={"color": INK, "stroke_width": 2}).move_to([cx, -0.75, 0])
            self.add(ax, xticks(ax, [0, 1, 2], "%g", 15), yticks(ax, [0.0, 0.5, 1.0, 1.5], "%g", 15),
                     axis_labels(ax, "time from the reversal (ns)", "pad (V)" if cx < 0 else "", 17))
            ttl = Text(title, font_size=18, color=INK).next_to(ax, UP, buff=0.25)
            self.play(FadeIn(ttl), Create(curve(ax, t, si, INK, 5)), run_time=1.0)
            yy = 1.42
            self.play(FadeIn(Text("transistor", font_size=17, color=INK).move_to(ax.c2p(1.75, yy))),
                      run_time=0.3)
            for suf, col, tag in rows:
                key = "rw_%s_%d" % (suf, w)
                if key not in D.files:
                    continue
                yy -= 0.19
                y = D[key]
                err = 100.0 * (float(y.max()) - peak) / peak
                self.play(Create(curve(ax, t, y, col, 4)), run_time=0.9)
                self.play(FadeIn(Text("%s   %+.1f %%" % (tag, err), font_size=17, color=col)
                                 .move_to(ax.c2p(1.75, yy))), run_time=0.35)
            self.wait(0.4)

    # ----------------------------------------------------------------- track 2 opening
    def beat_t2_open(self):
        """Track 2's motivation and method at a glance.

        The gap is "how the pad follows the gate". The output stage has no memory of its own,
        so Ku against the gate is a curve; the file implies one, the transistor can be asked
        directly. The standard two-fixture Ku/Kd extraction is assumed known and not re-derived.
        """
        self.act(2)
        cap = self.caption("track 2: measure how the pad follows the gate")
        sub = self.subcap("the file implies one curve  -  the transistor can be asked directly")
        self.play(FadeIn(cap), FadeIn(sub), run_time=0.6)

        out = box(2.6, 1.5, "", 18).move_to([0, 1.35, 0])
        inside = Text("Ku,  Kd", font_size=24, color=COOL).move_to(out[0].get_center())
        wg = link([-3.3, 1.35, 0], out[0].get_left())
        gl = Text("gate", font_size=18, color=INK).next_to(wg, UP, buff=0.12)
        wp = link(out[0].get_right(), [3.3, 1.35, 0])
        pl = Text("pad", font_size=18, color=INK).next_to(wp, UP, buff=0.12)
        self.play(FadeIn(VGroup(out, inside, wg, gl, wp, pl)), run_time=0.8)
        t1 = Text("the output stage has no memory of its own  -  it only follows where the gate is",
                  font_size=19, color=INK).move_to([0, 0.2, 0])
        self.play(FadeIn(t1), run_time=0.5)
        self.wait(0.5)

        ax = Axes(x_range=[-0.05, 1.05, 0.5], y_range=[-0.15, 1.15, 0.5],
                  x_length=3.6, y_length=2.0, tips=False,
                  axis_config={"color": INK, "stroke_width": 2}).move_to([-2.7, -1.95, 0])
        self.add(ax, xticks(ax, [0, 1], "%g", 14), yticks(ax, [0, 1], "%g", 14),
                 axis_labels(ax, "gate", "Ku", 16))
        self.play(Create(curve(ax, D["cmp_g"], D["cmp_prior"], CRIMSON, 3)), run_time=0.9)
        lf = Text("the file's map, as track 1 used it", font_size=17, color=CRIMSON).next_to(ax, UP, buff=0.2)
        qm = Text("?", font_size=52, color=CRIMSON).move_to(ax.c2p(0.32, 0.72))
        self.play(FadeIn(lf), FadeIn(qm), run_time=0.5)

        road = Text("Ku over time, from the standard two-fixture extraction\n"
                    "the gate over time, probed on the transistor\n"
                    "one against the other  -  a map\n"
                    "then put that map into the model",
                    font_size=18, color=INK, line_spacing=0.9).move_to([2.6, -1.95, 0])
        self.play(FadeIn(road), run_time=0.7)
        self.wait(2.6)
        self.wipe()

    # ----------------------------------------------------------------- beat 1f
    def beat_bench(self):
        """The bench, drawn once. Beats 3 and 4 use THIS bench and differ only in stimulus.

        A black curve is unreadable without the supply, the load, the stimulus and the probed
        node, so all four are established here rather than asserted later.
        """
        self.act(1)
        cap = self.caption("first: record the real gate")
        sub = self.subcap("one bench, one stimulus  -  probing node n4 on the transistor buffer")
        self.play(FadeIn(cap), FadeIn(sub), run_time=0.6)

        drv = box(1.9, 1.2, "ex2", 20).move_to([-4.8, 0.5, 0])
        vdd = Text("3.3 V", font_size=18, color=INK).next_to(drv, UP, buff=0.18)
        win = link([-6.75, 0.5, 0], drv[0].get_left())
        ilab = Text("in", font_size=18, color=INK).next_to(win, UP, buff=0.10)
        wout = link(drv[0].get_right(), [-1.2, 0.5, 0])
        padn = Dot([-3.0, 0.5, 0], color=INK, radius=0.075)
        plab = Text("pad", font_size=18, color=INK).next_to(padn, UP, buff=0.16)

        rb = link([-2.2, 0.5, 0], [-2.2, 0.05, 0])
        rr = Rectangle(width=0.40, height=0.85, color=INK, stroke_width=2.5,
                       fill_color=PAPER, fill_opacity=1.0).move_to([-2.2, -0.38, 0])
        rl = Text("50 ohm", font_size=16, color=INK).next_to(rr, LEFT, buff=0.14)
        rb2 = link([-2.2, -0.80, 0], [-2.2, -1.35, 0])

        cb = link([-1.2, 0.5, 0], [-1.2, -0.25, 0])
        cp1 = Line([-1.52, -0.25, 0], [-0.88, -0.25, 0], color=INK, stroke_width=3)
        cp2 = Line([-1.52, -0.47, 0], [-0.88, -0.47, 0], color=INK, stroke_width=3)
        cl_ = Text("2 pF", font_size=16, color=INK).next_to(cp1, RIGHT, buff=0.16)
        cb2 = link([-1.2, -0.47, 0], [-1.2, -1.35, 0])

        gnd = VGroup(Line([-2.7, -1.35, 0], [-0.7, -1.35, 0], color=INK, stroke_width=2.5),
                     Line([-2.42, -1.52, 0], [-0.98, -1.52, 0], color=INK, stroke_width=2.5),
                     Line([-2.14, -1.69, 0], [-1.26, -1.69, 0], color=INK, stroke_width=2.5))
        self.play(FadeIn(VGroup(drv, vdd, win, ilab, wout, padn, plab)), run_time=0.8)
        self.play(FadeIn(VGroup(rb, rr, rl, rb2, cb, cp1, cp2, cl_, cb2, gnd)), run_time=0.8)

        def pulse(w):
            return (np.array([4.0, 5.0, 5.05, 5.0 + w, 5.05 + w, 17.0]),
                    np.array([0.0, 0.0, 1.0, 1.0, 0.0, 0.0]))

        # Only the full-swing stimulus here. The 810 ps run has no motive at this point - it
        # arrives with the threshold, once the fit has shown what a full swing cannot pin.
        ax = Axes(x_range=[4.0, 17.0, 4.0], y_range=[-0.15, 1.3, 1.0],
                  x_length=5.2, y_length=1.3, tips=False,
                  axis_config={"color": INK, "stroke_width": 2}).move_to([3.5, 0.0, 0])
        self.add(ax, xticks(ax, [4, 8, 12, 16], "%g", 14))
        lab = Text("one 10 ns pulse  -  the full swing", font_size=18, color=INK).next_to(ax, UP, buff=0.2)
        xs, ys = pulse(10.0)
        self.play(FadeIn(lab), Create(curve(ax, xs, ys, INK, 4)), run_time=1.0)
        tl = Text("time (ns), 50 ps edges", font_size=17, color=INK).move_to([3.5, -1.15, 0])
        self.play(FadeIn(tl), run_time=0.4)
        self.wait(2.2)
        self.wipe()


    # ----------------------------------------------------------------- beat 7b
    def beat_four_maps(self):
        """Not one map: the solve yields Ku AND Kd, each split into an on and an off branch.

        Blue is Ku and crimson is Kd throughout, matching beat 6 where blue was the pull-up
        table and crimson the pull-down - which is precisely what Ku and Kd scale.
        """
        self.act(2)
        cap = self.caption("the same solve gives four maps, not one")
        self.play(FadeIn(cap), run_time=0.6)

        panels = (("ku_rise", "Ku, gate rising", COOL, -3.45, 0.85),
                  ("ku_fall", "Ku, gate falling", COOL, 3.45, 0.85),
                  ("kd_on", "Kd, turning on", CRIMSON, -3.45, -2.25),
                  ("kd_off", "Kd, turning off", CRIMSON, 3.45, -2.25))
        for key, title, col, cx, cy in panels:
            g, v = D["map4_%s_g" % key], D["map4_%s_v" % key]
            ax = Axes(x_range=[-0.05, 1.05, 0.5], y_range=[-0.18, 1.18, 0.5],
                      x_length=4.4, y_length=1.75, tips=False,
                      axis_config={"color": INK, "stroke_width": 2}).move_to([cx, cy, 0])
            self.add(ax, xticks(ax, [0.0, 0.5, 1.0], "%g", 15),
                     yticks(ax, [0.0, 1.0], "%g", 15))
            lab = Text(title, font_size=18, color=col).next_to(ax, UP, buff=0.18)
            self.play(FadeIn(lab), Create(curve(ax, g, v, col, 4)), run_time=0.9)
        # One shared x label would be wrong: the Kd maps are indexed by GDN = 1 - gate,
        # not by the gate, so each row gets its own.
        gu = Text("gate node, 0 to 1", font_size=17, color=COOL).move_to([0, -0.55, 0])
        gd = Text("GDN = 1 - gate", font_size=17, color=CRIMSON).move_to([0, -3.62, 0])
        self.play(FadeIn(gu), FadeIn(gd), run_time=0.5)
        self.wait(2.2)
        self.wipe()

    # ----------------------------------------------------------------- beat 8
    def beat_compare(self):
        """The measured map against the curve the file alone implies."""
        self.act(2)
        cap = self.caption("the measured map, against the one the file implies")
        self.play(FadeIn(cap), run_time=0.6)

        g, meas, prior = D["cmp_g"], D["cmp_meas"], D["cmp_prior"]
        ax = Axes(x_range=[-0.05, 1.05, 0.5], y_range=[-0.15, 1.15, 0.5],
                  x_length=7.0, y_length=3.9, tips=False,
                  axis_config={"color": INK, "stroke_width": 2}).shift(DOWN * 0.55)
        self.add(ax, xticks(ax, [0.0, 0.5, 1.0]), yticks(ax, [0.0, 0.5, 1.0]),
                 axis_labels(ax, "gate node, 0 to 1", "Ku"))
        cp = curve(ax, g, prior, CRIMSON, 4)
        cm = curve(ax, g, meas, COOL, 5)
        # Stacked in the plot's top-left, which is reliably empty: both maps sit near zero
        # at low gate. Anchored to a curve's own y instead, a caption floats unattached
        # wherever the two curves happen to be close.
        lm = Text("measured  (track 2)", font_size=19, color=COOL).move_to(ax.c2p(0.30, 1.02))
        lp = Text("the file's map, as track 1 used it", font_size=19, color=CRIMSON).move_to(ax.c2p(0.30, 0.84))
        self.play(Create(cp), run_time=1.1)
        self.play(FadeIn(lp), run_time=0.4)
        self.play(Create(cm), run_time=1.3)
        self.play(FadeIn(lm), run_time=0.4)
        self.wait(2.0)
        self.wipe()

    # ----------------------------------------------------------------- beat 8b
    def beat_mapgain(self):
        """Then what: put the measured map into the model, and see what it is worth.

        This pair replays the same measured gate and differs in nothing but the maps, so the
        gap between the two lines IS the map's contribution.
        """
        self.act(2)
        cap = self.caption("so: put the measured map into the model")
        sub = self.subcap("the same replayed gate in both - only the Ku and Kd maps differ")
        self.play(FadeIn(cap), FadeIn(sub), run_time=0.6)

        w = D["gain_w"]
        n = len(w)
        # x starts at -0.15, not -0.4: manim draws the y axis at x=0, and tick labels placed
        # at the range edge were left floating well clear of the line they label.
        ax = Axes(x_range=[-0.15, n - 0.85, 1.0], y_range=[-8.0, 3.5, 2.0],
                  x_length=7.6, y_length=3.6, tips=False,
                  axis_config={"color": INK, "stroke_width": 2}).shift(DOWN * 0.6 + RIGHT * 0.5)
        self.add(ax, yticks(ax, [-8, -6, -4, -2, 0, 2]),
                 axis_labels(ax, "pulse width (ps), more stressed to the right", "peak error (%)"))
        for i in range(n):
            self.add(Text("%d" % int(w[i]), font_size=17, color=INK)
                     .next_to(ax.c2p(i, -8.0), DOWN, buff=0.14))
        self.add(Line(ax.c2p(-0.15, 0.0), ax.c2p(n - 0.85, 0.0), color=DIM, stroke_width=2))

        xs = np.arange(n, dtype=float)
        for key, col, tag, yy in (("gain_ibis", CRIMSON, "the file's maps  (track 1)", -6.6),
                                  ("gain_meas", COOL, "measured maps  (track 2)", 2.4)):
            if key not in D.files:
                continue
            y = D[key]
            self.play(Create(curve(ax, xs, y, col, 4)), run_time=1.1)
            self.play(*[FadeIn(Dot(ax.c2p(xs[i], y[i]), color=col, radius=0.075))
                        for i in range(n)], run_time=0.4)
            lab = Text(tag, font_size=19, color=col).move_to(ax.c2p(1.5, yy))
            self.play(FadeIn(lab), run_time=0.45)
            self.wait(0.6)
        self.wait(2.0)
        self.wipe()

    # ----------------------------------------------------------------- beat 9
    def beat_payoff(self):
        """What it was all for: the stressed pulse, against the model that ships today."""
        self.act(2)
        cap = self.caption("both tracks together, on the same two pulses")
        sub = self.subcap("the same panels as track 1's result  -  now with the measured maps in")
        self.play(FadeIn(cap), FadeIn(sub), run_time=0.6)
        self.result_panels([("ship", CRIMSON, "last gate-state"), ("meas", HOT, "this method")])
        self.wait(2.6)
        self.wipe()

    # ----------------------------------------------------------------- run order
    def construct(self):
        if BGM.is_file():
            self.add_sound(str(BGM))
        self.rail = self.build_rail()
        self.add(self.rail)
        self.beat_buffer()      # 1  the buffer, with the real waveform propagating through it
        self.beat_works()       # 1b the file works on a full transition
        self.beat_breaks()      # 1c and comes apart on a short one
        self.beat_why()         # 1d WHY: the real gate stopped partway; the model's did not
        self.beat_plan()        # 1e the two GAPS, named - not the tracks
        self.beat_gatestate()   # 1f replay a schedule, or carry a state
        self.beat_t1_open()     # T1 track 1: why, and how, at a glance
        self.beat_bench()       #    record the real gate
        self.beat_knobs()       #    the four numbers, one at a time
        self.beat_fit()         #    fit them on the full swing
        self.beat_why_stress()  #    why vt needs a pulse cut short
        self.beat_bisect()      #    place vt on the short pulse
        self.beat_t1_result()   #    track 1's result, and what is not good enough
        self.beat_t2_open()     # T2 track 2: why, and how, at a glance
        self.beat_map()         #    Ku and the gate, one against the other
        self.beat_four_maps()   # 7b Ku and Kd, on and off - four maps, not one
        self.beat_compare()     # 8  measured against the file's own curve
        self.beat_mapgain()     # 8b then what: swap the map in, across five widths
        self.beat_payoff()      # 9  what it was all for
        self.wait(0.8)
