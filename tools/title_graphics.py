#!/usr/bin/env python3
"""English New/Continue screens: the title menu and its copy in the event art.

Each screen is one 4bpp background: a speech bubble explaining 起 (start) and
転 (continue) plus two kanji buttons. The bubble text is redrawn with the
in-game VWF font, the buttons get NEW / LOAD in the battle menu's compact
font at 3x. Edited cells get fresh tiles appended to the .chr (deduplicated)
so tiles shared with other cells keep their pixels; the map points at them
and keeps each cell's palette bank.

    python tools/title_graphics.py --preview title_preview.png
"""
from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from pathlib import Path

from battle_graphics import FONT
from cmp_codec import decode, encode_raw
from text_raster import render

# At 3x the 3-wide W reads as H; the big labels get a 5-wide one.
BIG_FONT = dict(FONT, W="10001/10001/10101/11011/10001")
MAX_TILES = 1024


@dataclass(frozen=True)
class Screen:
    chr: str
    scr: str
    pal: str
    fill: int            # bubble paper
    clear: frozenset     # Japanese inks inside the bubble
    area: tuple          # bubble interior (x0, y0, x1, y1)
    text_ink: int
    key_ink: int
    button_ink: int
    buttons: tuple       # ((label, search box), ...)


SCREENS = (
    # Title menu (sub BG1: characters at +16KB, map at 0).
    Screen("uno_all/kiten/bg00/char00.chr", "uno_all/kiten/bg00/scrn00.scr",
           "uno_all/kiten/bg00/palt.pal", 12, frozenset({1, 4, 6, 7, 8, 10}),
           (14, 8, 168, 112), 4, 7, 1,
           (("NEW", (32, 118, 112, 192)), ("LOAD", (144, 118, 224, 192)))),
    # The same screen as event art (dimmed palette, buttons cut off at the bottom).
    Screen("uno_all/vis/bgd/chr/kiten_b.chr", "uno_all/vis/bgd/scr/kiten_b.scr",
           "uno_all/vis/bgd/pal/kiten_b.pal", 15, frozenset({1, 3, 4}),
           (24, 20, 160, 142), 1, 3, 3,  # x<24 and x>=160 are bank-1 border cells
           (("NEW", (36, 150, 120, 192)), ("LOAD", (148, 150, 232, 192)))),
)
LINES = [
    [("To start a new game,", "text")],
    [("choose ", "text"), ("NEW", "key"), (".", "text")],
    [],
    [("To continue a saved", "text")],
    [("game, choose ", "text"), ("LOAD", "key"), (".", "text")],
    [],
    [("Pick one!", "text")],
]


def _decode_tiles(chr_raw):
    size = struct.unpack_from("<I", chr_raw, 0)[0]
    if size != len(chr_raw) - 4 or size % 32:
        raise ValueError("Unexpected title screen char header")
    return [chr_raw[4 + i:4 + i + 32] for i in range(0, size, 32)]


