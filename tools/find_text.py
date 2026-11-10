#!/usr/bin/env python3
"""Find files containing real contiguous Shift-JIS Japanese strings.

Distinguishes actual text from random binary by requiring runs of N+
consecutive valid double-byte SJIS Japanese characters.
"""
import os
import sys


def is_sjis_lead(b):
    return (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xFC)


def is_sjis_trail(b):
    return (0x40 <= b <= 0x7E) or (0x80 <= b <= 0xFC)


def count_jp_runs(data, minrun=6):
    """Return (num_runs, longest_run) of consecutive valid 2-byte SJIS chars."""
    runs = 0
    longest = 0
    cur = 0
    i = 0
    n = len(data)
    while i + 1 < n:
        if is_sjis_lead(data[i]) and is_sjis_trail(data[i + 1]):
            cur += 1
            i += 2
        else:
            if cur >= minrun:
                runs += 1
                longest = max(longest, cur)
            cur = 0
            i += 1
    if cur >= minrun:
        runs += 1
        longest = max(longest, cur)
    return runs, longest


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    results = []
    for dp, _, files in os.walk(root):
        for fn in files:
            if fn.endswith(".scs"):
                continue
            p = os.path.join(dp, fn)
            try:
                d = open(p, "rb").read()
            except OSError:
                continue
            runs, longest = count_jp_runs(d)
            if runs >= 3:
                results.append((runs, longest, len(d), p))
    results.sort(reverse=True)
    print(f"{'runs':>5} {'long':>5} {'size':>9}  path")
    for runs, longest, size, p in results[:60]:
        print(f"{runs:5d} {longest:5d} {size:9d}  {p}")
    print(f"\nTotal candidate files: {len(results)}")


if __name__ == "__main__":
    main()
