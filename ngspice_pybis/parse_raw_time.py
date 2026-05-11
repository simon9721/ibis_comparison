import re
import struct
import sys

if len(sys.argv) != 2:
    print("usage: parse_raw_time.py <raw-file>")
    raise SystemExit(1)

path = sys.argv[1]
with open(path, "rb") as f:
    header = f.read(4096)
    m = re.search(rb"No\. Variables:\s+(\d+)", header)
    if not m:
        raise RuntimeError("No. Variables not found")
    nv = int(m.group(1))

    bi = header.find(b"Binary:\x0a") + 8
    if bi < 8:
        raise RuntimeError("Binary marker not found")

    f.seek(0, 2)
    sz = f.tell()
    nrows = (sz - bi) // (nv * 8)

    f.seek(bi + (nrows - 1) * nv * 8)
    t = struct.unpack("<d", f.read(8))[0]

pct = t / 1e-6 * 100.0
print(f"nv={nv} n={nrows:,} t={t*1e9:.3f}ns ({pct:.1f}%)")
