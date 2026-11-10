"""Short names for the top-screen battle status panel.

The panel (ov_000) draws gear and items in 68px cells and scrolls in a 7-column
grid of 28px cells sized for two-kanji names, so full English names collide
(and the last column wraps around the 256px bitmap). Its name lookups go
through ARM9 stubs to the shared display accessors; those panel calls are
retargeted to small lookups that return a short form when one exists and
otherwise defer to the original accessor. Menus keep the full names.

Each lookup has a u16 table indexed by id: 0 = no short form, else the short
string's address minus SHORT_BASE. Code, tables and strings live in old ARM9
string storage left free after combat_text has packed its strings.

The same module fixes the battle message wait cursor. Every 8 frames ov_000
draws "▼" or "　" (which clears the cell) at the message cursor through
RENDERER, then subtracts a fixed 12 to undo the renderer's advance. VWF makes
"　" advance 4px, so the cursor crept 8px left per blink and the clearing cell
ate the end of the message. A wrapper around those two draws leaves the cursor
exactly 12px past where the draw started, whatever the glyph's width.
"""
import json
from pathlib import Path
import re
import struct

from combat_text import prepare_combat_text, SOURCES
from native_pool import ARM9_RAM
from native_strings import encode_native
from vwf_font import measure_line_px

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "translation/battle_panel.json"
OVERLAY_RAM = 0x022AFE40  # ov_000 load address
SHORT_BASE = 0x020F0000
STUB_CODE = bytes.fromhex("00c09fe51cff2fe1")  # ldr ip, [pc]; bx ip
LOOKUP_WORDS = 13
RENDERER = 0x020768DC  # battle message renderer; strb's its end cursor to CURSOR+0x26
CURSOR = 0x022F3164
BLINK_SITES = (0x2DB0, 0x2DDC)  # ov_000 `bl RENDERER` for the "▼" / "　" blink


def _bl(site_ram, target_ram):
    displacement = target_ram - (site_ram + 8)
    if displacement % 4 or not -(1 << 25) <= displacement < (1 << 25):
        raise ValueError("BL target is unaligned or out of range")
    return 0xEB000000 | ((displacement >> 2) & 0xFFFFFF)


def lookup_code(count, table_ram, accessor):
    """r0 = id -> r0 = short-name pointer, else tail-call the original accessor."""
    return [
        0xE3500000 | count,  # cmp r0, #count
        0x2A000006,          # bhs fallback
        0xE59F1018,          # ldr r1, [pc, #0x18]   (table)
        0xE0811080,          # add r1, r1, r0, lsl #1
        0xE1D110B0,          # ldrh r1, [r1]
        0xE3510000,          # cmp r1, #0
        0x159F000C,          # ldrne r0, [pc, #0xc]  (SHORT_BASE)
        0x10800001,          # addne r0, r0, r1
        0x112FFF1E,          # bxne lr
        0xE59FF004,          # fallback: ldr pc, [pc, #4] (accessor)
        table_ram,
        SHORT_BASE,
        accessor,
    ]


def blink_code(code_ram, scratch_ram):
    """Call RENDERER, then set the cursor to its start x + 12 (r2 = start x)."""
    return [
        0xE59FC020,                          # ldr ip, [pc, #0x20]  (scratch)
        0xE58CE000,                          # str lr, [ip]
        0xE5CC2004,                          # strb r2, [ip, #4]
        _bl(code_ram + 12, RENDERER),        # bl RENDERER (stack args untouched)
        0xE59FC010,                          # ldr ip, [pc, #0x10]  (scratch)
        0xE5DC1004,                          # ldrb r1, [ip, #4]
        0xE281100C,                          # add r1, r1, #12
        0xE59F2008,                          # ldr r2, [pc, #8]     (CURSOR)
        0xE5C21026,                          # strb r1, [r2, #0x26]
        0xE59CF000,                          # ldr pc, [ip]
        scratch_ram,
        CURSOR,
    ]


def load_catalog(catalog=None):
    catalog = catalog or json.loads(CATALOG.read_text(encoding="utf-8"))
    for lookup in catalog["lookups"]:
        rows = catalog[lookup["name"]]
        indexes = [r["index"] for r in rows]
        if len(set(indexes)) != len(indexes) or not all(0 <= i < lookup["count"] for i in indexes):
            raise ValueError(f"Invalid battle panel indexes: {lookup['name']}")
        if not 0 < lookup["count"] < 0x100:
            raise ValueError(f"Battle panel count must fit cmp #imm8: {lookup['name']}")
        for r in rows:
            short = r["short"]
            if not short.strip() or re.search(r"[^\x20-\x7e]", short):
                raise ValueError(f"Unsupported battle panel name: {lookup['name']}/{r['index']}")
            if measure_line_px(short) > lookup["max_width_px"]:
                raise ValueError(f"Battle panel name exceeds its cell: {short}")
    return catalog


