#!/usr/bin/env python3
"""Do the written recipe and the explainer page still make the same claims?

`docs/track1_recipe.md` and `docs/track1_explainer.template.html` are two presentations of one
argument - the doc carries the numbers and the exact procedure, the page carries the figures -
and they drifted apart once already: the page gained the sampling argument (a full transition
visits only the ends of the gate's travel, so only a truncation reaches the interior) while the
doc still led with three unordered measurements, and the doc kept the band rule's numbers after
the page had quietly dropped them.

This will not prove they agree. It checks that each load-bearing number appears in both, which
is enough to catch one being edited without the other. Run it after touching either.

Exit status is 1 if any fact is missing from either side.

    python scripts/check_recipe_agreement.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "track1_recipe.md"
PAGE = ROOT / "docs" / "track1_explainer.template.html"

# (what the claim is, the strings that carry it). Written so a value can move around in the
# sentence but not change: it is the numbers that must not drift, not the prose.
FACTS = [
    ("the headline: 12 of 12 within +-10 %", ["12"]),
    ("our error range", ["3.2", "10.0 %"]),
    ("our mean error", ["6.9 %"]),
    ("where the shipped model lands", ["35-76 %"]),
    ("inv_chain file-only against track-1", ["5.1 %", "25.8 %"]),
    ("M1 hysteresis", ["0.07", "0.10"]),
    ("ex2's implied Ku at the declared C_comp", ["1.24"]),
    ("ex2's loop-measured C_comp", ["1.70"]),
    ("ex2's knee C_comp", ["2.64"]),
    ("M2 predicts the stressed gate to", ["0.05"]),
    ("linear superposition is off by", ["0.17"]),
    ("x_lin pinned, and the measured range", ["0.45", "0.37", "0.63"]),
    ("p is indistinguishable at full swing", ["0.002", "0.007"]),
    ("the free fit is degenerate", ["0.23", "0.76"]),
    ("K = 7 and K = 9 are identical", ["0.0032"]),
    ("inv_chain's gate at K = 7", ["0.672"]),
    ("the selector, on the waveform", ["52.3", "51.7", "217.3"]),
    ("how late the peak-ranked picks are", ["155", "300"]),
    ("io_buf's pull-down is inert", ["0.7", "163", "322"]),
    ("the three regimes' gate excursions", ["0.42", "0.63", "0.91", "1.03"]),
    ("what the full swing costs", ["61", "16"]),
    ("the band rule", ["25 %", "1 of 13"]),
    ("the shape grid", ["0.50, 0.70", "0.40, 0.60", "0.40, 0.90"]),
    ("the depth coverage", ["50, 60, 70, 80, 90"]),
]


def text(path: Path, strip_tags: bool) -> str:
    s = path.read_text(encoding="utf-8")
    if strip_tags:
        s = re.sub(r"<script>.*?</script>", " ", s, flags=re.S)
        s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("–", "-").replace("—", "-").replace(" ", " ")
    return re.sub(r"\s+", " ", s)


def main() -> int:
    doc, page = text(DOC, False), text(PAGE, True)
    bad = 0
    for name, needles in FACTS:
        miss = {"doc": [n for n in needles if n not in doc],
                "page": [n for n in needles if n not in page]}
        if miss["doc"] or miss["page"]:
            bad += 1
            print(f"  MISMATCH  {name}")
            for side in ("doc", "page"):
                if miss[side]:
                    print(f"      missing from the {side}: {miss[side]}")
    print(f"{len(FACTS) - bad} of {len(FACTS)} claims present in both "
          f"({DOC.name}, {PAGE.name})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
