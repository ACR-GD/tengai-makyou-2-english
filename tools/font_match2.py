#!/usr/bin/env python3
"""bbox-normalized glyph matching: robust across fonts."""
import sys
import numpy as np
from PIL import Image, ImageFont, ImageDraw

sys.path.insert(0, "tools")
from font import get_glyph, GLYPH_BYTES

FONT_TTF = "/System/Library/Fonts/Arial Unicode.ttf"
FONT_PATH = "extracted/data/string_work/grph/font12_GothicW3_bit.cobj"
N = 12  # normalized grid


def norm_grid(bits):
    """bits: HxW numpy 0/1 -> NxN normalized by ink bbox, or None if empty."""
    ys, xs = np.where(bits > 0)
    if len(xs) == 0:
        return None
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    crop = bits[y0:y1 + 1, x0:x1 + 1]
    im = Image.fromarray((crop * 255).astype(np.uint8))
    im = im.resize((N, N), Image.BILINEAR)
    return (np.asarray(im) > 96).astype(np.uint8).reshape(N * N)


def load_game(path=FONT_PATH):
    data = open(path, "rb").read()
    nG = len(data) // GLYPH_BYTES
    grids = np.zeros((nG, N * N), np.uint8)
    valid = np.zeros(nG, bool)
    for i in range(nG):
        g = np.array(get_glyph(data, i), np.uint8)
        ng = norm_grid(g)
        if ng is not None and g.sum() >= 4:
            grids[i] = ng
            valid[i] = True
    return grids, valid


def ref_grids(ch):
    out = []
    for size in (12, 13, 14, 15, 16, 18, 20):
        fnt = ImageFont.truetype(FONT_TTF, size)
        im = Image.new("L", (32, 32), 0)
        ImageDraw.Draw(im).text((4, 2), ch, fill=255, font=fnt)
        bits = (np.asarray(im) > 96).astype(np.uint8)
        ng = norm_grid(bits)
        if ng is not None:
            out.append(ng)
    return out


def match(grids, valid, ch, topk=3):
    refs = ref_grids(ch)
    bestd = np.full(grids.shape[0], 9999)
    for r in refs:
        d = (grids ^ r).sum(axis=1)
        bestd = np.minimum(bestd, d)
    bestd[~valid] = 9999
    order = np.argsort(bestd)[:topk]
    return [(int(i), int(bestd[i])) for i in order]


if __name__ == "__main__":
    grids, valid = load_game()
    print("nG =", grids.shape[0], "valid =", int(valid.sum()))
    chars = sys.argv[1:] or list("0123456789") + list("ABCDEFGHIJ")
    for ch in chars:
        res = match(grids, valid, ch)
        print(f"{ch!r}: " + "  ".join(f"slot{ i} d{d}" for i, d in res))
