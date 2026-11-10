#!/usr/bin/env python3
"""Append translation/native.bin while preserving existing NitroFS identifiers.

Integration:
    info = append_native_resource(modified_rom_bytearray, original_nds, payload)

original_nds is the tools/nds_extract.py NDS instance for the original ROM,
or any object with an original-ROM ``data`` bytes attribute.
The CURRENT ROM header and FAT supply all existing file allocations.
The original FNT supplies the existing names and directory IDs; the current
FNT must still equal it. No input is mutated unless all validation succeeds.

This deliberately does not update device capacity, used-ROM-size fields,
header CRC, secure-area checksums, or outer ROM padding. The integrating
builder must perform its usual final size/checksum work after this call.
"""

import struct


def _u16(data, offset):
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def _range(data, offset, size, label):
    if offset < 0 or size < 0 or offset > len(data) or size > len(data) - offset:
        raise ValueError(f"{label} outside ROM bounds")
    return bytes(data[offset:offset + size])


def _tables(data):
    if len(data) < 0x200:
        raise ValueError("ROM header is shorter than 0x200 bytes")
    fnt_offset, fnt_size, fat_offset, fat_size = struct.unpack_from(
        "<4I", data, 0x40
    )
    if fnt_offset < 0x200 or fat_offset < 0x200:
        raise ValueError("FNT/FAT overlaps the ROM header")
    if fnt_size < 9 or fat_size % 8:
        raise ValueError("Invalid FNT size or unaligned FAT size")
    if fnt_offset < fat_offset + fat_size and fat_offset < fnt_offset + fnt_size:
        raise ValueError("FNT and FAT overlap")
    fnt = _range(data, fnt_offset, fnt_size, "FNT")
    fat = _range(data, fat_offset, fat_size, "FAT")
    count = fat_size // 8
    if count > 0x10000:
        raise ValueError("FAT file IDs exceed 16 bits")
    for fid in range(count):
        start, end = struct.unpack_from("<II", fat, fid * 8)
        if start > end or end > len(data):
            raise ValueError(f"FAT entry {fid} outside ROM bounds")
    return fnt, fat, (fnt_offset, fnt_size, fat_offset, fat_size)


def _parse_fnt(fnt, file_count):
    """Validate directories and return entries, terminators, and raw children."""
    if len(fnt) < 9:
        raise ValueError("FNT too short")
    count = _u16(fnt, 6)
    if not 1 <= count <= 0x1000 or count * 8 >= len(fnt):
        raise ValueError("Invalid directory count/main table")
    entries = []
    endings = []
    children = []
    ranges = []
    file_ids = set()
    for index in range(count):
        offset, first_file, parent = struct.unpack_from("<IHH", fnt, index * 8)
        if not count * 8 <= offset < len(fnt):
            raise ValueError("Subtable offset outside FNT data")
        if index and not 0xF000 <= parent < 0xF000 + count:
            raise ValueError("Invalid directory parent ID")
        if first_file > file_count:
            raise ValueError("Directory first file ID outside FAT")
        pos, fid = offset, first_file
        names = set()
        items = []
        while True:
            if pos >= len(fnt):
                raise ValueError("Unterminated FNT subtable")
            tag = fnt[pos]
            pos += 1
            if tag == 0:
                endings.append(pos - 1)
                break
            size = tag & 0x7F
            if not size or pos + size > len(fnt):
                raise ValueError("Invalid/truncated FNT name")
            name = bytes(fnt[pos:pos + size])
            pos += size
            if b"\0" in name or b"/" in name or name in names:
                raise ValueError("Invalid or duplicate child name")
            names.add(name)
            if tag & 0x80:
                if pos + 2 > len(fnt):
                    raise ValueError("Truncated child directory ID")
                child_id = _u16(fnt, pos)
                pos += 2
                if not 0xF001 <= child_id < 0xF000 + count:
                    raise ValueError("Invalid child directory ID")
                items.append((name, child_id))
            else:
                if fid >= file_count or fid in file_ids:
                    raise ValueError("Invalid or duplicate file ID")
                file_ids.add(fid)
                fid += 1
                items.append((name, None))
        entries.append((offset, first_file, parent))
        children.append(items)
        ranges.append((offset, pos))
    ordered_ranges = sorted(ranges)
    for previous, following in zip(ordered_ranges, ordered_ranges[1:]):
        if previous[1] > following[0]:
            raise ValueError("Overlapping FNT subtables")

    references = {}
    for index, items in enumerate(children):
        for _, child_id in items:
            if child_id is not None:
                if child_id in references:
                    raise ValueError("Directory has multiple references")
                references[child_id] = 0xF000 + index
    for index in range(1, count):
        directory_id = 0xF000 + index
        if references.get(directory_id) != entries[index][2]:
            raise ValueError("Missing directory reference or mismatched parent")
    visited = {0xF000}
    pending = [0xF000]
    while pending:
        directory_id = pending.pop()
        for _, child_id in children[directory_id - 0xF000]:
            if child_id is not None:
                if child_id in visited:
                    raise ValueError("Directory cycle")
                visited.add(child_id)
                pending.append(child_id)
    if len(visited) != count:
        raise ValueError("Unreachable directory/cycle")
    return entries, endings, children


