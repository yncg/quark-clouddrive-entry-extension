#!/usr/bin/env python3
"""Minimal Chromium .pak reader/writer.

Format:
  header: version(u32) encoding(u8) resource_count(u16) alias_count(u16)
  index : resource_count * (resource_id u16, offset u32)
          alias_count    * (resource_id u16, entry_index u16)
  data  : raw bytes (usually gzip)
offset is absolute file offset.
"""
import struct
import sys
import gzip
import zlib


def read_pak(path):
    with open(path, "rb") as f:
        data = f.read()
    pos = 0
    version, = struct.unpack_from("<I", data, pos); pos += 4
    # Chromium pak v5 stores encoding as uint32
    encoding, = struct.unpack_from("<I", data, pos); pos += 4
    resource_count, = struct.unpack_from("<H", data, pos); pos += 2
    alias_count, = struct.unpack_from("<H", data, pos); pos += 2
    resources = []
    for _ in range(resource_count):
        rid, off = struct.unpack_from("<HI", data, pos); pos += 6
        resources.append([rid, off])
    aliases = []
    for _ in range(alias_count):
        rid, idx = struct.unpack_from("<HH", data, pos); pos += 4
        aliases.append((rid, idx))
    index_end = pos
    # sort by offset to know sizes
    order = sorted(range(resource_count), key=lambda i: resources[i][1])
    sizes = [0] * resource_count
    for k, i in enumerate(order):
        start = resources[i][1]
        end = resources[order[k + 1]][1] if k + 1 < len(order) else len(data)
        sizes[i] = end - start
    entries = []
    for i in range(resource_count):
        rid, off = resources[i]
        raw = data[off:off + sizes[i]]
        entries.append((rid, raw))
    return {
        "version": version,
        "encoding": encoding,
        "resource_count": resource_count,
        "alias_count": alias_count,
        "index_end": index_end,
        "aliases": aliases,
        "entries": entries,
        "raw_data": data,
    }


def decompress(raw):
    if raw[:2] == b"\x1f\x8b":
        return gzip.decompress(raw)
    return raw


def compress(data):
    # mimic chromium: gzip with no filename, mtime 0
    co = zlib.compressobj(9, zlib.DEFLATED, 16 + zlib.MAX_WBITS)
    return co.compress(data) + co.flush()


def build_pak(pak, new_entries):
    """new_entries: dict rid -> raw_bytes (already final, uncompressed->we compress).
       If value is bytes and not starting with gzip magic, we gzip it."""
    out_data = bytearray()
    # header placeholder
    n = len(pak["entries"])
    header_len = 4 + 4 + 2 + 2 + n * 6 + len(pak["aliases"]) * 4
    out = bytearray()
    out += struct.pack("<IIHH", pak["version"], pak["encoding"], n, len(pak["aliases"]))
    index = bytearray()
    payload = bytearray()
    base = header_len
    for rid, raw in pak["entries"]:
        if rid in new_entries:
            val = new_entries[rid]
            if val[:2] != b"\x1f\x8b":
                val = compress(val)
            blob = val
        else:
            blob = raw
        index += struct.pack("<HI", rid, base + len(payload))
        payload += blob
    for rid, idx in pak["aliases"]:
        index += struct.pack("<HH", rid, idx)
    out += index
    out += payload
    return bytes(out)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "list":
        pak = read_pak(sys.argv[2])
        print("version", pak["version"], "encoding", pak["encoding"],
              "count", pak["resource_count"], "alias", pak["alias_count"],
              "index_end", pak["index_end"])
        for rid, raw in pak["entries"][:20]:
            print(rid, len(raw), raw[:4].hex())
    elif cmd == "extract":
        pak = read_pak(sys.argv[2])
        rid = int(sys.argv[3])
        for r, raw in pak["entries"]:
            if r == rid:
                print("len", len(raw), "magic", raw[:2].hex())
                with open(sys.argv[4], "wb") as f:
                    f.write(decompress(raw))
                print("wrote", sys.argv[4])
                break
        else:
            print("not found")
    elif cmd == "find":
        pak = read_pak(sys.argv[2])
        needle = sys.argv[3].encode()
        for rid, raw in pak["entries"]:
            try:
                d = decompress(raw)
            except Exception:
                continue
            if needle in d:
                print(rid, len(raw), len(d))
