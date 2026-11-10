#!/usr/bin/env python3
"""Build an English ROM via in-place, size-preserving .scs reinsertion.

Because each .scs keeps its exact byte length, the .scs pointer table and the
whole NitroFS layout (FNT/FAT) stay valid, so the ROM rebuild is just a byte
overwrite at each file's FAT offset -- the safest possible patch.

English text is poured into the existing Japanese text-run byte slots; control
codes are left untouched. Encoding is selectable:
  --enc ascii      single-byte ASCII  (compact; renders only if engine supports
                                        half-width inline -- to be verified)
  --enc fullwidth  full-width SJIS     (always renders, 2 bytes/char, wide)
"""
import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
from nds_extract import NDS

TERMINATOR = 0x0012


def is_sjis_char(lead, trail):
    return ((0x81 <= lead <= 0x9F) or (0xE0 <= lead <= 0xFC)) and \
           ((0x40 <= trail <= 0x7E) or (0x80 <= trail <= 0xFC))


def split_messages(region):
    """Yield (msg_text_runs, msg_clean) where text_runs = [(off,len)] in region."""
    msgs = []
    i = 0
    n = len(region)
    runs = []
    clean = []
    run_start = None
    run_len = 0

    def close_run():
        nonlocal run_start, run_len
        if run_start is not None:
            runs.append((run_start, run_len))
            run_start, run_len = None, 0

    while i + 1 < n:
        lead, trail = region[i], region[i + 1]
        w = lead | (trail << 8)
        if is_sjis_char(lead, trail):
            if run_start is None:
                run_start = i
            run_len += 2
            clean.append(region[i:i + 2].decode("shift_jis", "replace"))
            i += 2
        else:
            close_run()
            if w == 0x000D:
                clean.append("\n")
            i += 2
            if w == TERMINATOR:
                msgs.append((runs, "".join(clean)))
                runs, clean = [], []
    close_run()
    if runs or clean:
        msgs.append((runs, "".join(clean)))
    return msgs


def has_japanese(s):
    return any(0x3040 <= ord(c) <= 0x30FF or 0x4E00 <= ord(c) <= 0x9FFF
               or 0xFF00 <= ord(c) <= 0xFFEF for c in s)


TRANSLIT = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2026": "...", "\u2014": "-", "\u2013": "-", "\u3000": " ",
    "\u30fb": "-", "\uff5c": "|",
}


def translit(s):
    return "".join(TRANSLIT.get(ch, ch) for ch in s)


def to_ascii(s):
    return translit(s).encode("ascii", "replace")  # non-ascii -> '?'


def to_fullwidth(s):
    """Map ASCII letters/digits/space to full-width SJIS bytes."""
    out = bytearray()
    for ch in translit(s):
        o = ord(ch)
        if ch == " ":
            out += b"\x81\x40"
        elif 0x21 <= o <= 0x7E:
            try:
                out += chr(0xFF00 + (o - 0x20)).encode("shift_jis")
            except Exception:
                out += b"\x81\x40"
        else:
            out += b"\x81\x40"
    return bytes(out)


def pour(region, msgs, en_list, enc):
    """Overwrite text-run bytes with English; preserve byte length exactly."""
    buf = bytearray(region)
    ji = 0
    for runs, clean in msgs:
        if not has_japanese(clean):
            continue
        en = en_list[ji] if ji < len(en_list) else ""
        ji += 1
        total = sum(l for _, l in runs)
        if total == 0:
            continue
        data = to_ascii(en) if enc == "ascii" else to_fullwidth(en)
        # fit to total budget
        if len(data) > total:
            data = data[:total]
        else:
            data = data + b"\x20" * (total - len(data))   # pad with spaces
        pos = 0
        for off, length in runs:
            buf[off:off + length] = data[pos:pos + length]
            pos += length
    return bytes(buf), ji


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("out_rom")
    ap.add_argument("--enc", choices=["ascii", "fullwidth"], default="ascii")
    ap.add_argument("--json", default="translation/tengai2_script.translated.json")
    args = ap.parse_args()

    recs = json.load(open(args.json, encoding="utf-8"))
    en_by_file = {}
    for r in recs:
        en_by_file.setdefault(r["file"], []).append(r["en"])

    nds = NDS(args.rom)
    files = nds.parse_fnt()
    path_to_fid = {p: fid for p, fid in files}

    rom = bytearray(nds.data)
    patched = 0
    msgs_filled = 0
    for rel_in_script, en_list in en_by_file.items():
        full = "script/" + rel_in_script
        fid = path_to_fid.get(full)
        if fid is None:
            continue
        start, end = nds.fat[fid]
        data = bytes(rom[start:end])
        hdr = struct.unpack_from("<I", data, 0)[0]
        if hdr < 4 or hdr > len(data):
            continue
        region = data[hdr:]
        msgs = split_messages(region)
        new_region, ji = pour(region, msgs, en_list, args.enc)
        assert len(new_region) == len(region), "size changed!"
        new_file = data[:hdr] + new_region
        assert len(new_file) == (end - start), "file size changed!"
        rom[start:end] = new_file
        patched += 1
        msgs_filled += ji

    # NDS header has no global checksum that emulators enforce except the
    # logo/header CRC at 0x15E (header only) -- our edits are far past it.
    with open(args.out_rom, "wb") as f:
        f.write(rom)
    print(f"Patched {patched} .scs files, {msgs_filled} messages, enc={args.enc}")
    print(f"Wrote {args.out_rom} ({len(rom)} bytes, same size as source)")


if __name__ == "__main__":
    main()
