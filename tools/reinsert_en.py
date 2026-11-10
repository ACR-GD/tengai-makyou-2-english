#!/usr/bin/env python3
"""Re-insert control-code tags into the English translation at the sub-message level.

Key guarantees:
  * 2-word opcodes ({0010}, {0011}, {0014}, {0015}, {0019}) keep their parameter
    word attached (including when {000D} was decoded as '\\n' or {0012} caused a
    decode_spans split).
  * Every true {0000}-terminated sub-message is translated as a complete unit
    (never fragment-by-fragment across mid-sentence {0011}/{0010}/{0008} tags).
  * Place-name banners ({0016}{0005}...{0004}...), variable-tag messages
    ({001A}/{001B}/{001E}/{0019}), and {0001} choice menus use verified mappings.
  * Timed non-{0012} cutscene subtitles preserve their exact total frame budget
    while typing English at 1 frame/char so subtitles never get cut off early.
"""
import csv
import argparse
import copy
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from en_fixes import (
    BANNER_KANJI_MAP,
    CHOICE_SUB_MAP,
    CLEAN_SUB_OVERRIDES,
    MERGED_SPLIT_MAP,
    VAR_SUB_MAP,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "translation"))
OP2 = {"{0010}", "{0011}", "{0014}", "{0015}", "{0019}"}
TAG = re.compile(r"\{[0-9A-Fa-f]{4}\}|<[0-9A-Fa-f]{2}>")


def tokenize_op2(raw):
    """Tokenize raw .scs string with 2-word opcode awareness."""
    toks = []
    i = 0
    while i < len(raw):
        m = TAG.match(raw, i)
        if m:
            t = m.group(0).upper()
            i = m.end()
            if t in OP2 and i < len(raw):
                m2 = TAG.match(raw, i)
                if m2:
                    toks.append(("op2", t, m2.group(0).upper()))
                    i = m2.end()
                    continue
                elif raw[i] == "\n":
                    toks.append(("op2", t, "{000D}"))
                    i += 1
                    continue
            toks.append(("op1", t))
        elif raw[i] == "\n":
            toks.append(("nl", "\n"))
            i += 1
        else:
            j = i + 1
            while j < len(raw) and raw[j] not in "\n{<":
                j += 1
            toks.append(("txt", raw[i:j]))
            i = j
    return toks


def render_toks(toks):
    return "".join(t[1] + t[2] if t[0] == "op2" else t[1] for t in toks)


def split_tok(toks, sep):
    subs, cur = [], []
    for t in toks:
        if t == sep:
            subs.append(cur)
            cur = []
        else:
            cur.append(t)
    subs.append(cur)
    return subs


def is_jp_char(c):
    o = ord(c)
    return (0x3040 <= o <= 0x30FF) or (0x4E00 <= o <= 0x9FFF)


