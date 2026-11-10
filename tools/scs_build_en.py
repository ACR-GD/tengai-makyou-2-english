#!/usr/bin/env python3
"""Rebuild .scs files with VWF English text, 3-line pagination, and exact 1-to-1 pointer remap."""
import os
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from scs_codec import NEWLINE, decode_spans, enc_char, encode_raw
from vwf_font import measure_line_px, wrap_pixels

_TAG = re.compile(r"\{([0-9A-Fa-f]{4})\}|<([0-9A-Fa-f]{2})>")
OP2_WORDS = {0x0010, 0x0011, 0x0014, 0x0015, 0x0019}
OP2_TAGS = {"{0010}", "{0011}", "{0014}", "{0015}", "{0019}"}
NBSP = "\u00a0"
MAX_BOX_LINES = 3


def _nbsp_lines(text):
    return "\n".join(line.replace(" ", NBSP) for line in text.split("\n"))


def _tokenize_op2(raw):
    """Tokenize a tagged string with 2-word opcode awareness."""
    toks = []
    i = 0
    while i < len(raw):
        m = _TAG.match(raw, i)
        if m:
            t = m.group(0).upper()
            i = m.end()
            if t in OP2_TAGS and i < len(raw):
                m2 = _TAG.match(raw, i)
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


def _render_toks(toks):
    return "".join(t[1] + t[2] if t[0] == "op2" else t[1] for t in toks)


def _split_tok(toks, sep):
    subs, cur = [], []
    for t in toks:
        if t == sep:
            subs.append(cur)
            cur = []
        else:
            cur.append(t)
    subs.append(cur)
    return subs


def _is_content_tok(t):
    if t[0] == "txt":
        return bool(t[1].strip())
    if t[0] == "op1" and t[1] in ("{001A}", "{001B}", "{001E}", "{0008}", "{0009}"):
        return True
    if t[0] == "op2" and t[1] == "{0019}":
        return True
    return False


def _format_submessage_vwf(sub_toks, wrap):
    """Format a single {0000}-delimited sub-message for VWF display."""
    if not any(_is_content_tok(t) for t in sub_toks):
        return _nbsp_lines(_render_toks(sub_toks))

    op1s = {t[1] for t in sub_toks if t[0] == "op1"}

    # 1. Menu choices ({0001}) or place-name banners ({0004}/{0005}/{0006} without {0012}):
    # Keep their explicit line structure and spacing intact, converting spaces to NBSP.
    if "{0001}" in op1s or (
        "{0012}" not in op1s and ("{0004}" in op1s or "{0005}" in op1s or "{0006}" in op1s)
    ):
        return _nbsp_lines(_render_toks(sub_toks))

    # 2. Non-{0012} auto-advancing cutscene subtitles / prompts:
    # Wrap each {000C} page at 212 px (no blinking cursor on the right), preserving
    # leading/trailing timing tags ({0011}{XXXX}, {0010}{XXXX}).
    if "{0012}" not in op1s:
        c_wrap = 212 if wrap else 0
        pages = _split_tok(sub_toks, ("op1", "{000C}"))
        out_pages = []
        for p_idx, p in enumerate(pages):
            if not p:
                out_pages.append("")
                continue
            txt_indices = [k for k, t in enumerate(p) if _is_content_tok(t)]
            if not txt_indices:
                out_pages.append(_nbsp_lines(_render_toks(p)))
                continue
            f_idx, l_idx = txt_indices[0], txt_indices[-1]
            lead = _render_toks(p[:f_idx])
            trail = _render_toks(p[l_idx + 1 :])
            mid_toks = p[f_idx : l_idx + 1]
            # Collapse soft newlines to spaces before pixel-wrapping
            prose_parts = []
            for t in mid_toks:
                if t[0] == "nl":
                    prose_parts.append(" ")
                elif t[0] == "op2":
                    prose_parts.append(t[1] + t[2])
                else:
                    prose_parts.append(t[1])
            prose = re.sub(r" +", " ", "".join(prose_parts)).strip()
            if c_wrap:
                prose = wrap_pixels(prose, c_wrap)
            out_pages.append(lead + _nbsp_lines(prose) + trail)
        return "{000C}".join(out_pages)

    # 3. Interactive dialogue sub-message (ends with {0012}, no {0001}):
    # Reflow each {000C} page to `wrap` px (default 196 px) and auto-paginate into
    # chunks of at most 3 lines separated by {0012}{000C}.
    pages = _split_tok(sub_toks, ("op1", "{000C}"))
    out_chunks = []
    has_leading_0c = bool(sub_toks and sub_toks[0] == ("op1", "{000C}"))

    for p_idx, p in enumerate(pages):
        # Remove {0012} tokens inside the page; we re-attach {0012} at page boundaries
        p_clean = [t for t in p if t != ("op1", "{0012}")]
        txt_indices = [k for k, t in enumerate(p_clean) if _is_content_tok(t)]
        if not txt_indices:
            if p_clean:
                out_chunks.append((p_idx > 0 or has_leading_0c, "", _render_toks(p_clean), ""))
            continue
        f_idx, l_idx = txt_indices[0], txt_indices[-1]
        lead_toks = p_clean[:f_idx]
        trail_toks = p_clean[l_idx + 1 :]
        mid_toks = p_clean[f_idx : l_idx + 1]

        lead_str = _render_toks(lead_toks)
        trail_str = _render_toks(trail_toks)
        # Preserve {0016} (instant text speed) on continuation pages if present
        cont_prefix = "{0016}" if ("op1", "{0016}") in lead_toks else ""

        prose_parts = []
        for t in mid_toks:
            if t[0] == "nl":
                prose_parts.append(" ")
            elif t[0] == "op2":
                prose_parts.append(t[1] + t[2])
            else:
                prose_parts.append(t[1])
        prose = re.sub(r" +", " ", "".join(prose_parts)).strip()
        if wrap:
            prose = wrap_pixels(prose, wrap)
        lines = [_nbsp_lines(line) for line in prose.split("\n") if line]
        if not lines:
            lines = [""]

        for c_start in range(0, len(lines), MAX_BOX_LINES):
            chunk_body = "\n".join(lines[c_start : c_start + MAX_BOX_LINES])
            if c_start == 0:
                needs_0c = (p_idx > 0) or has_leading_0c
                out_chunks.append((needs_0c, lead_str, chunk_body, trail_str if c_start + MAX_BOX_LINES >= len(lines) else ""))
            else:
                out_chunks.append((True, cont_prefix, chunk_body, trail_str if c_start + MAX_BOX_LINES >= len(lines) else ""))

    if not out_chunks:
        return _nbsp_lines(_render_toks(sub_toks))

    rendered = []
    for idx_c, (needs_0c, lead_s, body_s, trail_s) in enumerate(out_chunks):
        prefix = "{000C}" if needs_0c else ""
        suffix = "{0012}"
        rendered.append(prefix + lead_s + body_s + trail_s + suffix)
    return "".join(rendered)


