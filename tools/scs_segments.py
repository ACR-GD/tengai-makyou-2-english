#!/usr/bin/env python3
"""Dump each pointer-table segment of a .scs file with hex + decode.

Goal: understand whether pointer entries delimit complete strings, and whether
they fall on token boundaries.
"""
import struct
import sys


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def decode(blob):
    out = []
    i = 0
    run = bytearray()
    while i < len(blob):
        b = blob[i]
        # double-byte SJIS?
        if i + 1 < len(blob) and ((0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xFC)):
            t = blob[i + 1]
            if (0x40 <= t <= 0x7E) or (0x80 <= t <= 0xFC):
                run += blob[i:i + 2]
                i += 2
                continue
        if run:
            out.append(run.decode("shift_jis", "replace"))
            run = bytearray()
        out.append(f"<{b:02X}>")
        i += 1
    if run:
        out.append(run.decode("shift_jis", "replace"))
    return "".join(out)


def main():
    path = sys.argv[1]
    d = open(path, "rb").read()
    hdr = u32(d, 0)
    n = (hdr - 4) // 2
    offs = [u16(d, 4 + i * 2) for i in range(n)]
    print(f"file={path} size=0x{len(d):X} header=0x{hdr:X} entries={n}")
    print("raw offsets:", [f"0x{o:X}" for o in offs])
    starts = [hdr + o for o in offs]
    ends = starts[1:] + [len(d)]
    for i, (s, e) in enumerate(zip(starts, ends)):
        blob = d[s:e]
        parity = "ODD" if (s % 2) else "even"
        print(f"\n[{i}] off=0x{offs[i]:X} abs=0x{s:X}({parity})-0x{e:X} len={e-s}")
        print("  hex:", blob[:32].hex(" "))
        print("  dec:", decode(blob))


if __name__ == "__main__":
    main()
