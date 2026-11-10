#!/usr/bin/env python3
"""Identify game-font glyph slots by matching against PIL-rendered references."""
import sys
import numpy as np
from PIL import Image, ImageFont, ImageDraw

sys.path.insert(0, "tools")
from font import get_glyph, GLYPH_BYTES

FONT_TTF = "/System/Library/Fonts/Arial Unicode.ttf"
FONT_PATH = "extracted/data/string_work/grph/font12_GothicW3_bit.cobj"


def load_game(path=FONT_PATH):
    data = open(path, "rb").read()
    nG = len(data) // GLYPH_BYTES
    arr = np.zeros((nG, 256), np.uint8)
    for i in range(nG):
        g = get_glyph(data, i)
        arr[i] = np.array(g, np.uint8).reshape(256)
    return data, arr


def ref_variants(ch, sizes=(14, 15, 16, 17, 18), oxs=(-1, 0, 1, 2), oys=(-2, -1, 0, 1, 2)):
    out = []
    for size in sizes:
        fnt = ImageFont.truetype(FONT_TTF, size)
        for ox in oxs:
            for oy in oys:
                im = Image.new("L", (16, 16), 0)
                ImageDraw.Draw(im).text((ox, oy), ch, fill=255, font=fnt)
                a = (np.asarray(im) > 96).astype(np.uint8).reshape(256)
                if a.sum() >= 6:
                    out.append(a)
    return out


def best_match(arr, ch):
    best_h, best_i = 999, -1
    for r in ref_variants(ch):
        d = (arr ^ r).sum(axis=1)        # broadcast XOR over all glyphs
        i = int(d.argmin())
        if d[i] < best_h:
            best_h, best_i = int(d[i]), i
    return best_i, best_h


if __name__ == "__main__":
    _, arr = load_game()
    print("nG =", arr.shape[0])
    for ch in sys.argv[1:] or ["あ", "ア", "Ａ", "０", "卍", "水", "火", "、", "。"]:
        i, h = best_match(arr, ch)
        sj = ch.encode("shift_jis").hex()
        print(f"{ch}: idx={i} ham={h}  SJIS=0x{sj}")
