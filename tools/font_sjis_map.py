#!/usr/bin/env python3
"""Build SJIS -> glyph-index map by matching rendered references to font12."""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFont, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from font import get_glyph, GLYPH_BYTES, GW, GH

FONT_TTF = "/System/Library/Fonts/Arial Unicode.ttf"
FONT_PATH = "extracted/data/string_work/grph/font12_GothicW3_bit.cobj"
N = 12
HAM_OK = 80


def norm_grid(bits):
    ys, xs = np.where(bits > 0)
    if len(xs) == 0:
        return None
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    crop = bits[y0:y1 + 1, x0:x1 + 1]
    im = Image.fromarray((crop * 255).astype(np.uint8))
    im = im.resize((N, N), Image.BILINEAR)
    return (np.asarray(im) > 96).astype(np.uint8).reshape(N * N)


def load_font():
    data = open(FONT_PATH, "rb").read()
    nG = len(data) // GLYPH_BYTES
    grids = np.zeros((nG, N * N), np.uint8)
    valid = np.zeros(nG, bool)
    for i in range(nG):
        g = np.array(get_glyph(data, i), np.uint8)
        ng = norm_grid(g)
        if ng is not None and g.sum() >= 4:
            grids[i] = ng
            valid[i] = True
    return data, grids, valid


def ref_grid(ch, size=14):
    fnt = ImageFont.truetype(FONT_TTF, size)
    im = Image.new("L", (32, 32), 0)
    ImageDraw.Draw(im).text((4, 2), ch, fill=255, font=fnt)
    bits = (np.asarray(im) > 96).astype(np.uint8)
    return norm_grid(bits)


def match_char(grids, valid, ch):
    refs = [ref_grid(ch, s) for s in (12, 13, 14, 15, 16)]
    refs = [r for r in refs if r is not None]
    if not refs:
        return None, 9999
    bestd = np.full(grids.shape[0], 9999)
    for r in refs:
        bestd = np.minimum(bestd, (grids ^ r).sum(axis=1))
    bestd[~valid] = 9999
    i = int(bestd.argmin())
    return i, int(bestd[i])


def sjis_candidates():
    out = []
    for lead in range(0x81, 0xA0):
        for trail in list(range(0x40, 0x7E + 1)) + list(range(0x80, 0xFC + 1)):
            try:
                ch = bytes([lead, trail]).decode("shift_jis")
            except Exception:
                continue
            out.append((bytes([lead, trail]), ch))
    for lead in range(0xE0, 0xFD):
        for trail in list(range(0x40, 0x7E + 1)) + list(range(0x80, 0xFC + 1)):
            try:
                ch = bytes([lead, trail]).decode("shift_jis")
            except Exception:
                continue
            out.append((bytes([lead, trail]), ch))
    return out


def main():
    data, grids, valid = load_font()
    mapping = {}  # sjis hex -> {idx, ham, ch}
    for sjis, ch in sjis_candidates():
        if len(ch) != 1:
            continue
        idx, ham = match_char(grids, valid, ch)
        if ham <= HAM_OK:
            mapping[sjis.hex()] = {"idx": idx, "ham": ham, "ch": ch}

    out = "translation/font_sjis_map.json"
    json.dump(mapping, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"mapped {len(mapping)} SJIS codes -> {out}")
    # show F0 block sample
    f0 = {k: v for k, v in mapping.items() if k.startswith("f0")}
    print(f"F0xx mapped: {len(f0)}")
    for k in sorted(f0)[:5]:
        print(f"  {k}: idx={f0[k]['idx']} ch={f0[k]['ch']!r}")


if __name__ == "__main__":
    main()
