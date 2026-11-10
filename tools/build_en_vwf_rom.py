#!/usr/bin/env python3
"""Build the English draft ROM with VWF, resized scripts and context-specific subtitles."""
import argparse
import hashlib
import json
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from nds_extract import NDS
from scs_build_en import build_all
from vwf_arm9 import apply_to_rom
from vwf_font import build_from_bytes, build_half_from_bytes
from ov008_build import patch_ov008
from bps_patch import create_patch
from native_strings import apply_native, DEFAULT_DATA as NATIVE_UI_DATA
from native_pool import build_native_payload, CATALOG_PATH, LAYOUT_PATH
from native_boot import install_native_boot, SCRATCH_PATCH_PATH
from nitrofs_resource import append_native_resource
from battle_graphics import build_battle_graphics, _source_reader
from menu_graphics import build_menu_graphics
from title_graphics import build_title_graphics
from saveload_graphics import build_saveload_graphics
from usd_graphics import build_usd_graphics
from combat_text import apply_combat_text, CATALOG as COMBAT_CATALOG
from battle_panel import apply_battle_panel, CATALOG as PANEL_CATALOG
from native_relocate import apply_relocation, CATALOG as RELOCATED_CATALOG
from ov008_build import BATTLE_NUMERIC_RENDERER
from subtitle_layout import apply_subtitle_layout

FONT_ROM_PATH = "string_work/grph/font12_GothicW3_bit.cobj"
HALF_FONT_ROM_PATH = "string_work/grph/HalfCharacter_bit.cobj"
OV008_FAT_ID = 8


def finalize_header(rom):
    """Declare expanded ROM capacity/used size and refresh the NDS header CRC16."""
    units = (len(rom) + 0x1FFFF) // 0x20000
    rom[0x14] = max(0, (units - 1).bit_length())
    struct.pack_into("<I", rom, 0x80, len(rom))
    crc = 0xFFFF
    for byte in rom[:0x15E]:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0xA001 if crc & 1 else 0)
    struct.pack_into("<H", rom, 0x15E, crc)


