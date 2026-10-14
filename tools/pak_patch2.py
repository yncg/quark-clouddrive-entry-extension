#!/usr/bin/env python3
"""Replace resources inside resources.pak, preserving each original
resource's storage form (gzip vs. plain) so Chromium reads them the same way.

layout (verified):
  [0,12)         header  u32 version, u32 encoding, u16 count, u16 aliases
  [12,15516)     2584 * {u16 id, u32 offset}
  [15516,15522)  6-byte end marker (verbatim)
  [15522,15886)  91 * {u16 id, u16 entry_index} aliases (verbatim)
  [15886,...)    blobs, ascending offset order

usage: pak_patch2.py <src.pak> <out.pak> <rid>:<file> [...]
"""
import gzip
import struct
import sys
import zlib

HEADER = 12
MARKER_END = 15522
ALIAS_END = 15886
DATA_START = 15886


def gz(data):
    co = zlib.compressobj(9, zlib.DEFLATED, 16 + zlib.MAX_WBITS)
    return co.compress(data) + co.flush()


def main():
    src, out = sys.argv[1], sys.argv[2]
    want = {}
    for a in sys.argv[3:]:
        rid, path = a.split(":", 1)
        want[int(rid)] = open(path, "rb").read()

    data = open(src, "rb").read()
    version, encoding, count, alias_count = struct.unpack_from("<IIHH", data, 0)
    entries = []
    for k in range(count):
        rid, off = struct.unpack_from("<HI", data, HEADER + k * 6)
        entries.append([rid, off])

    offs = sorted((o, i) for i, (_, o) in enumerate(entries))
    out_data = bytearray()
    new_off = {}
    replaced = []
    for k, (off, i) in enumerate(offs):
        rid = entries[i][0]
        end = offs[k + 1][0] if k + 1 < len(offs) else len(data)
        original = data[off:end]
        if rid in want:
            body = want[rid]
            if original[:2] == b"\x1f\x8b" and body[:2] != b"\x1f\x8b":
                body = gz(body)                       # keep gzip storage
            elif original[:2] != b"\x1f\x8b" and body[:2] == b"\x1f\x8b":
                body = gzip.decompress(body)          # keep plain storage
            replaced.append((rid, len(original), len(body),
                             "gzip" if original[:2] == b"\x1f\x8b" else "plain"))
        else:
            assert rid not in want, rid
            body = original
        new_off[rid] = DATA_START + len(out_data)
        out_data += body

    head = bytearray(data[:DATA_START])
    for i, (rid, _) in enumerate(entries):
        struct.pack_into("<HI", head, HEADER + i * 6, rid, new_off[rid])

    # index ends with a sentinel entry {id:0, offset:<end of data>} that Chromium
    # validates as "<= file size"; it must be refreshed when the size changes.
    sentinel_pos = HEADER + count * 6
    struct.pack_into("<HI", head, sentinel_pos, 0, DATA_START + len(out_data))

    with open(out, "wb") as f:
        f.write(bytes(head) + bytes(out_data))

    print("pak %d -> %d 字节" % (len(data), len(head) + len(out_data)))
    for rid, before, after, mode in replaced:
        print("   rid=%-6d %7d -> %-7d (%s)" % (rid, before, after, mode))


if __name__ == "__main__":
    main()
