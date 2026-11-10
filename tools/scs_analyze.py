#!/usr/bin/env python3
"""Analyze .scs script-string files with param-aware opcode handling.

Decodes the whole string region as a word stream so SJIS text is never split
by the pointer table, and splits into messages on the in-band terminator.
"""
import struct
import sys
from collections import Counter


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


# opcode -> number of u16 parameter words that follow it
OPCODE_PARAMS = {
    0x000D: 0,   # newline
    0x0010: 1,   # text/window/speaker attribute (param 1..3 seen)
    0x0011: 1,   # wait / timing (param = frames)
    0x0012: 0,   # part of terminator
    0x000C: 0,   # end-of-message marker
    0x0000: 0,   # filler / sub-terminator
}


def tokenize(blob):
    """Return list of tokens: ('txt', bytes) or ('op', opcode, [params])."""
    toks = []
    i = 0
    n = len(blob)
    run = bytearray()

    def flush():
        if run:
            toks.append(("txt", bytes(run)))
            run.clear()

    while i + 1 < n:
        w = u16(blob, i)
        lo = w & 0xFF
        if lo < 0x20:                       # control opcode
            flush()
            nparams = OPCODE_PARAMS.get(w, 0)
            params = []
            i += 2
            for _ in range(nparams):
                if i + 1 < n:
                    params.append(u16(blob, i))
                    i += 2
            toks.append(("op", w, params))
        else:                               # SJIS text word
            run += blob[i:i + 2]
            i += 2
    if i < n:
        run.append(blob[i])
    flush()
    return toks


def render(toks):
    out = []
    for t in toks:
        if t[0] == "txt":
            out.append(t[1].decode("shift_jis", "replace"))
        else:
            _, op, params = t
            if op == 0x000D:
                out.append("\n")
            elif params:
                out.append(f"{{{op:02X}:{','.join(f'{p:04X}' for p in params)}}}")
            else:
                out.append(f"{{{op:02X}}}")
    return "".join(out)


def main():
    path = sys.argv[1]
    data = open(path, "rb").read()
    hdr = u32(data, 0)
    region = data[hdr:]
    toks = tokenize(region)

    # opcode frequency
    opcounts = Counter(t[1] for t in toks if t[0] == "op")
    print(f"file={path} size={len(data)} header=0x{hdr:X}")
    print("opcodes:", {f"{k:02X}": v for k, v in sorted(opcounts.items())})
    print("=" * 60)

    # split messages on terminator: 0x12 then 0x0C (the 12 00 00 00 0c 00 seq)
    msg = []
    idx = 0
    for t in toks:
        msg.append(t)
        if t[0] == "op" and t[1] == 0x000C:
            text = render(msg).strip()
            if text:
                print(f"\n[msg {idx}]\n{text}")
                idx += 1
            msg = []
    if msg:
        text = render(msg).strip()
        if text:
            print(f"\n[msg {idx}]\n{text}")


if __name__ == "__main__":
    main()
