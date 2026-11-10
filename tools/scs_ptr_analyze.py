#!/usr/bin/env python3
"""Classify where pointer offsets land relative to region tokens."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
from scs_extract import is_sjis_char


def tokenize_offsets(region):
    """Return set of token-start offsets, and a map offset->('txt'|'op') span info.

    token_starts: set of byte offsets where a token begins
    in_text: set of byte offsets that are *inside* (not start of) a text run
    in_char_mid: set of offsets that split a 2-byte char
    """
    token_starts = set()
    in_text = set()
    mid_char = set()
    i, n = 0, len(region)
    while i + 1 < n:
        w = struct.unpack_from("<H", region, i)[0]
        if is_sjis_char(w):
            # start of (or continuation of) a text run
            # find run extent
            token_starts.add(i)
            j = i
            while j + 1 < n and is_sjis_char(struct.unpack_from("<H", region, j)[0]):
                # offsets inside this char pair
                if j != i:
                    in_text.add(j)
                mid_char.add(j + 1)  # odd boundary inside the char
                j += 2
            i = j
        else:
            token_starts.add(i)
            i += 2
    return token_starts, in_text, mid_char


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "extracted/data/script"
    files = []
    for dp, _, fs in os.walk(root):
        for fn in fs:
            if fn.endswith(".scs"):
                files.append(os.path.join(dp, fn))
    at_tok = inside_text = mid = total = 0
    examples = []
    for p in files:
        d = open(p, "rb").read()
        if len(d) < 4:
            continue
        hdr = struct.unpack_from("<I", d, 0)[0]
        if hdr < 4 or hdr > len(d) or (hdr - 4) % 2:
            continue
        n = (hdr - 4) // 2
        offs = [struct.unpack_from("<H", d, 4 + 2 * i)[0] for i in range(n)]
        region = d[hdr:]
        ts, intext, midc = tokenize_offsets(region)
        for o in offs:
            total += 1
            if o in midc:
                mid += 1
                if len(examples) < 8:
                    examples.append((os.path.relpath(p, root), o))
            elif o in intext:
                inside_text += 1
            elif o in ts or o >= len(region):
                at_tok += 1
            else:
                inside_text += 1
    print(f"total pointers={total}")
    print(f"  at token boundary : {at_tok} ({100*at_tok/total:.1f}%)")
    print(f"  inside a text run : {inside_text} ({100*inside_text/total:.1f}%)")
    print(f"  mid-character     : {mid} ({100*mid/total:.1f}%)")
    for e in examples:
        print("   midchar example:", e)


if __name__ == "__main__":
    main()