def append_scs(rom: bytearray, nds: NDS, files_map: dict) -> int:
    path_to_fid = {p: fid for p, fid in nds.parse_fnt()}
    fat_off = nds.fat_off
    n = 0
    for path, newbytes in files_map.items():
        fid = path_to_fid.get(path)
        if fid is None:
            raise ValueError(f"Rebuilt script is absent from ROM file table: {path}")
        start, end = nds.fat[fid]
        if bytes(rom[start:end]) == newbytes:
            continue
        while len(rom) % 4:
            rom.append(0)
        off = len(rom)
        rom += newbytes
        struct.pack_into("<I", rom, fat_off + fid * 8, off)
        struct.pack_into("<I", rom, fat_off + fid * 8 + 4, off + len(newbytes))
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rom")
    ap.add_argument("out_rom")
    ap.add_argument("--json", default="translation/tengai2_script.translated.json")
    ap.add_argument("--script-root", default="extracted/data/script")
    ap.add_argument("--bps", type=Path, help="also create a distributable BPS patch")
    ap.add_argument(
        "--wrap",
        type=int,
        default=196,
        help="soft wrap max line width in pixels for rebuilt dialogue messages (0=off; 196 fits the 208px DS dialogue box + 12px cursor)",
    )
    args = ap.parse_args()
    if Path(args.rom).resolve() == Path(args.out_rom).resolve():
        ap.error("Output must not overwrite the source ROM")
    if Path(args.out_rom).exists():
        ap.error("Output already exists; choose a new build filename")
    metadata_path = Path(args.out_rom).with_suffix(".build.json")
    if metadata_path.exists() or (args.bps and args.bps.exists()):
        ap.error("Build metadata/patch output already exists; choose new filenames")
    if args.bps and args.bps.resolve() in (
        Path(args.rom).resolve(), Path(args.out_rom).resolve(), metadata_path.resolve()
    ):
        ap.error("Patch, metadata and ROM paths must be different")

    nds = NDS(args.rom)
    if nds.gamecode != "ATMJ" or nds.arm9_ram != 0x02000000:
        ap.error("This patch targets the Japanese ATMJ ROM only")
    rom = bytearray(nds.data)
    native_count = apply_native(
        rom, nds, Path(args.script_root).resolve().parents[1],
    )
    print(f"patched {native_count} mapped native UI strings in place")
    native_payload, native_pool_stats = build_native_payload(
        nds.data[nds.arm9_rom_off:nds.arm9_rom_off + nds.arm9_size],
    )
    print(
        f"native catalog: {native_pool_stats['records']} runtime pointers, "
        f"{native_pool_stats['resource_bytes']} resource bytes, "
        f"{native_pool_stats['empty_sentinels']} preserved empty slots"
    )

    files_map, stats = build_all(args.json, args.script_root, args.wrap, vwf=True)
    battle_files, battle_graphics_stats = build_battle_graphics(nds.data)
    files_map.update(battle_files)
    read_source = _source_reader(nds.data)
    menu_files, menu_graphics_stats = build_menu_graphics(read_source)
    files_map.update(menu_files)
    title_files, title_graphics_stats = build_title_graphics(read_source)
    files_map.update(title_files)
    saveload_files, saveload_graphics_stats = build_saveload_graphics(read_source)
    files_map.update(saveload_files)
    usd_files, usd_graphics_stats = build_usd_graphics(read_source)
    files_map.update(usd_files)
    source_fids = dict(nds.parse_fnt())
    for path in files_map:
        fid = source_fids.get(path)
        source_path = (
            Path(args.script_root) / path.removeprefix("script/")
            if path.startswith("script/") else Path(args.script_root).parent / path
        )
        if fid is None or nds.file_bytes(fid) != source_path.read_bytes():
            raise ValueError(f"Extracted script does not match source ROM: {path}")
    print(
        f"scs rebuild: {stats['files']} files, "
        f"resized msgs ~{stats['resized']}, locked ~{stats['locked']}, "
        f"grew {stats['grew']} files"
    )
    appended = append_scs(rom, nds, files_map)
    print(f"appended {appended} changed script/graphics files to ROM tail")

    o8s, o8e = nds.fat[OV008_FAT_ID]
    ov_n = patch_ov008(rom, o8s, o8e, nds.arm9_rom_off, nds.arm9_size)
    print(f"patched {ov_n} ov_008 cutscene subtitles across 3 arenas")
    layout_stats = apply_subtitle_layout(rom, nds)
    print(f"moved {sum(layout_stats.values())} cutscene subtitle positions")

    # narrow Latin font (left-aligned glyphs) + per-glyph width table
    path_to_fid = {p: fid for p, fid in nds.parse_fnt()}
    font_fid = path_to_fid.get(FONT_ROM_PATH)
    half_fid = path_to_fid.get(HALF_FONT_ROM_PATH)
    width_table = None
    if font_fid is not None:
        fs, fe = nds.fat[font_fid]
        new_font, width_table = build_from_bytes(bytes(rom[fs:fe]))
        rom[fs:fe] = new_font
        print(f"patched VWF font12 @0x{fs:X}..0x{fe:X} ({len(width_table)} glyph widths)")
        if half_fid is not None:
            hs, he = nds.fat[half_fid]
            rom[hs:he] = build_half_from_bytes(bytes(rom[hs:he]), new_font)
            print(f"patched VWF HalfCharacter @0x{hs:X}..0x{he:X}")
    else:
        raise ValueError("Required font12 resource is missing from ROM")
    if half_fid is None:
        raise ValueError("Required HalfCharacter resource is missing from ROM")

    vwf_log = apply_to_rom(rom, nds.arm9_rom_off, nds.arm9_size, width_table)
    print("ARM9 VWF:")
    for line in vwf_log:
        print(f"  {line}")
    native_pool_stats["loader"] = install_native_boot(rom, nds)
    combat_stats = apply_combat_text(rom, nds)
    panel_stats = apply_battle_panel(rom, nds)
    print(f"battle panel: {panel_stats['static_bytes']} bytes, {panel_stats['call_sites']} call sites")
    relocated_stats = apply_relocation(rom, nds)
    print(f"relocated {relocated_stats['strings']} native UI strings ({relocated_stats['static_bytes']} bytes)")
    renderer_start, renderer_end = BATTLE_NUMERIC_RENDERER
    if rom[nds.arm9_rom_off + renderer_start:nds.arm9_rom_off + renderer_end] != nds.data[
        nds.arm9_rom_off + renderer_start:nds.arm9_rom_off + renderer_end
    ]:
        raise ValueError("Live battle numeric renderer was modified; preserve the user's crash fix")
    native_pool_stats["resource"] = append_native_resource(rom, nds, native_payload)
    native_pool_stats["resource_sha256"] = hashlib.sha256(native_payload).hexdigest()
    print(
        f"installed native loader ({native_pool_stats['loader']['hook_bytes']} bytes), "
        f"resource file ID {native_pool_stats['resource']['file_id']}"
    )

    while len(rom) % 4:
        rom.append(0)
    finalize_header(rom)
    metadata = {
        "status": "english_draft_not_complete_localization",
        "source_sha256": hashlib.sha256(nds.data).hexdigest(),
        "target_sha256": hashlib.sha256(rom).hexdigest(),
        "translation_sha256": hashlib.sha256(Path(args.json).read_bytes()).hexdigest(),
        "native_ui_sha256": hashlib.sha256(NATIVE_UI_DATA.read_bytes()).hexdigest(),
        "native_catalog_sha256": hashlib.sha256(CATALOG_PATH.read_bytes()).hexdigest(),
        "native_pool_layout_sha256": hashlib.sha256(LAYOUT_PATH.read_bytes()).hexdigest(),
        "native_scratch_patch_sha256": hashlib.sha256(SCRATCH_PATCH_PATH.read_bytes()).hexdigest(),
        "native_pool": native_pool_stats,
        "combat_text": combat_stats,
        "battle_graphics": battle_graphics_stats,
        "menu_graphics": menu_graphics_stats,
        "title_graphics": title_graphics_stats,
        "saveload_graphics": saveload_graphics_stats,
        "usd_graphics": usd_graphics_stats,
        "combat_text_sha256": hashlib.sha256(COMBAT_CATALOG.read_bytes()).hexdigest(),
        "battle_panel": panel_stats,
        "battle_panel_sha256": hashlib.sha256(PANEL_CATALOG.read_bytes()).hexdigest(),
        "native_ui_relocated": relocated_stats,
        "native_ui_relocated_sha256": hashlib.sha256(RELOCATED_CATALOG.read_bytes()).hexdigest(),
        "subtitles_sha256": hashlib.sha256(
            (Path(__file__).resolve().parents[1] / "translation/ov008_subtitles.json").read_bytes()
        ).hexdigest(),
        "script_stats": stats, "subtitle_pointers": ov_n, "subtitle_moves": layout_stats,
        "wrap_pixels": args.wrap,
        "native_ui_strings": native_count, "runtime_verified": False,
    }
    # Exclusive creation prevents accidental replacement of a prior build.
    with open(args.out_rom, "xb") as f:
        f.write(rom)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    if args.bps:
        with args.bps.open("xb") as f:
            f.write(create_patch(nds.data, rom, b"Tengai Makyou II English draft"))
        print(f"BPS patch: {args.bps}")
    print(f"ROM {len(nds.data)} -> {len(rom)} bytes -> {args.out_rom}")


if __name__ == "__main__":
    main()
