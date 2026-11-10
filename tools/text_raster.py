"""Rasterize English with the patched in-game VWF font (for baked-in graphics).

render(text) -> (width, height, set of (x, y) ink pixels), using the same
left-aligned Latin glyphs and advances that build_from_bytes() installs in
font12, so repainted images match the dialogue text.
"""
from functools import lru_cache
from pathlib import Path

from font import get_glyph
from sjis_glyph import sjis_to_glyph
from scs_codec import enc_char
from vwf_font import FONT_IN, build_from_bytes

LINE_HEIGHT = 12


@lru_cache(maxsize=1)
def _font():
    with open(Path(__file__).resolve().parents[1] / FONT_IN, "rb") as f:
        return build_from_bytes(f.read())


def glyph(ch):
    data, widths = _font()
    sj = enc_char(ch, translit=True)
    if len(sj) != 2 or (sj[0], sj[1]) not in widths:
        raise ValueError(f"No VWF glyph for {ch!r}")
    return get_glyph(data, sjis_to_glyph(sj)), widths[(sj[0], sj[1])]


def render(text):
    """One line; returns (advance width, LINE_HEIGHT, ink pixel set)."""
    ink, x = set(), 0
    for ch in text:
        grid, advance = glyph(ch)
        for y, row in enumerate(grid[:LINE_HEIGHT]):
            for gx, value in enumerate(row):
                if value:
                    ink.add((x + gx, y))
        x += advance
    return x, LINE_HEIGHT, ink
