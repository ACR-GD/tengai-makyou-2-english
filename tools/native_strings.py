"""Insert explicitly mapped native strings without moving addresses or truncating.

Unmapped strings are not modified. This is not a general-purpose ARM9 pool
relocator: long item/name strings still require separate format work.
"""
import json
from pathlib import Path
import re
import struct

from scs_codec import enc_char, FW_SPACE

DEFAULT_DATA = Path(__file__).resolve().parents[1] / "translation/native_ui.json"
ESCAPE = re.compile(r"￥(?:Ｚ[０-９]+|.)")


def encode_native(text):
    """Full-width English, preserving the engine's literal ￥ escape language."""
    out = bytearray()
    position = 0
    while position < len(text):
        command = ESCAPE.match(text, position)
        if command:
            # Native commands are byte protocols, not display prose. In
            # particular SCS transliteration maps ＠ to a space and would
            # corrupt the real native ￥＠ opcode.
            out += command.group().encode("shift_jis")
            position = command.end()
            continue
        char = text[position]
        position += 1
        if char in "\n\r\x00":
            raise ValueError("Native UI strings cannot contain raw newlines or NUL")
        encoded = enc_char(char, translit=True)
        if len(encoded) % 2 or (encoded == FW_SPACE and not char.isspace()):
            raise ValueError(f"Unsupported native UI character: {char!r}")
        out += encoded
    return bytes(out) + b"\0\0"


def load_native(path=DEFAULT_DATA):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    seen = set()
    for r in rows:
        key = (r["source"], r["offset"])
        if key in seen:
            raise ValueError(f"Duplicate native UI address: {r['id']}")
        seen.add(key)
        if not isinstance(r["offset"], int) or r["offset"] < 0:
            raise ValueError(f"Invalid native UI offset: {r['id']}")
        if r["source"] != "__system__/arm9.bin" and not re.fullmatch(
            r"overlays/ov_[0-9]{3}\.bin", r["source"]
        ):
            raise ValueError(f"Unsupported native UI source: {r['source']}")
        if ESCAPE.findall(r["jp"]) != ESCAPE.findall(r["en"]):
            raise ValueError(f"Native UI escape sequence changed: {r['id']}")
        prose = ESCAPE.sub("", r["en"])
        if not prose.strip() or re.search(r"[\u3040-\u30ff\u4e00-\u9fff\uff66-\uff9f]", prose):
            raise ValueError(f"Missing English native UI text: {r['id']}")
        raw = encode_native(r["en"])
        original = r["jp"].encode("shift_jis") + b"\0\0"
        if len(raw) > len(original):
            raise ValueError(f"Native UI translation requires relocation: {r['id']}")
    return rows


def apply_native(rom, nds, root, records=None):
    """Verify extracted bytes and source ROM bytes before changing fixed spans."""
    if records is None:
        records = load_native()
    spans = []
    for r in records:
        source = r["source"]
        extracted = (Path(root) / source).read_bytes()
        if source == "__system__/arm9.bin":
            base, end = nds.arm9_rom_off, nds.arm9_rom_off + nds.arm9_size
        else:
            # Extraction names ov_NNN.bin correspond to NitroFS FAT file IDs,
            # not to the overlay ID field in the overlay table.
            fid = int(Path(source).stem.split("_")[1])
            overlay_fids = {
                struct.unpack_from("<I", nds.data, nds.arm9_ovl_off + i + 24)[0]
                for i in range(0, nds.arm9_ovl_size, 32)
            }
            if fid not in overlay_fids:
                raise ValueError(f"File ID is not an ARM9 overlay: {source}")
            base, end = nds.fat[fid]
        if nds.data[base:end] != extracted:
            raise ValueError(f"Extracted native binary differs from original ROM: {source}")
        offset = r["offset"]
        expected = r["jp"].encode("shift_jis") + b"\0\0"
        start, finish = base + offset, base + offset + len(expected)
        if finish > end or nds.data[start:finish] != expected:
            raise ValueError(f"Native UI Japanese precondition failed: {r['id']}")
        if any(start < b and a < finish for a, b in spans):
            raise ValueError(f"Overlapping native UI translations: {r['id']}")
        encoded = encode_native(r["en"])
        if len(encoded) > len(expected):
            raise ValueError(f"Native UI translation requires relocation: {r['id']}")
        spans.append((start, finish))
        if bytes(rom[start:finish]) != expected:
            raise ValueError(f"Native UI range conflicts with another patch: {r['id']}")
        rom[start:finish] = encoded + b"\0" * (len(expected) - len(encoded))
    return len(records)
