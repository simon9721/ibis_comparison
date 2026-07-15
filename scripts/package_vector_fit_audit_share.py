from __future__ import annotations

import argparse
import csv
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STUDY = ROOT / "results" / "sparam_vector_fit_campaign_v1_2026-06-17_fast_overnight_v2"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def resolve_path(text: object) -> Path:
    path = Path(str(text or ""))
    if path.is_absolute():
        return path
    return ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def safe_name(text: object) -> str:
    chars = []
    for ch in str(text):
        if ch.isalnum() or ch in ("-", "_", "."):
            chars.append(ch)
        else:
            chars.append("_")
    return "".join(chars).strip("._") or "item"


def copy_if_exists(src_text: object, dest: Path) -> str:
    src = resolve_path(src_text)
    if not src.exists() or not src.is_file():
        return ""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return rel(dest)


def case_metric_table(row: dict[str, str]) -> list[str]:
    keys = [
        "hspice_audit_class",
        "hspice_audit_reason",
        "rx_hspice_audit_class",
        "rx_hspice_audit_reason",
        "reflection_hspice_audit_class",
        "reflection_hspice_audit_reason",
        "rx_shape_hspice_audit_class",
        "rx_timing_hspice_audit_class",
        "tx_active_rmse_v",
        "tx_active_maxabs_v",
        "rx_active_rmse_v",
        "rx_active_maxabs_v",
        "rx_minus_tx_rise50_ps_delta_ps",
        "rx_minus_tx_fall50_ps_delta_ps",
        "hspice_threshold_delay_confidence",
        "hspice_threshold_delay_confidence_reasons",
    ]
    lines = ["| Metric | Value |", "| --- | --- |"]
    for key in keys:
        value = row.get(key, "")
        if value != "":
            lines.append(f"| `{key}` | `{value}` |")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Package vector-fit HSPICE/ngspice audit cases for sharing.")
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_STUDY)
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    study_dir = args.study_dir if args.study_dir.is_absolute() else ROOT / args.study_dir
    out_dir = args.out_dir or (study_dir / "share_pack")
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    corr_rows = [row for row in read_csv(study_dir / "vf_hspice_correlation.csv") if row.get("correlation_status") == "ok"]
    ranking = {row.get("channel_id", ""): row for row in read_csv(study_dir / "vf_ranking.csv")}
    side_index = read_csv(study_dir / "plots" / "side_overlays" / "index.csv")
    side_plots = {
        (row.get("channel_id", ""), row.get("candidate_id", ""), row.get("case", ""), row.get("side", "")): row
        for row in side_index
    }

    index_rows: list[dict[str, object]] = []
    for row in corr_rows:
        channel_id = row.get("channel_id", "")
        candidate_id = row.get("candidate_id", "")
        case = row.get("case", "")
        audit_class = row.get("hspice_audit_class", "UNKNOWN") or "UNKNOWN"
        rank = ranking.get(channel_id, {})
        case_id = safe_name(f"{channel_id}_{candidate_id}_{case}")
        case_dir = out_dir / f"audit_{audit_class.lower()}" / case_id

        copied: dict[str, str] = {}
        copied["rx_overlay"] = copy_if_exists(
            side_plots.get((channel_id, candidate_id, case, "rx"), {}).get("plot", ""),
            case_dir / "figures" / "rx_overlay.png",
        )
        copied["tx_overlay"] = copy_if_exists(
            side_plots.get((channel_id, candidate_id, case, "tx"), {}).get("plot", ""),
            case_dir / "figures" / "tx_overlay.png",
        )
        copied["two_panel_overlay"] = copy_if_exists(
            row.get("overlay_plot", ""),
            case_dir / "figures" / "hspice_ngspice_two_panel.png",
        )
        freq_plot = study_dir / "plots" / "frequency_fit" / f"{channel_id}_{candidate_id}.png"
        copied["frequency_fit_plot"] = copy_if_exists(freq_plot, case_dir / "figures" / "frequency_fit.png")
        passivity_plot = study_dir / "plots" / "passivity" / f"{channel_id}_{candidate_id}.png"
        copied["passivity_plot"] = copy_if_exists(passivity_plot, case_dir / "figures" / "passivity.png")

        copied["vector_fit_model"] = copy_if_exists(
            rank.get("selected_model_copy", ""),
            case_dir / "models" / "ngspice_vector_fit_model.sp",
        )
        copied["original_touchstone"] = copy_if_exists(
            rank.get("channel_path", ""),
            case_dir / "inputs" / Path(str(rank.get("channel_path", "channel.s2p"))).name,
        )
        h_tr0 = resolve_path(row.get("hspice_tr0", ""))
        n_raw = resolve_path(row.get("ngspice_raw", ""))
        copied["hspice_deck"] = copy_if_exists(h_tr0.with_suffix(".sp"), case_dir / "hspice" / "hspice_native_s_element.sp")
        copied["hspice_tr0"] = copy_if_exists(row.get("hspice_tr0", ""), case_dir / "hspice" / "hspice.tr0")
        copied["hspice_lis"] = copy_if_exists(row.get("hspice_lis", ""), case_dir / "hspice" / "hspice.lis")
        copied["hspice_local_touchstone"] = copy_if_exists(h_tr0.parent / "input_channel.s2p", case_dir / "hspice" / "input_channel.s2p")
        if not copied["hspice_local_touchstone"]:
            copied["hspice_local_touchstone"] = copy_if_exists(h_tr0.parent / "input_channel.s4p", case_dir / "hspice" / "input_channel.s4p")
        copied["ngspice_deck"] = copy_if_exists(n_raw.with_suffix(".sp"), case_dir / "ngspice" / "ngspice_vector_fit_testbench.sp")
        copied["ngspice_raw"] = copy_if_exists(row.get("ngspice_raw", ""), case_dir / "ngspice" / "ngspice.raw")
        copied["ngspice_log"] = copy_if_exists(row.get("ngspice_log", ""), case_dir / "ngspice" / "ngspice.log")

        case_readme = [
            f"# {channel_id} - {case}",
            "",
            f"- Candidate: `{candidate_id}`",
            f"- Independent class: `{row.get('independent_trust_class', '')}`",
            f"- HSPICE audit: `{audit_class}`",
            f"- RX audit: `{row.get('rx_hspice_audit_class', '')}`",
            f"- TX/reflection audit: `{row.get('reflection_hspice_audit_class', '')}`",
            f"- Edge: `{row.get('edge_ps', '')} ps`",
            "",
            "## Key Figures",
            "",
            "- `figures/rx_overlay.png`",
            "- `figures/tx_overlay.png`",
            "- `figures/hspice_ngspice_two_panel.png`",
            "- `figures/frequency_fit.png`",
            "- `figures/passivity.png`",
            "",
            "## Metrics",
            "",
            *case_metric_table(row),
            "",
            "## Included Files",
            "",
            "- `models/ngspice_vector_fit_model.sp`",
            "- `inputs/`: original Touchstone",
            "- `hspice/`: native S-element deck plus `.tr0`/`.lis`",
            "- `ngspice/`: vector-fit testbench plus `.raw`/`.log`",
            "",
        ]
        (case_dir / "README.md").write_text("\n".join(case_readme), encoding="utf-8")

        index = {
            "case_id": case_id,
            "channel_id": channel_id,
            "candidate_id": candidate_id,
            "case": case,
            "edge_ps": row.get("edge_ps", ""),
            "independent_trust_class": row.get("independent_trust_class", ""),
            "hspice_audit_class": audit_class,
            "rx_hspice_audit_class": row.get("rx_hspice_audit_class", ""),
            "reflection_hspice_audit_class": row.get("reflection_hspice_audit_class", ""),
            "case_dir": rel(case_dir),
        }
        index.update(copied)
        index_rows.append(index)

    write_csv(out_dir / "index.csv", index_rows)
    class_counts: dict[str, int] = {}
    for row in index_rows:
        klass = str(row.get("hspice_audit_class", "UNKNOWN"))
        class_counts[klass] = class_counts.get(klass, 0) + 1

    lines = [
        "# Vector-Fit Audit Share Pack",
        "",
        f"Source study: `{rel(study_dir)}`",
        "",
        "This folder packages the audited scikit-rf vector-fit cases with the exact models, HSPICE decks, ngspice decks, raw outputs, and one-side-per-figure overlays.",
        "",
        "## Counts",
        "",
    ]
    for klass in sorted(class_counts):
        lines.append(f"- `{klass}`: `{class_counts[klass]}` cases")
    lines.extend(
        [
            "",
            "## Folder Layout",
            "",
            "- `audit_pass/`: cases whose HSPICE audit passed.",
            "- `audit_warn/`: cases with usable but caveated HSPICE agreement, usually fast-edge RX timing/shape sensitivity.",
            "- `audit_fail/`: cases where HSPICE-vs-ngspice mismatch is large enough to reject the vector-fit model for that case.",
            "- `index.csv`: machine-readable index of copied files and metrics.",
            "",
            "The class names are audit outcomes, not value judgments about the original Touchstone channel.",
        ]
    )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote share pack: {out_dir}")
    print(f"Packaged cases: {len(index_rows)}")
    for klass in sorted(class_counts):
        print(f"{klass}: {class_counts[klass]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
