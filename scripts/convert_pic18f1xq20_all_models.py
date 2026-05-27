from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2] / "spice" / "pybis2spice"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pybis2spice import pybis2spice  # noqa: E402
from pybis2spice import subcircuit  # noqa: E402


IBIS_ROOT = Path(__file__).resolve().parents[1] / "PIC18F1xQ20_LV_IBIS_Models"
OUTPUT_ROOT = IBIS_ROOT / "converted_inputdriven_typical"
COMPONENT_NAME = "PIC18F1xQ20"
CORNER = "Typical"
SUBCIRCUIT_TYPE = "InputDriven"
IO_TYPES = ("Input", "Output")


def summarize_results(path: Path, io_type: str, results: dict) -> dict:
    return {
        "ibis_file": path.name,
        "io_type": io_type,
        "generated_count": len(results["generated"]),
        "skipped_count": len(results["skipped"]),
        "failed_count": len(results["failed"]),
        "generated_files": [Path(item).name for item in results["generated"]],
        "skipped_models": results["skipped"],
        "failed_models": results["failed"],
    }


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    summary_rows = []

    for ibis_path in sorted(IBIS_ROOT.glob("*.ibs")):
        ibis = pybis2spice.get_ibis_model_ecdtools(str(ibis_path))
        package_root = OUTPUT_ROOT / ibis_path.stem

        for io_type in IO_TYPES:
            out_dir = package_root / io_type
            results = subcircuit.generate_spice_models_for_all_models(
                ibis_model_ecdtools=ibis,
                component_name=COMPONENT_NAME,
                output_dir=str(out_dir),
                io_type=io_type,
                subcircuit_type=SUBCIRCUIT_TYPE,
                corner=CORNER,
            )
            summary_rows.append(summarize_results(ibis_path, io_type, results))

    summary_json = OUTPUT_ROOT / "conversion_summary.json"
    summary_json.write_text(json.dumps(summary_rows, indent=2), encoding="utf-8")

    summary_md = OUTPUT_ROOT / f"conversion_summary_{date.today().isoformat()}.md"
    lines = [
        "# PIC18F1xQ20 LV IBIS Conversion Summary",
        "",
        f"- Mode: `{SUBCIRCUIT_TYPE}`",
        f"- Corner: `{CORNER}`",
        f"- Component: `{COMPONENT_NAME}`",
        f"- Source folder: `{IBIS_ROOT}`",
        f"- Output folder: `{OUTPUT_ROOT}`",
        "",
        "| IBIS File | I/O Type | Generated | Skipped | Failed |",
        "| --- | --- | ---: | ---: | ---: |",
    ]

    for row in summary_rows:
        lines.append(
            f"| `{row['ibis_file']}` | `{row['io_type']}` | "
            f"{row['generated_count']} | {row['skipped_count']} | {row['failed_count']} |"
        )

    lines.extend(["", "## Notes", ""])

    for row in summary_rows:
        lines.append(f"### {row['ibis_file']} / {row['io_type']}")
        lines.append("")
        if row["generated_files"]:
            lines.append("Generated files:")
            for item in row["generated_files"]:
                lines.append(f"- `{item}`")
        if row["skipped_models"]:
            lines.append("Skipped models:")
            for item in row["skipped_models"]:
                lines.append(f"- `{item['model']}`: {item['reason']}")
        if row["failed_models"]:
            lines.append("Failed models:")
            for item in row["failed_models"]:
                lines.append(f"- `{item['model']}`: {item['reason']}")
        lines.append("")

    summary_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote conversion outputs to: {OUTPUT_ROOT}")
    print(f"Wrote summaries: {summary_md.name}, {summary_json.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
