#!/usr/bin/env python3
"""Robustly scan for glyph-fetch shifts (lsl #5 / #4 / mul 0x20) in ARM & Thumb."""
import sys
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_ARM

path = sys.argv[1]; base = int(sys.argv[2], 16)
data = open(path, "rb").read()


def robust(md, mode):
    step = 2 if mode == CS_MODE_THUMB else 4
    off = 0
    out = []
    while off < len(data):
        got = False
        for ins in md.disasm(data[off:], base + off):
            out.append(ins); off += ins.size; got = True
            if off > len(data):
                break
        if not got:
            off += step
    return out


for mode, label in ((CS_MODE_ARM, "A"), (CS_MODE_THUMB, "T")):
    md = Cs(CS_ARCH_ARM, mode)
    ins = robust(md, mode)
    for i, x in enumerate(ins):
        s = (x.mnemonic + " " + x.op_str)
        hit = ("lsl #5" in s or "lsl #4" in s
               or (x.mnemonic in ("lsls", "lsl") and x.op_str.endswith(("#5", "#4")))
               or (x.mnemonic == "mov" and "lsl #5" in s))
        if hit:
            ctx = ins[max(0, i-2):i+3]
            print(f"[{label}] 0x{x.address:08X}: " + " | ".join(
                f"{c.mnemonic} {c.op_str}" for c in ctx))
