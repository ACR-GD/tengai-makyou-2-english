#!/usr/bin/env python3
"""Scan an ARM9/overlay image for SJIS lead-byte range checks (Thumb & ARM)."""
import sys
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_ARM

path = sys.argv[1]
base = int(sys.argv[2], 16)
data = open(path, "rb").read()

IMMS = {0x81, 0x9f, 0xe0, 0xfc, 0xa0, 0x40, 0x7f}


def scan(mode, label):
    md = Cs(CS_ARCH_ARM, mode)
    md.detail = False
    step = 2 if mode == CS_MODE_THUMB else 4
    hits = []
    # disassemble linearly; collect cmp #imm sites
    cmps = []  # (addr, imm)
    for ins in md.disasm(data, base):
        if ins.mnemonic.startswith("cmp") and "#0x" in ins.op_str:
            try:
                imm = int(ins.op_str.split("#")[-1], 16)
            except ValueError:
                continue
            if imm in IMMS:
                cmps.append((ins.address, imm))
    # cluster: window of 0x40 bytes containing both 0x81 and 0xe0 (or 0x9f)
    for i, (a, imm) in enumerate(cmps):
        window = [c for c in cmps if 0 <= c[0] - a <= 0x60]
        imms = {w[1] for w in window}
        if 0x81 in imms and (0xe0 in imms or 0x9f in imms):
            hits.append((a, sorted(imms)))
    # dedupe by ~proximity
    seen = []
    for a, imms in hits:
        if not seen or a - seen[-1] > 0x80:
            seen.append(a)
            print(f"[{label}] 0x{a:08X}  imms={[hex(x) for x in imms]}")


scan(CS_MODE_THUMB, "T")
scan(CS_MODE_ARM, "A")