def format_en_vwf(raw, wrap=196):
    """VWF dialogue formatter: pixel-accurate word-wrap + 3-line auto-pagination.

    *wrap* is the max line width in pixels for interactive dialogue (default 196 px,
    leaving 12 px for the blinking cursor inside the 208 px dialogue box).
    """
    toks = _tokenize_op2(raw)
    subs = _split_tok(toks, ("op1", "{0000}"))
    return "{0000}".join(_format_submessage_vwf(s, wrap) for s in subs)


def parse(d):
    if len(d) < 4:
        raise ValueError("SCS header is missing")
    hdr = struct.unpack_from("<I", d, 0)[0]
    if hdr < 4 or hdr > len(d) or hdr % 2 or (len(d) - hdr) % 2:
        raise ValueError(f"Invalid SCS header/region length: {hdr}/{len(d)}")
    n = (hdr - 4) // 2
    offs = [struct.unpack_from("<H", d, 4 + 2 * i)[0] for i in range(n)]
    if any(o > (len(d) - hdr) // 2 for o in offs):
        raise ValueError("SCS pointer is outside the word-addressed text region")
    return hdr, n, offs, d[hdr:]


def true_submessage_starts(region):
    """Return the list of 16-bit word offsets where each true {0000}-delimited
    sub-message begins in `region` (skipping parameter words of 2-word opcodes).
    """
    if len(region) % 2:
        raise ValueError("SCS text region must contain complete 16-bit words")
    starts = [0]
    nwords = len(region) // 2
    w_idx = 0
    while w_idx < nwords:
        w = struct.unpack_from("<H", region, w_idx * 2)[0]
        if w in OP2_WORDS:
            if w_idx + 1 >= nwords:
                raise ValueError(f"Opcode {w:04X} has no parameter")
            w_idx += 2
            continue
        if w == 0x0000:
            starts.append(w_idx + 1)
        w_idx += 1
    return starts


def encode_en(raw, wrap=0):
    """Encode an en_tagged string to region bytes, with optional soft word-wrap."""
    out = bytearray()
    col = 0
    i = 0
    word_start_out = None
    word_cols = 0
    while i < len(raw):
        m = _TAG.match(raw, i)
        if m:
            if m.group(1) is not None:
                w = int(m.group(1), 16)
                out += struct.pack("<H", w)
                if w == NEWLINE:
                    col = 0
                    word_start_out = None
                    word_cols = 0
            else:
                out += bytes([int(m.group(2), 16)])
            i = m.end()
            continue
        ch = raw[i]
        i += 1
        if ch == "\n":
            out += struct.pack("<H", NEWLINE)
            col = 0
            word_start_out = None
            word_cols = 0
            continue
        b = enc_char(ch, translit=True)
        ncols = len(b) // 2
        if ch in (" ", NBSP):
            out += b
            col += ncols
            if ch == " ":
                word_start_out = None
                word_cols = 0
        else:
            if word_start_out is None:
                word_start_out = len(out)
                word_cols = 0
            out += b
            col += ncols
            word_cols += ncols
        if wrap and col > wrap and word_start_out is not None and word_cols < wrap:
            ws = word_start_out
            head = out[:ws]
            if head[-2:] == b"\x81\x40":
                head = head[:-2]
            tail = out[ws:]
            out = bytearray(head) + struct.pack("<H", NEWLINE) + tail
            col = word_cols
            word_start_out = len(out) - len(tail)
    return bytes(out)


def rebuild_region(region, trans, wrap, stats, force_inplace=False, vwf=False):
    msgs = decode_spans(region)
    old_starts = true_submessage_starts(region)

    new_region = bytearray()
    for m in msgs:
        s, e = m["start"], m["end"]
        if m["mi"] in trans:
            raw = trans[m["mi"]]
            if vwf:
                raw = format_en_vwf(raw, wrap)
                enc_wrap = 0
            else:
                enc_wrap = wrap
            nb = encode_en(raw, enc_wrap)
            stats["resized"] += 1
        else:
            nb = region[s:e]
        new_region += nb

    new_region_bytes = bytes(new_region)
    new_starts = true_submessage_starts(new_region_bytes)
    if len(old_starts) != len(new_starts):
        raise ValueError(
            f"Translation changed entry-point count: {len(old_starts)} -> {len(new_starts)}"
        )
    start_map = dict(zip(old_starts, new_starts))

    def remap(o):
        if o in start_map:
            return start_map[o]
        if o >= len(region) // 2:
            return len(new_region_bytes) // 2 + (o - len(region) // 2)
        raise ValueError(
            f"Pointer word offset {o} not in true sub-message starts (len={len(old_starts)})"
        )

    return new_region_bytes, remap


def rebuild_file(d, recs, wrap, stats, vwf=False):
    hdr, n, offs, region = parse(d)
    messages = decode_spans(region)
    trans = {}
    for r in recs:
        mi = r["msg"]
        if mi in trans:
            raise ValueError(f"Duplicate translation message: {r['id']}")
        if not isinstance(mi, int) or not 0 <= mi < len(messages):
            raise ValueError(f"Unknown translation message: {r['id']}")
        if messages[mi]["raw"].strip() != r["jp"].strip():
            raise ValueError(f"Japanese source changed for {r['id']}")
        if "en_tagged" not in r or not isinstance(r["en_tagged"], str):
            raise ValueError(f"Missing build-facing translation: {r['id']}")
        # An empty string deliberately suppresses a continuation already merged
        # into the preceding record. It is not a missing translation.
        trans[mi] = r["en_tagged"]
    stats["_ptrs"] = offs

    new_region, remap = rebuild_region(region, trans, wrap, stats, False, vwf)
    new_offs = [remap(o) for o in offs]

    if new_offs and max(new_offs) > 0xFFFF:
        raise ValueError(f"u16 pointer overflow: {max(new_offs)}")
    if len(new_region) // 2 > 0xFFFF:
        raise ValueError("SCS text region exceeds the u16 word-address space")

    out = bytearray(struct.pack("<I", hdr))
    for i in range(n):
        out += struct.pack("<H", new_offs[i])
    while len(out) < hdr:
        out += b"\x00"
    out += new_region
    return bytes(out)


def new_stats():
    return {
        "files": 0,
        "grew": 0,
        "old_total": 0,
        "new_total": 0,
        "locked": 0,
        "resized": 0,
        "overflow_fallback": 0,
        "_ptrs": [],
    }


def build_all(json_path, script_root, wrap, vwf=False):
    import json

    recs = json.loads(Path(json_path).read_text(encoding="utf-8"))
    if not recs:
        raise ValueError("Translation dataset is empty")
    by_file = {}
    for r in recs:
        by_file.setdefault(r["file"], []).append(r)
    stats = new_stats()
    result = {}
    for rel, rs in by_file.items():
        path = os.path.join(script_root, rel)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Missing source script: {path}")
        d = Path(path).read_bytes()
        nd = rebuild_file(d, rs, wrap, stats, vwf)
        result["script/" + rel] = nd
        stats["files"] += 1
        stats["old_total"] += len(d)
        stats["new_total"] += len(nd)
        stats["grew"] += len(nd) != len(d)
    stats.pop("_ptrs", None)
    return result, stats


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="translation/tengai2_script.translated.json")
    ap.add_argument("--script-root", default="extracted/data/script")
    ap.add_argument("--wrap", type=int, default=196)
    ap.add_argument("--vwf", action="store_true", default=True)
    a = ap.parse_args()
    _, stats = build_all(a.json, a.script_root, a.wrap, vwf=a.vwf)
    print(stats)


if __name__ == "__main__":
    main()
