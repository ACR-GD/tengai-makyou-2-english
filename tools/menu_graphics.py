#!/usr/bin/env python3
"""English labels for the field menu sprites in data/usd/mainmenu.obc.

The file is LZ10 around a small container: u32 palette size (bit 31 set),
the palette, u32 tile size, then 8bpp OBJ tiles. The game loads the tiles at
OBJ VRAM offset 0x10000 with 128-byte 1D mapping, so an OAM tile number N
starts at byte (N - 512) * 128 of the tile data.

Text sprites have a transparent background over separate frame sprites, so a
label is repainted by clearing the sprite and drawing the battle menu's
compact font in the original ink. Labels that span several sprites (the
Command/Help bar, the item action words) are painted on one canvas and split.
Only tile bytes change; palette, sizes and OAM layout stay as they are.

    python tools/menu_graphics.py --preview menu_preview.png
"""
from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path

from battle_graphics import FONT as BATTLE_FONT, lz10_decode, lz10_encode

PATH = "data/usd/mainmenu.obc"
UNIT_BASE = 512
BUTTON_INK = (37, 34)   # white ink, slate shadow (default OBJ palette)
BOX_INK = (2, 3)        # name box / action words (their own palette bank)
FONT = dict(BATTLE_FONT, **{".": "0/0/0/0/1"})
LEFT = None  # align a label to the sprite's left edge, like the Japanese names

# (label, [(OAM tile, width, height), ...] left to right, ink, text rows,
#  [(text, center x on the canvas), ...])
LABELS = [
    ("command_help", [(706, 32, 16), (710, 32, 16), (714, 32, 16)], BUTTON_INK, (2, 13),
     [("Menu", 20), ("Help", 68)]),
    ("close", [(718, 32, 16)], BUTTON_INK, (2, 13), [("Close", 16)]),
    ("back", [(722, 32, 16)], BUTTON_INK, (2, 13), [("Back", 16)]),
    ("list", [(726, 32, 16)], BUTTON_INK, (2, 13), [("List", 16)]),
    ("status", [(730, 32, 16)], BUTTON_INK, (2, 13), [("Status", 16)]),
    ("items", [(734, 32, 16)], BUTTON_INK, (2, 13), [("Items", 16)]),
    ("scrolls", [(738, 32, 16)], BUTTON_INK, (2, 13), [("Scrolls", 16)]),
    ("gear", [(742, 32, 16)], BUTTON_INK, (2, 13), [("Gear", 16)]),
    ("techs", [(746, 32, 16)], BUTTON_INK, (2, 13), [("Techs", 16)]),
    ("cannon", [(754, 32, 16)], BUTTON_INK, (2, 13), [("Cannon", 16)]),
    ("warp", [(758, 32, 16)], BUTTON_INK, (2, 13), [("Warp", 16)]),
    ("map", [(762, 32, 16)], BUTTON_INK, (2, 13), [("Map", 16)]),
    ("mode", [(766, 32, 16)], BUTTON_INK, (2, 13), [("Mode", 16)]),
    ("tactics", [(770, 32, 16)], BUTTON_INK, (2, 13), [("Tactics", 16)]),
    # The HP/TP label sprites start 26px right of the name: short forms only.
    ("name_manjimaru", [(774, 32, 16)], BOX_INK, (0, 11), [("Manji", LEFT)]),
    ("name_kabuki", [(778, 32, 16)], BOX_INK, (0, 11), [("Kabuki", LEFT)]),
    ("name_gokuraku", [(782, 32, 16)], BOX_INK, (0, 11), [("Gokur.", LEFT)]),
    ("name_kinu", [(786, 32, 16)], BOX_INK, (0, 11), [("Kinu", LEFT)]),
    ("label_hp", [(790, 16, 16)], BOX_INK, (0, 11), [("HP", 8)]),
    ("label_tp", [(792, 16, 16)], BOX_INK, (0, 11), [("TP", 8)]),
    ("label_level", [(794, 16, 16)], BOX_INK, (0, 11), [("Lv", 8)]),
    # あと N: points to the next level (shown when praying at a shrine).
    ("label_next", [(796, 16, 16)], BOX_INK, (0, 11), [("Nxt", 8)]),
    ("use", [(838, 16, 16), (840, 16, 16), (842, 16, 16)], BOX_INK, (0, 11), [("Use", 24)]),
    ("buy", [(844, 16, 16), (846, 16, 16), (848, 16, 16)], BOX_INK, (0, 11), [("Buy", 24)]),
    ("sell", [(850, 16, 16), (852, 16, 16), (854, 16, 16)], BOX_INK, (0, 11), [("Sell", 24)]),
    ("store", [(856, 16, 16), (858, 16, 16), (860, 16, 16)], BOX_INK, (0, 11), [("Store", 24)]),
    ("take", [(862, 16, 16), (864, 16, 16), (866, 16, 16)], BOX_INK, (0, 11), [("Take", 24)]),
    ("drop", [(868, 16, 16), (870, 16, 16), (872, 16, 16)], BOX_INK, (0, 11), [("Drop", 24)]),
]


def split_container(raw):
    head = struct.unpack_from("<I", raw, 0)[0]
    pal_size = head & 0x7FFFFFFF
    if not head & 0x80000000 or pal_size != 192:
        raise ValueError("Unexpected mainmenu.obc palette header")
    tile_size = struct.unpack_from("<I", raw, 4 + pal_size)[0]
    start = 8 + pal_size
    if start + tile_size != len(raw) or tile_size % 128:
        raise ValueError("Unexpected mainmenu.obc tile block size")
    return start, tile_size


