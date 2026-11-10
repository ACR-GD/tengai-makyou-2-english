#!/usr/bin/env python3
"""Fit cutscene subtitles to their rows by moving them, not by truncating.

The cutscene scripts live in overlays ov_003/010/012/015/016 as 16-byte
records: u16 frame, u16 opcode 0x1C, then for a subtitle draw (byte 5 == 3)
the line index, x, y, 0xFF, 0x0C. A record with byte 4 == 2 clears the box.
The Japanese often splits one row into two timed halves (卍丸 / お前は…); the
English first half is usually wider, so the second half is moved right to
start just after it, and lines that would run off the right edge move left.
Anything that still does not fit stops the build: reword it.
"""
from __future__ import annotations

import json
from pathlib import Path

from vwf_font import measure_line_px

ROOT = Path(__file__).resolve().parents[1]
SUBTITLES = ROOT / "translation/ov008_subtitles.json"
OVERLAYS = ("ov_003", "ov_010", "ov_012", "ov_015", "ov_016")
LEFT, RIGHT, GAP = 20, 240, 5


def _records(data):
    for offset in range(0, len(data) - 16, 2):
        if data[offset + 2:offset + 4] != b"\x1c\x00":
            continue
        if data[offset + 5] == 3 and data[offset + 9] == 0xFF and data[offset + 10] == 0x0C:
            yield offset, "draw"
        elif data[offset + 4] == 2:
            yield offset, "clear"


def plan(name, data, english):
    """Return [(record offset, old x, old y, new x, new y)] for one overlay."""
    moves, shown = [], []
    for offset, kind in _records(data):
        if kind == "clear":
            shown = []
            continue
        index, x, y = data[offset + 6], data[offset + 7], data[offset + 8]
        width = measure_line_px(english[index])
        nx, ny = x, y
        left = [sx + sw for _, sx, sy, sw in shown if sy == y and sx < x]
        floor = max(left) + GAP if left else LEFT
        nx = max(nx, floor)
        if nx + width > RIGHT:
            nx = max(floor, RIGHT - width)
        if nx + width > RIGHT:
            raise ValueError(f"Subtitle {index} does not fit its row: {english[index]!r}")
        for other, sx, sy, sw in shown:
            if sy == ny and sx < nx + width and nx < sx + sw:
                raise ValueError(f"Subtitles {other} and {index} overlap")
        shown.append((index, nx, ny, width))
        if (nx, ny) != (x, y):
            moves.append((offset, x, y, nx, ny))
    return moves


def apply_subtitle_layout(rom, nds):
    english = {r["index"]: r["en"] for r in json.loads(SUBTITLES.read_text(encoding="utf-8"))}
    stats = {}
    for name in OVERLAYS:
        fid = int(name.split("_")[1])
        start, end = nds.fat[fid]
        original = nds.data[start:end]
        if bytes(rom[start:end]) != original:
            raise ValueError(f"{name} was already patched")
        moves = plan(name, original, english)
        for offset, x, y, nx, ny in moves:
            rom[start + offset + 7] = nx
            rom[start + offset + 8] = ny
        stats[name] = len(moves)
    return stats