def _canvas(tiles, entries):
    img = [[0] * 256 for _ in range(256)]
    for cell, e in enumerate(entries):
        ti, hf, vf = e & 1023, (e >> 10) & 1, (e >> 11) & 1
        tile = tiles[ti]
        for y in range(8):
            for x in range(8):
                sx, sy = (7 - x if hf else x), (7 - y if vf else y)
                img[(cell // 32) * 8 + y][(cell % 32) * 8 + x] = (tile[sy * 4 + sx // 2] >> (4 * (sx & 1))) & 15
    return img


def _box(img, area):
    """Bounding box of the button paper: its commonest colour other than ink."""
    x0, y0, x1, y1 = area
    counts = {}
    for y in range(y0, y1):
        for x in range(x0, x1):
            counts[img[y][x]] = counts.get(img[y][x], 0) + 1
    fill = max((v for v in counts if v), key=counts.get)
    pts = [(x, y) for y in range(y0, y1) for x in range(x0, x1) if img[y][x] == fill]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return fill, (min(xs), min(ys), max(xs) + 1, max(ys) + 1)


def paint(img, screen):
    x0, y0, x1, y1 = screen.area
    for y in range(y0, y1):
        for x in range(x0, x1):
            if img[y][x] in screen.clear:
                img[y][x] = screen.fill
    inks = {"text": screen.text_ink, "key": screen.key_ink}
    for row, line in enumerate(LINES):
        x = x0
        for text, role in line:
            width, _, pixels = render(text)
            for px, py in pixels:
                X, Y = x + px, y0 + 1 + row * 14 + py
                if not (x0 <= X < x1 and y0 <= Y < y1):
                    raise ValueError(f"Bubble line overflows: {text!r}")
                img[Y][X] = inks[role]
            x += width
    for label, area in screen.buttons:
        fill, (bx0, by0, bx1, by1) = _box(img, area)
        by1 = min(by1, 192)  # only the visible part counts
        for y in range(by0, by1):
            for x in range(bx0, bx1):
                if img[y][x] != fill:
                    img[y][x] = fill
        glyphs = [BIG_FONT[c].split("/") for c in label]
        width = sum(len(g[0]) * 3 + 3 for g in glyphs) - 3
        if width > bx1 - bx0 - 4 or by1 - by0 < 17:
            raise ValueError(f"{label} does not fit its button")
        x = bx0 + (bx1 - bx0 - width) // 2
        top = by0 + (by1 - by0 - 15) // 2
        for g in glyphs:
            for gy, bits in enumerate(g):
                for gx, bit in enumerate(bits):
                    if bit == "1":
                        for dy in range(3):
                            for dx in range(3):
                                img[top + gy * 3 + dy][x + gx * 3 + dx] = screen.button_ink
            x += len(g[0]) * 3 + 3
    return img


def _encode_tile(img, cell):
    out = bytearray(32)
    ox, oy = (cell % 32) * 8, (cell // 32) * 8
    for y in range(8):
        for x in range(8):
            out[y * 4 + x // 2] |= img[oy + y][ox + x] << (4 * (x & 1))
    return bytes(out)


def build_screen(read, screen):
    chr_raw, scr_raw = decode(read(screen.chr)), decode(read(screen.scr))
    tiles = _decode_tiles(chr_raw)
    entries = list(struct.unpack_from("<1024H", scr_raw, 4))
    before = _canvas(tiles, entries)
    after = paint([row[:] for row in before], screen)
    index = {t: i for i, t in reversed(list(enumerate(tiles)))}
    changed = 0
    for cell in range(1024):
        oy, ox = (cell // 32) * 8, (cell % 32) * 8
        if all(before[oy + y][ox:ox + 8] == after[oy + y][ox:ox + 8] for y in range(8)):
            continue
        tile = _encode_tile(after, cell)
        if tile not in index:
            index[tile] = len(tiles)
            tiles.append(tile)
        entries[cell] = (entries[cell] & 0xF000) | index[tile]  # keep the bank, drop flips
        changed += 1
    if len(tiles) > MAX_TILES:
        raise ValueError(f"{screen.chr} exceeds its character block")
    new_chr = struct.pack("<I", len(tiles) * 32) + b"".join(tiles)
    new_scr = scr_raw[:4] + struct.pack("<1024H", *entries) + scr_raw[4 + 2048:]
    return {screen.chr: encode_raw(new_chr), screen.scr: encode_raw(new_scr)}, changed


def build_title_graphics(read):
    files, stats = {}, []
    for screen in SCREENS:
        out, changed = build_screen(read, screen)
        files.update(out)
        stats.append({"chr": screen.chr, "cells_changed": changed})
    return files, {"screens": stats, "runtime_verified": False}


def preview(read, destination):
    from PIL import Image
    files, _ = build_title_graphics(read)
    sheet = Image.new("RGB", (512, 192 * len(SCREENS)))
    for row, screen in enumerate(SCREENS):
        pal_raw = decode(read(screen.pal))
        colors = struct.unpack_from(f"<{(len(pal_raw) - 4) // 2}H", pal_raw, 4)
        rgb = [((c & 31) * 8, ((c >> 5) & 31) * 8, ((c >> 10) & 31) * 8) for c in colors]
        for i, (c, s) in enumerate(((read(screen.chr), read(screen.scr)), (files[screen.chr], files[screen.scr]))):
            tiles = _decode_tiles(decode(c))
            entries = struct.unpack_from("<1024H", decode(s), 4)
            img = _canvas(tiles, entries)
            for y in range(192):
                for x in range(256):
                    v = img[y][x]
                    bank = entries[(y // 8) * 32 + x // 8] >> 12
                    sheet.putpixel((i * 256 + x, row * 192 + y), rgb[bank * 16 + v] if v else (0, 0, 0))
    sheet.resize((1024, 384 * len(SCREENS)), Image.NEAREST).save(destination)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1] / "extracted/data")
    ap.add_argument("--preview", type=Path, required=True)
    args = ap.parse_args()
    preview(lambda path: (args.root / path).read_bytes(), args.preview)


if __name__ == "__main__":
    main()
