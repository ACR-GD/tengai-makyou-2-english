#!/usr/bin/env python3
"""VWF Latin font: left-align and normalize the native Hudson Soft pixel-art
Latin glyphs inside font12_GothicW3_bit.cobj, and measure each glyph's advance
width (px).

Ground truth (verified via PyGhidra on ARM9 FUN_020185c8 & FUN_020190d4):
  * font12_GothicW3_bit.cobj stores 16x16 glyphs (12x12 active cell, default
    advance 12 px) across 40 SJIS lead-byte rows of 0x17A0 bytes each, split
    into two 0xBD0-byte top/bottom 8-scanline halves with bit-swapped 2-bit pairs.
  * The original font12 and HalfCharacter binaries ALREADY contain crisp 1bpp
    hand-drawn pixel-art glyphs for all ASCII characters (0x21..0x7E):
      - Lowercase 'a'..'z' are 1px-stroke glyphs on y=4..9 (ascenders y=1..9,
        descenders y=10), 1..6 px wide.
      - Uppercase 'A'..'Z', digits '0'..'9', and '!'/'?' are 1px-stroke glyphs
        that were stretched to y=0..10 by duplicating one interior scanline;
        removing the duplicated scanline places all capitals and digits cleanly
        on y=1..9 (matching lowercase ascenders y=1 and baseline y=9!).
  * Shifting each glyph's ink left to x=0 and advancing by (ink_w + 1) px
    (min 3 px, space = 4 px) gives an average width of ~5.7 px/char while
    preserving 100% authentic DS pixel art and leaving all Japanese glyphs
    untouched.

Output:
  * patched font bytes (same size as input cobj: 241,920 bytes)
  * width table: dict {(lead, trail): advance_px} for SJIS 0x81 / 0x82 VWF glyphs
"""
from __future__ import annotations

import os
import sys
from typing import Dict, Tuple

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from font import set_glyph, get_glyph, GW, GH  # noqa: E402
from scs_codec import enc_char  # noqa: E402
from sjis_glyph import sjis_to_glyph  # noqa: E402

FONT_IN = "extracted/data/string_work/grph/font12_GothicW3_bit.cobj"
HALF_FONT_IN = "extracted/data/string_work/grph/HalfCharacter_bit.cobj"

MIN_ADV = 3        # min advance (px) so 1px glyphs ('i', 'l', 'I', '!') have room for shadow + gap
MAX_ADV = 12       # full-width cell advance in font12 is 12 px (0x0C)
SPACE_ADV = 4      # advance for space (0x8140)
PAD = 1            # 1px gap after ink

# ---------------------------------------------------------------------------
# Static per-character pixel advance table (matches the ARM9 width table).
# Non-Latin / Japanese chars use the engine's native full-width advance (12px).
# ---------------------------------------------------------------------------
CHAR_WIDTHS: "Dict[str, int]" = {
    ' ': 4, '!': 3, '"': 6, '#': 8, '$': 7, '%': 10, '&': 9, "'": 3,
    '(': 5, ')': 5, '*': 8, '+': 8, ',': 3, '-': 5, '.': 3, '/': 9,
    '0': 7, '1': 5, '2': 7, '3': 7, '4': 8, '5': 7, '6': 7, '7': 8,
    '8': 7, '9': 7, ':': 3, ';': 3, '<': 9, '=': 8, '>': 9, '?': 8,
    '@': 8, 'A': 9, 'B': 8, 'C': 8, 'D': 8, 'E': 7, 'F': 7, 'G': 8,
    'H': 8, 'I': 3, 'J': 7, 'K': 9, 'L': 7, 'M': 10, 'N': 9, 'O': 8,
    'P': 8, 'Q': 8, 'R': 8, 'S': 8, 'T': 7, 'U': 8, 'V': 10, 'W': 10,
    'X': 9, 'Y': 10, 'Z': 9, '[': 4, '\\': 11, ']': 4, '^': 5, '_': 12,
    '`': 5, 'a': 7, 'b': 7, 'c': 6, 'd': 7, 'e': 7, 'f': 5, 'g': 7,
    'h': 7, 'i': 3, 'j': 3, 'k': 6, 'l': 3, 'm': 8, 'n': 7, 'o': 7,
    'p': 6, 'q': 6, 'r': 5, 's': 6, 't': 5, 'u': 7, 'v': 7, 'w': 8,
    'x': 7, 'y': 7, 'z': 6, '{': 5, '|': 7, '}': 5, '~': 9,
    '\u00a0': 4, '\u3000': 4,
}

