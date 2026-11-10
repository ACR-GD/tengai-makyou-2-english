#!/usr/bin/env python3
"""Disassemble a file range in ARM or Thumb, resolving PC-relative literals."""
import sys
import struct
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_ARM

path = sys.argv[1]
base = int(sys.argv[2], 16)       # RAM base of file offset 0
start = int(sys.argv[3], 16)      # file offset start
length = int(sys.argv[4], 16)
mode_s = sys.argv[5] if len(sys.argv) > 5 else "thumb"

data = open(path, "rb").read()
mode = CS_MODE_THUMB if mode_s == "thumb" else CS_MODE_ARM
md = Cs(CS_ARCH_ARM, mode)
md.detail = True

seg = data[start:start + length]
addr0 = base + start


def gen(seg, addr0):
    off = 0
    step = 2 if mode == CS_MODE_THUMB else 4
    while off < len(seg):
        got = False
        for ins in md.disasm(seg[off:], addr0 + off):
            yield ins
            got = True
            off += ins.size
        if not got:
            print(f"{addr0+off:08X}: .data    {seg[off:off+step].hex()}")
            off += step


for ins in gen(seg, addr0):
    extra = ""
    # resolve ldr rX, [pc, #imm] literal pools
    if ins.mnemonic.startswith("ldr") and "pc" in ins.op_str:
        # compute literal address
        try:
            imm = int(ins.op_str.split("#")[-1].rstrip("]"), 16)
            pcv = (ins.address + (4 if mode == CS_MODE_THUMB else 8)) & ~3
            lit = pcv + imm
            foff = lit - base
            if 0 <= foff + 4 <= len(data):
                val = struct.unpack("<I", data[foff:foff + 4])[0]
                extra = f"   ; =0x{val:08X}"
        except Exception:
            pass
    print(f"{ins.address:08X}: {ins.mnemonic:8} {ins.op_str}{extra}")
