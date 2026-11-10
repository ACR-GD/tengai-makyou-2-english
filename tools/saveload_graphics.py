#!/usr/bin/env python3
"""English save/load message windows (uno_all/saveload/mes_obj).

Each window is three 64x64 OBJ (tiles 0x00/0x40/0x80, left to right) over a
row of 32x8 border strips (tiles 0xC0..). The Japanese is white (15) on navy
(4) and every tile in the three big sprites is unique, so text is cleared and
redrawn in place with the in-game VWF font. In 07/08 the fourth Japanese line
reaches into the first two strips, which are unique there too. mes04 also
holds eight 32x16 "file number" tags drawn at (16, 16) before its first line
(tag 1 sits before its border strips at 0xC8, tags 2-8 after them).

    python tools/saveload_graphics.py --preview saveload_preview.png
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

from cmp_codec import decode, encode_raw
from text_raster import render

BASE = "uno_all/saveload/mes_obj/"
BG, INK = 4, 15
AREA = (7, 6, 185, 64)  # window interior inside the frame
MESSAGES = {
    1: ["Loading file...", "Do not remove the DS Card", "or turn off the power."],
    2: ["Failed to load.", "Press a button or", "touch the screen."],
    3: ["This file is not empty.", "Please erase it first."],
    4: [(52, "will be erased."), "Are you sure?"],
    5: ["A file already exists.", "Overwrite it?"],
    6: ["Saving...", "Do not remove the DS Card", "or turn off the power."],
    7: ["Failed to load data.", "Turn off the power and", "reinsert the DS Card."],
    8: ["Failed to save data.", "Turn off the power and", "reinsert the DS Card."],
}
TAG_TILES = (0xC0, *range(0xE0, 0x118, 8))  # mes04 number tags 1..8 (frames 1..8), 32x16
STRIP_TEXT = {7: (0xC0, 0xC8), 8: (0xC0, 0xC8)}  # strips under x=0..64 holding text
# Option labels: cur_obj/curNN is a 32x16 (tiles 0-7) + 8x16 (tiles 16-17)
# white label; btn_obj/btnNN has a 32x16 label at tile 32 (ink 4) over its frame.
CURSORS = {1: "Yes", 2: "No", 3: "Load", 4: "Copy", 5: "Erase"}
BUTTONS = {1: "Back", 2: "OK", 3: "Erase"}  # btn01: やめる (leave the file screen)
# The event Yes/No prompt uses the same 40x16 label layout, side by side.
EVENT_YESNO = ("uno_all/vis/sys/yesno.chr", (("Yes", [(0, 32), (16, 8)]), ("No", [(8, 32), (18, 8)])))


def _px(tiles, tile, x, y):
    return (tiles[tile * 32 + y * 4 + x // 2] >> (4 * (x & 1))) & 15


def _set(tiles, tile, x, y, v):
    o = tile * 32 + y * 4 + x // 2
    shift = 4 * (x & 1)
    tiles[o] = (tiles[o] & ~(15 << shift)) | (v << shift)


def _window(tiles, strips):
    """(read, write) over a 192x72 canvas: 3 big sprites + optional text strips."""
    def locate(X, Y):
        if Y < 64:
            return (X // 64) * 64 + (Y // 8) * 8 + (X % 64) // 8, X % 8, Y % 8
        if X < 64 and strips:
            return strips[X // 32] + (X % 32) // 8, X % 8, Y - 64
        return None
    return locate


def paint_message(tiles, number):
    locate = _window(tiles, STRIP_TEXT.get(number))
    x0, y0, x1, y1 = AREA
    bottom = 69 if number in STRIP_TEXT else y1
    for Y in range(y0, bottom):
        for X in range(x0, x1):
            spot = locate(X, Y)
            if spot and _px(tiles, *spot) == INK:
                _set(tiles, *spot, BG)
    lines = MESSAGES[number]
    top = y0 + (y1 - y0 - (16 * len(lines) - 4)) // 2
    for row, line in enumerate(lines):
        x, text = line if isinstance(line, tuple) else (16, line)
        width, _, ink = render(text)
        if x + width > x1:
            raise ValueError(f"Save message {number} line too wide: {text!r}")
        for px, py in ink:
            spot = locate(x + px, top + row * 16 + py)
            _set(tiles, *spot, INK)


def paint_tag(tiles, first_tile, number):
    for Y in range(16):
        for X in range(32):
            _set(tiles, first_tile + (Y // 8) * 4 + X // 8, X % 8, Y % 8, 0)
    width, _, ink = render(f"File {number}")
    if width > 32:
        raise ValueError("File tag too wide")
    left = (32 - width) // 2
    for px, py in ink:
        X, Y = left + px, 2 + py
        _set(tiles, first_tile + (Y // 8) * 4 + X // 8, X % 8, Y % 8, INK)


def paint_label(tiles, parts, text, ink):
    """parts: [(first tile, width)] laid out left to right, 16px tall."""
    width = sum(w for _, w in parts)
    def locate(X, Y):
        for first, w in parts:
            if X < w:
                return first + (Y // 8) * (w // 8) + X // 8, X % 8, Y % 8
            X -= w
    for Y in range(16):
        for X in range(width):
            _set(tiles, *locate(X, Y), 0)
    advance, _, pixels = render(text)
    if advance > width:
        raise ValueError(f"Save/load label too wide: {text!r}")
    left = (width - advance) // 2
    for px, py in pixels:
        _set(tiles, *locate(left + px, py + 1), ink)


def _rewrite(read, files, path, paint):
    raw = decode(read(path))
    if struct.unpack_from("<I", raw, 0)[0] != len(raw) - 4:
        raise ValueError(f"Unexpected {path} header")
    tiles = bytearray(raw[4:])
    paint(tiles)
    files[path] = encode_raw(raw[:4] + bytes(tiles))


def build_saveload_graphics(read):
    files = {}
    for number in MESSAGES:
        path = f"{BASE}mes{number:02d}.chr"
        raw = decode(read(path))
        size = struct.unpack_from("<I", raw, 0)[0]
        if size != len(raw) - 4:
            raise ValueError(f"Unexpected {path} header")
        tiles = bytearray(raw[4:])
        paint_message(tiles, number)
        if number == 4:
            for n, first in enumerate(TAG_TILES, 1):
                paint_tag(tiles, first, n)
        files[path] = encode_raw(raw[:4] + bytes(tiles))
    for number, text in CURSORS.items():
        _rewrite(read, files, f"uno_all/saveload/cur_obj/cur{number:02d}.chr",
                 lambda t, text=text: paint_label(t, [(0, 32), (16, 8)], text, 15))
    for number, text in BUTTONS.items():
        first = 0 if number == 1 else 32  # btn01's label leads its tiles
        _rewrite(read, files, f"uno_all/saveload/btn_obj/btn{number:02d}.chr",
                 lambda t, text=text, first=first: paint_label(t, [(first, 32)], text, 4))
    path, labels = EVENT_YESNO
    def paint_yesno(tiles):
        for text, parts in labels:
            paint_label(tiles, parts, text, 15)
    _rewrite(read, files, path, paint_yesno)
    return files, {"messages": len(MESSAGES), "labels": len(CURSORS) + len(BUTTONS) + len(labels),
                   "runtime_verified": False}


def preview(read, destination):
    from PIL import Image
    pal = decode(read(BASE + "mes_com.pal"))
    rgb = [((c & 31) * 8, ((c >> 5) & 31) * 8, ((c >> 10) & 31) * 8) for c in struct.unpack_from("<16H", pal, 4)]
    files, _ = build_saveload_graphics(read)
    sheet = Image.new("RGB", (400, 4 * 80 + 24), (60, 60, 60))
    for number in MESSAGES:
        tiles = decode(files[f"{BASE}mes{number:02d}.chr"])[4:]
        locate = _window(tiles, STRIP_TEXT.get(number) or (0xC0, 0xC8))
        ox, oy = ((number - 1) % 2) * 200, ((number - 1) // 2) * 80
        for Y in range(72):
            for X in range(192):
                spot = locate(X, Y)
                v = _px(tiles, *spot) if spot else 0
                sheet.putpixel((ox + X, oy + Y), rgb[v] if v else (0, 0, 0))
        if number == 4:
            for n, first in enumerate(TAG_TILES):
                for Y in range(16):
                    for X in range(32):
                        v = _px(tiles, first + (Y // 8) * 4 + X // 8, X % 8, Y % 8)
                        sheet.putpixel((n * 40 + X, 4 * 80 + 4 + Y), rgb[v] if v else (0, 0, 0))
    sheet.resize((800, sheet.height * 2), Image.NEAREST).save(destination)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1] / "extracted/data")
    ap.add_argument("--preview", type=Path, required=True)
    args = ap.parse_args()
    preview(lambda path: (args.root / path).read_bytes(), args.preview)


if __name__ == "__main__":
    main()
