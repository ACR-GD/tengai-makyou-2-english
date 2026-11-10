#!/usr/bin/env python3
"""Build an English ROM by rebuilding .scs files (variable size) and appending
them at the end of the ROM, updating only their FAT entries.

No existing file moves; the NDS header (and its CRC) is untouched. Emulators
read file data via FAT offsets, so appended data past the original end is fine.
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
from nds_extract import NDS
from scs_build_en import build_all


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("out_rom")
    ap.add_argument("--json", default="translation/tengai2_script.translated.json")
    ap.add_argument("--script-root", default="extracted/data/script")
    ap.add_argument("--wrap", type=int, default=18)
    a = ap.parse_args()

    files_map, stats = build_all(a.json, a.script_root, a.wrap)
    print("rebuild stats:", stats)

    nds = NDS(a.rom)
    path_to_fid = {p: fid for p, fid in nds.parse_fnt()}
    rom = bytearray(nds.data)
    fat_off = nds.fat_off

    appended = changed_bytes = 0
    for path, newbytes in files_map.items():
        fid = path_to_fid.get(path)
        if fid is None:
            continue
        start, end = nds.fat[fid]
        if bytes(nds.data[start:end]) == newbytes:
            continue
        while len(rom) % 4:
            rom += b"\x00"
        off = len(rom)
        rom += newbytes
        struct.pack_into("<I", rom, fat_off + fid * 8, off)
        struct.pack_into("<I", rom, fat_off + fid * 8 + 4, off + len(newbytes))
        appended += 1
        changed_bytes += len(newbytes)

    while len(rom) % 4:
        rom += b"\x00"

    with open(a.out_rom, "wb") as f:
        f.write(rom)
    print(f"appended {appended} .scs files ({changed_bytes} bytes)")
    print(f"ROM: {len(nds.data)} -> {len(rom)} bytes")
    print(f"wrote {a.out_rom}")


if __name__ == "__main__":
    main()
