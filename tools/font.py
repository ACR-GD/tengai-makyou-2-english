#!/usr/bin/env python3
"""Tengai Makyou II font codec (verified against ARM9 FUN_020185c8 & FUN_020190d4).

Format:
  * glyph = 16x16 px, 1bpp (32 bytes/glyph)
  * Each SJIS lead-byte row is 0x17A0 (6,048) bytes = 189 glyphs, split into
    two 0xBD0 (3,024) byte halves:
      - Top 8 scanlines (ty=0, y=0..7):     row_idx * 0x17A0 + col_idx * 16 + tx * 8 + y
      - Bottom 8 scanlines (ty=1, y=8..15): row_idx * 0x17A0 + col_idx * 16 + 0xBD0 + tx * 8 + (y - 8)
  * Within each byte, adjacent bits in each 2-bit pair are swapped:
      swapped = ((b >> 1) & 0x55) | ((b & 0x55) << 1)
    and then shifted out MSB-first for x = 0..7.
"""
import struct
import zlib

GLYPH_BYTES = 32
ROW_BYTES = 0x17A0
HALF_ROW_BYTES = 0xBD0
GLYPHS_PER_ROW = 189
GW = GH = 16


def _glyph_base(idx: int) -> int:
    row_idx = idx // GLYPHS_PER_ROW
    col_idx = idx % GLYPHS_PER_ROW
    return row_idx * ROW_BYTES + col_idx * 16


def _pair_swap(b: int) -> int:
    return (((b >> 1) & 0x55) | ((b & 0x55) << 1)) & 0xFF


def get_glyph(data, idx):
    """Return 16x16 list-of-rows (each row list of 0/1)."""
    base = _glyph_base(idx)
    grid = [[0] * GW for _ in range(GH)]
    for ty in range(2):
        half = base + (HALF_ROW_BYTES if ty == 1 else 0)
        for tx in range(2):
            toff = half + tx * 8
            for y in range(8):
                b = data[toff + y] if toff + y < len(data) else 0
                swapped = _pair_swap(b)
                for x in range(8):
                    grid[ty * 8 + y][tx * 8 + x] = (swapped >> (7 - x)) & 1
    return grid


def set_glyph(data, idx, grid):
    """Write a 16x16 grid back into data (bytearray) at glyph idx."""
    base = _glyph_base(idx)
    for ty in range(2):
        half = base + (HALF_ROW_BYTES if ty == 1 else 0)
        for tx in range(2):
            toff = half + tx * 8
            for y in range(8):
                swapped = 0
                for x in range(8):
                    swapped = (swapped << 1) | (grid[ty * 8 + y][tx * 8 + x] & 1)
                data[toff + y] = _pair_swap(swapped)


def _png(w, h, px):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += px[y * w:(y + 1) * w]
    def ch(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n"
            + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + ch(b"IDAT", zlib.compress(bytes(raw), 9)) + ch(b"IEND", b""))


def sheet(data, out, start=0, count=512, cols=32, scale=1):
    cw, chh = GW + 1, GH + 1
    rows = (count + cols - 1) // cols
    W, H = cols * cw, rows * chh
    px = bytearray([40] * (W * H))
    for gi in range(count):
        if (start + gi) * GLYPH_BYTES >= len(data):
            break
        g = get_glyph(data, start + gi)
        ox, oy = (gi % cols) * cw, (gi // cols) * chh
        # faint cell separators every column to aid counting
        for y in range(GH):
            for x in range(GW):
                if g[y][x]:
                    px[(oy + y) * W + (ox + x)] = 255
    if scale > 1:
        W2, H2 = W * scale, H * scale
        px2 = bytearray(W2 * H2)
        for y in range(H):
            for x in range(W):
                v = px[y * W + x]
                for dy in range(scale):
                    for dx in range(scale):
                        px2[(y * scale + dy) * W2 + (x * scale + dx)] = v
        px, W, H = px2, W2, H2
    open(out, "wb").write(_png(W, H, px))
    print(f"wrote {out} ({W}x{H}) glyphs {start}..{start+count}")


if __name__ == "__main__":
    import sys
    d = open(sys.argv[1], "rb").read()
    out = sys.argv[2]
    start = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    count = int(sys.argv[4]) if len(sys.argv) > 4 else 512
    cols = int(sys.argv[5]) if len(sys.argv) > 5 else 32
    scale = int(sys.argv[6]) if len(sys.argv) > 6 else 1
    sheet(d, out, start, count, cols, scale)
