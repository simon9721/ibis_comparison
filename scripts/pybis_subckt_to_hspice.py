#!/usr/bin/env python3
"""Translate a pybis (ngspice) InputDriven subcircuit into HSPICE syntax.

The point is decoupling, not shipping: to tell a SPICE-engine difference from an
IBIS-implementation difference, the same pybis model has to run in both engines.
pybis emits ngspice-flavoured syntax that HSPICE rejects, so this rewrites the
`.sub` into the equivalent HSPICE deck. Same topology, same tables, same
expressions -- only the surface syntax changes:

    .SUBCKT ... params: X=a     ->  .SUBCKT ... X=a          (drop "params:")
    {name}                      ->  name                     (param braces)
    Bxxx n+ n- V = EXPR         ->  Exxx n+ n- VOL='EXPR'     (behavioural V)
    Bxxx n+ n- I = {EXPR}       ->  Gxxx n+ n- CUR='EXPR'     (behavioural I)
    Td={x}                      ->  TD=x                      (T-line delay)

Functions used inside the expressions -- pwl, min, max, abs, the ternary, and
the TIME variable -- are all valid in HSPICE behavioural E/G sources, so the
bodies are carried over unchanged apart from brace removal.

    py -3.14 scripts/pybis_subckt_to_hspice.py in.sub out.sub
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def _strip_braces(text: str) -> str:
    """`{expr}` -> `expr`. pybis only braces bare param names and whole RHS
    expressions, never nests them, so a single non-greedy pass is exact."""
    return re.sub(r"\{([^{}]*)\}", r"\1", text)


def _wrap(line: str, width: int = 780) -> str:
    """HSPICE continuation for lines past its record limit.

    ngspice allows arbitrarily long lines; HSPICE overflows its internal record
    buffer on the giant pwl tables. Break at commas -- always inside the pwl
    argument list, so a mid-expression split is safe -- and continue with `+`,
    which HSPICE joins back into one logical line.
    """
    if len(line) <= width:
        return line
    pieces: list[str] = []
    current = ""
    for token in line.split(","):
        candidate = (current + "," + token) if current else token
        if len(candidate) > width and current:
            pieces.append(current + ",")
            current = token
        else:
            current = candidate
    pieces.append(current)
    return ("\n+ ").join(pieces)


def _pwl_table_to_pairs(table: str) -> str:
    """`x0, y0, x1, y1, ...` -> `x0,y0 x1,y1 ...` for a G/E PWL(1) element."""
    nums = [t.strip() for t in table.split(",") if t.strip()]
    return " ".join(f"{nums[i]},{nums[i + 1]}" for i in range(0, len(nums) - 1, 2))


def _parse_pwl_body(expr: str):
    """`[SCALE *] pwl(CONTROL, TABLE)` -> (scale|None, control, table), or None.

    Paren-aware, because CONTROL can itself be `min(max(V(NX),0),LIM)` -- nested
    commas a regex would split on. HSPICE cannot hold a 100+ point table inside a
    VOL/CUR expression, so a body of this exact shape is turned into a native
    PWL(1) lookup; anything else is left as an ordinary behavioural source.
    """
    expr = expr.strip()
    idx = expr.find("pwl(")
    if idx == -1:
        return None
    scale = None
    if idx > 0:
        head = expr[:idx].strip()
        if not head.endswith("*"):
            return None            # something other than a pure scale prefix
        scale = head[:-1].strip()
    # find the matching close paren for this pwl(
    depth, i = 0, idx + 3
    start = i + 1
    while i < len(expr):
        if expr[i] == "(":
            depth += 1
        elif expr[i] == ")":
            depth -= 1
            if depth == 0:
                break
        i += 1
    if depth != 0 or i != len(expr) - 1:
        return None                # pwl(...) is not the whole (post-scale) body
    inner = expr[start:i]
    # split control from table at the first top-level comma
    depth, split = 0, -1
    for j, ch in enumerate(inner):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            split = j
            break
    if split == -1:
        return None
    return scale, inner[:split].strip(), inner[split + 1:].strip()


def translate(src: str) -> str:
    out: list[str] = []
    lut = 0
    for raw in src.splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.lower().startswith(".subckt"):
            out.append(_strip_braces(line).replace(" params:", ""))
            continue

        m = re.match(r"^(\s*)B(\S+)\s+(\S+)\s+(\S+)\s+([VI])\s*=\s*(.*)$", line)
        if m:
            indent, name, np_, nn, kind, expr = m.groups()
            expr = _strip_braces(expr).strip()
            body = _parse_pwl_body(expr)
            if body:
                # Restructure `[scale *] pwl(ctrl, table)` into a PWL(1) lookup.
                # The control must be a node, so wrap a non-trivial control
                # expression in its own tiny E-source first.
                lut += 1
                scale_pfx, ctrl, table = body
                pairs = _pwl_table_to_pairs(table)
                two = re.fullmatch(r"V\(\s*(\w+)\s*,\s*(\w+)\s*\)", ctrl)
                one = re.fullmatch(r"V\(\s*(\w+)\s*\)", ctrl)
                if two:
                    cp, cn = two.group(1), two.group(2)
                elif one:
                    cp, cn = one.group(1), "0"
                else:
                    cp, cn = f"CTRL{lut}", "0"
                    out.append(f"{indent}ECTRL{lut} CTRL{lut} 0 VOL='{ctrl}'")
                lut_node = f"LUT{lut}"
                out.append(_wrap(f"{indent}GLUT{lut} {lut_node} 0 PWL(1) {cp} {cn} {pairs}"))
                out.append(f"{indent}RLUT{lut} {lut_node} 0 1")
                value = f"{_strip_braces(scale_pfx).strip()}*V({lut_node})" if scale_pfx else f"V({lut_node})"
                if kind == "V":
                    out.append(f"{indent}E{name} {np_} {nn} VOL='{value}'")
                else:
                    out.append(f"{indent}G{name} {np_} {nn} CUR='{value}'")
                continue
            # Ordinary short behavioural source.
            if kind == "V":
                out.append(_wrap(f"{indent}E{name} {np_} {nn} VOL='{expr}'"))
            else:
                out.append(_wrap(f"{indent}G{name} {np_} {nn} CUR='{expr}'"))
            continue

        out.append(_strip_braces(line).replace("Td=", "TD="))
    return "\n".join(out) + "\n"


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: pybis_subckt_to_hspice.py <in.sub> <out.sub>")
        return 2
    src = Path(sys.argv[1]).read_text(encoding="utf-8")
    Path(sys.argv[2]).write_text(translate(src), encoding="utf-8")
    print(f"wrote {sys.argv[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
