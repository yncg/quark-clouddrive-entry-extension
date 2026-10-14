#!/usr/bin/env python3
"""Minimal Electron asar reader helpers.

asar layout:
  u32 4 (pickle header size, always 4)
  u32 header_size (json + 8)
  u32 json_size   (json + 4)
  u32 json_string_size
  <json>          {"files": {...}}  (offsets are relative to data_start)
  <data>
"""
import json
import struct


def read_asar(path):
    f = open(path, "rb")
    for _ in range(3):
        struct.unpack("<I", f.read(4))
    json_size, = struct.unpack("<I", f.read(4))
    header = json.loads(f.read(json_size).decode("utf-8"))
    return f, header, 16 + json_size, header


def walk(node, path=""):
    for k, v in node.get("files", {}).items():
        np = path + "/" + k
        if "files" in v:
            yield from walk(v, np)
        else:
            yield np, v