# Transliteration aliases that scs_codec maps before encoding
_TRANSLIT_MAP = {
    '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
    '\u2026': '...', '\u2014': '-', '\u2013': '-',
    '\u30fb': '-', '\uff5c': '|', '\u2640': '!?',
}
_PUNCT_ALIAS: "Dict[str, str]" = {"'": "'", '"': '"', '-': '-', '~': '~'}


def char_width_px(ch: str) -> int:
    """Return the VWF advance width (px) for one display character.

    Handles transliteration aliases so the result matches what the ARM9
    actually renders.  Non-Latin glyphs default to 12 px (native font12 advance).
    """
    if ch in _TRANSLIT_MAP:
        return sum(char_width_px(c) for c in _TRANSLIT_MAP[ch])
    if ch in _PUNCT_ALIAS:
        ch = _PUNCT_ALIAS[ch]
    return CHAR_WIDTHS.get(ch, 12)


def measure_line_px(line: str) -> int:
    """Return the pixel width of a single line of display text (no \\n)."""
    import re as _re
    _TAG_RE = _re.compile(r'\{([0-9A-Fa-f]{4})\}|<([0-9A-Fa-f]{2})>')
    _PARAM_OPS = {'0010', '0011', '0014', '0015', '0019'}
    px = 0
    i = 0
    while i < len(line):
        m = _TAG_RE.match(line, i)
        if m:
            i = m.end()
            w = (m.group(1) or '').upper()
            if w in _PARAM_OPS and i < len(line):
                m2 = _TAG_RE.match(line, i)
                if m2:
                    i = m2.end()
                if w == '0019':
                    px += 60
            elif w == '001A':
                px += 60
            elif w in ('001B', '001E'):
                px += 36
            elif w == '0008':
                px += 6
            continue
        px += char_width_px(line[i])
        i += 1
    return px


def wrap_pixels(text: str, max_px: int = 196) -> str:
    """Word-wrap *text* so no line exceeds *max_px* pixels.

    Breaks only at ASCII spaces.  Inline {XXXX} tags (including 2-word opcodes
    and variable tags {001A}/{001B}/{001E}/{0019}) are kept with their words and
    have their rendered widths accounted for.  Existing \\n breaks are preserved.
    """
    import re as _re
    _TAG_RE = _re.compile(r'\{([0-9A-Fa-f]{4})\}|<([0-9A-Fa-f]{2})>')
    _PARAM_OPS = {'0010', '0011', '0014', '0015', '0019'}

    out_lines: "list[str]" = []
    space_px = char_width_px(' ')

    for paragraph in text.split('\n'):
        # Split paragraph into space-separated words (tags stay attached to adjacent words)
        words: "list[str]" = []
        cur_w: "list[str]" = []
        i = 0
        while i < len(paragraph):
            m = _TAG_RE.match(paragraph, i)
            if m:
                w = (m.group(1) or '').upper()
                end = m.end()
                if w in _PARAM_OPS and end < len(paragraph):
                    m2 = _TAG_RE.match(paragraph, end)
                    if m2:
                        end = m2.end()
                cur_w.append(paragraph[i:end])
                i = end
            elif paragraph[i] == ' ':
                if cur_w:
                    words.append(''.join(cur_w))
                    cur_w = []
                while i < len(paragraph) and paragraph[i] == ' ':
                    i += 1
            else:
                cur_w.append(paragraph[i])
                i += 1
        if cur_w:
            words.append(''.join(cur_w))

        if not words:
            out_lines.append('')
            continue

        cur_line: "list[str]" = []
        cur_px = 0
        for w_str in words:
            w_px = measure_line_px(w_str)
            if not cur_line:
                cur_line.append(w_str)
                cur_px = w_px
            elif cur_px + space_px + w_px <= max_px:
                cur_line.append(w_str)
                cur_px += space_px + w_px
            else:
                out_lines.append(' '.join(cur_line))
                cur_line = [w_str]
                cur_px = w_px
        if cur_line:
            out_lines.append(' '.join(cur_line))

    return '\n'.join(out_lines)


