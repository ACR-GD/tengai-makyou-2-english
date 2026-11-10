#!/usr/bin/env python3
"""Option A: two narrow Latin letters per 16x16 full-width glyph cell.

Builds:
  translation/pair_map.json   digraph -> {sjis, glyph_idx, char}
  Patched font12 .cobj with digraph bitmaps written into hijacked slots.
"""
import json
import os
import re
import struct
import sys
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from font import get_glyph, set_glyph, GLYPH_BYTES, GW, GH
from scs_codec import is_sjis_char
from sjis_glyph import sjis_to_glyph

FONT_TTF = "/System/Library/Fonts/Arial Unicode.ttf"
FONT_PATH = "extracted/data/string_work/grph/font12_GothicW3_bit.cobj"
OUT_FONT = "translation/font12_pairs.cobj"
OUT_MAP = "translation/pair_map.json"
N_PAIRS = 1235   # all unique digraphs (~98.5% was top-428; need full set)
def used_sjis(script_root):
    used = set()
    for dp, _, fs in os.walk(script_root):
        for fn in fs:
            if not fn.endswith(".scs"):
                continue
            d = open(os.path.join(dp, fn), "rb").read()
            if len(d) < 4:
                continue
            hdr = struct.unpack_from("<I", d, 0)[0]
            reg = d[hdr:]
            i = 0
            while i + 1 < len(reg):
                w = struct.unpack_from("<H", reg, i)[0]
                if is_sjis_char(w):
                    used.add(bytes(reg[i:i + 2]))
                i += 2
    return used


def collect_digraphs(json_path):
    recs = json.load(open(json_path, encoding="utf-8"))
    pairs = Counter()
    for r in recs:
        t = re.sub(r"\{[0-9A-F]{4}\}", "", r.get("en_tagged", ""))
        t = "".join(c if ord(c) < 128 else "?" for c in t)
        t = re.sub(r"[^ -~]", " ", t).lower()
        t = re.sub(r" +", " ", t).strip()
        if len(t) % 2:
            t += " "
        for i in range(0, len(t), 2):
            pairs[t[i:i + 2]] += 1
    return [p for p, _ in pairs.most_common(N_PAIRS)]


def pool_unused_slots(used):
    """SJIS codes not used in scripts, with valid glyph index (< 7560)."""
    pool = []
    seen_g = set()
    # Prefer high rows (rare kanji) so original shapes are unobtrusive if mis-patched
    for lead in range(0xE0, 0xFD):
        for trail in list(range(0x40, 0x7E + 1)) + list(range(0x80, 0xFC + 1)):
            sjis = bytes([lead, trail])
            if sjis in used:
                continue
            try:
                ch = sjis.decode("shift_jis")
            except Exception:
                continue
            if len(ch) != 1:
                continue
            g = sjis_to_glyph(sjis)
            if g >= 7560 or g in seen_g:
                continue
            seen_g.add(g)
            pool.append({"sjis": sjis.hex(), "glyph_idx": g, "orig": ch})
            if len(pool) >= N_PAIRS:
                return pool
    for lead in range(0x81, 0xA0):
        for trail in list(range(0x40, 0x7E + 1)) + list(range(0x80, 0xFC + 1)):
            sjis = bytes([lead, trail])
            if sjis in used:
                continue
            try:
                ch = sjis.decode("shift_jis")
            except Exception:
                continue
            if len(ch) != 1:
                continue
            g = sjis_to_glyph(sjis)
            if g >= 7560 or g in seen_g:
                continue
            seen_g.add(g)
            pool.append({"sjis": sjis.hex(), "glyph_idx": g, "orig": ch})
            if len(pool) >= N_PAIRS:
                return pool
    return pool


def render_pair_grid(c1, c2, size=6):
    """16x16 0/1 grid with two narrow letters side by side."""
    grid = [[0] * GW for _ in range(GH)]
    fnt = ImageFont.truetype(FONT_TTF, size)
    im = Image.new("L", (GW, GH), 0)
    dr = ImageDraw.Draw(im)
    xs = (1, 9) if c1 != " " else (9, 9)
    chars = (c1, c2)
    for i, ch in enumerate(chars):
        if ch == " ":
            continue
        dr.text((xs[i], 4), ch, fill=255, font=fnt)
    px = (np.asarray(im) > 96).astype(int)
    for y in range(GH):
        for x in range(GW):
            grid[y][x] = int(px[y, x])
    return grid


def build(json_path, script_root):
    used = used_sjis(script_root)
    digraphs = collect_digraphs(json_path)
    print(f"{len(digraphs)} digraphs to map", flush=True)

    data = bytearray(open(FONT_PATH, "rb").read())
    pool = pool_unused_slots(used)
    print(f"unused kanji slots: {len(pool)}", flush=True)
    if len(pool) < len(digraphs):
        raise SystemExit(f"need {len(digraphs)} slots, got {len(pool)}")

    pair_map = {}
    for pair, slot in zip(digraphs, pool):
        c1, c2 = pair[0], pair[1] if len(pair) > 1 else " "
        grid = render_pair_grid(c1, c2)
        set_glyph(data, slot["glyph_idx"], grid)
        pair_map[pair] = {
            "sjis": slot["sjis"],
            "glyph_idx": slot["glyph_idx"],
            "orig_kanji": slot["orig"],
        }

    open(OUT_FONT, "wb").write(data)
    json.dump(pair_map, open(OUT_MAP, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"wrote {OUT_FONT} ({len(data)} bytes)")
    print(f"wrote {OUT_MAP} ({len(pair_map)} entries)")
    return pair_map


if __name__ == "__main__":
    build(
        sys.argv[1] if len(sys.argv) > 1 else "translation/tengai2_script.translated.json",
        sys.argv[2] if len(sys.argv) > 2 else "extracted/data/script",
    )