def free_ranges(arm9, overlay):
    """Old string storage that combat_text zeroes but leaves unused."""
    arenas, writes, _, _ = prepare_combat_text(arm9, overlay)
    used = sorted((start, start + len(raw)) for start, raw in writes)
    result = []
    for start, end in arenas:
        cursor = start
        for a, b in used:
            if a < end and cursor < b:
                if a > cursor:
                    result.append([cursor, a])
                cursor = max(cursor, b)
        if cursor < end:
            result.append([cursor, end])
    return result


def place(free, size, align):
    for span in free:
        start = (span[0] + align - 1) & ~(align - 1)
        if start + size <= span[1]:
            span[0] = start + size
            return start
    raise ValueError(f"No free {size}-byte span for the battle panel")


def prepare_battle_panel(arm9, overlay, catalog=None):
    catalog = load_catalog(catalog)
    free = free_ranges(arm9, overlay)
    writes, calls = [], []
    stats = {"lookups": {}, "call_sites": 0, "runtime_verified": False}
    for lookup in catalog["lookups"]:
        count, accessor = lookup["count"], lookup["accessor"]
        if struct.unpack_from("<I", arm9, accessor - ARM9_RAM)[0] != 0xE3500000 | count:
            raise ValueError(f"Battle panel accessor precondition failed: {lookup['name']}")
        code_off = place(free, LOOKUP_WORDS * 4, 4)
        table_off = place(free, count * 2, 2)
        table = [0] * count
        for r in catalog[lookup["name"]]:
            raw = encode_native(r["short"])
            start = place(free, len(raw), 2)
            relative = ARM9_RAM + start - SHORT_BASE
            if not 0 < relative < 0x10000:
                raise ValueError("Battle panel string is out of u16 range")
            writes.append((start, raw))
            table[r["index"]] = relative
        words = lookup_code(count, ARM9_RAM + table_off, accessor)
        writes.append((code_off, struct.pack(f"<{LOOKUP_WORDS}I", *words)))
        writes.append((table_off, struct.pack(f"<{count}H", *table)))
        for site in lookup["call_sites"]:
            stub, offset = site["stub"], site["offset"]
            if arm9[stub - ARM9_RAM:stub - ARM9_RAM + 12] != STUB_CODE + struct.pack("<I", accessor):
                raise ValueError(f"Battle panel stub precondition failed: {stub:#x}")
            site_ram = OVERLAY_RAM + offset
            if struct.unpack_from("<I", overlay, offset)[0] != _bl(site_ram, stub):
                raise ValueError(f"Battle panel call site precondition failed: {offset:#x}")
            calls.append((offset, _bl(site_ram, ARM9_RAM + code_off)))
        stats["lookups"][lookup["name"]] = {
            "short_names": len(catalog[lookup["name"]]), "lookup_ram": ARM9_RAM + code_off,
        }
    code_off = place(free, 12 * 4, 4)
    scratch_off = place(free, 8, 4)
    blink_ram = ARM9_RAM + code_off
    writes.append((code_off, struct.pack("<12I", *blink_code(blink_ram, ARM9_RAM + scratch_off))))
    writes.append((scratch_off, bytes(8)))  # reserve the wrapper's lr / start-x slot
    for offset in BLINK_SITES:
        site_ram = OVERLAY_RAM + offset
        if struct.unpack_from("<I", overlay, offset)[0] != _bl(site_ram, RENDERER):
            raise ValueError(f"Battle cursor blink precondition failed: {offset:#x}")
        calls.append((offset, _bl(site_ram, blink_ram)))
    stats["blink_ram"] = blink_ram
    stats["call_sites"] = len(calls)
    stats["static_bytes"] = sum(len(raw) for _, raw in writes)
    return writes, calls, stats


def apply_battle_panel(rom, nds):
    """Run after apply_combat_text: the target bytes must already be zeroed."""
    base = nds.arm9_rom_off
    ostart, oend = nds.fat[0]
    writes, calls, stats = prepare_battle_panel(
        nds.data[base:base + nds.arm9_size], nds.data[ostart:oend],
    )
    for start, raw in writes:
        if any(rom[base + start:base + start + len(raw)]):
            raise ValueError(f"Battle panel allocation overlaps another patch at {start:#x}")
    for offset, _ in calls:
        if rom[ostart + offset:ostart + offset + 4] != nds.data[ostart + offset:ostart + offset + 4]:
            raise ValueError(f"Battle panel call site was already patched: {offset:#x}")
    for start, raw in writes:
        rom[base + start:base + start + len(raw)] = raw
    for offset, word in calls:
        struct.pack_into("<I", rom, ostart + offset, word)
    return stats