def clean_en_text(s):
    """Clean English translation text of Hudson font artifacts and full-width chars."""
    out = []
    for c in s:
        o = ord(c)
        if 0xFF01 <= o <= 0xFF5E:
            out.append(chr(o - 0xFEE0))
        elif c == "\u3000":
            out.append(" ")
        else:
            out.append(c)
    s = "".join(out)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
    s = s.replace("＠", "").replace("@", "")
    s = s.replace("【", "[").replace("】", "]").replace("〜", "~").replace("−", "-")
    # In Hudson Soft's font12, ｜ (0x8162) is !! and ♀ (0x818A) is !?
    s = re.sub(r"\s*\|\s*", "! ", s)
    s = s.replace("｜", "!").replace("♀", "!?")
    s = s.replace("(female)", "!?").replace("(Female)", "!?")
    s = s.replace("卍", "Manji")
    s = s.replace("ありがたい", "appreciated")
    s = s.replace("「頭」", '"Head"').replace("頭", "Head")
    s = s.replace("さすがは", "worthy of")
    s = re.sub(r"!+\s*!", "!", s)
    lines = [" ".join(line.split()) for line in s.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def clean_jp_sub(toks):
    return "".join(
        t[1] if t[0] == "txt" else ("\n" if t[0] == "nl" else "") for t in toks
    ).replace("＠", "").strip()


def build_sub_en(sub_toks, r_en, use_whole_record_en, cache):
    raw_s = render_toks(sub_toks)
    if not any(t[0] == "txt" and t[1].strip() for t in sub_toks):
        return "".join(
            t[1] + t[2]
            if t[0] == "op2"
            else (t[1].replace("\u3000", " ") if t[0] == "txt" else t[1])
            for t in sub_toks
        )
    if raw_s in VAR_SUB_MAP:
        return VAR_SUB_MAP[raw_s]
    if raw_s in CHOICE_SUB_MAP:
        return CHOICE_SUB_MAP[raw_s]

    op1s = {t[1] for t in sub_toks if t[0] == "op1"}
    op2s = {t[1] for t in sub_toks if t[0] == "op2"}

    # Place-name banner ({0016}{0005}...{0004}... or {0016}<Region>)
    if (
        "{0012}" not in op1s
        and "{0001}" not in op1s
        and ("{0005}" in op1s or "{0004}" in op1s or "{0016}" in op1s)
    ):
        kanji = re.sub(
            r"\{[0-9A-F]{4}\}|\s+",
            "",
            raw_s.split("{0004}")[-1] if "{0004}" in raw_s else raw_s,
        )
        if kanji in BANNER_KANJI_MAP:
            return "{0016}{0004}" + BANNER_KANJI_MAP[kanji]

    # Debug choice menus (sdt/sdt.scs, set/set.scs, vst/waa0.scs)
    if "{0001}" in op1s:
        parts = []
        for t in sub_toks:
            if t[0] == "op2":
                parts.append(t[1] + t[2])
            elif t[0] in ("op1", "nl"):
                parts.append(t[1])
            else:
                core = t[1].strip()
                tr = cache.get(core, core) if any(is_jp_char(c) for c in core) else t[1]
                parts.append(clean_en_text(tr))
        return "".join(parts)

    # Regular dialogue or cutscene sub-message
    c_jp = clean_jp_sub(sub_toks)
    has_0c_lead = bool(sub_toks and sub_toks[0] == ("op1", "{000C}"))
    has_16_lead = ("op1", "{0016}") in sub_toks[:3]
    has_12_end = "{0012}" in op1s

    if c_jp in CLEAN_SUB_OVERRIDES:
        en_body = CLEAN_SUB_OVERRIDES[c_jp]
    elif use_whole_record_en and r_en.strip():
        en_body = clean_en_text(r_en)
    elif c_jp in cache:
        en_body = clean_en_text(cache[c_jp])
    else:
        pages = split_tok(sub_toks, ("op1", "{000C}"))
        p_outs = []
        for p in pages:
            cp = clean_jp_sub(p)
            if not cp:
                continue
            ep = CLEAN_SUB_OVERRIDES.get(cp) or clean_en_text(cache.get(cp, cp))
            p_outs.append(ep)
        en_body = "{000C}".join(p_outs)

    # Timed non-{0012} cutscene sub-messages: preserve total frame duration
    if not has_12_end and ("{0011}" in op2s or "{0010}" in op2s):
        seen_txt = False
        lead_p, inl_p, jp_frames = 0, 0, 0.0
        spd = 4
        hi_bit = 0
        for t in sub_toks:
            if t[0] == "op1" and t[1] == "{0016}":
                spd = 0
            elif t[0] == "op2" and t[1] == "{0010}":
                v = int(t[2][1:-1], 16)
                hi_bit |= v & 0x80
                spd = v & 0x7F
            elif t[0] == "op2" and t[1] == "{0011}":
                v = int(t[2][1:-1], 16)
                if not seen_txt:
                    lead_p += v
                else:
                    inl_p += v
            elif t[0] == "txt":
                seen_txt = True
                nch = len(t[1])
                if spd == 0:
                    pass
                elif spd >= 16:
                    jp_frames += nch
                else:
                    jp_frames += nch * (16.0 / spd)
        en_nch = len(re.sub(r"\{[0-9A-F]{4}\}", "", en_body))
        rem_p = max(0, round(jp_frames + inl_p - en_nch))
        if rem_p == 0x12:
            rem_p = 0x13
        if rem_p == 0x0D:
            rem_p = 0x0E
        if lead_p == 0x12:
            lead_p = 0x13
        if lead_p == 0x0D:
            lead_p = 0x0E
        prefix = (
            ("{000C}" if has_0c_lead else "")
            + (f"{{0011}}{{{lead_p:04X}}}" if lead_p > 0 else "")
            + f"{{0010}}{{{0x90 if hi_bit else 0x10:04X}}}"
        )
        suffix = f"{{0011}}{{{rem_p:04X}}}" if rem_p > 0 else ""
        return prefix + en_body + suffix

    prefix = (
        ("{000C}" if has_0c_lead and not en_body.startswith("{000C}") else "")
        + ("{0016}" if has_16_lead else "")
    )
    suffix = "{0012}" if has_12_end and not en_body.endswith("{0012}") else ""
    return prefix + en_body + suffix


def prepare_records(records, cache, regenerate=False):
    """Preserve the authoritative tagged text unless a proposal is requested."""
    recs = copy.deepcopy(records)

    for idx_r, r in enumerate(recs):
        if not regenerate and "en_tagged" in r:
            continue
        toks = tokenize_op2(r["jp"])
        subs = split_tok(toks, ("op1", "{0000}"))
        nonempty_cnt = sum(
            1 for s in subs if any(t[0] == "txt" and t[1].strip() for t in s)
        )
        prev_was_split = (
            idx_r > 0
            and recs[idx_r - 1]["file"] == r["file"]
            and (recs[idx_r - 1]["file"], recs[idx_r - 1]["msg"]) in MERGED_SPLIT_MAP
        )
        cur_is_split = (r["file"], r["msg"]) in MERGED_SPLIT_MAP
        use_whole = nonempty_cnt == 1 and not prev_was_split and not cur_is_split

        out_subs = []
        for idx_s, s in enumerate(subs):
            if idx_s == 0 and prev_was_split:
                out_subs.append("")
                continue
            if idx_s == len(subs) - 1 and cur_is_split:
                out_subs.append(MERGED_SPLIT_MAP[(r["file"], r["msg"])])
                continue
            out_subs.append(build_sub_en(s, r.get("en", ""), use_whole, cache))
        r["en_tagged"] = "{0000}".join(out_subs)
    return recs


def export_records(recs, root):
    """Export review copies; JSON remains the authoritative build input."""
    with open(
        os.path.join(root, "tengai2_script.tagged.csv"), "w", encoding="utf-8", newline=""
    ) as fh:
        w = csv.writer(fh)
        w.writerow(["id", "file", "msg", "jp", "en_tagged"])
        for r in recs:
            w.writerow([r["id"], r["file"], r["msg"], r["jp"], r["en_tagged"]])

    dump = os.path.join(root, "text_dump_tagged")
    by_file = {}
    for r in recs:
        by_file.setdefault(r["file"], []).append(r)
    for rel, rs in by_file.items():
        out_txt = os.path.join(dump, rel + ".txt")
        os.makedirs(os.path.dirname(out_txt), exist_ok=True)
        with open(out_txt, "w", encoding="utf-8") as fh:
            fh.write(f"# {rel}\n")
            for r in rs:
                fh.write(f"\n--- msg {r['msg']} ---\n")
                fh.write("JP: " + r["jp"].replace("\n", "\\n\n    ") + "\n")
                fh.write("EN: " + r["en_tagged"].replace("\n", "\\n\n    ") + "\n")

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path, default=Path(ROOT) / "tengai2_script.translated.json")
    ap.add_argument("--cache", type=Path, default=Path(ROOT) / "translate_cache.json")
    ap.add_argument(
        "--regenerate", action="store_true",
        help="regenerate a proposal for comparison, never overwrite the edited source",
    )
    ap.add_argument("--out", type=Path)
    ap.add_argument("--export", action="store_true", help="export CSV and readable tagged dumps")
    args = ap.parse_args()
    out = args.out or (
        args.json.with_name(args.json.stem + ".proposed.json") if args.regenerate else args.json
    )
    if args.regenerate and out.resolve() == args.json.resolve():
        ap.error("Regeneration must write a proposal, not overwrite the edited JSON")
    records = json.loads(args.json.read_text(encoding="utf-8"))
    needs_generation = args.regenerate or any("en_tagged" not in r for r in records)
    cache = json.loads(args.cache.read_text(encoding="utf-8")) if needs_generation else {}
    recs = prepare_records(records, cache, args.regenerate)
    if out.resolve() != args.json.resolve() or recs != records:
        out.write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")
    if args.export:
        if args.regenerate:
            ap.error("Export only the authoritative source, not a regeneration proposal")
        export_records(recs, out.parent)
    changed = sum(a.get("en_tagged") != b.get("en_tagged") for a, b in zip(records, recs))
    print(f"{len(recs)} records; {changed} tagged changes; output: {out}")


if __name__ == "__main__":
    main()
