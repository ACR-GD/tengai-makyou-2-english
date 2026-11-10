#!/usr/bin/env python3
"""Codec for the .scs region: decode to messages-with-spans, and encode back.

The region is a stream of 16-bit little-endian words:
  * a word is TEXT iff its two bytes form a valid double-byte Shift-JIS char,
  * else it is a control word (opcode / parameter), kept verbatim,
  * word 0x000D is a line break,
  * messages are split *after* the terminator word 0x0012.

decode_spans() returns, for each message, its byte span [start,end) in the
region plus a reversible raw string (text + {XXXX} tags + \\n).
encode_raw() is the exact inverse of that raw string.
"""
import struct

NEWLINE = 0x000D
TERMINATOR = 0x0012


def is_sjis_char(w):
    lead = w & 0xFF
    trail = (w >> 8) & 0xFF
    if not ((0x81 <= lead <= 0x9F) or (0xE0 <= lead <= 0xFC)):
        return False
    if not ((0x40 <= trail <= 0x7E) or (0x80 <= trail <= 0xFC)):
        return False
    return True


def decode_spans(region):
    """Yield dicts: {mi, start, end, raw} covering the whole region in order."""
    msgs = []
    i, n = 0, len(region)
    cur = []
    start = 0
    mi = 0

    def flush(end):
        nonlocal cur, start, mi
        raw = "".join(cur)
        msgs.append({"mi": mi, "start": start, "end": end, "raw": raw})
        mi += 1
        cur = []

    while i + 1 < n:
        w = struct.unpack_from("<H", region, i)[0]
        if is_sjis_char(w):
            cur.append(region[i:i + 2].decode("shift_jis", "replace"))
            i += 2
            continue
        if w == NEWLINE:
            cur.append("\n")
            i += 2
        else:
            cur.append(f"{{{w:04X}}}")
            i += 2
            if w == TERMINATOR:
                flush(i)
                start = i
    # trailing odd byte (region length odd) -> keep as raw byte tag
    if i < n:
        cur.append(f"<{region[i]:02X}>")
        i += 1
    if cur or start < n:
        flush(n)
    return msgs


FW_SPACE = b"\x81\x40"
TRANSLIT = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2026": "...", "\u2014": "-", "\u2013": "-", "\u2212": "-",
    "\u30fb": "-", "\uff5c": "|", "\u2640": "!?", "\uff20": " ",
    "\u00d7": "x",
}

# ASCII punctuation whose 0xFF00 full-width form is NOT Shift-JIS encodable
# (it silently became a full-width SPACE before).  Map to real full-width
# SJIS code points so apostrophes / hyphens / quotes actually render.
PUNCT_SJIS = {
    "'": b"\x81\x66",   # U+2019 '
    '"': b"\x81\x68",   # U+201D "
    "-": b"\x81\x7c",   # U+2212 - (full-width minus)
    "~": b"\x81\x60",   # U+301C ~
}


import unicodedata


def enc_char(ch, translit=False):
    """Encode one display character to region bytes."""
    if translit and ch in TRANSLIT:
        return b"".join(enc_char(c, False) for c in TRANSLIT[ch])
    o = ord(ch)
    if ch in ("\u3000", " ", "\u00a0"):  # full-width / ASCII / NBSP space
        return FW_SPACE
    if ch in PUNCT_SJIS:          # punctuation w/o a 0xFF00 SJIS form
        return PUNCT_SJIS[ch]
    if o < 0x80:                  # ASCII -> full-width SJIS
        if 0x21 <= o <= 0x7E:
            try:
                return chr(0xFF00 + (o - 0x20)).encode("shift_jis")
            except Exception:
                return FW_SPACE
        return FW_SPACE
    try:
        return ch.encode("shift_jis")   # Japanese / symbols -> their SJIS bytes
    except Exception:
        pass
    # accented latin (romaji) -> strip diacritics to ASCII full-width
    deco = unicodedata.normalize("NFKD", ch)
    ascii_chars = [c for c in deco if not unicodedata.combining(c) and ord(c) < 0x80]
    if ascii_chars:
        return b"".join(enc_char(c, False) for c in ascii_chars)
    return FW_SPACE                      # last-resort placeholder


import re
_TAG = re.compile(r"\{([0-9A-Fa-f]{4})\}|<([0-9A-Fa-f]{2})>")


def encode_raw(raw, translit=False):
    """Inverse of the raw string form -> region bytes."""
    out = bytearray()
    i = 0
    while i < len(raw):
        m = _TAG.match(raw, i)
        if m:
            if m.group(1) is not None:
                out += struct.pack("<H", int(m.group(1), 16))
            else:
                out += bytes([int(m.group(2), 16)])
            i = m.end()
        elif raw[i] == "\n":
            out += struct.pack("<H", NEWLINE)
            i += 1
        else:
            out += enc_char(raw[i], translit)
            i += 1
    return bytes(out)
