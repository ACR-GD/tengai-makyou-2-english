#!/usr/bin/env python3
"""Import complete native translation batches into the authoritative catalog.

Batches contain {id,jp,en,notes?} for display/description rows only. Reading
entries derive from the English display name at the same original index.
"""
import argparse
import copy
import json
from pathlib import Path

from native_pool import CATALOG_PATH


def import_translations(catalog, batches):
    result = copy.deepcopy(catalog)
    records = result["records"]
    expected = {r["id"]: r for r in records if not r["category"].endswith("_reading")}
    edits = {}
    for batch in batches:
        for edit in batch:
            rid = edit["id"]
            if rid not in expected or rid in edits:
                raise ValueError(f"Unknown or duplicate native translation ID: {rid}")
            source = expected[rid]
            if edit["jp"] != source["jp"] or not isinstance(edit.get("en"), str):
                raise ValueError(f"Native translation source/type mismatch: {rid}")
            if bool(edit["en"].strip()) != bool(source["jp"]):
                raise ValueError(f"Native translation changed an empty sentinel: {rid}")
            edits[rid] = edit
    if set(edits) != set(expected):
        missing = sorted(set(expected) - set(edits))
        raise ValueError(f"Native translation batch is incomplete: {missing[:8]}")
    translations = {}
    for r in records:
        if r["id"] not in edits:
            continue
        edit = edits[r["id"]]
        key = (r["category"], r["jp"])
        if key in translations and translations[key] != edit["en"]:
            raise ValueError(f"Duplicate Japanese has inconsistent native English: {r['id']}")
        translations[key] = edit["en"]
        r["en"] = edit["en"]
        r["review_status"] = "draft_native_translation" if r["jp"] else "original_empty_sentinel"
        r["insertion_status"] = "native_pool"
        if edit.get("notes"):
            r["notes"] = edit["notes"]
    by_id = {r["id"]: r for r in records}
    for r in records:
        if r["category"].endswith("_reading"):
            display_id = r["id"].replace("_reading/", "_display/")
            r["en"] = by_id[display_id]["en"]
            r["reading_source"] = display_id
            r["review_status"] = "derived_english_reading" if r["jp"] else "original_empty_sentinel"
            r["insertion_status"] = "native_pool"
            r["notes"] = (
                "Fullwidth English display name at the same source index; original kana "
                "preserved in jp. Runtime sorting behavior requires verification."
            )
    result["limitations"] = (
        "Complete catalog coverage is not a full-game localization or bilingual/runtime approval. "
        "Short enemy UI names obey verified 32-byte copy buffers; source aliases and indices are preserved."
    )
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("batches", nargs="+", type=Path)
    ap.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    args = ap.parse_args()
    source = json.loads(args.catalog.read_text(encoding="utf-8"))
    batches = [json.loads(path.read_text(encoding="utf-8")) for path in args.batches]
    result = import_translations(source, batches)
    args.catalog.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Imported {sum(len(b) for b in batches)} translations; {len(result['records'])} total native entries")


if __name__ == "__main__":
    main()
