"""Localize native combat strings without adding another heap lifetime.

Reclaim only catalog-owned old text and the replaced combat message strings.
Exclude subtitles, actor scratch, unresolved aliases and runtime-generated
pointer cells. Overlay pointers target persistent ARM9 text, not heap pointers.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct

from native_catalog import extract_catalog
from native_pool import ARM9_RAM, verified_arenas, pack_strings, merge_ranges
from native_strings import ESCAPE, encode_native
from ov008_build import SUBTITLE_ARM9_ARENA, BATTLE_NUMERIC_RENDERER
from vwf_font import measure_line_px

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "translation/combat_text.json"
SOURCES = ("__system__/arm9.bin", "overlays/ov_000.bin")


def subtract_ranges(ranges, excluded):
    result = [list(r) for r in ranges]
    for a, b in excluded:
        next_ranges = []
        for start, end in result:
            if start < b and a < end:
                if start < a:
                    next_ranges.append([start, a])
                if end > b:
                    next_ranges.append([b, end])
            else:
                next_ranges.append([start, end])
        result = next_ranges
    return result


def expanded_bound(text, item_bytes=52):
    """Conservative bound including generated names/numbers and native controls."""
    total, cursor = 2, 0
    for match in ESCAPE.finditer(text):
        total += len(encode_native(text[cursor:match.start()])) - 2
        token = match.group()
        total += (
            32 if token in ("￥Ｚ１", "￥Ｚ２") else
            item_bytes if token == "￥Ｚ３" else
            22 if token == "￥Ｄ" else 16
        )
        cursor = match.end()
    return total + len(encode_native(text[cursor:])) - 2


def validate_translation(row):
    jp, en = row["jp"], row["en"]
    if not isinstance(en, str) or bool(jp) != bool(en.strip()):
        raise ValueError(f"Missing combat translation: {row['id']}")
    # Line breaks are layout, so English may break lines where Japanese did not.
    jp_controls, en_controls = (
        [t for t in ESCAPE.findall(text) if t != "￥／"] for text in (jp, en)
    )
    if Counter(jp_controls) != Counter(en_controls):
        raise ValueError(f"Changed combat control/variable count: {row['id']}")
    is_variable = lambda token: token.startswith("￥Ｚ")
    if [t for t in jp_controls if not is_variable(t)] != [t for t in en_controls if not is_variable(t)]:
        raise ValueError(f"Changed combat control order: {row['id']}")
    if re.search(r"[^\x20-\x7e]", ESCAPE.sub("", en)):
        raise ValueError(f"Unsupported/untranslated combat prose: {row['id']}")
    if row.get("max_width_px") and measure_line_px(en) > row["max_width_px"]:
        raise ValueError(f"Combat menu label exceeds its proven column: {row['id']}")
    if expanded_bound(en) > 512:
        raise ValueError(f"Combat message can overflow the 512-byte buffer: {row['id']}")
    return encode_native(en)


def prepare_combat_text(arm9, overlay, catalog=None):
    catalog = catalog or json.loads(CATALOG.read_text(encoding="utf-8"))
    source = dict(zip(SOURCES, (arm9, overlay)))
    for name, data in source.items():
        if hashlib.sha256(data).hexdigest() != catalog["source_sha256"][name]:
            raise ValueError(f"Combat source hash differs: {name}")
    rows = catalog["labels"] + catalog["messages"]
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate combat translation ID")
    encoded = {}
    for row in rows:
        original = row["jp"].encode("shift_jis") + b"\0\0"
        offset = row["offset"]
        if source[row["source"]][offset:offset + len(original)] != original:
            raise ValueError(f"Combat Japanese precondition failed: {row['id']}")
        encoded[row["id"]] = validate_translation(row)
    arenas = verified_arenas(arm9, extract_catalog(arm9))
    # Include only nonempty messages whose known table references all move.
    for row in catalog["messages"]:
        if not row["jp"]:
            continue
        start = row["offset"]
        end = start + len(bytes.fromhex(row["raw_hex"]))
        if arm9[start:end] != bytes.fromhex(row["raw_hex"]):
            raise ValueError(f"Combat raw-source precondition failed: {row['id']}")
        aligned_end = (end + 3) & ~3
        if any(arm9[end:aligned_end]):
            raise ValueError(f"Combat alignment is not padding: {row['id']}")
        arenas.append([start, aligned_end])
    protected = [
        [0xF44DC, 0xF461C], list(SUBTITLE_ARM9_ARENA),
        list(BATTLE_NUMERIC_RENDERER),
        *catalog["protected_reclaim_ranges"],
    ]
    arenas = subtract_ranges(merge_ranges(arenas), protected)
    placements, writes = pack_strings(encoded.values(), arenas)
    patches = {}
    for row in rows:
        refs = row.get("pointer_refs")
        if refs is None:
            refs = [
                {"source": "__system__/arm9.bin", "offset": p,
                 "expected_pointer": ARM9_RAM + row["offset"]}
                for p in row["pointer_offsets"]
            ]
        if not row["jp"]:
            continue
        for ref in refs:
            key = ref["source"], ref["offset"]
            raw = source[key[0]]
            expected = ref["expected_pointer"]
            if struct.unpack_from("<I", raw, key[1])[0] != expected:
                raise ValueError(f"Combat pointer precondition failed: {row['id']}")
            address = ARM9_RAM + placements[encoded[row["id"]]]
            value = expected, address
            if key in patches and patches[key] != value:
                raise ValueError(f"Conflicting combat pointer translations: {key}")
            patches[key] = value
    forbidden_cells = {r["pointer_offset"] for r in catalog["preserve_pointer_entries"]}
    for (name, offset), _ in patches.items():
        if name == "__system__/arm9.bin" and offset in forbidden_cells:
            raise ValueError("Attempt to replace a runtime-generated combat pointer")
        if name == "__system__/arm9.bin" and any(s < offset + 4 and offset < e for s, e in arenas):
            raise ValueError("Combat allocation overlaps a pointer table")
    return arenas, writes, patches, {
        "labels": len(catalog["labels"]), "messages": len(catalog["messages"]),
        "pointer_cells": len(patches), "static_text_bytes": sum(len(raw) for _, raw in writes),
        "available_bytes": sum(e - s for s, e in arenas),
        "max_expanded_message_bound": max(expanded_bound(r["en"]) for r in rows),
        "runtime_generated_cells_preserved": len(forbidden_cells),
        "runtime_verified": False,
    }


def apply_combat_text(rom, nds):
    base = nds.arm9_rom_off
    arm9 = nds.data[base:base + nds.arm9_size]
    ostart, oend = nds.fat[0]
    arenas, writes, patches, stats = prepare_combat_text(arm9, nds.data[ostart:oend])
    sources = {SOURCES[0]: (base, arm9), SOURCES[1]: (ostart, nds.data[ostart:oend])}
    # Validate every span before changing even the in-memory ROM.
    for start, end in arenas:
        if bytes(rom[base + start:base + end]) != arm9[start:end]:
            raise ValueError(f"Combat text allocation overlaps another patch at {start:#x}")
    for (name, offset), (expected, _) in patches.items():
        if struct.unpack_from("<I", rom, sources[name][0] + offset)[0] != expected:
            raise ValueError(f"Combat pointer overlaps another patch: {name}@{offset:#x}")
    for start, end in arenas:
        rom[base + start:base + end] = b"\0" * (end - start)
    for start, raw in writes:
        rom[base + start:base + start + len(raw)] = raw
    for (name, offset), (_, address) in patches.items():
        struct.pack_into("<I", rom, sources[name][0] + offset, address)
    return stats
