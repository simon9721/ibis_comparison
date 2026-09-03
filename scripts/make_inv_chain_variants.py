#!/usr/bin/env python3
"""Build inverter-chain variants: different silicon, same everything else.

Item 1 of `0902_plan.md`. The study has three buffers and every conclusion in it
rests on those three. Variants of a buffer we already understand are the cheapest
way to ask whether a conclusion is about the model or about the device.

The base `invchain` is eight tapered inverters, x2 per stage (m = 1 .. 128),
Wn = 1 um, Wp = 2 um, L = 180 nm, on a 1.8 V supply. Each variant changes one
thing, so any difference downstream has one candidate explanation:

  stage4   Four stages instead of eight, m = 16 .. 128. The final stage and
           therefore the output drive are identical; only the predriver depth
           changes. The command layer models exactly this delay -- io_buf's
           pu_on_delay of 0.99 ns is its predriver -- so this sweeps the
           quantity the command layer exists to represent, on a device where we
           know what we changed.

  skewp    Wp = Wn = 1 um, so the PMOS is half its usual strength relative to
           the NMOS. Rise gets slower, fall does not. io_buf's dead zone is a
           1.76 ns gap between pullup-off and pulldown-on, and we have never
           seen that asymmetry anywhere else. This makes it on purpose, at a
           size we choose.

  weak     Wn = 0.5 um, Wp = 1 um: half the drive at every stage, taper and
           stage count unchanged. Slower edges into the same 50 ohm load,
           without touching the timing structure.

Each variant gets its own inputs directory with the three corner files (which
differ only in supply, as the base does) and its own s2ibispy recipe, so it can
go straight through `select_s2ibispy_parameters.py`.

    py -3.14 scripts/make_inv_chain_variants.py
"""
from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results" / "inv_chain_s2ibispy_slow_fast_2026-07-27"
BASE_INPUTS = BASE / "inputs"
BASE_CONFIG = BASE / "configs" / "inv_chain_fast_5ps.yaml"
OUT = ROOT / "results" / "inv_chain_variants_2026-09-02"

CORNERS = {"typ": "typ", "slow": "min", "fast": "max"}


@dataclass
class Variant:
    key: str
    title: str
    purpose: str
    multipliers: list[int]
    wn: float = 1e-6
    wp: float = 2e-6
    ln: float = 180e-9
    lp: float = 180e-9


VARIANTS = [
    Variant("base8", "eight stages, x2 taper (reference build)",
            "Identical to the shipped inv_chain. Built here so every variant, "
            "including the reference, comes out of the same generator.",
            [1, 2, 4, 8, 16, 32, 64, 128]),
    Variant("stage4", "four stages, same final drive",
            "Halves the predriver depth while leaving the output stage alone, "
            "so the fitted onset delays should shorten and nothing else should.",
            [16, 32, 64, 128]),
    Variant("skewp", "weak PMOS, Wp = Wn",
            "Makes rise slower than fall on purpose, to see whether the "
            "asymmetry that produces io_buf's dead zone reproduces on a device "
            "where we set its size.",
            [1, 2, 4, 8, 16, 32, 64, 128], wp=1e-6),
    Variant("weak", "half drive at every stage",
            "Slower edges into the same load, with the timing structure "
            "unchanged.",
            [1, 2, 4, 8, 16, 32, 64, 128], wn=0.5e-6, wp=1e-6),
]


def subckt(variant: Variant, corner_suffix: str) -> str:
    """One corner file, in the same shape as the base netlist.

    The subcircuit keeps the name `invchain` in every variant. Each lives in its
    own inputs directory, so the recipes need no rename and the only difference
    between two conversions is the silicon.
    """
    stages = []
    node_in = "VIN"
    last = len(variant.multipliers)
    for index, m in enumerate(variant.multipliers, start=1):
        node_out = "VOUT8" if index == last else f"VOUT{index}"
        stages.append(
            f"MPM_inv{index} {node_out} {node_in} vccq vccq pch_tn "
            f"W=Wp L=Lp m={m}\n"
            f"MNM_inv{index} {node_out} {node_in} vssq vssq nch_tn "
            f"W=Wn L=Ln m={m}\n")
        node_in = node_out
    return (
        f".lib 'HL18G-S3.7S.lib' tt_tn\n"
        f".param Wn={variant.wn:.6G}\n"
        f".param Wp={variant.wp:.6G}\n"
        f".param Ln={variant.ln:.6G}\n"
        f".param Lp={variant.lp:.6G}\n"
        f"\n"
        f".PARAM  vccq      = vccq_{corner_suffix}\n"
        f".PARAM  vccr      = vccr_{corner_suffix}\n"
        f"\n"
        f".subckt invchain VIN VOUT8 vccq vssq\n"
        f"\n"
        + "\n".join(stages)
        + "\n.ends\n"
    )


