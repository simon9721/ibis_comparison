"""Write results/INDEX.md: every study folder in results/, grouped by line of work, with its
description (from its own write-up), its write-up files and the script that writes it.

Run after adding or archiving a study: `python scripts/make_results_index.py`. Folders are
placed into groups by name (GROUPS below); one that matches no group lands in "Other", which
is the cue to add a pattern.
"""
import ast
import re
from pathlib import Path

from lib.paths import repo_root

ROOT = repo_root(__file__)
RES = ROOT / "results"
OUT = RES / "INDEX.md"

GROUPS = [
    ("Track 1 and track 2: the gate-state chain", "The current work. The chain is fitted to the IBIS file's Ku(t) "
     "(track 1) or to a measured Ku-vs-gate map (track 2).",
     r"^(gate_chain_prototype|stage_count_from_file|build_chain_model|gate_cascade_prototype|gate_ramp_prototype|"
     r"gate_step_prototype|gate_chain_train_calib|predriver_stages|physics_map_gate|current_limited_stages|gate_physics|"
     r"full_swing_fixtures|full_swing_silicon_kukd|residual_depth_rule|variant_gate_probe|silicon_kukd_conditioning_2026-09|"
     r"ex2_ccomp_correction|edge_rate_check|two_pulse|review_|ccomp_from_file|inv_chain_single_curve|"
     r"inv_chain_fall_rate|shape_from_stressed_run|io_buf_pulldown|inv_chain_last_stage|"
     r"selector_from_one_run|train_check_today|track1_summary)"),
    ("Pulse trains", "", r"^(pulse_train|track2_train_check|variant_train_check)"),
    ("Open-drain", "", r"^(opendrain_|s2ibispy_parameter_selection_ex2_od_)"),
    ("Native IBIS behaviour", "", r"^native_"),
    ("Stress pedestal and command layer (09-01 to 09-08)", "Earlier line of work, kept because current scripts or "
     "deck notes still read it.",
     r"^(cross_device_stress|bump_marker|pu_off_|delay_pedestal|settled_offset_diagnosis|timing_shift_|v_indexed_|"
     r"command_mechanism|cmd_clean_slides)"),
    ("Buffers, variants and reference runs - inputs", "Read by many scripts; regenerate rather than edit.",
     r"^(ex2_variants|inv_chain_variants|variant_stress_cases|stress_method_matrix|three_buffer_|io_buf_|ex2_s2ibispy|"
     r"inv_chain_s2ibispy|silicon_kukd_recovery|_golden_hspice_cache)"),
    ("Meeting decks, figures and film", "", r"^(meeting_deck_|method_animations)"),
]

scripts = {p: p.read_text(encoding="utf-8", errors="replace")
           for p in list((ROOT / "scripts").glob("*.py")) + list((ROOT / "scripts" / "archive").glob("*.py"))
           + list((ROOT / "scripts" / "deck_0918").glob("*.py"))
           if p.name != Path(__file__).name}  # this file names folders in GROUPS; it writes none of them


def writers(name):
    """Scripts that write the folder: those assigning it to an output variable, else those
    that name it."""
    out_pat = re.compile(r"^\s*(OUT\w*|HERE|DEST|RES_DIR|OUTDIR|OUTPUT\w*|DECK_DIR|FIG\w*)\s*=.*" + re.escape(name), re.M)
    hits = [p for p, t in scripts.items() if out_pat.search(t)]
    if not hits:
        hits = [p for p, t in scripts.items() if name in t]
    hits.sort(key=lambda p: ("archive" in p.parts, p.name))
    return hits[:2]


def docstring_line(path):
    """First non-empty line of a script's module docstring."""
    try:
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8", errors="replace"))) or ""
    except SyntaxError:
        doc = ""
    return next((l.strip() for l in doc.splitlines() if l.strip()), "")


