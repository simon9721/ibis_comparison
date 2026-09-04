#!/usr/bin/env python3
"""ex2 as an open-drain buffer: the output pullup removed.

Item 2 of `0902_plan.md`. ex2 is a real layout-extracted netlist, not a
parameterized one, so it does not admit the clean width/stage sweeps inv_chain
did. It admits one structurally interesting change: strip the output pullup and
make it open-drain.

That is the change worth making. Every buffer in the study so far is push-pull,
and the gate-state model, the command layer and the pybis subcircuit were all
built around a pullup and a pulldown. An open-drain buffer has no pullup at all
-- the pad can only be driven low, and reaches high through an external
termination. If the machinery has quietly assumed push-pull, this is where it
shows.

ex2's output stage is five pullup PMOS (mx24-28) and five pulldown NMOS
(mx15-19), both gated by the predriver node n4. Removing the five PMOS leaves
the predriver and the pulldown untouched, so the only thing that changes is that
the pad has lost its path to VCC. The Miller caps from n4 to out (cx3, cx5, cx8)
are kept -- they are physical and independent of the pullup.

    py -3.14 scripts/make_ex2_opendrain_variant.py
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EX2 = ROOT / "buffers" / "ex2"
BASE_CONFIG = ROOT / "results" / "ex2_s2ibispy_slow_fast_2026-07-28" / "configs" / "ex2_fast_5ps.yaml"
OUT = ROOT / "results" / "ex2_variants_2026-09-03"

# The five output-stage pullup PMOS, gated by n4, connecting out to vdd.
OUTPUT_PULLUP = {"mx24", "mx25", "mx26", "mx27", "mx28"}


def open_drain_netlist() -> tuple[str, list[str]]:
    """buffer.sp with the output pullup devices commented out."""
    removed: list[str] = []
    lines: list[str] = []
    for raw in (EX2 / "buffer.sp").read_text(encoding="utf-8").splitlines():
        device = raw.split()[0].lower() if raw.split() else ""
        if device in OUTPUT_PULLUP:
            removed.append(device)
            lines.append(f"* [open-drain: output pullup removed] {raw}")
            continue
        lines.append(raw)
    return "\n".join(lines) + "\n", sorted(removed)


def _pullup_only_fixtures(lines: list[str]) -> list[str]:
    """Keep only the pull-up (V_fixture = VCC) entry in each waveform block.

    An open-drain pad cannot rise into a fixture that pulls it to ground, so the
    inherited V_fixture=0 rising waveform is flat at 0 and ibischk rejects it
    ("DC endpoints of 0.00V and -0.00V"). Push-pull characterization uses both
    fixtures; open-drain uses the pull-up fixture alone.
    """
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() in ("rising_waveforms:", "falling_waveforms:"):
            out.append(line)
            i += 1
            entries: list[list[str]] = []
            while i < len(lines):
                stripped = lines[i].strip()
                if lines[i].lstrip().startswith("- R_fixture"):
                    entries.append([lines[i]])
                elif entries and stripped and lines[i].startswith("    "):
                    entries[-1].append(lines[i])
                else:
                    break
                i += 1
            for entry in entries:
                if any("V_fixture:" in e and "3.3" in e for e in entry):
                    out.extend(entry)
            continue
        out.append(line)
        i += 1
    return out


def recipe(inputs_dir: Path) -> str:
    """The ex2 recipe with the model retyped Open_drain and files repointed."""
    lines: list[str] = []
    in_driver = False
    for raw in BASE_CONFIG.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped == "- name: driver":
            in_driver = True
            lines.append(raw)
            continue
        if stripped.startswith("- name:") and stripped != "- name: driver":
            in_driver = False
        if in_driver and stripped.startswith("type:"):
            lines.append(raw.split("type:")[0] + "type: Open_drain")
            continue
        if stripped.startswith("file_name:"):
            lines.append("file_name: ex2_opendrain.ibs")
            continue
        if stripped.startswith("source:"):
            lines.append("source: ex2 open-drain variant -- output pullup removed")
            continue
        if stripped.startswith("notes:"):
            lines.append("notes: ex2 with the five output-stage pullup PMOS removed, "
                         "so the pad has no path to VCC and is driven low only.")
            continue
        if stripped.startswith("modelFile"):
            key = stripped.split(":")[0]
            lines.append(raw.split(key)[0] + f"{key}: {(inputs_dir / 'hspice.mod').as_posix()}")
            continue
        if stripped.startswith("spiceFile:"):
            lines.append(raw.split("spiceFile:")[0]
                         + f"spiceFile: {(inputs_dir / 'buffer.sp').as_posix()}")
            continue
        lines.append(raw)
    lines = _pullup_only_fixtures(lines)
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = (args.out if args.out.is_absolute() else ROOT / args.out).resolve()

    inputs = out / "opendrain" / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    netlist, removed = open_drain_netlist()
    (inputs / "buffer.sp").write_text(netlist, encoding="utf-8")
    shutil.copy2(EX2 / "hspice.mod", inputs / "hspice.mod")

    configs = out / "opendrain" / "configs"
    configs.mkdir(parents=True, exist_ok=True)
    (configs / "ex2_opendrain.yaml").write_text(recipe(inputs), encoding="utf-8")

    print(f"removed output pullup: {', '.join(removed)}")
    print(f"kept the predriver and all five pulldown NMOS")
    print(f"\nwrote {out / 'opendrain'}")
    print(f"\nnext:\n  py -3.14 scripts/select_s2ibispy_parameters.py \\\n"
          f"      --config {configs / 'ex2_opendrain.yaml'} \\\n"
          f"      --inputs {inputs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