def read_sprite(tiles, unit, width, height):
    base = (unit - UNIT_BASE) * 128
    if base < 0 or base + width * height > len(tiles):
        raise ValueError(f"Sprite tile {unit} is outside mainmenu.obc")
    cols = width // 8
    return [[tiles[base + ((y // 8) * cols + x // 8) * 64 + (y % 8) * 8 + x % 8]
             for x in range(width)] for y in range(height)]


def write_sprite(tiles, unit, pixels):
    base = (unit - UNIT_BASE) * 128
    cols = len(pixels[0]) // 8
    for y, row in enumerate(pixels):
        for x, value in enumerate(row):
            tiles[base + ((y // 8) * cols + x // 8) * 64 + (y % 8) * 8 + x % 8] = value


def text_width(text):
    return sum(len(FONT[c].split("/")[0]) for c in text.upper()) + len(text) - 1


def paint(canvas, text, center, rows, ink, max_right=None):
    """Compact font at 2x vertical, shadow one pixel down; must not clip."""
    top, bottom = rows
    if bottom - top < 11:
        raise ValueError("Label rows are shorter than the 11px font")
    ink_index, shadow_index = ink
    width = text_width(text)
    left = 0 if center is LEFT else center - width // 2
    if left < 0 or left + width > (max_right or len(canvas[0])):
        raise ValueError(f"{text!r} does not fit its sprite canvas")
    y0 = top + (bottom - top - 11) // 2
    points, cursor = [], left
    for char in text.upper():
        glyph = FONT[char].split("/")
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit == "1":
                    points += [(cursor + gx, y0 + gy * 2), (cursor + gx, y0 + gy * 2 + 1)]
        cursor += len(glyph[0]) + 1
    for x, y in points:
        canvas[y + 1][x] = shadow_index
    for x, y in points:
        canvas[y][x] = ink_index


def build_menu_graphics(read):
    """read(path) -> original bytes. Returns ({path: new LZ10 bytes}, stats)."""
    compressed = read(PATH)
    raw = lz10_decode(compressed)
    start, size = split_container(raw)
    tiles = bytearray(raw[start:start + size])
    seen, stats = set(), []
    for name, sprites, ink, rows, texts in LABELS:
        for unit, width, height in sprites:
            span = range(unit, unit + width * height // 128)
            if seen.intersection(span):
                raise ValueError(f"Overlapping menu sprites: {name}")
            seen.update(span)
            read_sprite(tiles, unit, width, height)
        if any(h != sprites[0][2] for _, _, h in sprites):
            raise ValueError(f"Mixed sprite heights in {name}")
        canvas = [[0] * sum(w for _, w, _ in sprites) for _ in range(sprites[0][2])]
        for text, center in texts:
            paint(canvas, text, center, rows, ink, 24 if name.startswith("name_") else None)
        x = 0
        for unit, width, height in sprites:
            write_sprite(tiles, unit, [row[x:x + width] for row in canvas])
            x += width
        stats.append({"label": name, "text": [t for t, _ in texts],
                      "tiles": [s[0] for s in sprites]})
    new_raw = raw[:start] + bytes(tiles)
    encoded = lz10_encode(new_raw)
    if lz10_decode(encoded) != new_raw:
        raise AssertionError("mainmenu.obc roundtrip failed")
    return {PATH: encoded}, {
        "path": PATH, "labels": len(stats), "decoded_bytes": len(new_raw),
        "source_sha256": hashlib.sha256(compressed).hexdigest(),
        "compressed_bytes": len(encoded), "palette_changed": False,
        "runtime_verified": False, "assets": stats,
    }


def preview(read, destination, scale=3):
    from PIL import Image, ImageDraw
    old = lz10_decode(read(PATH))
    new = lz10_decode(build_menu_graphics(read)[0][PATH])
    start, size = split_container(old)
    pal = [struct.unpack_from("<H", old, 4 + i * 2)[0] for i in range(96)]
    rgb = [((c & 31) * 8, ((c >> 5) & 31) * 8, ((c >> 10) & 31) * 8) for c in pal]
    shade = {2: (255, 255, 255), 3: (70, 70, 120)}
    rows = []
    for name, sprites, ink, _, _ in LABELS:
        pair = []
        for raw in (old, new):
            tiles = raw[start:start + size]
            width = sum(w for _, w, _ in sprites)
            im = Image.new("RGB", (width, sprites[0][2]), (25, 30, 80))
            x = 0
            for unit, w, h in sprites:
                for yy, row in enumerate(read_sprite(tiles, unit, w, h)):
                    for xx, v in enumerate(row):
                        if v:
                            im.putpixel((x + xx, yy), shade.get(v, rgb[v] if v < 96 else (255, 0, 255))
                                        if ink == BOX_INK else (rgb[v] if v < 96 else (255, 0, 255)))
                x += w
            pair.append(im)
        rows.append((name, pair))
    sheet = Image.new("RGB", (240, 20 * len(rows)), (50, 50, 50))
    draw = ImageDraw.Draw(sheet)
    for i, (name, (a, b)) in enumerate(rows):
        draw.text((2, i * 20 + 4), name[:14], fill=(220, 220, 220))
        sheet.paste(a, (90, i * 20 + 2))
        sheet.paste(b, (140, i * 20 + 2))
    sheet.resize((sheet.width * scale, sheet.height * scale), Image.NEAREST).save(destination)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1] / "extracted/data")
    ap.add_argument("--preview", type=Path, required=True)
    args = ap.parse_args()
    preview(lambda path: (args.root / path).read_bytes(), args.preview)


if __name__ == "__main__":
    main()