def _align4(value):
    return (value + 3) & ~3


def append_native_resource(rom, source_nds, payload):
    """Transactionally append one resource; return file/directory ID and offsets.

    Existing source directory/file names, directory IDs/parents, file IDs,
    overlay tables, and CURRENT FAT entries are preserved byte-for-byte.
    Existing root ``translation`` entries (directory or file) are rejected.
    File IDs through 65535 and directory IDs through 0xFFFF are supported;
    appending beyond either space is rejected.
    """
    if type(rom) is not bytearray:
        raise TypeError("rom must be a bytearray")
    if not isinstance(payload, (bytes, bytearray, memoryview)):
        raise TypeError("payload must be bytes-like")
    original = source_nds.data
    if not isinstance(original, (bytes, bytearray, memoryview)):
        raise TypeError("source_nds.data must be bytes-like")
    payload = bytes(payload)
    original_fnt, original_fat, _ = _tables(original)
    current_fnt, current_fat, _ = _tables(rom)
    if current_fnt != original_fnt:
        raise ValueError("Current FNT differs from original; resource may exist")
    if len(current_fat) != len(original_fat):
        raise ValueError("Current FAT file count differs from original")
    old_count = len(current_fat) // 8
    if old_count >= 0x10000:
        raise ValueError("No free 16-bit file ID")
    entries, terminators, children = _parse_fnt(original_fnt, old_count)
    directory_count = len(entries)
    if directory_count >= 0x1000:
        raise ValueError("No free NitroFS directory ID")
    if any(name == b"translation" for name, _ in children[0]):
        raise ValueError("Root translation directory/file already exists")

    new_directory_id = 0xF000 + directory_count
    root_terminator = terminators[0]
    root_entry = (
        bytes([0x80 | len(b"translation")])
        + b"translation"
        + struct.pack("<H", new_directory_id)
    )
    main_size = directory_count * 8
    new_fnt = bytearray(original_fnt[:main_size])
    new_fnt.extend(b"\0" * 8)
    new_fnt.extend(original_fnt[main_size:root_terminator])
    new_fnt.extend(root_entry)
    new_fnt.extend(original_fnt[root_terminator:])
    for index, (offset, first_file, parent) in enumerate(entries):
        adjusted_offset = offset + 8
        if offset > root_terminator:
            adjusted_offset += len(root_entry)
        struct.pack_into(
            "<IHH", new_fnt, index * 8,
            adjusted_offset, first_file,
            directory_count + 1 if index == 0 else parent,
        )
    new_subtable_offset = len(new_fnt)
    new_fnt.extend(bytes([len(b"native.bin")]) + b"native.bin\0")
    struct.pack_into(
        "<IHH", new_fnt, main_size,
        new_subtable_offset, old_count, 0xF000,
    )
    _parse_fnt(new_fnt, old_count + 1)

    payload_offset = _align4(len(rom))
    payload_end = payload_offset + len(payload)
    fat_offset = _align4(payload_end)
    if max(payload_offset, payload_end, fat_offset) > 0xFFFFFFFF:
        raise ValueError("Appended payload offsets exceed 32 bits")
    new_fat = current_fat + struct.pack("<II", payload_offset, payload_end)
    fnt_offset = _align4(fat_offset + len(new_fat))
    final_size = fnt_offset + len(new_fnt)
    if max(payload_end, fat_offset, fnt_offset, final_size) > 0xFFFFFFFF:
        raise ValueError("Appended ROM offsets exceed 32 bits")
    staged = bytearray(rom)
    staged.extend(b"\0" * (payload_offset - len(staged)))
    staged.extend(payload)
    staged.extend(b"\0" * (fat_offset - len(staged)))
    staged.extend(new_fat)
    staged.extend(b"\0" * (fnt_offset - len(staged)))
    staged.extend(new_fnt)
    struct.pack_into(
        "<4I", staged, 0x40,
        fnt_offset, len(new_fnt), fat_offset, len(new_fat),
    )
    rom[:] = staged
    return {
        "path": "translation/native.bin",
        "file_id": old_count,
        "directory_id": new_directory_id,
        "payload_offset": payload_offset,
        "payload_size": len(payload),
        "fat_offset": fat_offset,
        "fat_size": len(new_fat),
        "fnt_offset": fnt_offset,
        "fnt_size": len(new_fnt),
    }
