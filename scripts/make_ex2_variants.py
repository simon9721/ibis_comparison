#!/usr/bin/env python3
"""ex2 variants: the inv_chain axes, applied to a real extracted buffer.

I previously claimed ex2 did not admit parameterized variants because it is a
flat layout-extracted netlist. That was wrong. `ex2/buffer.sp` carries an explicit
`w=` on every device, so the same axes swept on inv_chain -- drive strength,
pull-up/pull-down balance, predriver speed -- are a matter of scaling widths.

ex2's structure, from the netlist:

    predriver      mx20-23 (pfet)  mx11-14 (nfet)   in -> n2 -> n3 -> n4
    output stage   mx24-28 (pfet)  mx15-19 (nfet)   gated by n4, drives out

Variants, each changing one thing so a downstream difference has one candidate
explanation:

  base      unchanged, rebuilt through this generator -- the control on the
            generator itself, exactly as base8 was for inv_chain.
  weak      output stage widths halved, both devices. Weaker drive, slower edge
            into the same load, timing structure untouched.
  skewp     output PMOS halved only. Rise slows, fall does not -- the deliberate
            asymmetry that on inv_chain inflated max|Ku| while leaving Kd alone.
            Worth repeating on a device with a real extracted layout.
  slowpre   predriver widths halved. ex2 cannot lose a stage the way inv_chain
            could, but a weaker predriver takes longer to swing n4, which moves
            the onset delay the command layer models.

The `[open-drain]` variant lives separately in `make_ex2_opendrain_variant.py`,
since removing the pullup outright is a structural change rather than a scaling.

    py -3.14 scripts/make_ex2_variants.py
"""
from __future__ import annotations

import argparse
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EX2 = ROOT / "ex2"
BASE_CONFIG = (ROOT / "results" / "ex2_s2ibispy_slow_fast_2026-07-28" /
               "configs" / "ex2_fast_5ps.yaml")
OUT = ROOT / "results" / "ex2_variants_2026-09-03"

OUTPUT_PMOS = {"mx24", "mx25", "mx26", "mx27", "mx28"}
OUTPUT_NMOS = {"mx15", "mx16", "mx17", "mx18", "mx19"}
PREDRIVER = {"mx20", "mx21", "mx22", "mx23", "mx11", "mx12", "mx13", "mx14"}


@dataclass
class Variant:
    key: str
    title: str
    purpose: str
    scale: dict[str, float] = field(default_factory=dict)   # device -> width factor


VARIANTS = [
    Variant("base", "unchanged reference",
            "Identical to the shipped ex2. Built through the same generator so "
            "the reference and the variants differ only in the silicon."),
    Variant("weak", "output stage at half width",
            "Halves both output devices: weaker drive and a slower edge into the "
            "same load, with the timing structure untouched.",
            {d: 0.5 for d in OUTPUT_PMOS | OUTPUT_NMOS}),
    Variant("skewp", "output PMOS at half width",
            "Halves only the pullup, so rise slows and fall does not. On "
            "inv_chain this inflated max|Ku| while leaving Kd untouched; this "
            "repeats it on a real extracted layout.",
            {d: 0.5 for d in OUTPUT_PMOS}),
    Variant("slowpre", "predriver at half width",
            "Weakens the three predriver stages, so n4 swings more slowly and "
            "the output onset is delayed -- ex2's analogue of inv_chain's stage "
            "count, which is the quantity the command layer represents.",
            {d: 0.5 for d in PREDRIVER}),
]

WIDTH = re.compile(r"(\bw=)([0-9.eE+-]+)")


def scaled_netlist(variant: Variant) -> tuple[str, list[str]]:
    """buffer.sp with the named devices' widths scaled."""
    touched: list[str] = []
    lines: list[str] = []
    for raw in (EX2 / "buffer.sp").read_text(encoding="utf-8").splitlines():
        device = raw.split()[0].lower() if raw.split() else ""
        factor = variant.scale.get(device)
        if factor is None:
            lines.append(raw)
            continue

        def rescale(m: re.Match) -> str:
            return f"{m.group(1)}{float(m.group(2)) * factor:.6g}"

        new = WIDTH.sub(rescale, raw, count=1)
        touched.append(device)
        lines.append(new)
    return "\n".join(lines) + "\n", sorted(touched)


def recipe(variant: Variant, inputs_dir: Path) -> str:
    """The ex2 recipe with the netlist and model files repointed at this variant."""
    lines: list[str] = []
    for raw in BASE_CONFIG.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if s.startswith("file_name:"):
            lines.append(f"file_name: ex2_{variant.key}.ibs")
            continue
        if s.startswith("source:"):
            lines.append(f"source: ex2 variant '{variant.key}' -- {variant.title}")
            continue
        if s.startswith("notes:"):
            lines.append(f"notes: {variant.purpose}")
            continue
        if s.startswith("modelFile"):
            key = s.split(":")[0]
            lines.append(raw.split(key)[0] + f"{key}: {(inputs_dir / 'hspice.mod').as_posix()}")
            continue
        if s.startswith("spiceFile:"):
            lines.append(raw.split("spiceFile:")[0]
                         + f"spiceFile: {(inputs_dir / 'buffer.sp').as_posix()}")
            continue
        lines.append(raw)
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    out = (args.out if args.out.is_absolute() else ROOT / args.out).resolve()

    print(f"{'variant':<10}{'devices scaled':>16}   {'what changed'}")
    for v in VARIANTS:
        inputs = out / v.key / "inputs"
        inputs.mkdir(parents=True, exist_ok=True)
        netlist, touched = scaled_netlist(v)
        (inputs / "buffer.sp").write_text(netlist, encoding="utf-8")
        shutil.copy2(EX2 / "hspice.mod", inputs / "hspice.mod")

        configs = out / v.key / "configs"
        configs.mkdir(parents=True, exist_ok=True)
        (configs / f"ex2_{v.key}.yaml").write_text(recipe(v, inputs), encoding="utf-8")
        print(f"{v.key:<10}{len(touched):>16}   {v.title}")

    (out / "README.md").write_text(
        "# ex2 variants\n\nGenerated by `scripts/make_ex2_variants.py` -- the same\n"
        "axes swept on inv_chain, applied to ex2's extracted device widths.\n\n"
        "| variant | what changed |\n|---|---|\n"
        + "\n".join(f"| `{v.key}` | {v.title} |" for v in VARIANTS)
        + "\n\n" + "\n\n".join(f"**`{v.key}`** — {v.purpose}" for v in VARIANTS)
        + "\n\nThe open-drain variant is generated separately by\n"
          "`scripts/make_ex2_opendrain_variant.py`; removing the pullup is a\n"
          "structural change rather than a width scaling.\n",
        encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
