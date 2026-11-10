"""Native UI strings whose English is longer than the Japanese storage.

Each string here is reached only through the pointer cells recorded in the
catalog (status-name tables, list titles, AI-tactic tables, prompts). The
English goes into old ARM9 string storage still free after combat_text and
battle_panel, and those cells are repointed. ARM9 is always resident, so the
same copy serves pointers from overlays too. The Japanese bytes stay in place.
"""
import json
from pathlib import Path
import struct

from battle_panel import free_ranges, place, prepare_battle_panel
from combat_text import subtract_ranges
from native_pool import ARM9_RAM
from native_strings import encode_native, load_native

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "translation/native_ui_relocated.json"
OVERLAY_RAM = {"overlays/ov_000.bin": 0x022AFE40, "overlays/ov_011.bin": 0x022AFE40}


def load_catalog(path=CATALOG):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate relocated native UI ID")
    in_place = {(r["source"], r["offset"]) for r in load_native()}
    for r in rows:
        if (r["source"], r["offset"]) in in_place:
            raise ValueError(f"String is also patched in place: {r['id']}")
        if not r["pointer_refs"]:
            raise ValueError(f"Relocated string has no pointer to repoint: {r['id']}")
        base = ARM9_RAM if r["source"] == "__system__/arm9.bin" else OVERLAY_RAM[r["source"]]
        for ref in r["pointer_refs"]:
            if ref["expected_pointer"] != base + r["offset"]:
                raise ValueError(f"Pointer ref does not name its string: {r['id']}")
        encode_native(r["en"])
    return rows


def prepare_relocation(sources, catalog=None):
    """sources: original bytes keyed by catalog source name."""
    rows = catalog if catalog is not None else load_catalog()
    arm9, overlay = sources["__system__/arm9.bin"], sources["overlays/ov_000.bin"]
    panel_writes, _, _ = prepare_battle_panel(arm9, overlay)
    free = subtract_ranges(
        free_ranges(arm9, overlay), [(s, s + len(raw)) for s, raw in panel_writes],
    )
    placed, writes, patches = {}, [], {}
    for r in rows:
        original = r["jp"].encode("shift_jis") + b"\0\0"
        if sources[r["source"]][r["offset"]:r["offset"] + len(original)] != original:
            raise ValueError(f"Relocated native UI Japanese precondition failed: {r['id']}")
        raw = encode_native(r["en"])
        if raw not in placed:
            placed[raw] = place(free, len(raw), 2)
            writes.append((placed[raw], raw))
        for ref in r["pointer_refs"]:
            key = ref["source"], ref["offset"]
            if struct.unpack_from("<I", sources[key[0]], key[1])[0] != ref["expected_pointer"]:
                raise ValueError(f"Relocated native UI pointer precondition failed: {r['id']}")
            if key in patches:
                raise ValueError(f"Pointer cell listed twice: {key}")
            patches[key] = (ref["expected_pointer"], ARM9_RAM + placed[raw])
    return writes, patches, {
        "strings": len(rows), "unique_encoded": len(placed), "pointer_cells": len(patches),
        "static_bytes": sum(len(raw) for _, raw in writes), "runtime_verified": False,
    }


def apply_relocation(rom, nds):
    """Run after apply_battle_panel: the target bytes must already be zeroed."""
    base = nds.arm9_rom_off
    spans = {"__system__/arm9.bin": (base, base + nds.arm9_size)}
    for name in OVERLAY_RAM:
        spans[name] = nds.fat[int(Path(name).stem.split("_")[1])]
    sources = {name: nds.data[s:e] for name, (s, e) in spans.items()}
    writes, patches, stats = prepare_relocation(sources)
    for start, raw in writes:
        if any(rom[base + start:base + start + len(raw)]):
            raise ValueError(f"Relocated native UI overlaps another patch at {start:#x}")
    for (name, offset), (expected, _) in patches.items():
        if struct.unpack_from("<I", rom, spans[name][0] + offset)[0] != expected:
            raise ValueError(f"Relocated pointer was already patched: {name}@{offset:#x}")
    for start, raw in writes:
        rom[base + start:base + start + len(raw)] = raw
    for (name, offset), (_, address) in patches.items():
        struct.pack_into("<I", rom, spans[name][0] + offset, address)
    return stats
