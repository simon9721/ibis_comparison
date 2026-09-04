"""Dump variable names from a ngspice RAW file header to stdout/file."""
import re
import sys

def get_vars(path):
    with open(path, "rb") as f:
        raw = f.read(8192)
    # Find Variables section
    text = raw.decode("latin-1", errors="replace")
    # Find all variable lines
    m = re.search(r"No\. Variables:\s+(\d+)", text)
    nv = int(m.group(1)) if m else "?"
    m2 = re.search(r"No\. Points:\s+(\d+)", text)
    npts = int(m2.group(1)) if m2 else "?"
    # Find "Variables:" section
    vi = text.find("Variables:")
    bi = text.find("Binary:")
    if vi >= 0 and bi > vi:
        var_block = text[vi:bi]
        lines = [l.strip() for l in var_block.splitlines() if l.strip()]
    else:
        lines = []
    return nv, npts, lines

if __name__ == "__main__":
    for path in sys.argv[1:]:
        nv, npts, lines = get_vars(path)
        out = path + ".vars.txt"
        with open(out, "w") as f:
            f.write(f"File: {path}\n")
            f.write(f"Num variables: {nv}, Num points: {npts}\n\n")
            for l in lines:
                f.write(l + "\n")
        print(f"Written: {out}")
