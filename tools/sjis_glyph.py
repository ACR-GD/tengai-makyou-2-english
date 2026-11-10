#!/usr/bin/env python3
"""SJIS -> font12 glyph index & byte offset (verified in ARM9 FUN_020185c8 & FUN_020190d4).

Each Shift-JIS lead-byte row is 0x17A0 (6,048) bytes = 189 glyphs * 32 bytes,
split into two 0xBD0 (3,024) byte halves:
  * Top 8 scanlines (y=0..7):     row_base + (trail - 0x40) * 16
  * Bottom 8 scanlines (y=8..15): row_base + (trail - 0x40) * 16 + 0xBD0
"""
ROW_BYTES = 0x17A0
HALF_ROW_BYTES = 0xBD0
GLYPHS_PER_ROW = 189


def sjis_row_index(lead: int) -> int:
    lead &= 0xFF
    if lead <= 0x9F:
        return lead - 0x81
    return lead - 0xC1


def sjis_offset(lead: int, trail: int) -> int:
    """Return byte offset of the top-half 8x16 slice in the font binary."""
    trail &= 0xFF
    return sjis_row_index(lead) * ROW_BYTES + (trail - 0x40) * 16


def sjis_to_glyph(sjis: bytes) -> int:
    """Return sequential glyph index (0..7559 for font12, 0..566 for HalfCharacter)."""
    if len(sjis) != 2:
        raise ValueError(sjis)
    return sjis_row_index(sjis[0]) * GLYPHS_PER_ROW + ((sjis[1] & 0xFF) - 0x40)


def glyph_to_offset(idx: int) -> int:
    """Return top-half byte offset in the font binary for sequential glyph index `idx`."""
    row_idx = idx // GLYPHS_PER_ROW
    col_idx = idx % GLYPHS_PER_ROW
    return row_idx * ROW_BYTES + col_idx * 16


def glyph_to_sjis_candidates():
    """Yield valid SJIS pairs whose glyph index is < 7560."""
    for lead in list(range(0x81, 0xA0)) + list(range(0xE0, 0xE9)):
        for trail in list(range(0x40, 0x7E + 1)) + list(range(0x80, 0xFC + 1)):
            try:
                b = bytes([lead, trail])
                b.decode("shift_jis")
            except Exception:
                continue
            g = sjis_to_glyph(b)
            if 0 <= g < 7560:
                yield b, g