def _compress_11_to_9(grid: list) -> list:
    """Compress 11-row (y=0..10) font12 caps/digits to 9 rows (y=1..9) by
    removing duplicated interior scanlines so caps align with lowercase (y=1..9).
    """
    rows = [grid[y][:] for y in range(11)]
    if not any(rows[8]) and not any(rows[9]) and any(rows[10]):
        # Exclamation / question mark style: top bar on 0..7, gap on 8, dot on 10
        top = rows[:8]
        for i in [3, 4, 2, 5, 1, 6, 0]:
            if i + 1 < len(top) and top[i] == top[i + 1]:
                top.pop(i)
                break
        else:
            top.pop(len(top) // 2)
        new_rows = top + [[0] * GW, rows[10]]
    else:
        while len(rows) > 9:
            removed = False
            for i in [3, 4, 2, 6, 7, 5, 1, 8, 0, 9]:
                if i + 1 < len(rows) and rows[i] == rows[i + 1]:
                    rows.pop(i)
                    removed = True
                    break
            if not removed:
                rows.pop(len(rows) // 2)
        new_rows = rows
    out = [[0] * GW for _ in range(GH)]
    for idx, r in enumerate(new_rows):
        out[1 + idx] = r
    return out


def _compress_cols_if_dup(grid: list, target_w: int = 7) -> list:
    """Trim duplicated interior columns so wide glyphs fit target_w cleanly."""
    xs = [x for y in range(GH) for x in range(GW) if grid[y][x]]
    if not xs:
        return grid
    x0, x1 = min(xs), max(xs)
    cols = [[grid[y][x] for y in range(GH)] for x in range(x0, x1 + 1)]
    while len(cols) > target_w:
        removed = False
        mid_order = sorted(range(1, len(cols) - 1), key=lambda i: abs(i - len(cols) // 2))
        for i in mid_order:
            if i + 1 < len(cols) and cols[i] == cols[i + 1]:
                cols.pop(i)
                removed = True
                break
        if not removed:
            break
    out = [[0] * GW for _ in range(GH)]
    for cx, col in enumerate(cols):
        for y in range(GH):
            out[y][cx] = col[y]
    return out


def _build_native_glyph(ch: str, orig_font12: bytes, orig_half: bytes | None) -> Tuple[list, int]:
    """Return (16x16 grid of 0/1, advance_px) for one ASCII character."""
    if ch == ' ':
        return [[0] * GW for _ in range(GH)], SPACE_ADV
    if ch == '-':
        g = [[0] * GW for _ in range(GH)]
        for x in range(4):
            g[5][x] = 1
        return g, 5
    if ch == 'm':
        g = [[0] * GW for _ in range(GH)]
        rows = [
            "#.##.#.",
            "##.#..#",
            "#..#..#",
            "#..#..#",
            "#..#..#",
            "#..#..#",
        ]
        for dy, r in enumerate(rows):
            for x, c in enumerate(r):
                g[4 + dy][x] = 1 if c == '#' else 0
        return g, 8
    if ch == 'w':
        g = [[0] * GW for _ in range(GH)]
        rows = [
            "#..#..#",
            "#..#..#",
            "#.#.#.#",
            "#.#.#.#",
            ".#...#.",
            ".#...#.",
        ]
        for dy, r in enumerate(rows):
            for x, c in enumerate(r):
                g[4 + dy][x] = 1 if c == '#' else 0
        return g, 8

    sj = enc_char(ch)
    gi = sjis_to_glyph(sj)
    if orig_half is not None and ch in ('/', '<', '>', '+', '=', '~', '@'):
        g = get_glyph(orig_half, gi)
    else:
        g = get_glyph(orig_font12, gi)
        ys = [y for y in range(GH) for x in range(GW) if g[y][x]]
        if ys and min(ys) == 0 and max(ys) == 10:
            g = _compress_11_to_9(g)
        if 'A' <= ch <= 'Z':
            g = _compress_cols_if_dup(g, 6 if ch in "EFJLTZ" else 7)
        elif '0' <= ch <= '9' or ch in ('?', '|', '#', '$', '%', '&', '*'):
            g = _compress_cols_if_dup(g, 6)

    xs = [x for y in range(GH) for x in range(GW) if g[y][x]]
    if not xs:
        return [[0] * GW for _ in range(GH)], SPACE_ADV
    x0, x1 = min(xs), max(xs)
    w = x1 - x0 + 1
    out = [[0] * GW for _ in range(GH)]
    for y in range(GH):
        for x in range(x0, x1 + 1):
            if x - x0 < GW:
                out[y][x - x0] = g[y][x]
    adv = max(MIN_ADV, min(MAX_ADV, w + PAD))
    return out, adv


def build_from_bytes(font_bytes: bytes, ttf: str | None = None
                     ) -> Tuple[bytes, Dict[Tuple[int, int], int]]:
    """Left-align and normalize the Latin glyphs in `font_bytes`; return (patched, widths)."""
    orig_font12 = bytes(font_bytes)
    orig_half = open(HALF_FONT_IN, "rb").read() if os.path.exists(HALF_FONT_IN) else None
    data = bytearray(font_bytes)
    widths: Dict[Tuple[int, int], int] = {}

    for o in [0x20] + [x for x in range(0x21, 0x7F)]:
        ch = chr(o)
        sj = enc_char(ch)
        if len(sj) != 2:
            continue
        gi = sjis_to_glyph(sj)
        # Keep 0x815F ('＼') bitmap intact as backslash, but in FUN_020178b8 0x815F is an 8px spacer
        grid, adv = _build_native_glyph(ch, orig_font12, orig_half)
        set_glyph(data, gi, grid)
        widths[(sj[0], sj[1])] = adv
    return bytes(data), widths


def build_vwf_font(font_path: str = FONT_IN, ttf: str | None = None
                   ) -> Tuple[bytes, Dict[Tuple[int, int], int]]:
    return build_from_bytes(open(font_path, "rb").read(), ttf)


def build_half_from_bytes(half_bytes: bytes, patched_font12: bytes) -> bytes:
    """Copy left-aligned VWF Latin glyphs into HalfCharacter_bit.cobj (3 SJIS rows),
    preserving '0'..'9' (0x824F..0x8258) for FUN_02016a44 fixed-8px numeric columns.
    """
    half_data = bytearray(half_bytes)
    for o in [0x20] + [x for x in range(0x21, 0x7F)]:
        ch = chr(o)
        if '0' <= ch <= '9':
            continue
        sj = enc_char(ch)
        if len(sj) != 2 or sj[0] not in (0x81, 0x82, 0x83):
            continue
        gi = sjis_to_glyph(sj)
        set_glyph(half_data, gi, get_glyph(patched_font12, gi))
    return bytes(half_data)


def width_table_bytes(widths: Dict[Tuple[int, int], int]) -> bytes:
    """512-byte table: page0=lead 0x81, page1=lead 0x82, indexed by trail.

    Default 0x00 so untouched Japanese symbols/kana fall back to the engine's
    native advance ([ctx, #0xc] = 12px for font12 or 8px for HalfCharacter).
    """
    tbl = bytearray([0x00] * 512)
    for (lead, trail), w in widths.items():
        if lead == 0x81:
            tbl[trail & 0xFF] = w & 0xFF
        elif lead == 0x82:
            tbl[256 + (trail & 0xFF)] = w & 0xFF
    return bytes(tbl)


def preview(font_path: str, out_png: str, ttf: str | None = None) -> None:
    """Render a preview sheet of the narrowed Latin glyphs with advance marks."""
    data, widths = build_vwf_font(font_path, ttf)
    chars = [chr(o) for o in range(0x20, 0x7F)]
    cols = 16
    cw, chh = GW + 2, GH + 4
    rows = (len(chars) + cols - 1) // cols
    W, H = cols * cw, rows * chh
    im = Image.new("RGB", (W, H), (20, 20, 30))
    px = im.load()
    for idx, ch in enumerate(chars):
        sj = enc_char(ch)
        gi = sjis_to_glyph(sj)
        g = get_glyph(bytearray(data), gi)
        adv = widths.get((sj[0], sj[1]), 12)
        ox, oy = (idx % cols) * cw, (idx // cols) * chh
        for y in range(GH):
            for x in range(GW):
                if g[y][x]:
                    px[ox + x, oy + y] = (235, 235, 235)
        if 0 <= adv < GW:
            for y in range(GH):
                px[ox + adv, oy + y] = (200, 60, 60)
    im = im.resize((W * 4, H * 4), Image.NEAREST)
    im.save(out_png)
    print(f"wrote {out_png} ({im.size[0]}x{im.size[1]})")
    print("widths:", {chr(o): widths.get((enc_char(chr(o))[0], enc_char(chr(o))[1]))
                       for o in range(0x41, 0x5B)})


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", default=FONT_IN)
    ap.add_argument("--ttf", default=None)
    ap.add_argument("--preview", default="docs/vwf_font_preview.png")
    a = ap.parse_args()
    preview(a.font, a.preview, a.ttf)

