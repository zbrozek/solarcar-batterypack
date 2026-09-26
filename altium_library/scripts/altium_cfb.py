"""Minimal, dependency-free Compound File Binary reader and writer.

Altium SchLib, PcbLib and IntLib files use Microsoft's CFB container. This
module copies their streams without interpreting or re-encoding Altium data.
The writer emits version 3 CFB, including mini streams and red-black directory
trees. It is deliberately independent of Altium and Windows COM.

    source = CompoundFile("source.SchLib")
    payload = source.read("FileHeader")
    write_compound("copy.SchLib", source.streams, source.metadata)

Stream and metadata keys use slash-separated storage paths. The empty metadata
key describes the root storage. ``write_compound`` also preserves empty
storages supplied in metadata.
"""

from __future__ import annotations

import os
import struct
from pathlib import Path
from typing import Mapping

SIGNATURE = bytes.fromhex("d0cf11e0a1b11ae1")
FREE = 0xFFFFFFFF
END = 0xFFFFFFFE
FAT_SECTOR = 0xFFFFFFFD
DIFAT_SECTOR = 0xFFFFFFFC
NO_STREAM = FREE
MINI_CUTOFF = 4096


class CompoundFile:
    """Read a CFB file, exposing exact stream bytes and directory metadata."""

    def __init__(self, source: str | os.PathLike | bytes | bytearray):
        self.data = (
            bytes(source) if isinstance(source, (bytes, bytearray))
            else Path(source).read_bytes()
        )
        data = self.data
        if len(data) < 512 or data[:8] != SIGNATURE:
            raise ValueError("Not a Compound File Binary document")
        major, byte_order, sector_shift, mini_shift = struct.unpack_from(
            "<4H", data, 26
        )
        if byte_order != 0xFFFE or (major, sector_shift) not in ((3, 9), (4, 12)):
            raise ValueError("Unsupported CFB version, sector size or byte order")
        if mini_shift != 6:
            raise ValueError("Unsupported mini-sector size")
        self.sector_size = 1 << sector_shift
        self.mini_sector_size = 1 << mini_shift
        fat_count, directory_start = struct.unpack_from("<II", data, 44)
        cutoff, mini_start, mini_count, difat_start, difat_count = struct.unpack_from(
            "<5I", data, 56
        )
        if cutoff != MINI_CUTOFF:
            raise ValueError("Unsupported mini-stream cutoff")
        difat = list(struct.unpack_from("<109I", data, 76))
        seen = set()
        next_sector = difat_start
        for _ in range(difat_count):
            if next_sector in seen:
                raise ValueError("Cyclic DIFAT")
            seen.add(next_sector)
            values = struct.unpack(
                "<" + "I" * (self.sector_size // 4), self._sector(next_sector)
            )
            difat.extend(values[:-1])
            next_sector = values[-1]
        fat_sectors = [value for value in difat if value != FREE]
        if len(fat_sectors) != fat_count:
            raise ValueError("Inconsistent FAT sector count")
        self.fat = []
        for sector in fat_sectors:
            self.fat.extend(struct.unpack(
                "<" + "I" * (self.sector_size // 4), self._sector(sector)
            ))
        directory = self._regular(directory_start)
        self.entries = []
        for offset in range(0, len(directory), 128):
            entry = directory[offset:offset + 128]
            name_length = struct.unpack_from("<H", entry, 64)[0]
            kind, color = struct.unpack_from("<BB", entry, 66)
            if kind and (name_length < 2 or name_length > 64 or name_length % 2):
                raise ValueError("Invalid directory entry name")
            name = entry[:max(0, name_length - 2)].decode("utf-16le") if kind else ""
            left, right, child = struct.unpack_from("<3I", entry, 68)
            start, size = struct.unpack_from("<IQ", entry, 116)
            if major == 3:
                size &= 0xFFFFFFFF
            self.entries.append({
                "name": name, "kind": kind, "color": color,
                "left": left, "right": right, "child": child,
                "clsid": entry[80:96],
                "state_bits": struct.unpack_from("<I", entry, 96)[0],
                "created": struct.unpack_from("<Q", entry, 100)[0],
                "modified": struct.unpack_from("<Q", entry, 108)[0],
                "start": start, "size": size,
            })
        if not self.entries or self.entries[0]["kind"] != 5:
            raise ValueError("Missing root directory entry")
        root = self.entries[0]
        self.mini_stream = self._regular(root["start"], root["size"])
        mini_data = self._regular(mini_start, mini_count * self.sector_size)
        self.mini_fat = list(struct.unpack("<" + "I" * (len(mini_data) // 4), mini_data))
        self.streams: dict[str, bytes] = {}
        self.metadata: dict[str, dict] = {"": root.copy()}
        visited = {0}

        def visit(index: int, prefix: str) -> None:
            if index == NO_STREAM:
                return
            if index >= len(self.entries) or index in visited:
                raise ValueError("Invalid or cyclic directory tree")
            visited.add(index)
            entry = self.entries[index]
            visit(entry["left"], prefix)
            path = prefix + entry["name"]
            if path in self.metadata:
                raise ValueError("Duplicate CFB path: " + path)
            self.metadata[path] = entry.copy()
            if entry["kind"] == 1:
                visit(entry["child"], path + "/")
            elif entry["kind"] == 2:
                if entry["size"] < MINI_CUTOFF:
                    parts = []
                    for sector in self._chain(entry["start"], self.mini_fat):
                        start = sector * self.mini_sector_size
                        part = self.mini_stream[start:start + self.mini_sector_size]
                        if len(part) != self.mini_sector_size:
                            raise ValueError("Mini sector outside root stream")
                        parts.append(part)
                    payload = b"".join(parts)[:entry["size"]]
                    if len(payload) != entry["size"]:
                        raise ValueError("Truncated mini stream")
                    self.streams[path] = payload
                else:
                    self.streams[path] = self._regular(entry["start"], entry["size"])
            else:
                raise ValueError("Unexpected directory entry kind")
            visit(entry["right"], prefix)

        visit(root["child"], "")

    def _sector(self, sector: int) -> bytes:
        offset = (sector + 1) * self.sector_size
        result = self.data[offset:offset + self.sector_size]
        if len(result) != self.sector_size:
            raise ValueError("Sector outside CFB file")
        return result

    @staticmethod
    def _chain(start: int, table: list[int]):
        seen = set()
        while start != END:
            if start >= len(table) or start in seen:
                raise ValueError("Invalid or cyclic allocation chain")
            seen.add(start)
            yield start
            start = table[start]

    def _regular(self, start: int, size: int | None = None) -> bytes:
        data = b"".join(self._sector(s) for s in self._chain(start, self.fat))
        if size is not None:
            if len(data) < size:
                raise ValueError("Truncated regular stream")
            data = data[:size]
        return data

    def read(self, path: str) -> bytes:
        return self.streams[path.replace("\\", "/")]


def _name_key(name: str):
    """CFB directory ordering: UTF-16 length, then case-insensitive name."""
    return (len(name.encode("utf-16le")), name.upper())


def write_compound(
    destination: str | os.PathLike,
    streams: Mapping[str, bytes],
    metadata: Mapping[str, dict] | None = None,
) -> None:
    """Write stream bytes into a new CFB container (v3, 512-byte sectors).

    Directory metadata is optional. Stream sizes and allocation information
    are always computed from the supplied bytes. Files larger than 2 GiB and
    names longer than 31 UTF-16 code units are intentionally unsupported.
    """
    metadata = metadata or {}
    entries = [{"name": "Root Entry", "kind": 5, "path": "", "children": []}]
    path_ids = {"": 0}

    def add(path: str, kind: int) -> int:
        if path in path_ids:
            index = path_ids[path]
            if entries[index]["kind"] != kind:
                raise ValueError("Path is both a storage and stream: " + path)
            return index
        parent, _, name = path.rpartition("/")
        if not name or len(name.encode("utf-16le")) > 62 or "\0" in name:
            raise ValueError("Invalid CFB directory name: " + repr(name))
        parent_index = add(parent, 1) if parent else 0
        if any(_name_key(entries[x]["name"]) == _name_key(name)
               for x in entries[parent_index]["children"]):
            raise ValueError("Case-insensitive duplicate directory name: " + path)
        index = len(entries)
        path_ids[path] = index
        entries.append({"name": name, "kind": kind, "path": path, "children": []})
        entries[parent_index]["children"].append(index)
        return index

    for path, details in metadata.items():
        if path and details.get("kind") == 1:
            add(path, 1)
    for path, payload in streams.items():
        if not isinstance(payload, bytes):
            payload = bytes(payload)
        index = add(path, 2)
        entries[index]["payload"] = payload

    for entry in entries:
        entry.update(left=NO_STREAM, right=NO_STREAM, child=NO_STREAM,
                     parent=NO_STREAM, color=1, start=END, size=0)

    # Each storage's child entries form their own red-black binary tree.
    for storage in entries:
        root = NO_STREAM

        def rotate_left(x: int) -> None:
            nonlocal root
            y = entries[x]["right"]
            entries[x]["right"] = entries[y]["left"]
            if entries[y]["left"] != NO_STREAM:
                entries[entries[y]["left"]]["parent"] = x
            entries[y]["parent"] = entries[x]["parent"]
            if entries[x]["parent"] == NO_STREAM:
                root = y
            elif x == entries[entries[x]["parent"]]["left"]:
                entries[entries[x]["parent"]]["left"] = y
            else:
                entries[entries[x]["parent"]]["right"] = y
            entries[y]["left"] = x
            entries[x]["parent"] = y

        def rotate_right(x: int) -> None:
            nonlocal root
            y = entries[x]["left"]
            entries[x]["left"] = entries[y]["right"]
            if entries[y]["right"] != NO_STREAM:
                entries[entries[y]["right"]]["parent"] = x
            entries[y]["parent"] = entries[x]["parent"]
            if entries[x]["parent"] == NO_STREAM:
                root = y
            elif x == entries[entries[x]["parent"]]["right"]:
                entries[entries[x]["parent"]]["right"] = y
            else:
                entries[entries[x]["parent"]]["left"] = y
            entries[y]["right"] = x
            entries[x]["parent"] = y

        def color(index: int) -> int:
            return 1 if index == NO_STREAM else entries[index]["color"]

        for index in storage["children"]:
            parent, cursor = NO_STREAM, root
            while cursor != NO_STREAM:
                parent = cursor
                side = "left" if _name_key(entries[index]["name"]) < _name_key(entries[cursor]["name"]) else "right"
                cursor = entries[cursor][side]
            entries[index]["parent"] = parent
            if parent == NO_STREAM:
                root = index
            else:
                side = "left" if _name_key(entries[index]["name"]) < _name_key(entries[parent]["name"]) else "right"
                entries[parent][side] = index
            entries[index]["color"] = 0
            current = index
            while color(entries[current]["parent"]) == 0:
                parent = entries[current]["parent"]
                grand = entries[parent]["parent"]
                if parent == entries[grand]["left"]:
                    uncle = entries[grand]["right"]
                    if color(uncle) == 0:
                        entries[parent]["color"] = entries[uncle]["color"] = 1
                        entries[grand]["color"] = 0
                        current = grand
                    else:
                        if current == entries[parent]["right"]:
                            current = parent
                            rotate_left(current)
                            parent = entries[current]["parent"]
                            grand = entries[parent]["parent"]
                        entries[parent]["color"] = 1
                        entries[grand]["color"] = 0
                        rotate_right(grand)
                else:
                    uncle = entries[grand]["left"]
                    if color(uncle) == 0:
                        entries[parent]["color"] = entries[uncle]["color"] = 1
                        entries[grand]["color"] = 0
                        current = grand
                    else:
                        if current == entries[parent]["left"]:
                            current = parent
                            rotate_right(current)
                            parent = entries[current]["parent"]
                            grand = entries[parent]["parent"]
                        entries[parent]["color"] = 1
                        entries[grand]["color"] = 0
                        rotate_left(grand)
            entries[root]["color"] = 1
        storage["child"] = root

    sectors: list[bytes] = []
    fat: list[int] = []

    def allocate(payload: bytes) -> int:
        if not payload:
            return END
        start = len(sectors)
        for offset in range(0, len(payload), 512):
            sectors.append(payload[offset:offset + 512].ljust(512, b"\0"))
            fat.append(len(sectors))
        fat[-1] = END
        return start

    mini_fat: list[int] = []
    mini_stream = bytearray()
    for entry in entries:
        if entry["kind"] != 2:
            continue
        payload = entry["payload"]
        entry["size"] = len(payload)
        if 0 < len(payload) < MINI_CUTOFF:
            entry["start"] = len(mini_fat)
            for offset in range(0, len(payload), 64):
                mini_stream.extend(payload[offset:offset + 64].ljust(64, b"\0"))
                mini_fat.append(len(mini_fat) + 1)
            mini_fat[-1] = END
        else:
            entry["start"] = allocate(payload)
    entries[0]["start"] = allocate(bytes(mini_stream))
    entries[0]["size"] = len(mini_stream)
    mini_bytes = b"".join(struct.pack("<I", value) for value in mini_fat)
    mini_bytes += b"\xff" * ((-len(mini_bytes)) % 512)
    mini_start = allocate(mini_bytes)
    mini_count = len(mini_bytes) // 512

    directory = bytearray()
    for entry in entries:
        record = bytearray(128)
        encoded = (entry["name"] + "\0").encode("utf-16le")
        record[:len(encoded)] = encoded
        struct.pack_into("<HBBIII", record, 64, len(encoded), entry["kind"],
                         entry["color"], entry["left"], entry["right"], entry["child"])
        details = metadata.get(entry["path"], {})
        clsid = details.get("clsid", bytes(16))
        if len(clsid) != 16:
            raise ValueError("CFB CLSID must be 16 bytes")
        record[80:96] = clsid
        struct.pack_into("<IQQIQ", record, 96,
                         details.get("state_bits", 0), details.get("created", 0),
                         details.get("modified", 0), entry["start"], entry["size"])
        directory.extend(record)
    directory_start = allocate(bytes(directory))

    base_count = len(sectors)
    fat_count = difat_count = 0
    while True:
        new_fat = (base_count + fat_count + difat_count + 127) // 128
        new_difat = max(0, (new_fat - 109 + 126) // 127)
        if (new_fat, new_difat) == (fat_count, difat_count):
            break
        fat_count, difat_count = new_fat, new_difat
    difat_start = base_count if difat_count else END
    fat_ids = list(range(base_count + difat_count, base_count + difat_count + fat_count))
    fat.extend([DIFAT_SECTOR] * difat_count + [FAT_SECTOR] * fat_count)
    for index in range(difat_count):
        values = fat_ids[109 + index * 127:109 + (index + 1) * 127]
        values += [FREE] * (127 - len(values))
        values.append(base_count + index + 1 if index + 1 < difat_count else END)
        sectors.append(struct.pack("<128I", *values))
    fat += [FREE] * (fat_count * 128 - len(fat))
    for index in range(fat_count):
        sectors.append(struct.pack("<128I", *fat[index * 128:(index + 1) * 128]))
    if (len(sectors) + 1) * 512 >= 2 ** 31:
        raise ValueError("CFB files larger than 2 GiB are unsupported")

    header = bytearray(512)
    header[:8] = SIGNATURE
    struct.pack_into("<5H", header, 24, 0x003E, 3, 0xFFFE, 9, 6)
    struct.pack_into("<9I", header, 40, 0, fat_count, directory_start, 0,
                     MINI_CUTOFF, mini_start, mini_count, difat_start, difat_count)
    initial_difat = fat_ids[:109] + [FREE] * max(0, 109 - len(fat_ids))
    struct.pack_into("<109I", header, 76, *initial_difat)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        output.write(header)
        for sector in sectors:
            output.write(sector)
