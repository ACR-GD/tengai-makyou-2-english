#!/usr/bin/env python3
"""Find candidate VWF patch sites: fixed +16 cursor advance after SJIS glyph index.

Usage:
  python3 tools/vwf_scan.py <bin> <ram_base_hex>

Examples:
  python3 tools/vwf_scan.py extracted/__system__/arm9.bin 0x02000000
  python3 tools/vwf_scan.py extracted/overlays/ov_011.bin 0x022B6000
"""
import re
import sys

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB


def scan(path: str, base: int):
    data = open(path, "rb").read()
    print(f"=== {path} ({len(data)} bytes, base 0x{base:X}) ===\n")

    # ARM32: add rX, rX, #16 / #0x10
    md = Cs(CS_ARCH_ARM, CS_MODE_ARM)
    arm_hits = []
    off = 0
    while off < len(data):
        try:
            for ins in md.disasm(data[off : off + 4], base + off, count=1):
                s = f"{ins.mnemonic} {ins.op_str}"
                if ins.mnemonic == "add" and re.search(r"#0x10\b|#16\b", ins.op_str):
                    arm_hits.append((off, ins.address, s))
                off += 4
                break
            else:
                off += 4
        except Exception:
            off += 4

    print(f"ARM add +16: {len(arm_hits)}")
    for foff, addr, s in arm_hits[:40]:
        print(f"  file+0x{foff:06X}  RAM 0x{addr:08X}  {s}")
    if len(arm_hits) > 40:
        print(f"  ... +{len(arm_hits) - 40} more")

    # Thumb: add rX, #16
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    thumb_hits = []
    off = 0
    while off + 2 <= len(data):
        try:
            for ins in md.disasm(data[off : off + 4], base + off, count=1):
                s = f"{ins.mnemonic} {ins.op_str}"
                if ins.mnemonic in ("add", "adds") and "#16" in ins.op_str:
                    thumb_hits.append((off, ins.address, s))
                off += max(ins.size, 2)
                break
            else:
                off += 2
        except Exception:
            off += 2

    print(f"\nThumb add #16: {len(thumb_hits)}")
    for foff, addr, s in thumb_hits[:40]:
        print(f"  file+0x{foff:06X}  RAM 0x{addr:08X}  {s}")
    if len(thumb_hits) > 40:
        print(f"  ... +{len(thumb_hits) - 40} more")

    # SJIS index recipe: mul + lsl #4 nearby
    print("\nSJIS index (mul …, lsl #4) windows:")
    blob = data
    pat = re.compile(
        rb"\x00\xA0\x17\x00"  # ldr r0, [pc, #imm] = 0x17A0 little in literal pool
    )
    for m in pat.finditer(blob):
        foff = m.start()
        ctx_off = max(0, foff - 32)
        print(f"  literal 0x17A0 @ file+0x{foff:X} (RAM ~0x{base + foff:X})")


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    scan(sys.argv[1], int(sys.argv[2], 16))


if __name__ == "__main__":
    main()
