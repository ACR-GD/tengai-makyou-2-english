"""ARM9 bootstrap for translation/native.bin using the game's own file allocator.

Runs after each existing state clear: free the previous English resource, load
the resource, validate magic/count, and reinstall the original pointer tables.
Both actor-name scratch producers use five dedicated 64-byte slots in verified
old string storage. The original state structure and ARM9/BSS sizes do not grow.
"""
import hashlib
import json
from pathlib import Path
import struct

from native_catalog import extract_catalog
from native_pool import SOURCE_SHA256, ARM9_RAM, PAYLOAD_MAGIC
from vwf_arm9 import _hooks, WIDTH_TABLE_LEN
from ov008_build import COMBAT_RELOAD_ARENA

ROOT = Path(__file__).resolve().parents[1]
SCRATCH_PATCH_PATH = ROOT / "translation/native_scratch_patch.json"
BOOT_START = 0x11D54C
BOOT_END = 0x11D5FC
STATE_CLEAR_CALLS = (0x1ABF8, 0x4E054)
CLEAR_FUNCTION = 0x02089D74
LOAD_FUNCTION = 0x020198A0
FREE_FUNCTION = 0x02019930
RESOURCE_PATH = b"rom:/translation/native.bin\0"
FREE_ALL_FUNCTION = 0x02088C34
FREE_ALL_PROLOGUE = 0xE92D4070


def branch_word(offset, address, link=False, condition=0xE):
    displacement = address - (ARM9_RAM + offset + 8)
    if displacement % 4 or not -(1 << 25) <= displacement < (1 << 25):
        raise ValueError("ARM branch target is unaligned or out of range")
    return (condition << 28) | (0x0B000000 if link else 0x0A000000) | (
        (displacement >> 2) & 0xFFFFFF
    )


def bootstrap_blob(count):
    """Assemble a small ARM-state stub; no assembler dependency in release builds."""
    words = []
    labels = {}
    fixups = []

    def emit(word):
        words.append(word)

    def label(name):
        labels[name] = BOOT_START + len(words) * 4

    def relative(kind, name, register=0, condition=0xE):
        fixups.append((len(words), kind, name, register, condition))
        emit(0)

    emit(0xE92D41F0)  # push {r4-r8,lr}; 24-byte aligned frame
    emit(branch_word(BOOT_START + 4, CLEAR_FUNCTION, link=True))
    label("post_clear")
    emit(0xE1A08000)  # preserve original clear-call r0 for the surrounding function/caller
    relative("adr", "cache", register=4)
    emit(0xE5940000)  # r0 = previous resource allocation
    emit(0xE3500000)
    emit(branch_word(BOOT_START + len(words) * 4, FREE_FUNCTION, link=True, condition=1))
    emit(0xE3A05000)  # r5 = 0: original loader's open-failure path otherwise inherits r5
    relative("adr", "filename")
    emit(branch_word(BOOT_START + len(words) * 4, LOAD_FUNCTION, link=True))
    emit(0xE3500000)
    relative("branch", "failure", condition=0)
    emit(0xE5901000)
    relative("ldr", "magic", register=2)
    emit(0xE1510002)
    relative("branch", "failure", condition=1)
    emit(0xE5901004)
    emit(0xE3510001)
    relative("branch", "failure", condition=1)
    emit(0xE5840000)  # cache the loaded allocation for the next initialization
    emit(0xE1A04000)
    emit(0xE5945008)
    relative("ldr", "count", register=7)
    emit(0xE1550007)
    relative("branch", "failure", condition=1)
    emit(0xE2846020)  # r6 = first (table-cell address, string offset) record
    label("loop")
    emit(0xE8B60003)  # ldmia r6!,{r0,r1}
    emit(0xE0841001)  # r1 = loaded resource + string offset
    emit(0xE5801000)
    emit(0xE2555001)
    relative("branch", "loop", condition=1)
    emit(0xE1A00008)
    emit(0xE8BD81F0)  # pop {r4-r8,pc}
    label("failure")
    relative("branch", "failure")
    label("magic")
    emit(struct.unpack("<I", PAYLOAD_MAGIC)[0])
    label("count")
    emit(count)
    label("cache")
    emit(0)
    label("filename")
    tail = RESOURCE_PATH
    tail += b"\0" * (-len(tail) % 4)
    for index, kind, name, register, condition in fixups:
        offset = BOOT_START + index * 4
        target = labels[name]
        if kind == "branch":
            words[index] = branch_word(offset, ARM9_RAM + target, condition=condition)
        else:
            distance = target - (offset + 8)
            if distance < 0 or distance > (255 if kind == "adr" else 4095):
                raise ValueError("Bootstrap literal/address fixup is out of range")
            words[index] = (
                0xE28F0000 if kind == "adr" else 0xE59F0000
            ) | (register << 12) | distance
    blob = struct.pack("<" + "I" * len(words), *words) + tail
    if BOOT_START + len(blob) > BOOT_END:
        raise ValueError("Native bootstrap overlaps the end of verified ARM9 padding")
    return blob, {name: ARM9_RAM + offset for name, offset in labels.items()}


