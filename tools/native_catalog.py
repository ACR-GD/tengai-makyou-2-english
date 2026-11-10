#!/usr/bin/env python3
"""Export ARM9 pointer-backed text tables while preserving edited English.

Table bases/counts were identified from the original ATMJ ARM accessors.
Reading names are included because some may be displayed as well as sorted.
tools/native_pool.py inserts the catalog in the main ROM build.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
ARM9_RAM = 0x02000000
TABLES = (
    ("arts_display", 0xF7B2C, 33),
    ("arts_reading", 0xF7BB0, 33),
    ("arts_description", 0xF7C34, 33),
    ("spells_display", 0xF7CB8, 69),
    ("spells_reading", 0xF7DCC, 69),
    ("spells_description", 0xF7EE0, 69),
    ("items_reading", 0xF7FF4, 125),
    ("items_description", 0xF81E8, 125),
    ("items_display", 0xF83DC, 125),
    ("equipment_display", 0xF85D0, 237),
    ("equipment_reading", 0xF8984, 237),
    ("enemies_reading", 0xFC5B4, 369),
    ("enemies_display", 0xFCB78, 369),
    # Province + location names for the field menu header bar.
    ("places_display", 0xD3960, 195),
)
# Province map labels: per-province lists of (name pointer, u32 below-icon
# flag), ending at a null pointer (at most 16, see 0x02009F40).
LABEL_LISTS = ("map_labels", 0xCEB14, 17)
# Strings whose Japanese storage is not reclaimed: they are also reached
# through other tables (e.g. the 白川村 copy at 0xCC400) that stay as is.
UNRECLAIMED_CATEGORIES = {"places_display", "map_labels"}


def _record(data, key, name, pointer_offset, address):
    offset = address - ARM9_RAM
    if not 0 <= offset < len(data) - 1 or offset % 2:
        raise ValueError(f"Invalid {key} pointer: {address:#x}")
    end = offset
    while end + 1 < len(data) and data[end:end + 2] != b"\0\0":
        end += 2
    if end + 1 >= len(data):
        raise ValueError(f"Unterminated {key} string")
    return {
        "id": f"arm9/{key}", "category": name,
        "source": "__system__/arm9.bin", "pointer_offset": pointer_offset,
        "offset": offset, "original_bytes_with_nul": end - offset + 2,
        "jp": data[offset:end].decode("shift_jis"), "en": "", "review_status": "untranslated",
        "insertion_status": "not_inserted_requires_pool_strategy",
    }


def extract_catalog(data):
    result = []
    for name, table, count in TABLES:
        for index in range(count):
            pointer_offset = table + 4 * index
            if pointer_offset + 4 > len(data):
                raise ValueError(f"Missing ARM9 table: {name}")
            address = struct.unpack_from("<I", data, pointer_offset)[0]
            result.append(_record(data, f"{name}/{index:03d}", name, pointer_offset, address))
    name, table, provinces = LABEL_LISTS
    for province in range(provinces):
        base = struct.unpack_from("<I", data, table + 4 * province)[0] - ARM9_RAM
        if not 0 <= base < len(data):
            raise ValueError(f"Invalid {name} list {province}")
        for index in range(16):
            pointer_offset = base + 8 * index
            address = struct.unpack_from("<I", data, pointer_offset)[0]
            if address == 0:
                break
            result.append(_record(data, f"{name}/{province:02d}_{index:02d}", name, pointer_offset, address))
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arm9", type=Path, default=ROOT / "extracted/__system__/arm9.bin")
    ap.add_argument("--out", type=Path, default=ROOT / "translation/native_catalog.json")
    args = ap.parse_args()
    data = args.arm9.read_bytes()
    rows = extract_catalog(data)
    if args.out.exists():
        old = json.loads(args.out.read_text(encoding="utf-8"))
        if old["source_sha256"] != hashlib.sha256(data).hexdigest():
            ap.error("Source binary changed; do not reuse translations without re-analysis")
        previous = {r["id"]: r for r in old["records"]}
        if len(previous) != len(old["records"]) or set(previous) != {r["id"] for r in rows}:
            ap.error("Catalog IDs are missing, duplicated, or changed; preserve the edited source")
        for r in rows:
            existing = previous.get(r["id"])
            if existing:
                if any(existing[k] != r[k] for k in ("jp", "offset", "pointer_offset")):
                    ap.error(f"Catalog source changed: {r['id']}")
                for key in ("en", "review_status", "insertion_status", "notes", "reading_source"):
                    if key in existing:
                        r[key] = existing[key]
    output = {
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "evidence": "Static ARM9 indexed-pointer accessors; not runtime-verified",
        "limitations": (
            "Not the complete UI corpus. Native pool insertion preserves array IDs/order "
            "and uses fullwidth English readings; runtime sorting/layout and bilingual review remain required."
        ),
        "records": rows,
    }
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Exported {len(rows)} indexed name/description entries to {args.out}")


if __name__ == "__main__":
    main()
