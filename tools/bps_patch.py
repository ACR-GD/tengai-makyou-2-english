"""Write BPS1 patches using SourceRead and TargetRead instructions."""
import struct
import zlib


def number(value):
    if value < 0:
        raise ValueError("BPS integers must be non-negative")
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value == 0:
            out.append(byte | 0x80)
            return bytes(out)
        out.append(byte)
        value -= 1


def create_patch(source, target, metadata=b""):
    """Use equal 4KiB blocks as SourceRead, and only literal changed ranges.

    This favors a simple, verifiable patch over an optimal copy search. There
    are no encoded machine paths or ROM data in the metadata.
    """
    out = bytearray(b"BPS1")
    out += number(len(source)) + number(len(target)) + number(len(metadata)) + metadata
    position = 0
    pending = bytearray()
    equal_length = 0

    def flush_equal():
        nonlocal equal_length
        if equal_length:
            out.extend(number((equal_length - 1) << 2))
            equal_length = 0

    def flush_literal():
        if pending:
            out.extend(number(((len(pending) - 1) << 2) | 1))
            out.extend(pending)
            pending.clear()

    while position < len(target):
        end = min(position + 4096, len(target))
        a = source[position:end]
        b = target[position:end]
        if a == b:
            flush_literal()
            equal_length += len(b)
        else:
            # Trim common edges so a four-byte hook does not embed a full block.
            start = 0
            while start < min(len(a), len(b)) and a[start] == b[start]:
                start += 1
            tail = len(b)
            if len(a) == len(b):
                while tail > start and a[tail - 1] == b[tail - 1]:
                    tail -= 1
            if start:
                flush_literal()
                equal_length += start
            flush_equal()
            pending.extend(b[start:tail])
            if tail < len(b):
                flush_literal()
                equal_length += len(b) - tail
        position = end
    flush_equal()
    flush_literal()
    out += struct.pack("<II", zlib.crc32(source), zlib.crc32(target))
    out += struct.pack("<I", zlib.crc32(out))
    return bytes(out)
