#!/usr/bin/env python3
"""Static battle-label patcher. Never writes a ROM or repository files.

build_battle_graphics(project_root_or_nds_bytes) -> (NitroFS replacement map, stats).
Only the optional --preview PNG and explicit --stats JSON are written by the CLI.
The caller owns FAT allocation, ROM integration, and runtime verification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

PREFIX = "iv_battle/grph/obj/files/"
COMMANDS = {
    1: "Fight", 2: "Sword", 3: "Break", 4: "Scroll", 5: "Stance",
    6: "Tactics", 7: "Gear", 8: "Items", 9: "??", 10: "Arts",
    11: "Skills", 12: "Demon", 13: "Cannon", 14: "Attack",
    15: "Flame", 16: "Torpedo", 17: "Heatshot",
}
NAMES = {1: "Manjimaru", 2: "Kabuki", 3: "Gokuraku", 4: "Kinu"}
# Each slash-separated row has the same width; narrow I and J are intentional.
FONT = {
    "A": "010/101/111/101/101", "B": "110/101/110/101/110",
    "C": "011/100/100/100/011", "D": "110/101/101/101/110",
    "E": "111/100/110/100/111", "F": "111/100/110/100/100",
    "G": "011/100/101/101/011", "H": "101/101/111/101/101",
    "I": "1/1/1/1/1", "J": "01/01/01/01/10",
    "K": "101/101/110/101/101", "L": "100/100/100/100/111",
    "M": "101/111/111/101/101", "N": "101/111/111/111/101",
    "O": "010/101/101/101/010", "P": "110/101/110/100/100",
    "Q": "010/101/101/111/011", "R": "110/101/110/101/101",
    "S": "011/100/010/001/110", "T": "111/010/010/010/010",
    "U": "101/101/101/101/111", "V": "101/101/101/101/010",
    "W": "101/101/111/111/101", "X": "101/101/010/101/101",
    "Y": "101/101/010/010/010", "Z": "111/001/010/100/111",
    "?": "110/001/010/000/010", "'": "1/1/0/0/0",
    "0": "111/101/101/101/111", "1": "01/11/01/01/01",
    "2": "110/001/010/100/111", "3": "110/001/010/001/110",
    "4": "101/101/111/001/001", "5": "111/100/110/001/110",
    "6": "011/100/110/101/010", "7": "111/001/010/010/010",
    "8": "010/101/010/101/010", "9": "010/101/011/001/110",
}
# Filled from the static evidence manifest before handoff; SHA-256 of source LZ10.
SOURCE_HASHES = {'bs_obj_command_icon0.cobj': '1155e7686badb25a458b076bd6053f4323d660b6d8de8dbc13ab5d32aa8a403e',
 'bs_obj_command_icon0_b.cobj': 'aed83f5914f3ac1154c5a66e9125340048a014e9c006b2e3a357ee26a1d99245',
 'bs_obj_command_icon0_c.cobj': '6017181009446fa75c067b2438e17671633eacc88fe96af6955ef98913d77c96',
 'bs_obj_command_icon1.cobj': 'c3b859ad4c1e545da039fe735fb0339b9267d244cf5ab98eb0d60e142f21f8ee',
 'bs_obj_command_icon10.cobj': '09384489906a247311b633d7c760722d9d5ed2c9b2feeb6d0f56efb7d7e5f274',
 'bs_obj_command_icon11.cobj': '43906b67b5fbf046992fad12cc5b65874a1deaf4a603a203612814562c71db47',
 'bs_obj_command_icon12.cobj': 'd26ddcd6c6f9db4e7a0c295131ab8eccd9bcbbbdec9a8c6dd01b5a2853bc11bb',
 'bs_obj_command_icon13.cobj': '51ad65449fac075c31ae845051eac9d2e1f36d4d278d6fdef666e4d231fe69b2',
 'bs_obj_command_icon14.cobj': '07d24064247735dc969be9b61fb2ed54cdaf8491c1586dd36134f11fa7b4e517',
 'bs_obj_command_icon15.cobj': '0d220d40c9c72fc81bd86eb6c6c2a14442e300e57b965198fb0a90cfe075f287',
 'bs_obj_command_icon16.cobj': '10644b3e465d9b552663eaddb00dc5ae73ef7f0ff92825c0cf7d973220904f3d',
 'bs_obj_command_icon17.cobj': '0c01440f8ca33659bf0580d1294090579030ef36d1f8bc57e1a6e071ee7412d1',
 'bs_obj_command_icon2.cobj': '70ac859a0d56dcbb33626a26c212917a26f63c116ca8b51938675d1c3332e199',
 'bs_obj_command_icon3.cobj': '1e2e63ed8a775759ee7b8e03df14b5afdb3161dde7a1d1feee9cc4bc978ccec9',
 'bs_obj_command_icon4.cobj': 'af545cd2b3521de6d8649771ca72d8e1f4276c7af35ff6d7a054cc252fa870f2',
 'bs_obj_command_icon5.cobj': '9cac8bbf3d064fe33cfd1411b84962804ba0c5a27459a14ca792bd4f768af961',
 'bs_obj_command_icon6.cobj': '83bafc10319bc7afbf6972d2e8fb986149af01b857c4825887c7ed84bb387ec0',
 'bs_obj_command_icon7.cobj': '12f20dc485b3349b1f4c3503d82379b068439e51faf1a81c5477e3a418343cfd',
 'bs_obj_command_icon8.cobj': 'c1f9fbe706b3083de988a54fe79e4b018245e6193e07b655b333cca1716ecdee',
 'bs_obj_command_icon9.cobj': 'c9fcdb5dc8a9666b407a45a3c215c2810aeae4ead9dc725045fe1b0ee466d396',
 'bs_obj_name_p1.cobj': '818d9ee7940afc9467fac05371b6c6830c95c7bd7678920f5c8c6551b78046fb',
 'bs_obj_name_p2.cobj': '03af61776f8b803d5b8049e42fe76104edd923271d4b2645c22caa66b588c6df',
 'bs_obj_name_p3.cobj': '06598adc26ae1167bc527140e923ceb9c6f59536f84c9f56f304ab4d4a8a6a03',
 'bs_obj_name_p4.cobj': '54a458f53b163c66733a41ac83bfdb65fec28e4792c2dfa120d1286a39d32aa1'}


def lz10_decode(data):
    """Decode one LZ10 stream, rejecting truncation, invalid references/overruns.

    Up to three trailing alignment bytes are allowed (their values are ignored).
    """
    data = bytes(data)
    if len(data) < 4 or data[0] != 0x10:
        raise ValueError("Expected LZ10 header")
    size = int.from_bytes(data[1:4], "little")
    if not size:
        raise ValueError("Zero-size/extended LZ10 is unsupported")
    out = bytearray()
    pos = 4
    while len(out) < size:
        if pos >= len(data):
            raise ValueError("Truncated LZ10 flags")
        flags = data[pos]
        pos += 1
        for shift in range(7, -1, -1):
            if len(out) == size:
                break
            if flags & (1 << shift):
                if pos + 2 > len(data):
                    raise ValueError("Truncated LZ10 reference")
                a, b = data[pos:pos + 2]
                pos += 2
                length, distance = (a >> 4) + 3, ((a & 15) << 8 | b) + 1
                if distance > len(out) or length > size - len(out):
                    raise ValueError("Invalid LZ10 reference distance/output size")
                for _ in range(length):
                    out.append(out[-distance])
            else:
                if pos >= len(data):
                    raise ValueError("Truncated LZ10 literal")
                out.append(data[pos])
                pos += 1
    if len(data) - pos > 3:
        raise ValueError("Unexpected data after LZ10 stream")
    return bytes(out)


def lz10_encode(raw):
    """Produce a standards-compatible literal-only stream, padded to four bytes."""
    raw = bytes(raw)
    if not 0 < len(raw) <= 0xFFFFFF:
        raise ValueError("LZ10 size must be 1..0xFFFFFF")
    out = bytearray(b"\x10" + len(raw).to_bytes(3, "little"))
    for pos in range(0, len(raw), 8):
        out.append(0)
        out.extend(raw[pos:pos + 8])
    out.extend(b"\0" * (-len(out) % 4))
    return bytes(out)


def tiles4_decode(raw, width, height):
    """Return rows of palette indices from row-major 8x8, low-nibble-first tiles."""
    if width <= 0 or height <= 0 or width % 8 or height % 8:
        raise ValueError("Tile canvas dimensions must be positive multiples of 8")
    if len(raw) != width * height // 2:
        raise ValueError("4bpp decoded size does not match canvas")
    pixels = [[0] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            tile = (y // 8) * (width // 8) + x // 8
            off = tile * 32 + (y % 8) * 4 + (x % 8) // 2
            pixels[y][x] = (raw[off] >> (4 * (x & 1))) & 15
    return pixels


def tiles4_encode(pixels):
    if not pixels or not pixels[0]:
        raise ValueError("Empty pixel canvas")
    width, height = len(pixels[0]), len(pixels)
    if width % 8 or height % 8 or any(len(row) != width for row in pixels):
        raise ValueError("Ragged or non-tile-aligned pixel canvas")
    out = bytearray(width * height // 2)
    for y, row in enumerate(pixels):
        for x, value in enumerate(row):
            if not isinstance(value, int) or not 0 <= value <= 15:
                raise ValueError("4bpp palette index outside 0..15")
            tile = (y // 8) * (width // 8) + x // 8
            off = tile * 32 + (y % 8) * 4 + (x % 8) // 2
            out[off] |= value << (4 * (x & 1))
    return bytes(out)


def text_width(text):
    if not text:
        return 0
    try:
        return sum(len(FONT[c].split("/")[0]) for c in text.upper()) + len(text) - 1
    except KeyError as error:
        raise ValueError(f"Unsupported compact-font character: {error.args[0]!r}") from error


def paint_text(pixels, text, rect):
    """Clear rect; center 3x5 variable-width text at 2x vertical scale.

    Shadow is one pixel down, not right, so a 32px name never clips horizontally.
    All bounds and character checks happen before any pixels are modified.
    """
    x, y, width, height = rect
    pw, ph = len(pixels[0]), len(pixels)
    tw = text_width(text)
    if width <= 0 or height <= 0 or x < 0 or y < 0 or x + width > pw or y + height > ph:
        raise ValueError("Text rectangle outside canvas")
    if tw > width or 11 > height:
        raise ValueError(f"{text!r} does not fit {width}x{height}: {tw}x11")
    points = []
    cursor = x + (width - tw) // 2
    top = y + (height - 11) // 2
    for char in text.upper():
        glyph = FONT[char].split("/")
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit == "1":
                    points.extend([(cursor + gx, top + gy * 2),
                                   (cursor + gx, top + gy * 2 + 1)])
        cursor += len(glyph[0]) + 1
    for xx, yy in points:
        if not (x <= xx < x + width and y <= yy and yy + 1 < y + height):
            raise ValueError("Text/shadow would clip")
    for yy in range(y, y + height):
        pixels[yy][x:x + width] = [0] * width
    for xx, yy in points:
        pixels[yy + 1][xx] = 2
    for xx, yy in points:
        pixels[yy][xx] = 5


def _nds_files(data):
    """Read-only NitroFS reader for source-NDS byte input."""
    data = bytes(data)
    if len(data) < 0x200:
        raise ValueError("Truncated NDS header")
    fnt_off, fnt_size, fat_off, fat_size = struct.unpack_from("<4I", data, 0x40)
    if (fat_size % 8 or fnt_size < 9 or fnt_off < 0x200 or fat_off < 0x200
            or fnt_off + fnt_size > len(data) or fat_off + fat_size > len(data)):
        raise ValueError("Invalid NDS FNT/FAT ranges")
    fnt = data[fnt_off:fnt_off + fnt_size]
    count = struct.unpack_from("<H", fnt, 6)[0]
    if not 1 <= count <= 0x1000 or count * 8 >= len(fnt):
        raise ValueError("Invalid NDS directory count")
    result, seen = {}, set()

    def walk(index, prefix):
        if index >= count or index in seen:
            raise ValueError("Invalid/cyclic NitroFS directory")
        seen.add(index)
        pos, fid = struct.unpack_from("<IH", fnt, index * 8)
        if pos < count * 8:
            raise ValueError("NitroFS subtable overlaps main table")
        while True:
            if pos >= len(fnt):
                raise ValueError("Truncated NitroFS directory")
            tag = fnt[pos]
            pos += 1
            if not tag:
                break
            length = tag & 0x7F
            if not length or pos + length > len(fnt):
                raise ValueError("Truncated NitroFS name")
            name = fnt[pos:pos + length].decode("ascii")
            pos += length
            if "/" in name or "\0" in name:
                raise ValueError("Unsafe NitroFS name")
            path = prefix + name
            if tag & 0x80:
                if pos + 2 > len(fnt):
                    raise ValueError("Truncated NitroFS directory ID")
                child = struct.unpack_from("<H", fnt, pos)[0]
                pos += 2
                if not 0xF000 <= child < 0xF000 + count:
                    raise ValueError("Invalid NitroFS child ID")
                walk(child - 0xF000, path + "/")
            else:
                if fid >= fat_size // 8 or path in result:
                    raise ValueError("Invalid NitroFS file ID/duplicate path")
                start, end = struct.unpack_from("<II", data, fat_off + fid * 8)
                if start > end or end > len(data):
                    raise ValueError("Invalid NitroFS file range")
                result[path] = (start, end)
                fid += 1
    walk(0, "")
    return {path: data[a:b] for path, (a, b) in result.items()}


def _source_reader(source):
    if isinstance(source, (bytes, bytearray, memoryview)):
        files = _nds_files(source)
        return lambda path: files[path]
    root = Path(source)
    if root.is_file():
        return _source_reader(root.read_bytes())
    candidates = [root / "extracted/data", root / "data", root]
    data_root = next((p for p in candidates if (p / PREFIX).is_dir()), None)
    if data_root is None:
        raise ValueError("Cannot locate extracted battle graphics under source root")
    return lambda path: (data_root / path).read_bytes()


def build_battle_graphics(source):
    """Return (21 replacement NitroFS paths -> LZ10 bytes, JSON-safe statistics)."""
    read = _source_reader(source)
    if len(SOURCE_HASHES) != 24:
        raise ValueError("Expected hash manifest for all 24 source assets")
    palette = read(PREFIX + "bs_obj.cplt")
    if hashlib.sha256(palette).hexdigest() != '0f6bd29ecf4543b336dc0b698703ec8e92038dc70075577091dd69ed682c5945':
        raise ValueError("Source hash precondition failed: bs_obj.cplt")
    verified, originals = {}, {}
    for filename, expected_hash in SOURCE_HASHES.items():
        compressed = read(PREFIX + filename)
        if hashlib.sha256(compressed).hexdigest() != expected_hash:
            raise ValueError(f"Source hash precondition failed: {filename}")
        raw = lz10_decode(compressed)
        width, height = (32, 40) if "_name_p" in filename else (
            (64, 32) if "icon0" in filename else (32, 16))
        pixels = tiles4_decode(raw, width, height)
        if tiles4_encode(pixels) != raw or lz10_decode(lz10_encode(raw)) != raw:
            raise AssertionError("Codec roundtrip failed")
        verified[filename], originals[filename] = pixels, raw
    replacements, asset_stats = {}, []
    for kind, labels in (("command_icon", COMMANDS), ("name_p", NAMES)):
        for index, text in labels.items():
            filename = f"bs_obj_{kind}{index}.cobj"
            pixels = [row[:] for row in verified[filename]]
            paint_text(pixels, text, (0, 0, 32, 16))
            if kind == "name_p":
                # Original status ink occupies the left 16px, unlike the 32px name.
                # Clear full rows, then keep HP/TP within that existing footprint.
                for row in pixels[16:40]:
                    row[:] = [0] * 32
                paint_text(pixels, "HP", (0, 16, 16, 12))
                paint_text(pixels, "TP", (0, 28, 16, 12))
            raw = tiles4_encode(pixels)
            if len(raw) != len(originals[filename]):
                raise AssertionError("Decoded allocation changed")
            encoded = lz10_encode(raw)
            if lz10_decode(encoded) != raw:
                raise AssertionError("Encoded replacement roundtrip failed")
            path = PREFIX + filename
            replacements[path] = encoded
            asset_stats.append({
                "path": path, "text": text, "text_width": text_width(text),
                "width": 32, "height": len(pixels), "bpp": 4,
                "decoded_bytes": len(raw), "compressed_bytes": len(encoded),
                "sha256": hashlib.sha256(encoded).hexdigest(),
                "palette_indices": sorted({p for row in pixels for p in row}),
            })
    return replacements, {
        "source_assets_verified": len(verified), "replacement_assets": len(replacements),
        "decorative_assets_unchanged": [
            PREFIX + f"bs_obj_command_icon0{suffix}.cobj" for suffix in ("", "_b", "_c")
        ],
        "palette_changed": False, "font_files_changed": False,
        "oam_geometry_changed": False, "static_only": True,
        "compression": "literal-only LZ10; caller must relocate/rebuild FAT",
        "shadow": "palette 2, one pixel down; white ink palette 5; background 0",
        "assets": asset_stats,
    }


def preview(source, replacements, destination):
    """Write a sheet rendered from the actual encoded-decoded replacement bytes."""
    from PIL import Image, ImageDraw
    palette = _source_reader(source)(PREFIX + "bs_obj.cplt")
    if len(palette) != 512:
        raise ValueError("Expected original 512-byte battle palette")
    colors = [tuple(((value >> shift) & 31) * 255 // 31 for shift in (0, 5, 10))
              for value in struct.unpack("<256H", palette)]
    canvas = Image.new("RGB", (720, len(replacements) * 100), "#303030")
    draw = ImageDraw.Draw(canvas)
    for index, (path, compressed) in enumerate(replacements.items()):
        height = 40 if "_name_p" in path else 16
        pixels = tiles4_decode(lz10_decode(compressed), 32, height)
        image = Image.new("RGB", (32, height))
        image.putdata([colors[value] for row in pixels for value in row])
        draw.text((8, index * 100 + 8), Path(path).name, fill="white")
        scale = 2 if height == 40 else 4
        canvas.paste(image.resize((32 * scale, height * scale), Image.Resampling.NEAREST),
                     (430, index * 100))
    canvas.save(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--stats", type=Path)
    args = parser.parse_args()
    replacements, stats = build_battle_graphics(args.source)
    if args.preview:
        preview(args.source, replacements, args.preview)
    if args.stats:
        args.stats.write_text(json.dumps(stats, indent=2) + "\n")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
