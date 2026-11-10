#!/usr/bin/env python3
"""Build English ROM using full-width Latin (proven to render in-game).

Each text cell = one full-width character (2 bytes), same as Japanese.
English is shortened to fit the same number of cells per fragment as the
original Japanese (preserves control codes via fragment-aware pour).

Does NOT patch the font — uses the game's built-in full-width Ａ-Ｚ / ａ-ｚ.
"""
import argparse
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
from nds_extract import NDS
from scs_codec import decode_spans, is_sjis_char, enc_char, FW_SPACE
from scs_build_en import pour_inplace

FONT_ROM_PATH = "string_work/grph/font12_GothicW3_bit.cobj"

# NitroFS file ov_008.bin (ARM9 overlay 8 string table) — NOT FAT id 16.
OV008_FAT_ID = 8
OV008_JSON = "translation/ov008_en.json"


def enc_fw_fit(text, max_cells):
    """Encode to max_cells full-width characters (2 bytes each)."""
    t = "".join(c if ord(c) < 128 else "?" for c in text)
    t = re.sub(r"[^ -~]", " ", t)
    t = re.sub(r" +", " ", t).strip()
    out = bytearray()
    for ch in t:
        if len(out) >= max_cells * 2:
            break
        out += enc_char(ch, translit=True)
    while len(out) < max_cells * 2:
        out += FW_SPACE
    return bytes(out[: max_cells * 2])


def pour_fw_fit(mbytes, raw):
    """Fragment-aware pour with per-fragment cell budget = JP text slots."""
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
    tag = re.compile(r"\{[0-9A-F]{4}\}")
    while i < len(raw):
        m = tag.match(raw, i)
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
            blob = enc_fw_fit(frag, len(slots))
            for j, k in enumerate(slots):
                out[k * 2 : k * 2 + 2] = blob[j * 2 : j * 2 + 2]
    else:
        allslots = [k for run in runs for k in run]
        plain = tag.sub("", raw).replace("\n", " ")
        blob = enc_fw_fit(plain, len(allslots))
        for j, k in enumerate(allslots):
            out[k * 2 : k * 2 + 2] = blob[j * 2 : j * 2 + 2]
    return bytes(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("out_rom")
    ap.add_argument("--json", default="translation/tengai2_script.translated.json")
    args = ap.parse_args()

    recs = json.load(open(args.json, encoding="utf-8"))
    en_by_file = {}
    for r in recs:
        if r.get("en_tagged"):
            en_by_file.setdefault(r["file"], []).append(r)

    nds = NDS(args.rom)
    path_to_fid = {p: fid for p, fid in nds.parse_fnt()}
    rom = bytearray(nds.data)

    o8s, o8e = nds.fat[OV008_FAT_ID]
    ov_path = os.path.join(os.path.dirname(__file__), "..", OV008_JSON)
    ov_recs = json.load(open(ov_path, encoding="utf-8"))
    ov_n = 0
    for key, rec in ov_recs.items():
        off = int(key)
        size = rec["size"]
        if off + size > o8e - o8s:
            continue
        cells = size // 2
        rom[o8s + off : o8s + off + size] = enc_fw_fit(rec["en"], cells)
        ov_n += 1
    print(f"patched {ov_n} SJIS strings in ov_008 (FAT {OV008_FAT_ID})")

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
            region[s:e] = pour_fw_fit(bytes(region[s:e]), trans[m["mi"]])
            msgs += 1
        new_file = data[:hdr] + bytes(region)
        assert len(new_file) == len(data)
        rom[start:end] = new_file
        patched += 1

    with open(args.out_rom, "wb") as f:
        f.write(rom)
    print(f"patched {patched} .scs, {msgs} messages -> {args.out_rom}")
    print("(full-width Latin, shortened to JP cell count per fragment)")


if __name__ == "__main__":
    main()
