#!/usr/bin/env python3
"""English province tags on the province-select map (data/usd/fuw_bg.chr).

The file is LZ10 around: u32 palette size, palette, u32 tile size, 8bpp tiles
in reading order (a full 256x192 picture). Each province is a vertical paper
tag with two kanji; the English name is drawn rotated a quarter turn
clockwise (read top to bottom, like a book spine) in the in-game VWF font.

    python tools/usd_graphics.py --preview fuw_preview.png
"""
from __future__ import annotations

import argparse
import struct
from collections import Counter
from pathlib import Path

from battle_graphics import lz10_decode, lz10_encode
from text_raster import render

PATH = "data/usd/fuw_bg.chr"
INK = 0x60
PAPER = {0x7C, 0x7E, 0x7F}
# (left, top) of each tag's 12x42 paper, and its province.
TAGS = [
    ((39, 7), "Iwami"), ((71, 7), "Izumo"), ((102, 7), "Inaba"), ((144, 7), "Omi"),
    ((175, 7), "Echizen"), ((206, 7), "Etchu"), ((237, 7), "Echigo"),
    ((8, 60), "Nagato"), ((40, 60), "Aki"), ((71, 60), "Kibi"), ((102, 60), "Tanba"),
    ((144, 60), "Kyoto"), ((175, 60), "Hida"),
    ((102, 114), "Naniwa"), ((144, 114), "Ise"), ((175, 114), "Owari"),
    ((122, 144), "Kii"),
]
TAG_W, TAG_H = 12, 42


def _split(raw):
    pal = struct.unpack_from("<I", raw, 0)[0] & 0x7FFFFFFF
    size = struct.unpack_from("<I", raw, 4 + pal)[0]
    start = 8 + pal
    if size != 256 * 192 or start + size != len(raw):
        raise ValueError("Unexpected fuw_bg layout")
    return start


def _at(x, y):
    return ((y // 8) * 32 + x // 8) * 64 + (y % 8) * 8 + x % 8


def _spine(name, room):
    """Ink for name; letters close up by 1px when the normal spacing is too long."""
    for squeeze in (0, 1):
        ink, x = set(), 0
        for ch in name:
            advance, _, pixels = render(ch)
            ink |= {(x + px, py) for px, py in pixels}
            x += advance - squeeze
        if max(px for px, _ in ink) + 1 <= room:
            return ink
    raise ValueError(f"{name} does not fit its tag")


def paint(pixels):
    for (x0, y0), name in TAGS:
        # Paper colour per column (rows avoid the rounded ends).
        for x in range(x0, x0 + TAG_W):
            column = [pixels[_at(x, y)] for y in range(y0 + 2, y0 + TAG_H - 2)]
            paper = Counter(v for v in column if v in PAPER).most_common(1)
            if not paper:
                raise ValueError(f"No paper found in the {name} tag")
            for y in range(y0 + 2, y0 + TAG_H - 2):
                if pixels[_at(x, y)] not in PAPER:
                    pixels[_at(x, y)] = paper[0][0]
        ink = _spine(name, TAG_H - 4)
        width = max(px for px, _ in ink) + 1
        top = y0 + (TAG_H - width) // 2
        for px, py in ink:
            # Clockwise: text x runs down the tag, text y runs right to left.
            x, y = x0 + TAG_W - 1 - py, top + px
            if not (x0 <= x < x0 + TAG_W):
                raise ValueError(f"{name} spills out of its tag")
            pixels[_at(x, y)] = INK


def build_usd_graphics(read):
    raw = lz10_decode(read(PATH))
    start = _split(raw)
    pixels = bytearray(raw[start:])
    paint(pixels)
    encoded = lz10_encode(raw[:start] + bytes(pixels))
    return {PATH: encoded}, {"province_tags": len(TAGS), "runtime_verified": False}


def preview(read, destination):
    from PIL import Image
    files, _ = build_usd_graphics(read)
    sheet = Image.new("RGB", (512, 192))
    for i, blob in enumerate((read(PATH), files[PATH])):
        raw = lz10_decode(blob)
        start = _split(raw)
        pal = struct.unpack_from("<I", raw, 0)[0] & 0x7FFFFFFF
        colors = struct.unpack_from(f"<{pal // 2}H", raw, 4)
        rgb = [((c & 31) * 8, ((c >> 5) & 31) * 8, ((c >> 10) & 31) * 8) for c in colors]
        for y in range(192):
            for x in range(256):
                sheet.putpixel((i * 256 + x, y), rgb[raw[start + _at(x, y)]])
    sheet.resize((1024, 384), Image.NEAREST).save(destination)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1] / "extracted/data")
    ap.add_argument("--preview", type=Path, required=True)
    args = ap.parse_args()
    preview(lambda path: (args.root / path).read_bytes(), args.preview)


if __name__ == "__main__":
    main()
