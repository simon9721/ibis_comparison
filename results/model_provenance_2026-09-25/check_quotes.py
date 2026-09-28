# -*- coding: utf-8 -*-
"""Is every book quote in the stage-law reference audit verbatim in pages.json?

Checks the Tier-1 quotes in docs/stage_law_walkthrough.md 4.4.
Same discipline as docs/book/citations.md. OCR keeps hard line breaks, so
compare on whitespace-normalised text.
"""
import json
import re
from pathlib import Path

ROOT = Path(r"C:\Users\sh3qm\code\ibis_comparison")
pages = json.load(open(ROOT / "docs" / "book" / "pages.json", encoding="utf-8"))
norm = lambda s: re.sub(r"\s+", " ", s).strip()          # noqa: E731
by_pdf = {r["pdf_page"]: norm(r.get("text", "")) for r in pages}

QUOTES = [
    (105, "A few MOSFET model equations (3-23) through (3-26) are shown for "
          "illustration. These equations are level 1 and level 2 with terms for gate "
          "modulation specifically included"),
    (583, "All so-called physical models (Ebers-Moll [34], Shichman-Hodges [109]) are actually "
          "macromodels when compared to the device physics formulations."),
    (585, "But complex I/O requires some modeling of the buffer internal behavior. A new balance "
          "between simulation speed and I/O internal modeling will have to be devised."),
    (585, "The black-box model can simplify the physical model of the output stage so that we can "
          "model driver and pre-driver at a less detailed level."),
    (742, 'H. Shichman and D.A. Hodges, "Modeling and Simulation of Insulated-Gate Field- Effect '
          'Transistor Switching Circuits," IEEE Journal of Solid-State Circuits, SC-3 1968.'),
]

ok = True
for pdf, q in QUOTES:
    found = norm(q) in by_pdf.get(pdf, "")
    ok &= found
    print(f"  [{'OK ' if found else 'FAIL'}] pdf {pdf}: {q[:66]}...")

# the equations are OCR-mangled, so check the distinctive fragments instead
p105 = by_pdf[105]
print("\n  equation fragments on pdf 105:")
for frag in ("ID = 0", "ID=(KP/2) *(W/L) *(VGS- VTE",
             "ID=(KP/2) *(W/L)*VDS*(2 *(VGS- VTE)- VDS) *(1 +LAMBDA",
             "For: VGS - VTO < 0", "For:0 < VGS - VTO < VDS", "For: 0 < VDS < VGS - VTO"):
    found = norm(frag) in p105
    ok &= found
    print(f"    [{'OK ' if found else 'FAIL'}] {frag}")

print(f"\n  {'ALL QUOTES VERIFIED' if ok else 'SOME QUOTES DO NOT MATCH'}")

# and confirm the negative claims
for word in ("Sakurai", "velocity saturation", "alpha-power", "Ku", "Kd"):
    hits = sum(1 for t in by_pdf.values() if norm(word).lower() in t.lower())
    print(f"  pages mentioning {word!r}: {hits}")
