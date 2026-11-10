#!/usr/bin/env python3
"""Apply a BPS1 patch (all four actions) and check every CRC32.

    python tools/bps_apply.py original.nds patch.bps patched.nds

Used to prove a release patch rebuilds the exact target ROM; any BPS tool
(Rom Patcher JS, Flips, beat) produces the same bytes.
"""
import argparse
import struct
import zlib


def _number(data, pos):
    value, shift = 0, 1
    while True:
        byte = data[pos]
        pos += 1
        value += (byte & 0x7F) * shift
        if byte & 0x80:
            return value, pos
        shift <<= 7
        value += shift


def apply_patch(source, patch):
    if patch[:4] != b"BPS1":
        raise ValueError("Not a BPS1 patch")
    if zlib.crc32(patch[:-4]) != struct.unpack_from("<I", patch, len(patch) - 4)[0]:
        raise ValueError("Patch file is corrupt (patch CRC32 mismatch)")
    source_crc, target_crc = struct.unpack_from("<II", patch, len(patch) - 12)
    if zlib.crc32(source) != source_crc:
        raise ValueError("Wrong source ROM (source CRC32 mismatch)")
    pos = 4
    source_size, pos = _number(patch, pos)
    target_size, pos = _number(patch, pos)
    meta_size, pos = _number(patch, pos)
    pos += meta_size
    if len(source) != source_size:
        raise ValueError("Wrong source ROM size")
    target = bytearray()
    source_rel = target_rel = 0
    end = len(patch) - 12
    while pos < end:
        data, pos = _number(patch, pos)
        action, length = data & 3, (data >> 2) + 1
        if action == 0:      # SourceRead
            start = len(target)
            target += source[start:start + length]
        elif action == 1:    # TargetRead
            target += patch[pos:pos + length]
            pos += length
        else:
            offset, pos = _number(patch, pos)
            offset = (-1 if offset & 1 else 1) * (offset >> 1)
            if action == 2:  # SourceCopy
                source_rel += offset
                target += source[source_rel:source_rel + length]
                source_rel += length
            else:            # TargetCopy (may overlap the bytes it writes)
                target_rel += offset
                for _ in range(length):
                    target.append(target[target_rel])
                    target_rel += 1
    if len(target) != target_size or zlib.crc32(target) != target_crc:
        raise ValueError("Patched ROM does not match the patch's target CRC32")
    return bytes(target)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("patch")
    ap.add_argument("output")
    args = ap.parse_args()
    with open(args.source, "rb") as f:
        source = f.read()
    with open(args.patch, "rb") as f:
        patch = f.read()
    with open(args.output, "xb") as f:
        f.write(apply_patch(source, patch))


if __name__ == "__main__":
    main()