def recipe(variant: Variant, inputs_dir: Path) -> str:
    """The base recipe with the model files repointed and the notes rewritten.

    Only `modelFile*`, `file_name`, `source` and `notes` change. Everything that
    describes the measurement -- fixtures, supply, sim_time, tr/tf -- is
    inherited, because the point of the exercise is to vary the silicon and
    nothing else. `select_s2ibispy_parameters.py` chooses sim_time and tr per
    variant afterwards.
    """
    lines = []
    for raw in BASE_CONFIG.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped.startswith("file_name:"):
            lines.append(f"file_name: invchain_{variant.key}.ibs")
            continue
        if stripped.startswith("source:"):
            lines.append(f"source: inv_chain variant '{variant.key}' -- "
                         f"{variant.title}")
            continue
        if stripped.startswith("notes:"):
            lines.append(f"notes: {variant.purpose}")
            continue
        for field_name, corner in (("modelFileMin:", "slow"),
                                   ("modelFileMax:", "fast"),
                                   ("modelFile:", "typ")):
            if stripped.startswith(field_name):
                indent = raw.split(field_name)[0]
                path = inputs_dir / f"invchain_{variant.key}_subckt_{corner}.sp"
                lines.append(f"{indent}{field_name} "
                             f"{path.as_posix()}")
                break
        else:
            lines.append(raw)
            continue
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    library = BASE_INPUTS / "HL18G-S3.7S.lib"
    if not library.exists():
        raise SystemExit(f"transistor library not found: {library}")

    print(f"{'variant':<10}{'stages':>8}{'final m':>9}{'Wn um':>8}{'Wp um':>8}"
          f"   {'purpose'}")
    for variant in VARIANTS:
        inputs_dir = out / variant.key / "inputs"
        inputs_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(library, inputs_dir / library.name)
        shutil.copy2(BASE_INPUTS / "invchain_top.sp", inputs_dir / "invchain_top.sp")
        for corner, suffix in CORNERS.items():
            (inputs_dir / f"invchain_{variant.key}_subckt_{corner}.sp").write_text(
                subckt(variant, suffix), encoding="utf-8")

        config_dir = out / variant.key / "configs"
        config_dir.mkdir(parents=True, exist_ok=True)
        config = config_dir / f"invchain_{variant.key}.yaml"
        config.write_text(recipe(variant, inputs_dir), encoding="utf-8")

        print(f"{variant.key:<10}{len(variant.multipliers):>8}"
              f"{variant.multipliers[-1]:>9}{variant.wn * 1e6:>8.2f}"
              f"{variant.wp * 1e6:>8.2f}   {variant.title}")

    readme = out / "README.md"
    rows = "\n".join(
        f"| `{v.key}` | {len(v.multipliers)} | {v.multipliers[-1]} | "
        f"{v.wn * 1e6:g} | {v.wp * 1e6:g} | {v.title} |" for v in VARIANTS)
    readme.write_text(
        "# inv_chain variants\n\n"
        "Generated by `scripts/make_inv_chain_variants.py`. Each variant "
        "changes one property of the silicon and inherits everything else from "
        "the shipped `inv_chain` recipe.\n\n"
        "| variant | stages | final m | Wn (um) | Wp (um) | what changed |\n"
        "|---|---:|---:|---:|---:|---|\n" + rows + "\n\n"
        + "\n\n".join(f"**`{v.key}`** — {v.purpose}" for v in VARIANTS)
        + "\n\nNext step per variant:\n\n```\n"
          "py -3.14 scripts/select_s2ibispy_parameters.py \\\n"
          "    --config results/inv_chain_variants_2026-09-02/<key>/configs/"
          "invchain_<key>.yaml\n```\n",
        encoding="utf-8")

    print(f"\nwrote {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
