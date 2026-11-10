#!/usr/bin/env python3
"""Minimal Nintendo DS (NitroFS) ROM extractor.

Parses the NDS header, File Name Table (FNT) and File Allocation Table (FAT)
and extracts every file from the ROM into an output directory, preserving the
original folder hierarchy. Also dumps ARM9/ARM7 binaries and overlays.
"""
import os
import struct
import sys


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


class NDS:
    def __init__(self, path):
        with open(path, "rb") as f:
            self.data = f.read()
        d = self.data
        self.title = d[0x00:0x0C].rstrip(b"\x00").decode("ascii", "replace")
        self.gamecode = d[0x0C:0x10].decode("ascii", "replace")
        self.makercode = d[0x10:0x12].decode("ascii", "replace")

        self.arm9_rom_off = u32(d, 0x20)
        self.arm9_entry = u32(d, 0x24)
        self.arm9_ram = u32(d, 0x28)
        self.arm9_size = u32(d, 0x2C)
        self.arm7_rom_off = u32(d, 0x30)
        self.arm7_entry = u32(d, 0x34)
        self.arm7_ram = u32(d, 0x38)
        self.arm7_size = u32(d, 0x3C)

        self.fnt_off = u32(d, 0x40)
        self.fnt_size = u32(d, 0x44)
        self.fat_off = u32(d, 0x48)
        self.fat_size = u32(d, 0x4C)

        self.arm9_ovl_off = u32(d, 0x50)
        self.arm9_ovl_size = u32(d, 0x54)
        self.arm7_ovl_off = u32(d, 0x58)
        self.arm7_ovl_size = u32(d, 0x5C)

        # FAT: array of (start, end) u32 pairs, indexed by file id
        self.fat = []
        for i in range(0, self.fat_size, 8):
            start = u32(d, self.fat_off + i)
            end = u32(d, self.fat_off + i + 4)
            self.fat.append((start, end))

    def file_bytes(self, fid):
        start, end = self.fat[fid]
        return self.data[start:end]

    def parse_fnt(self):
        """Return list of (path, file_id) for every file in NitroFS."""
        d = self.data
        base = self.fnt_off
        # Main table entry 0 holds the directory count
        total_dirs = u16(d, base + 6)

        # Read each directory's main-table entry
        dirs = {}  # dir_id -> (subtable_off, first_file_id, parent_id)
        for i in range(total_dirs):
            e = base + i * 8
            sub_off = u32(d, e)
            first_file = u16(d, e + 4)
            parent = u16(d, e + 6)
            dirs[0xF000 + i] = (sub_off, first_file, parent)

        results = []

        def walk(dir_id, prefix):
            sub_off, first_file, _ = dirs[dir_id]
            p = base + sub_off
            fid = first_file
            while True:
                t = d[p]
                p += 1
                if t == 0:
                    break
                length = t & 0x7F
                is_dir = bool(t & 0x80)
                name = d[p:p + length].decode("shift_jis", "replace")
                p += length
                if is_dir:
                    sub_dir_id = u16(d, p)
                    p += 2
                    walk(sub_dir_id, prefix + name + "/")
                else:
                    results.append((prefix + name, fid))
                    fid += 1

        walk(0xF000, "")
        return results

    def extract_all(self, out_dir):
        os.makedirs(out_dir, exist_ok=True)
        # Dump system binaries
        sysdir = os.path.join(out_dir, "__system__")
        os.makedirs(sysdir, exist_ok=True)
        with open(os.path.join(sysdir, "arm9.bin"), "wb") as f:
            f.write(self.data[self.arm9_rom_off:self.arm9_rom_off + self.arm9_size])
        with open(os.path.join(sysdir, "arm7.bin"), "wb") as f:
            f.write(self.data[self.arm7_rom_off:self.arm7_rom_off + self.arm7_size])

        # ARM9 overlays are FAT entries outside the name table; files are
        # named by FAT ID (ov_NNN.bin), which the build tools rely on.
        ovdir = os.path.join(out_dir, "overlays")
        os.makedirs(ovdir, exist_ok=True)
        for i in range(0, self.arm9_ovl_size, 32):
            fid = struct.unpack_from("<I", self.data, self.arm9_ovl_off + i + 24)[0]
            with open(os.path.join(ovdir, f"ov_{fid:03d}.bin"), "wb") as f:
                f.write(self.file_bytes(fid))

        files = self.parse_fnt()
        count = 0
        for path, fid in files:
            blob = self.file_bytes(fid)
            full = os.path.join(out_dir, "data", path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as f:
                f.write(blob)
            count += 1
        return files, count


def main():
    rom = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "extracted"
    nds = NDS(rom)
    print(f"Title:    {nds.title}")
    print(f"GameCode: {nds.gamecode}  Maker: {nds.makercode}")
    print(f"ARM9: off=0x{nds.arm9_rom_off:X} size=0x{nds.arm9_size:X}")
    print(f"ARM7: off=0x{nds.arm7_rom_off:X} size=0x{nds.arm7_size:X}")
    print(f"FNT:  off=0x{nds.fnt_off:X} size=0x{nds.fnt_size:X}")
    print(f"FAT:  off=0x{nds.fat_off:X} size=0x{nds.fat_size:X} -> {len(nds.fat)} files")
    files, count = nds.extract_all(out)
    print(f"Extracted {count} files into {out}/data/")
    # Print directory tree summary
    print("\n--- File list (first 80) ---")
    for path, fid in files[:80]:
        start, end = nds.fat[fid]
        print(f"  [{fid:4d}] {end-start:9d}  {path}")
    if len(files) > 80:
        print(f"  ... and {len(files)-80} more")


if __name__ == "__main__":
    main()
