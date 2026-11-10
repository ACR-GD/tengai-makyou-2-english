#!/usr/bin/env python3
"""Model + round-trip validator for .scs files.

Model:
  file = u32 hdr | pointer-table (n = (hdr-4)/2 u16 entries) | region
  region starts at offset `hdr`; pointer entry i = byte offset (relative to hdr)
  of script block i.  Blocks partition the region in increasing order.

This validator parses, splits the region into blocks at the pointer offsets,
then reassembles and checks the result is byte-identical to the input.
"""
import os
import struct
import sys


def parse(data):
    hdr = struct.unpack_from("<I", data, 0)[0]
    n = (hdr - 4) // 2
    offs = [struct.unpack_from("<H", data, 4 + 2 * i)[0] for i in range(n)]
    region = data[hdr:]
    return hdr, offs, region


def split_blocks(offs, region):
    starts = list(offs)
    prefix = region[:starts[0]] if starts else region
    blocks = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(region)
        blocks.append(region[s:e])
    return prefix, blocks


def reassemble(hdr, n, prefix, blocks):
    region = bytearray(prefix)
    offs = []
    for b in blocks:
        offs.append(len(region))
        region += b
    out = bytearray()
    out += struct.pack("<I", hdr)
    for i in range(n):
        out += struct.pack("<H", offs[i] if i < len(offs) else 0)
    # pad pointer table to hdr if needed
    while len(out) < hdr:
        out += b"\x00"
    out += region
    return bytes(out)


def roundtrip(data):
    hdr, offs, region = parse(data)
    prefix, blocks = split_blocks(offs, region)
    return reassemble(hdr, len(offs), prefix, blocks)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "extracted/data/script"
    files = []
    for dp, _, fs in os.walk(root):
        for fn in fs:
            if fn.endswith(".scs"):
                files.append(os.path.join(dp, fn))
    ok = bad = skip = 0
    bad_list = []
    for p in files:
        d = open(p, "rb").read()
        if len(d) < 4:
            skip += 1
            continue
        hdr = struct.unpack_from("<I", d, 0)[0]
        if hdr < 4 or hdr > len(d) or (hdr - 4) % 2 != 0:
            skip += 1
            continue
        rt = roundtrip(d)
        if rt == d:
            ok += 1
        else:
            bad += 1
            if len(bad_list) < 20:
                # find first diff
                diff = next((i for i in range(min(len(rt), len(d))) if rt[i] != d[i]), -1)
                bad_list.append((p, len(d), len(rt), diff))
    print(f"files={len(files)} ok={ok} bad={bad} skipped={skip}")
    for p, a, b, diff in bad_list:
        print(f"  BAD {os.path.relpath(p, root)} len {a}->{b} firstdiff@0x{diff:X}")


if __name__ == "__main__":
    main()
