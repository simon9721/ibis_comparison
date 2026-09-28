# What in the stage law has a source, and what does not

**Question.** An outside review of the track-1 write-up said the stage law is "a physically
motivated reduced-order model, not one uniquely derived from CMOS device physics", and that
several claims were stated more strongly than the physics justifies. Which of its specific
technical objections hold up against our own fits and model card?

**Answer: all of the numerical ones, and two of them by a wider margin than the review knew.**

Run each script from the repo root with `py -3.14`.

## 1. `x_lin` is not the textbook saturation/triode boundary  (`check_xlin.py`)

A real device leaves saturation at `V_DS = V_GS - V_th`, so at full gate drive the resistive region
occupies `1 - V_th/V_DD` of the swing. Using `VTH0` from `buffers/models/hspice.mod`:

| | a real device | our model |
|---|---|---|
| 1.8 V parts | 0.77 (NMOS) / 0.80 (PMOS) | **0.45** |
| 3.3 V parts | 0.88 (NMOS) / 0.89 (PMOS) | **0.45** |

## 2. `x_lin` is not even fitted  (`check_xlin_fitted.py`)

`settings()` hands the fitter `x_lin_fixed = 0.45` on every pass that produces a shipped
number. Across all `step1` fit rows: **360 of ~390 have x_lin = 0.45 exactly**. In the one pass
where it is left free (`as_track1`, inv_chain) it lands anywhere between **0.02 and 1.50** — the
full-swing data barely constrains it.

So "fitted (pinned 0.45 on 10 of 12)", which the deck used to say, was wrong twice over.

## 3. `vt` is not the device threshold  (`check_xlin.py`)

Fitted `vt` at each buffer's best K, est_knee pull-up:

```
ex2 0.029   ex2_base 0.015   ex2_nomiller 0.033  ex2_skewp 0.022
ex2_slowpre 0.062   ex2_weak 0.029   inv_base8 0.325   inv_chain 0.447
inv_skewp 0.077   inv_stage4 0.018   inv_weak 0.524   io_buf 0.432
```

Range **0.015 to 0.524**, against a physical `V_th/V_DD` of 0.11 (3.3 V) or 0.20 (1.8 V). It is
an effective hand-over point, and the stressed-run calibration overwrites it anyway.

## 4. A device's current does factor, and ours is the same shape  (`check_factorisation.py`)

Level 1 over the two conducting regions collapses to a function of one ratio:

    I / I_sat  =  q(2 - q),    q = min(r, 1),    r = V_DS / (V_GS - V_th)

verified to 4e-16 over 20 000 random `(V_ov, V_DS)`, 66 % of them in saturation.

**Correction, 2026-09-28.** This was written as `min(1, r(2-r))` until an outside review
caught it. `r(2-r)` peaks at `r = 1` and falls after, so `min()` takes the falling branch
above saturation - max error 340 on the same sample. The clamp goes on `r`, not on the
result. `check_factorisation.py` always computed it correctly; only the wording was wrong,
here and in `docs/stage_law_walkthrough.md`. So the standard form is `[gate term] x [drain term]`,
exactly our shape. The three differences are: our exponent (1 not 2), our drain term
(`min(1,r')` not `min(1,r(2-r))`), and our normaliser (constant `x_lin`, not the overdrive).

## 5. The taper comparison runs the other way from the old claim  (`compare_taper.py`)

Comparing the two drain factors **at matched r is invalid** — the two normalise `r` by different
things. The deck used to say "half way into the region the book passes 0.75 and we pass 0.50" (and named a textbook as the authority),
which invited the reading that we are weak near the rail. Done properly at full gate drive,
3.3 V part:

| v | a real device | our model |
|---|---|---|
| 0.30 | 0.959 | 1.000 |
| 0.50 | 0.815 | 1.000 |
| 0.70 | 0.567 | 0.667 |
| 0.90 | 0.215 | 0.222 |
| 0.99 | 0.023 | 0.022 |

A real device gives up its constant current at **v = 0.12**; we hold ours to **v = 0.55**. Integrated
over the travel, **ours / a real device = 1.095**. We are *more* current-source-like than long-channel
theory, not less.

**The favourable reading.** A device's boundary is at `1 - v = u - vt`, so `x_lin = 0.45` is
where it lands at about **57 % gate drive** — right for a partly-driven stage, too generous for a
fully-driven one. The stressed pulse is the partly-driven case. Nobody chose 0.45 for that
reason, but it is defensible post hoc. Separately, these are ~0.6 um devices and velocity
saturation extends the real constant-current region, moving real silicon toward our model and away
from the long-channel form — a hypothesis, not a measurement.

## What was changed as a result

In `docs/track1_recipe.md` and the 09-24 deck:

* `vt` and `x_lin` are described as **effective parameters**, with the numbers above.
* `x_lin` is stated as **held at 0.45, not fitted**.
* The triode panel is redrawn as the full-drive comparison, with a real device at 57 % drive as a
  third curve.
* "Those three regimes are the whole of the stage law" → built from, not derived from.
* The law slide now says outright: **physically motivated reduced-order model, not derived from
  device physics.** The results stand on the measurements, not on the derivation.
* "a tapered predriver approximately is identical" → identical **normalised dynamics**, not
  dimensions.
* "a chain extinguishes a short pulse" → that is our model's hard threshold; in silicon the
  current falls off continuously and the pulse degrades stage by stage.
* `Ku <= 1` → a diagnostic, not an identity.
* "the only instrument" → the only one available to somebody holding a vendor IBIS file and a
  board.

**None of the measured results change.** What changes is the claim about where the model comes
from.

## 6. A framing change, not just wording

Simon's objection to the first pass of these corrections: *"putting 'x_lin is not the book's
boundary' is meaningless to the readers. reader doesn't know about the book, and we should stop
citing it blindly."*

He is right, and it was a framing problem rather than a wording one. The write-up had made a
textbook a character in the story: slide after slide compared "the book" against "ours", which
tells a reader nothing unless they have read it, and which quietly treats a citation as an
authority instead of explaining the physics.

The subject is **the transistor**. The question is **where our model departs from it, and by how
much**. So:

* every "the book" became "a real device" or "standard device behaviour";
* the provenance badges went from `book / book* / ours` to **`device / simplified / assumed`**,
  which say what they mean without needing a reference;
* the citation survives exactly once, as a small grey source note under the equations it
  actually sources, together with its own limitation: these are ~0.6 um devices, so the
  long-channel form is itself an approximation;
* the headline that read "x_lin is not the book's boundary" now reads **"our stage keeps
  pushing at full current for the first 55 % of its travel, where a real device gives up at
  12 %"** — which a reader can act on.

Count of "book" in the deck builder and in `docs/track1_recipe.md` afterwards: **zero**.