def describe(d, by):
    md = next((d / f for f in ("FINDINGS.md", "README.md") if (d / f).exists()), None) \
        or next(iter(sorted(d.glob("*.md"))), None)
    if md is None:
        return "(no write-up)"
    lines = md.read_text(encoding="utf-8", errors="replace").splitlines()
    if any(l.startswith("*Generated 2026-09-21") for l in lines[:5]):
        # a generated README quotes every script naming the folder; the writer's docstring is the one
        doc = docstring_line(by[0]) if by else ""
        return doc or "(generated README; producer not found)"
    for l in lines:
        s = l.strip()
        if s.startswith("# "):
            h = s[2:].strip()
            if h not in (d.name, f"results/{d.name}") and not h.lower().startswith(d.name.lower()):
                return re.sub(r"\s*-\s*findings$", "", h)
        elif s and not s.startswith(("#", "*", ">", "|", "-", "`")):
            return s
    return "(write-up has no summary line)"


def date(name):
    m = re.search(r"20\d\d-\d\d-\d\d", name)
    return m.group(0) if m else "0000"


dirs = sorted(p for p in RES.iterdir() if p.is_dir() and p.name != "archive")
placed, parts = set(), []
for title, note, pat in GROUPS + [("Other", "", r".")]:
    members = [d for d in dirs if d.name not in placed and re.search(pat, d.name)]
    if not members:
        continue
    placed |= {d.name for d in members}
    members.sort(key=lambda d: (date(d.name), d.name), reverse=True)
    parts.append(f"## {title}\n")
    if note:
        parts.append(note + "\n")
    parts.append("| folder | what it is | write-up | written by |\n|---|---|---|---|")
    for d in members:
        docs = " ".join(f.name for f in sorted(d.glob("*.md")))
        generated = "*Generated 2026-09-21" in (d / "README.md").read_text(encoding="utf-8", errors="replace")[:400] \
            if (d / "README.md").exists() else False
        docs = docs + (" (generated)" if generated and docs == "README.md" else "")
        by = writers(d.name)
        who = ", ".join(f"`{p.relative_to(ROOT).as_posix()}`" for p in by) or "-"
        parts.append(f"| `{d.name}` | {describe(d, by).replace('|', '/')[:140]} | {docs or '-'} | {who} |")
    parts.append("")

loose = sorted(p.name for p in RES.iterdir() if p.is_file() and p.name not in ("INDEX.md", "ARCHIVE_INDEX.md"))
stems = {}
for n in loose:
    stem = re.sub(r"(_(ex2|inv|io_buf|iobuf|od|log)[\w.-]*)?\.(log|txt)$", "", n)
    stems.setdefault(stem, []).append(n)
parts.append("## Loose files at the `results/` root\n")
parts.append("Stdout of runs whose study folder is above; nothing reads them. The one exception is\n"
             "`input_threshold_check_2026-09-10.txt`, a short result note the 09-18 deck cites.\n")
parts += [f"- `{s}*` ({len(v)} file{'s' if len(v) > 1 else ''})" for s, v in sorted(stems.items())]

head = f"""# results/ - study index

One line per study folder, grouped by line of work, newest first within a group.
Generated by `python scripts/make_results_index.py` - rerun it after adding or archiving a
study. {len(dirs)} folders.

- A study folder is `results/<topic>_<YYYY-MM-DD>/`, written by `scripts/<topic>.py` (the
  "written by" column), with its conclusions in `FINDINGS.md` (or `README.md`).
  "(generated)" means the README only says what the folder holds, not what it found.
- Archived studies (305 entries, on OneDrive as zips): [ARCHIVE_INDEX.md](ARCHIVE_INDEX.md).

"""
OUT.write_text(head + "\n".join(parts) + "\n", encoding="utf-8")
print(f"wrote {OUT}: {len(dirs)} folders in {sum(1 for p in parts if p.startswith('## ')) - 1} groups, {len(loose)} loose files")
other = [line for line in parts[parts.index("## Other\n") + 2:]] if "## Other\n" in parts else []
print("in Other:", [line.split("`")[1] for line in other if line.startswith("| `")] or "none")
