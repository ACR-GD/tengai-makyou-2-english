#!/usr/bin/env python3
"""Build English ROM with Option A: digraph glyphs + in-place .scs pour.

Patches:
  * string_work/grph/font12_GothicW3_bit.cobj  (pair bitmaps)
  * script/**/*.scs  (English as digraph SJIS, same byte length)
"""
import argparse
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
from nds_extract import NDS
from scs_codec import decode_spans, is_sjis_char, FW_SPACE

PAIR_MAP = "translation/pair_map.json"
FONT_PATCH = "translation/font12_pairs.cobj"
FONT_ROM_PATH = "string_work/grph/font12_GothicW3_bit.cobj"

# Opening mother dialogue (raw SJIS in overlay ov_008, not in .scs)
OV008_STRINGS = [
    (0x4E60, 8, "ma nj "),           # was 卍丸……
    (0x5A94, 32, "fought agn,huh? "),  # was またどこかでケンカしたんでしょう
    (0x5948, 30, "hopeless kid nee"),  # was まったく　しょうがない子ねえ…
]
OV008_FAT_ID = 8    # NitroFS ov_008.bin (25120 bytes @ ROM ~0x191E00)


def load_pairs(path=PAIR_MAP):
    raw = json.load(open(path, encoding="utf-8"))
    return {pair: bytes.fromhex(info["sjis"]) for pair, info in raw.items()}


def enc_pairs(text, pair_map):
    t = "".join(c if ord(c) < 128 else "?" for c in text)
    t = re.sub(r"[^ -~]", " ", t).lower()
    t = re.sub(r" +", " ", t).strip()
    if len(t) % 2:
        t += " "
    out = bytearray()
    for i in range(0, len(t), 2):
        p = t[i:i + 2]
        if p in pair_map:
            out += pair_map[p]
        else:
            # Never emit two full-width chars for one slot (causes garbage).
            out += pair_map.get("  ", FW_SPACE)
    return bytes(out)


_TAG = re.compile(r"\{[0-9A-F]{4}\}")


def _fill_slots_pairs(out, slots, text, pair_map):
    blob = enc_pairs(text, pair_map)
    budget = len(slots) * 2
    blob = blob[:budget] + FW_SPACE * ((budget - len(blob)) // 2)
    for j, k in enumerate(slots):
        out[k * 2:k * 2 + 2] = blob[j * 2:j * 2 + 2]


def pour_pairs_inplace(mbytes, raw, pair_map):
    """Like scs_build_en.pour_inplace but encodes each fragment as digraphs."""
    nwords = len(mbytes) // 2
    runs = []
    cur = []
    for k in range(nwords):
        w = struct.unpack_from("<H", mbytes, k * 2)[0]
        if is_sjis_char(w):
            cur.append(k)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)

    frags = []
    curf = []
    i = 0
    while i < len(raw):
        m = _TAG.match(raw, i)
        if m:
            frags.append("".join(curf))
            curf = []
            i = m.end()
        elif raw[i] == "\n":
            curf.append(" ")
            i += 1
        else:
            curf.append(raw[i])
            i += 1
    frags.append("".join(curf))
    nonempty = [f for f in frags if f.strip()]

    out = bytearray(mbytes)
    if len(nonempty) == len(runs):
        for slots, frag in zip(runs, nonempty):
            _fill_slots_pairs(out, slots, frag, pair_map)
    else:
        allslots = [k for run in runs for k in run]
        plain = re.sub(r"\{[0-9A-F]{4}\}", "", raw).replace("\n", " ")
        _fill_slots_pairs(out, allslots, plain, pair_map)
    return bytes(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("out_rom")
    ap.add_argument("--json", default="translation/tengai2_script.translated.json")
    args = ap.parse_args()

    pair_map = load_pairs()
    recs = json.load(open(args.json, encoding="utf-8"))
    en_by_file = {}
    for r in recs:
        if r.get("en_tagged"):
            en_by_file.setdefault(r["file"], []).append(r)

    nds = NDS(args.rom)
    path_to_fid = {p: fid for p, fid in nds.parse_fnt()}
    rom = bytearray(nds.data)

    font_new = open(FONT_PATCH, "rb").read()
    fid = path_to_fid[FONT_ROM_PATH]
    fs, fe = nds.fat[fid]
    rom[fs:fe] = font_new
    print(f"patched font @ 0x{fs:X}..0x{fe:X}")

    # overlay ov_008: fixed-length null-terminated SJIS strings (opening scene)
    o8s, o8e = nds.fat[OV008_FAT_ID]
    for off, size, text in OV008_STRINGS:
        blob = enc_pairs(text.replace("…", "..."), pair_map)
        if len(blob) > size:
            blob = blob[:size]
        else:
            blob = blob + bytes([0x81, 0x40]) * ((size - len(blob)) // 2)
        rom[o8s + off:o8s + off + size] = blob
    print(f"patched {len(OV008_STRINGS)} opening strings in ov_008 @ 0x{o8s:X}")

    patched = msgs = 0
    for rel, rs in en_by_file.items():
        full = "script/" + rel
        fid = path_to_fid.get(full)
        if fid is None:
            continue
        start, end = nds.fat[fid]
        data = bytes(rom[start:end])
        hdr = struct.unpack_from("<I", data, 0)[0]
        region = bytearray(data[hdr:])
        trans = {r["msg"]: r["en_tagged"] for r in rs}
        for m in decode_spans(bytes(region)):
            if m["mi"] not in trans:
                continue
            s, e = m["start"], m["end"]
            region[s:e] = pour_pairs_inplace(
                bytes(region[s:e]), trans[m["mi"]], pair_map)
            msgs += 1
        new_file = data[:hdr] + bytes(region)
        assert len(new_file) == len(data)
        rom[start:end] = new_file
        patched += 1

    with open(args.out_rom, "wb") as f:
        f.write(rom)
    print(f"patched {patched} .scs, {msgs} messages -> {args.out_rom}")


if __name__ == "__main__":
    main()
