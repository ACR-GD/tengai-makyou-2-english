#!/usr/bin/env python3
"""Audit the English build and write a coverage manifest, without changing game data.

Non-script string hits and layout warnings are candidates, not proof of visible
Japanese or runtime clipping. Graphical text needs visual inspection.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from ov008_build import allocate_subtitles, load_subtitles
from reinsert_en import tokenize_op2
from scs_build_en import build_all, format_en_vwf, parse, true_submessage_starts
from scs_codec import decode_spans, enc_char, FW_SPACE
from vwf_font import measure_line_px
from native_strings import load_native, encode_native
from native_pool import build_native_payload, resolve_payload

ROOT = Path(__file__).resolve().parents[1]
TAG = re.compile(r"\{[0-9A-Fa-f]{4}\}|<[0-9A-Fa-f]{2}>")
SJIS_RUN = re.compile(rb"(?:(?:[\x81-\x9f\xe0-\xef])[\x40-\x7e\x80-\xfc]){4,}")
TEXT_CANDIDATE_EXTENSIONS = {".bin", ".tbl", ".usd", ".nam", ".lst"}
GRAPHICS_EXTENSIONS = {".cobj", ".lcobj", ".cscr", ".chr", ".scr", ".bgd", ".fnt"}
BUILD_FONTS = {
    "data/string_work/grph/font12_GothicW3_bit.cobj",
    "data/string_work/grph/HalfCharacter_bit.cobj",
}


def has_japanese(text):
    return any(
        "\u3040" <= c <= "\u30ff" or "\u4e00" <= c <= "\u9fff"
        or "\uff66" <= c <= "\uff9f" for c in text
    )


def string_candidates(data):
    """Conservative byte-pattern scan; still permits binary false positives."""
    found = []
    for match in SJIS_RUN.finditer(data):
        try:
            text = match.group().decode("shift_jis")
        except UnicodeDecodeError:
            continue
        # Kana are less likely than kanji-only sequences to be random machine code.
        if not re.search(r"[\u3040-\u30ff]", text):
            continue
        found.append({"offset": match.start(), "jp_candidate": text})
    return found


def controls(raw):
    return Counter(
        t[1] for t in tokenize_op2(raw)
        if t[0] == "op1" and t[1] in ("{0000}", "{0001}", "{001A}", "{001B}", "{001E}")
    )


def layout_warnings(record):
    formatted = format_en_vwf(record["en_tagged"])
    warnings = []
    # Keep parameters attached before measuring lines/pages: {000C} can be data.
    tokens = tokenize_op2(formatted)
    page = []
    pages = []
    for t in tokens:
        if t[0] == "op1" and t[1] in ("{0000}", "{000C}"):
            pages.append(page)
            page = []
        else:
            page.append(t)
    pages.append(page)
    for idx, page in enumerate(pages):
        if not page:
            continue
        ops = {t[1] for t in page if t[0] == "op1"}
        limit = 196 if "{0012}" in ops else 212
        if "{0001}" in ops:
            limit = 208
        elif "{0012}" not in ops and ops.intersection(("{0004}", "{0005}", "{0006}")):
            limit = 76
        text = "".join(t[1] + t[2] if t[0] == "op2" else t[1] for t in page)
        lines = text.split("\n")
        for line_idx, line in enumerate(lines):
            width = measure_line_px(line)
            if width > limit:
                warnings.append({
                    "id": record["id"], "page": idx, "line": line_idx,
                    "kind": "possible_width_overflow", "width_px": width,
                    "assumed_limit_px": limit, "text": line,
                })
        # Choice menus open their own window, sized for one item per line.
        if len(lines) > 3 and "{0001}" not in ops and TAG.sub("", text).strip():
            warnings.append({
                "id": record["id"], "page": idx, "kind": "possible_line_overflow",
                "lines": len(lines), "text": text,
            })
    return warnings


def audit(root=ROOT):
    root = Path(root)
    records_path = root / "translation/tengai2_script.translated.json"
    records = json.loads(records_path.read_text(encoding="utf-8"))
    files, stats = build_all(
        str(records_path), str(root / "extracted/data/script"), 196, vwf=True,
    )
    errors = []
    warnings = []
    for r in records:
        if controls(r["jp"]) != controls(r["en_tagged"]):
            errors.append({"id": r["id"], "kind": "choice_variable_or_entry_count_changed"})
        if has_japanese(r["en_tagged"]):
            errors.append({"id": r["id"], "kind": "japanese_in_translation"})
        plain = TAG.sub("", r["en_tagged"]).replace("\n", "")
        unsupported = sorted({
            ch for ch in plain
            if ch not in (" ", "\u3000", "\u00a0", "\uff20")
            and enc_char(ch, translit=True) == FW_SPACE
        })
        if unsupported:
            errors.append({"id": r["id"], "kind": "silent_space_substitution", "chars": unsupported})
        warnings.extend(layout_warnings(r))

    resources = []
    native_rows = load_native(root / "translation/native_ui.json")
    native_by_file = {}
    for row in native_rows:
        native_by_file.setdefault(row["source"], []).append(row)
    for p in sorted((root / "extracted").rglob("*")):
        if not p.is_file() or p.name == ".DS_Store":
            continue
        rel = p.relative_to(root / "extracted").as_posix()
        raw = p.read_bytes()
        native_entries = native_by_file.get(rel, [])
        native_patched = bytearray(raw)
        for r in native_entries:
            expected = r["jp"].encode("shift_jis") + b"\0\0"
            start = r["offset"]
            if raw[start:start + len(expected)] != expected:
                errors.append({"id": r["id"], "kind": "native_source_changed"})
            encoded = encode_native(r["en"])
            native_patched[start:start + len(expected)] = encoded + b"\0" * (len(expected) - len(encoded))
        entry = {
            "source": "extracted/" + rel, "bytes": len(raw),
            "source_sha256": hashlib.sha256(raw).hexdigest(),
        }
        scs_rel = rel.removeprefix("data/")
        if p.suffix == ".scs":
            original_region = parse(raw)[3]
            if scs_rel in files:
                rebuilt = files[scs_rel]
                _, _, offsets, region = parse(rebuilt)
                starts = true_submessage_starts(region)
                if len(starts) != len(true_submessage_starts(original_region)):
                    errors.append({"source": rel, "kind": "entry_count_changed"})
                if not set(offsets).issubset(starts):
                    errors.append({"source": rel, "kind": "invalid_pointer"})
                if any(has_japanese(m["raw"]) for m in decode_spans(region)):
                    errors.append({"source": rel, "kind": "japanese_in_rebuilt_script"})
                entry.update(
                    status="inserted_draft", insertion="scs_word_pointer_rebuild",
                    build_bytes=len(rebuilt),
                )
            else:
                japanese = any(has_japanese(m["raw"]) for m in decode_spans(original_region))
                entry["status"] = "untranslated_script" if japanese else "no_japanese_by_scs_decoder"
                if japanese:
                    errors.append({"source": rel, "kind": "unindexed_japanese"})
        elif rel in BUILD_FONTS:
            entry["status"] = "existing_font_patch"
        elif p.suffix in TEXT_CANDIDATE_EXTENSIONS:
            entry["status"] = "needs_format_and_runtime_review"
            candidates = string_candidates(native_patched)
            if candidates:
                entry["candidate_strings"] = candidates
        elif p.suffix in GRAPHICS_EXTENSIONS:
            entry["status"] = "needs_visual_text_review"
        elif p.suffix == ".scb":
            entry["status"] = "bytecode_not_text_audited"
        else:
            entry["status"] = "not_classified"
        if rel == "overlays/ov_008.bin":
            entry["known_patch"] = "189 subtitle occurrences; other content not audited"
        if rel == "__system__/arm9.bin":
            entry["known_patch"] = (
                "1,893 native catalog pointers are replaced at both state initializers "
                "by the English translation/native.bin resource. Original Japanese ROM "
                "string bytes remain for source verification; they are not the active English text."
            )
        if native_entries:
            entry["mapped_native_ui_strings"] = len(native_entries)
            entry["insertion"] = "exact_source_checked_in_place"
        resources.append(entry)
    subtitles = load_subtitles(root / "translation/ov008_subtitles.json")
    allocate_subtitles(subtitles)
    status_counts = Counter(r.get("review_status", "machine_draft_unreviewed") for r in records)
    catalog_path = root / "translation/native_catalog.json"
    native_catalog = json.loads(catalog_path.read_text(encoding="utf-8"))["records"]
    arm9 = (root / "extracted/__system__/arm9.bin").read_bytes()
    payload, native_stats = build_native_payload(
        arm9, json.loads(catalog_path.read_text(encoding="utf-8")),
        json.loads((root / "translation/native_pool_layout.json").read_text(encoding="utf-8")),
    )
    resolved = resolve_payload(arm9, payload)
    for r in native_catalog:
        if resolved[r["id"]] != encode_native(r["en"]):
            errors.append({"id": r["id"], "kind": "native_payload_roundtrip_failed"})
    return {
        "schema_version": 1,
        "complete_localization": False,
        "limitations": [
            "No emulator/hardware verification is implied by this audit.",
            "Non-script string scans are heuristic and do not cover compressed or graphical text.",
            "Layout uses estimated variable widths and assumed box limits; warnings need scene review.",
            "English drafts require contextual bilingual review; nonempty English is not completion.",
        ],
        "summary": {
            "script_records": len(records), "script_build": stats,
            "editorial_status": dict(status_counts),
            "subtitle_occurrences": len(subtitles),
            "subtitle_status": dict(Counter(r["review_status"] for r in subtitles)),
            "native_ui_strings": len(native_rows),
            "native_catalog_entries": len(native_catalog),
            "native_catalog_status": dict(Counter(r["insertion_status"] for r in native_catalog)),
            "native_pool_build": native_stats,
            "resource_status": dict(Counter(r["status"] for r in resources)),
            "candidate_text_files": sum("candidate_strings" in r for r in resources),
            "errors": len(errors), "layout_warnings": len(warnings),
        },
        "errors": errors,
        "layout_warnings": warnings,
        "resources": resources,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--out", type=Path, default=ROOT / "translation/coverage.json")
    args = ap.parse_args()
    report = audit(args.root)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Coverage manifest: {args.out}")
    raise SystemExit(1 if report["errors"] else 0)


if __name__ == "__main__":
    main()
