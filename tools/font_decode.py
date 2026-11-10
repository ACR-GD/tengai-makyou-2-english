#!/usr/bin/env python3
"""Render a raw 1bpp DS font (.cobj) to a PNG glyph sheet for inspection."""
import sys
import struct
import zlib


def png(width, height, pixels):
    """pixels: bytearray of width*height grayscale bytes -> PNG bytes."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += pixels[y * width:(y + 1) * width]
    def chunk(typ, data):
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")


def pixel(rowbytes, rx, bpp, msb_first):
    if bpp == 1:
        byte = rowbytes[rx // 8] if rx // 8 < len(rowbytes) else 0
        bit = rx % 8
        v = (byte >> (7 - bit)) & 1 if msb_first else (byte >> bit) & 1
        return 255 if v else None
    if bpp == 2:
        byte = rowbytes[rx // 4] if rx // 4 < len(rowbytes) else 0
        sub = rx % 4
        shift = (3 - sub) * 2 if msb_first else sub * 2
        v = (byte >> shift) & 3
        return [None, 110, 190, 255][v]
    if bpp == 4:
        byte = rowbytes[rx // 2] if rx // 2 < len(rowbytes) else 0
        v = (byte >> 4) & 0xF if (rx % 2 == 0) == msb_first else byte & 0xF
        return None if v == 0 else 60 + v * 13
    return None


def render_sheet(data, gw, gh, bytes_per_row, out, cols=32, count=1024, start=0,
                 msb_first=True, bpp=1):
    bpg = bytes_per_row * gh
    rows = (count + cols - 1) // cols
    cell_w, cell_h = gw + 1, gh + 1
    W, H = cols * cell_w, rows * cell_h
    img = bytearray([40] * (W * H))            # dark gray background
    for gi in range(count):
        goff = (start + gi) * bpg
        if goff + bpg > len(data):
            break
        gx = (gi % cols) * cell_w
        gy = (gi // cols) * cell_h
        for ry in range(gh):
            rowbytes = data[goff + ry * bytes_per_row: goff + (ry + 1) * bytes_per_row]
            for rx in range(gw):
                v = pixel(rowbytes, rx, bpp, msb_first)
                if v is not None:
                    img[(gy + ry) * W + (gx + rx)] = v
    open(out, "wb").write(png(W, H, img))
    print(f"wrote {out}  ({W}x{H}, {count} glyphs, {gw}x{gh}, {bytes_per_row}B/row, "
          f"bpp={bpp}, msb={msb_first})")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("path"); ap.add_argument("gw", type=int); ap.add_argument("gh", type=int)
    ap.add_argument("bpr", type=int); ap.add_argument("out")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--count", type=int, default=1024)
    ap.add_argument("--bpp", type=int, default=1)
    ap.add_argument("--lsb", action="store_true")
    ap.add_argument("--cols", type=int, default=32)
    a = ap.parse_args()
    data = open(a.path, "rb").read()
    render_sheet(data, a.gw, a.gh, a.bpr, a.out, cols=a.cols, count=a.count,
                 start=a.start, msb_first=not a.lsb, bpp=a.bpp)
