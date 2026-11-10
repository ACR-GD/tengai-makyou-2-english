#!/usr/bin/env python3
"""Extract translatable Japanese text from every .scs script-string file.

Decoding strategy (robust + reversible):
  * The string region (after the u32 header = pointer-table size) is a stream
    of 16-bit little-endian words.
  * A word is TEXT iff its bytes form a valid double-byte Shift-JIS character.
  * Any other word is a control/parameter word, kept verbatim as a {XXXX} tag
    so the text can be re-encoded later without information loss.
  * Word 0x000D is rendered as a line break.
  * Messages are split on the terminator opcode 0x0012.

Outputs:
  text_dump/<relpath>.txt   human-readable, for reading/translating
  tengai2_script.json       structured records {id,file,msg,jp,jp_clean,en}
  tengai2_script.csv        flat jp/en sheet for translation
"""
import csv
import json
import os
import struct
import sys


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def is_sjis_char(w):
    """True if the 16-bit word (little-endian) is a valid 2-byte Shift-JIS char."""
    lead = w & 0xFF
    trail = (w >> 8) & 0xFF
    if not ((0x81 <= lead <= 0x9F) or (0xE0 <= lead <= 0xFC)):
        return False
    if not ((0x40 <= trail <= 0x7E) or (0x80 <= trail <= 0xFC)):
        return False
    return True


NEWLINE = 0x000D
TERMINATOR = 0x0012


def decode_region(region):
    """Return list of messages; each message is a list of tokens.

    token = ('txt', text_bytes) | ('nl',) | ('op', word)
    """
    messages = []
    cur = []
    run = bytearray()
    i = 0
    n = len(region)

    def flush_run():
        if run:
            cur.append(("txt", bytes(run)))
            run.clear()

    while i + 1 < n:
        w = u16(region, i)
        i += 2
        if is_sjis_char(w):
            run += struct.pack("<H", w)
            continue
        flush_run()
        if w == NEWLINE:
            cur.append(("nl",))
        else:
            cur.append(("op", w))
            if w == TERMINATOR:
                messages.append(cur)
                cur = []
    flush_run()
    if cur:
        messages.append(cur)
    return messages


def render_raw(tokens):
    """Reversible form: Japanese text with {XXXX} control tags and \\n."""
    out = []
    for t in tokens:
        if t[0] == "txt":
            out.append(t[1].decode("shift_jis", "replace"))
        elif t[0] == "nl":
            out.append("\n")
        else:
            out.append(f"{{{t[1]:04X}}}")
    return "".join(out)


def render_clean(tokens):
    """Readable form: Japanese text + line breaks only (control codes dropped)."""
    out = []
    for t in tokens:
        if t[0] == "txt":
            out.append(t[1].decode("shift_jis", "replace"))
        elif t[0] == "nl":
            out.append("\n")
    return "".join(out)


def has_japanese(s):
    for ch in s:
        o = ord(ch)
        if 0x3040 <= o <= 0x30FF or 0x4E00 <= o <= 0x9FFF or 0xFF00 <= o <= 0xFFEF:
            return True
    return False


def main():
    data_root = sys.argv[1] if len(sys.argv) > 1 else "extracted/data"
    out_root = sys.argv[2] if len(sys.argv) > 2 else "translation"
    script_root = os.path.join(data_root, "script")
    dump_dir = os.path.join(out_root, "text_dump")
    os.makedirs(dump_dir, exist_ok=True)

    records = []
    files = []
    for dp, _, fs in os.walk(script_root):
        for fn in fs:
            if fn.endswith(".scs"):
                files.append(os.path.join(dp, fn))
    files.sort()

    total_msgs = 0
    files_with_text = 0
    for path in files:
        data = open(path, "rb").read()
        if len(data) < 4:
            continue
        hdr = u32(data, 0)
        if hdr > len(data) or hdr < 4:
            continue
        region = data[hdr:]
        messages = decode_region(region)

        rel = os.path.relpath(path, script_root)
        file_records = []
        for mi, toks in enumerate(messages):
            raw = render_raw(toks).strip()
            clean = render_clean(toks).strip()
            if not has_japanese(clean):
                continue
            rec = {
                "id": f"{rel}#{mi}",
                "file": rel,
                "msg": mi,
                "jp": raw,
                "jp_clean": clean,
                "en": "",
            }
            file_records.append(rec)

        if not file_records:
            continue
        files_with_text += 1
        total_msgs += len(file_records)
        records.extend(file_records)

        # readable per-file dump
        out_txt = os.path.join(dump_dir, rel + ".txt")
        os.makedirs(os.path.dirname(out_txt), exist_ok=True)
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write(f"# {rel}\n")
            for rec in file_records:
                f.write(f"\n--- msg {rec['msg']} ---\n")
                f.write(rec["jp_clean"] + "\n")

    with open(os.path.join(out_root, "tengai2_script.json"), "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=1)

    with open(os.path.join(out_root, "tengai2_script.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "file", "msg", "jp", "en"])
        for r in records:
            w.writerow([r["id"], r["file"], r["msg"], r["jp"], r["en"]])

    print(f"Scanned {len(files)} .scs files")
    print(f"Files with Japanese text: {files_with_text}")
    print(f"Total messages extracted:  {total_msgs}")
    print(f"Outputs written under: {out_root}/")
    print(f"  - tengai2_script.json  (structured, reversible {{XXXX}} tags)")
    print(f"  - tengai2_script.csv   (jp/en translation sheet)")
    print(f"  - text_dump/**.txt     (human-readable)")


if __name__ == "__main__":
    main()
