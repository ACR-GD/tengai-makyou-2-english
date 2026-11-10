"""The "CMP" wrapper used by uno_all/* resources.

Header: b"CMP", layer count, u32 decoded size. The payload is that many nested
DS BIOS streams (0x10 LZ77, 0x24/0x28 Huffman, 0x30 RLE); see the ARM9 loader
at 0x02050310 and its layer loop at 0x0204FEDC. A layer count of zero means
the payload is stored as is, which is how replacements are written.
"""
import struct

from battle_graphics import lz10_decode

MAGIC = b"CMP"


def _rle_decode(data):
    size = struct.unpack_from("<I", data, 0)[0] >> 8
    out, pos = bytearray(), 4
    while len(out) < size:
        flag = data[pos]
        pos += 1
        if flag & 0x80:
            out += bytes([data[pos]]) * ((flag & 0x7F) + 3)
            pos += 1
        else:
            count = (flag & 0x7F) + 1
            out += data[pos:pos + count]
            pos += count
    return bytes(out[:size])


def _huffman_decode(data):
    header = struct.unpack_from("<I", data, 0)[0]
    bits, size = header & 0x0F, header >> 8
    tree_start = 4
    tree_size = (data[tree_start] + 1) * 2
    stream = tree_start + tree_size
    out_values, node = [], tree_start + 1
    total = size * 8 // bits
    while len(out_values) < total:
        word = struct.unpack_from("<I", data, stream)[0]
        stream += 4
        for bit in range(31, -1, -1):
            value = data[node]
            right = (word >> bit) & 1
            child = (node & ~1) + (value & 0x3F) * 2 + 2 + right
            if value & (0x40 if right else 0x80):
                out_values.append(data[child])
                node = tree_start + 1
                if len(out_values) == total:
                    break
            else:
                node = child
    out = bytearray()
    if bits == 8:
        out = bytearray(out_values)
    else:
        for i in range(0, len(out_values), 2):
            out.append(out_values[i] | (out_values[i + 1] << 4))
    return bytes(out[:size])


def _layer(data):
    kind = data[0] & 0xF0
    if kind == 0x10:
        return lz10_decode(data[:])
    if kind == 0x20:
        return _huffman_decode(data)
    if kind == 0x30:
        return _rle_decode(data)
    raise ValueError(f"Unknown BIOS compression {data[0]:#x}")


def decode(blob):
    if blob[:3] != MAGIC:
        raise ValueError("Not a CMP resource")
    layers, size = blob[3], struct.unpack_from("<I", blob, 4)[0]
    data = bytes(blob[8:])
    for _ in range(layers):
        data = _layer(data)
    if len(data) < size:
        raise ValueError("CMP payload is shorter than its declared size")
    return data[:size]


def encode_raw(data):
    return MAGIC + b"\0" + struct.pack("<I", len(data)) + bytes(data)
