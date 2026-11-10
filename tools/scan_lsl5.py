#!/usr/bin/env python3
import sys
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_ARM

path = sys.argv[1]; base = int(sys.argv[2], 16)
data = open(path, "rb").read()


def run(mode, label):
    md = Cs(CS_ARCH_ARM, mode)
    ins = list(md.disasm(data, base))
    for i, x in enumerate(ins):
        s = x.mnemonic + " " + x.op_str
        if ("lsl #5" in s) or (x.mnemonic.startswith("lsl") and s.endswith("#5")) or \
           (x.mnemonic in ("lsls", "lsl") and "#5" in x.op_str):
            ctx = ins[max(0, i - 3):i + 2]
            # only show if a nearby ldr (pointer load) exists
            window = ins[max(0, i - 6):i + 3]
            if any(w.mnemonic.startswith("ldr") for w in window):
                print(f"[{label}] 0x{x.address:08X}")
                for c in ctx:
                    print(f"    {c.address:08X}: {c.mnemonic:8} {c.op_str}")
                print()


run(CS_MODE_ARM, "A")
run(CS_MODE_THUMB, "T")
