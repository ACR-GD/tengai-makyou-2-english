"""Build the complete heap-loaded native English resource.

No ARM9/BSS expansion or lossy truncation. English display/readings share
strings, original table indices stay fixed, and only the known scratch area
is reclaimed from the old text storage by native_boot.py.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct

from native_catalog import ARM9_RAM, extract_catalog, UNRECLAIMED_CATEGORIES
from native_strings import encode_native, ESCAPE

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "translation/native_catalog.json"
LAYOUT_PATH = ROOT / "translation/native_pool_layout.json"
SOURCE_SHA256 = "4a4e50f1a607d5a20083e985c05615f4bda7808ae7dbd63afff5e52fec617b1e"
UNALIGNED_REFERENCE_GUARD = (0xF73F4, 0xF7408)
ENEMY_BUFFER_BYTES = 32  # display[32], reading[32], including the NUL terminator
PAYLOAD_MAGIC = b"TM2N"
PAYLOAD_HEADER_BYTES = 32


def merge_ranges(ranges):
    result = []
    for start, end in sorted(ranges):
        if result and start <= result[-1][1]:
            result[-1][1] = max(end, result[-1][1])
        else:
            result.append([start, end])
    return result


def verified_arenas(source, original):
    """Derive exact ownership + immediate four-byte zero alignment, not envelopes."""
    ranges = []
    for r in original:
        if not r["jp"] or r["category"] in UNRECLAIMED_CATEGORIES:
            # The empty enemy sentinel aliases a numeric record. Never reclaim it.
            continue
        start = r["offset"]
        end = start + r["original_bytes_with_nul"]
        aligned_end = (end + 3) & ~3
        if any(source[end:aligned_end]):
            raise ValueError(f"Nonzero string alignment bytes: {r['id']}")
        ranges.append((start, aligned_end))
    guard_start, guard_end = UNALIGNED_REFERENCE_GUARD
    result = []
    for start, end in merge_ranges(ranges):
        if start < guard_end and guard_start < end:
            if start < guard_start:
                result.append([start, guard_start])
            if end > guard_end:
                result.append([guard_end, end])
        else:
            result.append([start, end])
    return result


def validate_catalog(source, catalog, layout):
    digest = hashlib.sha256(source).hexdigest()
    if digest != SOURCE_SHA256 or catalog["source_sha256"] != digest or layout["source_sha256"] != digest:
        raise ValueError("Native text source hash differs from the verified ATMJ ARM9")
    original = extract_catalog(source)
    records = catalog["records"]
    if len(records) != len(original):
        raise ValueError("Native catalog is incomplete")
    by_id = {r["id"]: r for r in records}
    if len(by_id) != len(records):
        raise ValueError("Native catalog has duplicate IDs")
    encoded = {}
    for expected in original:
        r = by_id.get(expected["id"])
        if r is None or any(r.get(k) != expected[k] for k in (
            "id", "category", "source", "pointer_offset", "offset", "original_bytes_with_nul", "jp",
        )):
            raise ValueError(f"Native catalog source identity changed: {expected['id']}")
        en = r.get("en")
        if not isinstance(en, str) or (
            r["jp"] and not en.strip()
        ) or (not r["jp"] and en != ""):
            raise ValueError(f"Missing native translation or changed empty sentinel: {r['id']}")
        if ESCAPE.findall(en) != ESCAPE.findall(r["jp"]):
            raise ValueError(f"Changed native escape commands: {r['id']}")
        if re.search(r"[^\x20-\x7e]", ESCAPE.sub("", en)):
            raise ValueError(f"Native English must use supported ASCII prose: {r['id']}")
        raw = encode_native(en)
        if r["category"].startswith("enemies_") and len(raw) > ENEMY_BUFFER_BYTES:
            raise ValueError(f"Enemy name exceeds the 32-byte copy buffer: {r['id']} ({en})")
        encoded[r["id"]] = raw
    for r in records:
        if r["category"].endswith("_reading"):
            display_id = r["id"].replace("_reading/", "_display/")
            if r["en"] != by_id[display_id]["en"]:
                raise ValueError(f"Reading/display English diverges: {r['id']}")
    arenas = verified_arenas(source, original)
    if arenas != layout["arenas"] or sum(e - s for s, e in arenas) != 22156:
        raise ValueError("Native pool layout differs from independently verified string ownership")
    for a, b in layout["protected"]:
        if any(s < b and a < e for s, e in arenas):
            raise ValueError("Native pool overlaps a protected metadata/reference range")
    for r in original:
        if any(s < r["pointer_offset"] + 4 and r["pointer_offset"] < e for s, e in arenas):
            raise ValueError("Native pool overlaps a pointer table")
    return original, encoded, arenas


def pack_strings(strings, arenas):
    """Deterministic best-fit allocation with whole-string UTF-16/SJIS suffix sharing."""
    free = [list(pair) for pair in arenas]
    placements = {}
    writes = []
    unique = set(strings)
    if any(len(raw) % 2 or not raw.endswith(b"\0\0") for raw in unique):
        raise ValueError("Native pool requires complete two-byte characters and NUL words")
    for raw in sorted(unique, key=lambda value: (-len(value), value)):
        if raw == b"\0\0":
            continue
        # A suffix is valid only at a complete 16-bit character boundary.
        shared = next((
            offset + len(parent) - len(raw)
            for parent, offset in placements.items()
            if parent.endswith(raw) and (len(parent) - len(raw)) % 2 == 0
        ), None)
        if shared is not None:
            placements[raw] = shared
            continue
        candidates = [
            (end - start, start, i) for i, (start, end) in enumerate(free)
            if end - start >= len(raw)
        ]
        if not candidates:
            remaining = sum(e - s for s, e in free)
            raise ValueError(
                f"Native pool capacity exhausted: need a {len(raw)}-byte contiguous string, "
                f"{remaining} bytes remain; shorten complete inventory wording, never truncate"
            )
        _, start, index = min(candidates)
        placements[raw] = start
        writes.append((start, raw))
        free[index][0] += len(raw)
    return placements, writes


def build_native_payload(source, catalog=None, layout=None):
    if catalog is None:
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if layout is None:
        layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    original, encoded, _ = validate_catalog(source, catalog, layout)
    sentinel_offset = PAYLOAD_HEADER_BYTES + len(original) * 8
    strings_offset = sentinel_offset + 2
    upper_bound = sum(len(raw) for raw in set(encoded.values()) if raw != b"\0\0")
    placements, writes = pack_strings(encoded.values(), [(strings_offset, strings_offset + upper_bound)])
    size = max((offset + len(raw) for offset, raw in writes), default=strings_offset)
    result = bytearray(size)
    struct.pack_into(
        "<4s7I", result, 0, PAYLOAD_MAGIC, 1, len(original), strings_offset,
        size, 0, 0, 0,
    )
    for start, raw in writes:
        result[start:start + len(raw)] = raw
    for index, r in enumerate(original):
        raw = encoded[r["id"]]
        offset = sentinel_offset if not r["jp"] else placements[raw]
        struct.pack_into(
            "<II", result, PAYLOAD_HEADER_BYTES + index * 8,
            ARM9_RAM + r["pointer_offset"], offset,
        )
        if bytes(result[offset:offset + len(raw)]) != raw:
            raise ValueError(f"Native payload string round trip failed: {r['id']}")
    return bytes(result), {
        "records": len(original),
        "translated_nonempty": sum(bool(r["jp"]) for r in original),
        "empty_sentinels": sum(not r["jp"] for r in original),
        "category_counts": dict(Counter(r["category"] for r in original)),
        "allocated_bytes": sum(len(raw) for _, raw in writes),
        "resource_bytes": len(result),
        "heap_allocation_bytes": (len(result) + 15) & ~15,
        "unique_encoded_strings": len(set(encoded.values())),
        "stored_strings": len(writes),
        "method": "heap_loaded_nitrofs_resource_fullwidth_shared_readings_and_suffixes",
        "reading_policy": "English display text; original indices preserved; no sorting-table reordering",
        "runtime_verified": False,
    }


def resolve_payload(source, payload):
    """Validate all pointer records and expose the exact bytes used at runtime."""
    if len(payload) < PAYLOAD_HEADER_BYTES:
        raise ValueError("Native resource header is missing")
    magic, version, count, strings_offset, size, _, _, _ = struct.unpack_from("<4s7I", payload)
    original = extract_catalog(source)
    expected_strings = PAYLOAD_HEADER_BYTES + len(original) * 8 + 2
    if (
        magic != PAYLOAD_MAGIC or version != 1 or count != len(original)
        or strings_offset != expected_strings or size != len(payload)
        or strings_offset > len(payload)
    ):
        raise ValueError("Invalid native resource header")
    result = {}
    for index, r in enumerate(original):
        cell, offset = struct.unpack_from("<II", payload, PAYLOAD_HEADER_BYTES + 8 * index)
        if cell != ARM9_RAM + r["pointer_offset"] or offset % 2:
            raise ValueError(f"Invalid native resource table cell: {r['id']}")
        if not strings_offset - 2 <= offset < len(payload):
            raise ValueError(f"Invalid native resource string offset: {r['id']}")
        end = offset
        while end + 1 < len(payload) and payload[end:end + 2] != b"\0\0":
            end += 2
        if end + 1 >= len(payload):
            raise ValueError(f"Unterminated native resource string: {r['id']}")
        result[r["id"]] = bytes(payload[offset:end + 2])
    return result