def cleanup_blob(cache_address, post_clear_address):
    """Wrap FreeAll centrally, preserving private-heap calls without reloading.

    In the verified game, current heap is heap 0. Both negative current-heap
    selectors and explicit heap ID 0 free the English allocation.
    Invalidate its cache before reloading: cache-zero alone leaves dangling
    table pointers, while normal reload without invalidation double-frees it.
    """
    start, end = COMBAT_RELOAD_ARENA
    trampoline = start + 52
    return_site = start + 48
    words = [
        0xE92D41F0,  # push {r4-r8,lr}; same return frame as the normal bootstrap
        0xE1A06000,
        0xE1A07001,
        branch_word(start + 12, ARM9_RAM + trampoline, link=True),
        0xE3560000,
        branch_word(start + 20, ARM9_RAM + return_site, condition=1),
        0xE3570000,
        branch_word(start + 28, ARM9_RAM + return_site, condition=0xC),  # bgt: positive private heap
        0xE59F4014,
        0xE3A01000,
        0xE5841000,
        branch_word(start + 44, post_clear_address),
        0xE8BD81F0,
        FREE_ALL_PROLOGUE,  # replay the displaced SDK prologue exactly once
        branch_word(start + 56, FREE_ALL_FUNCTION + 4),
        cache_address,
    ]
    blob = struct.pack("<16I", *words)
    if start + len(blob) > end:
        raise ValueError("Native heap cleanup hook exceeds reserved subtitle padding")
    return blob


def install_native_boot(rom, nds):
    start = nds.arm9_rom_off
    source = nds.data[start:start + nds.arm9_size]
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError("Native bootstrap requires the verified original ARM9")
    _, table_offset, _ = _hooks()
    if table_offset + WIDTH_TABLE_LEN != BOOT_START:
        raise ValueError("VWF code/width table layout changed; native hook placement must be reviewed")
    patches = json.loads(SCRATCH_PATCH_PATH.read_text(encoding="utf-8"))
    if patches["source_sha256"] != SOURCE_SHA256:
        raise ValueError("Scratch patch evidence targets a different ARM9")
    if (
        patches["scratch_file_range"] != [0xF44DC, 0xF461C]
        or patches["slot_count"] != 5 or patches["slot_bytes"] != 64
    ):
        raise ValueError("Native scratch layout changed")
    if any(source[BOOT_START:BOOT_END]) or any(rom[start + BOOT_START:start + BOOT_END]):
        raise ValueError("Native bootstrap padding is occupied")
    blob, labels = bootstrap_blob(len(extract_catalog(source)))
    cleanup_start, cleanup_end = COMBAT_RELOAD_ARENA
    if any(source[cleanup_start:cleanup_end]) or any(rom[start + cleanup_start:start + cleanup_end]):
        raise ValueError("Native heap cleanup hook reservation is occupied")
    cleanup = cleanup_blob(labels["cache"], labels["post_clear"])
    changes = []
    for entry in patches["patches"]:
        offset = entry["offset"]
        expected = struct.pack("<I", entry["expected_word"])
        if source[offset:offset + 4] != expected or bytes(rom[start + offset:start + offset + 4]) != expected:
            raise ValueError(f"Native scratch instruction precondition failed at {offset:#x}")
        changes.append((offset, struct.pack("<I", entry["new_word"])))
    for offset in STATE_CLEAR_CALLS:
        expected = struct.pack("<I", branch_word(offset, CLEAR_FUNCTION, link=True))
        if source[offset:offset + 4] != expected or bytes(rom[start + offset:start + offset + 4]) != expected:
            raise ValueError(f"Native loader call precondition failed at {offset:#x}")
        changes.append((offset, struct.pack("<I", branch_word(
            offset, ARM9_RAM + BOOT_START, link=True,
        ))))
    sdk_offset = FREE_ALL_FUNCTION - ARM9_RAM
    expected = struct.pack("<I", FREE_ALL_PROLOGUE)
    if source[sdk_offset:sdk_offset + 4] != expected or bytes(rom[start + sdk_offset:start + sdk_offset + 4]) != expected:
        raise ValueError("SDK heap cleanup prologue differs from the verified source")
    changes.append((sdk_offset, struct.pack("<I", branch_word(
        sdk_offset, ARM9_RAM + cleanup_start,
    ))))
    for offset, data in changes:
        rom[start + offset:start + offset + len(data)] = data
    rom[start + BOOT_START:start + BOOT_START + len(blob)] = blob
    rom[start + cleanup_start:start + cleanup_start + len(cleanup)] = cleanup
    return {
        "hook_bytes": len(blob), "hook_ram": ARM9_RAM + BOOT_START,
        "resource_path": RESOURCE_PATH[:-1].decode("ascii"),
        "state_clear_calls": [ARM9_RAM + off for off in STATE_CLEAR_CALLS],
        "scratch_slots": 5, "scratch_slot_bytes": 64,
        "scratch_ram": patches["scratch_ram_base"],
        "failure_policy": "halt on resource-open/allocation/read or header-validation failure",
        "lifecycle": "free previous resource with game allocator, reload on both state initializers",
        "cache_ram": labels["cache"],
        "heap_cleanup_hook": ARM9_RAM + cleanup_start,
        "heap_cleanup_hook_bytes": len(cleanup),
        "heap_lifetime_policy": "reload arena0 FreeAll for current/heap0 selectors; positive private heap IDs pass through",
        "runtime_verified": False,
    }
