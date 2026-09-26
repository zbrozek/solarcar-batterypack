"""Extract a single footprint from an Altium binary PcbLib.

Geometry and auxiliary storage are retained; text uses the built-in default
stroke font and embedded font tables are emptied. Library layer information
is retained, component indexes are reduced to one entry, and only
models referenced by the footprint's MODELID GUIDs are retained. Embedded
model streams are renumbered with their corresponding model records; their
GUIDs, compressed STEP data and placement transforms are never changed.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path
from typing import Mapping

from altium_cfb import CompoundFile, write_compound


def _u32(data: bytes, offset: int = 0) -> int:
    if offset + 4 > len(data):
        raise ValueError("Truncated Altium record length")
    return struct.unpack_from("<I", data, offset)[0]


def _record(data: bytes, offset: int) -> tuple[bytes, int]:
    length = _u32(data, offset)
    end = offset + 4 + length
    if end > len(data):
        raise ValueError("Truncated Altium record")
    return data[offset + 4:end], end


def _pack_record(payload: bytes) -> bytes:
    return struct.pack("<I", len(payload)) + payload


def _pascal(payload: bytes) -> str:
    if not payload or payload[0] != len(payload) - 1:
        raise ValueError("Unsupported Altium Pascal string")
    return payload[1:].decode("cp1252")


def _pack_pascal(text: str) -> bytes:
    encoded = text.encode("cp1252")
    if len(encoded) > 255:
        raise ValueError("Altium footprint name exceeds 255 bytes")
    return _pack_record(bytes([len(encoded)]) + encoded)


def _streams(source: CompoundFile | Mapping[str, bytes]) -> Mapping[str, bytes]:
    return source.streams if isinstance(source, CompoundFile) else source


def footprint_names(source: CompoundFile | Mapping[str, bytes]) -> list[str]:
    """Return full footprint names from the Library/Data component index."""
    data = _streams(source)["Library/Data"]
    _, offset = _record(data, 0)
    count = _u32(data, offset)
    offset += 4
    result = []
    for _ in range(count):
        payload, offset = _record(data, offset)
        result.append(_pascal(payload))
    if offset != len(data):
        raise ValueError("Unexpected data after footprint-name table")
    return result


def section_keys(source: CompoundFile | Mapping[str, bytes]) -> dict[str, str]:
    """Return the full-name to CFB-storage-name aliases, if present."""
    data = _streams(source).get("SectionKeys")
    if data is None:
        return {}
    count = _u32(data)
    offset, result = 4, {}
    for _ in range(count):
        name, offset = _record(data, offset)
        key, offset = _record(data, offset)
        result[_pascal(name)] = _pascal(key)
    if offset != len(data):
        raise ValueError("Unexpected data after SectionKeys table")
    return result


def _properties(record: bytes) -> dict[bytes, bytes]:
    return {
        item.split(b"=", 1)[0].upper(): item.split(b"=", 1)[1]
        for item in record.rstrip(b"\0").split(b"|") if b"=" in item
    }


def extract_footprint(
    source: CompoundFile | Mapping[str, bytes], name: str,
) -> dict[str, bytes]:
    """Build a complete one-footprint PcbLib stream mapping.

    ``name`` is the original full library reference, including names longer
    than the CFB 31-character directory limit. The footprint is not renamed.
    Unsupported or inconsistent index records fail rather than being guessed.
    """
    streams = _streams(source)
    names = footprint_names(source)
    if names.count(name) != 1:
        raise ValueError("Footprint name missing or duplicated: " + name)
    aliases = section_keys(source)
    storage = aliases.get(name, name)
    prefix = storage + "/"
    if prefix + "Data" not in streams or prefix + "Parameters" not in streams:
        raise ValueError("Missing footprint storage: " + storage)
    component_roots = {aliases.get(item, item) for item in names}
    result = {
        path: payload for path, payload in streams.items()
        if path.split("/", 1)[0] not in component_roots or path.startswith(prefix)
    }

    data = streams["Library/Data"]
    _, offset = _record(data, 0)
    result["Library/Data"] = data[:offset] + struct.pack("<I", 1) + _pack_pascal(name)
    if "SectionKeys" in streams:
        result["SectionKeys"] = (
            struct.pack("<I", 1) + _pack_pascal(name) + _pack_pascal(storage)
            if name in aliases else struct.pack("<I", 0)
        )

    toc_path = "Library/ComponentParamsTOC/Data"
    if toc_path in streams:
        toc, offset = _record(streams[toc_path], 0)
        if offset != len(streams[toc_path]):
            raise ValueError("Unexpected ComponentParamsTOC record layout")
        lines = toc.rstrip(b"\0").splitlines(keepends=True)
        selected = [line for line in lines
                    if _properties(line.strip()).get(b"NAME", b"").decode("cp1252") == name]
        if len(selected) != 1:
            raise ValueError("Missing or duplicated footprint in ComponentParamsTOC")
        payload = selected[0]
        if toc.endswith(b"\0"):
            payload += b"\0"
        result[toc_path] = _pack_record(payload)

    referenced_ids = set()
    required_embedded_ids = set()
    for path, payload in streams.items():
        if path.startswith(prefix):
            for match in re.finditer(rb"(?:\||^)MODELID=([^|\x00]+)([^\x00]*)", payload):
                model_id = match.group(1).upper()
                referenced_ids.add(model_id)
                if _properties(match.group(2)).get(b"MODEL.EMBED", b"").upper() == b"TRUE":
                    required_embedded_ids.add(model_id)
    retained_ids = set()
    for group in ("Library/Models", "Library/ModelsNoEmbed"):
        data_path, header_path = group + "/Data", group + "/Header"
        if data_path not in streams:
            continue
        records = []
        offset = 0
        model_data = streams[data_path]
        while offset < len(model_data):
            payload, offset = _record(model_data, offset)
            records.append(payload)
        if header_path not in streams or _u32(streams[header_path]) != len(records):
            raise ValueError("Inconsistent model record count: " + group)
        for path in list(result):
            if path.startswith(group + "/") and path[len(group) + 1:].isdigit():
                del result[path]
        retained = []
        for index, payload in enumerate(records):
            properties = _properties(payload)
            model_id = properties.get(b"ID", b"").upper()
            if model_id not in referenced_ids:
                continue
            retained_ids.add(model_id)
            old_path = group + "/" + str(index)
            if old_path in streams:
                result[group + "/" + str(len(retained))] = streams[old_path]
            elif properties.get(b"EMBED", b"").upper() == b"TRUE":
                raise ValueError("Missing embedded model stream: " + old_path)
            retained.append(payload)
        result[data_path] = b"".join(_pack_record(payload) for payload in retained)
        result[header_path] = struct.pack("<I", len(retained))
    # Extruded bodies also carry MODELID but store their geometry directly in
    # the footprint, and external models need not appear in the model table.
    missing = required_embedded_ids - retained_ids
    if missing:
        raise ValueError("Footprint references unavailable models: " + repr(missing))
    return normalize_footprint_fonts(result)


def write_footprint(
    source: CompoundFile | str | Path, name: str, destination: str | Path,
) -> dict[str, bytes]:
    """Extract and write one footprint, returning its exact output streams."""
    if not isinstance(source, CompoundFile):
        source = CompoundFile(source)
    streams = extract_footprint(source, name)
    required_paths = {""}
    for path in streams:
        required_paths.add(path)
        while "/" in path:
            path = path.rsplit("/", 1)[0]
            required_paths.add(path)
    metadata = {path: details for path, details in source.metadata.items()
                if path in required_paths}
    write_compound(destination, streams, metadata)
    return streams


def _footprint_primitives(data: bytes):
    """Yield primitive tags and their exact length-prefixed record spans.

    PCB binary pads contain six subrecords, text contains two, and the other
    supported primitive types contain one. Unknown types fail rather than
    allowing a guessed boundary to modify geometry or embedded model data.
    """
    _, offset = _record(data, 0)  # Footprint-name Pascal record.
    blocks_by_type = {1: 1, 2: 6, 3: 1, 4: 1, 5: 2, 6: 1, 11: 1, 12: 1}
    while offset < len(data):
        primitive_start = offset
        tag = data[offset]
        offset += 1
        if tag not in blocks_by_type:
            raise ValueError(f"Unsupported PCB primitive type {tag} at {primitive_start}")
        spans = []
        for _ in range(blocks_by_type[tag]):
            start = offset
            _, offset = _record(data, offset)
            spans.append((start, start + 4, offset))
        yield tag, primitive_start, offset, spans
    if offset != len(data):
        raise ValueError("Unexpected bytes after footprint primitives")


def _footprint_text_records(streams: Mapping[str, bytes]):
    """Yield text payload locations in indexed and retained unindexed components."""
    indexed = {section_keys(streams).get(name, name) for name in footprint_names(streams)}
    components = {path.rsplit('/', 1)[0] for path in streams
                  if path.count('/') == 1 and path.endswith('/Parameters')}
    if not indexed.issubset(components):
        raise ValueError("Indexed footprint is missing its Parameters stream")
    for component in sorted(components):
        path = component + '/Data'
        if path not in streams:
            raise ValueError("Footprint is missing its Data stream: " + component)
        data = streams[path]
        for tag, _, _, spans in _footprint_primitives(data):
            if tag != 5:
                continue
            _, start, end = spans[0]
            payload = data[start:end]
            # The libraries currently use the 252-byte modern text layout.
            # Fail on another version rather than assume its extended offsets.
            if len(payload) != 252:
                raise ValueError(f"Unsupported text record length {len(payload)} in {path}")
            if payload[43] not in (0, 1) or payload[160] not in (0, 1):
                raise ValueError("Unsupported text/barcode font kind in " + path)
            if struct.unpack_from('<H', payload, 25)[0] not in (1, 2, 3):
                raise ValueError("Unknown stroke font selector in " + path)
            if struct.unpack_from('<i', payload, 36)[0] <= 0:
                raise ValueError("Stroke text requires a positive line width in " + path)
            if (payload[43] or payload[160]) and (payload[110] or payload[123]):
                raise ValueError("Inverted TrueType text requires review in " + path)
            yield path, start, payload


def validate_footprint_fonts(source: CompoundFile | Mapping[str, bytes]) -> dict[str, int]:
    """Require built-in default stroke text and no embedded font payloads."""
    streams = _streams(source)
    embedded = streams.get('Library/EmbeddedFonts')
    if embedded is not None and embedded != struct.pack('<I', 0):
        raise ValueError("Library still contains embedded font data")
    count = 0
    for path, _, payload in _footprint_text_records(streams):
        if payload[43] or payload[160] or struct.unpack_from('<H', payload, 25)[0] != 1:
            raise ValueError("Footprint text is not the built-in default stroke font: " + path)
        count += 1
    return {'text_records': count, 'embedded_fonts': 0}


def normalize_footprint_fonts(source: CompoundFile | Mapping[str, bytes]) -> dict[str, bytes]:
    """Change only font selectors, preserving all geometry and text content.

    Offsets are relative to the first text subrecord payload: stroke selector
    uint16 at 25; font kind at 43 and the modern overriding kind at 160.
    Both kinds must be zero. See the primary parser implementations:
    https://gitlab.com/kicad/code/kicad/-/blob/master/pcbnew/pcb_io/altium/altium_parser_pcb.cpp
    https://github.com/issus/AltiumSharp/blob/master/src/OriginalCircuit.Altium/Serialization/Readers/PcbLibReader.cs

    Existing inactive TrueType names/styles remain untouched, as do text
    height, width, position, rotation, layer and all non-text primitives.
    A four-byte zero font count is Altium's native empty embedded-font table.
    """
    streams = _streams(source)
    result = dict(streams)
    changed = {}
    for path, start, payload in _footprint_text_records(streams):
        if payload[43] or payload[160] or struct.unpack_from('<H', payload, 25)[0] != 1:
            target = changed.setdefault(path, bytearray(streams[path]))
            struct.pack_into('<H', target, start + 25, 1)
            target[start + 43] = 0
            target[start + 160] = 0
    result.update({path: bytes(data) for path, data in changed.items()})
    if 'Library/EmbeddedFonts' in result:
        result['Library/EmbeddedFonts'] = struct.pack('<I', 0)
    validate_footprint_fonts(result)
    return result


def footprint_pad_names(
    source: CompoundFile | Mapping[str, bytes], name: str,
) -> list[str]:
    """Return pad designators in primitive order, including repeated names."""
    streams = _streams(source)
    if footprint_names(streams).count(name) != 1:
        raise ValueError("Footprint name missing or duplicated: " + name)
    storage = section_keys(streams).get(name, name)
    data = streams[storage + "/Data"]
    result = []
    for tag, _, _, spans in _footprint_primitives(data):
        if tag == 2:
            _, start, end = spans[0]
            result.append(_pascal(data[start:end]))
    return result


def rename_footprint_pads(
    streams: Mapping[str, bytes], name: str, mapping: Mapping[str, str],
) -> dict[str, bytes]:
    """Rename selected pad designators simultaneously, preserving geometry.

    The input may contain one or many footprints. A copied stream dictionary
    is returned; only the named footprint's Data stream can change. Pad names
    are Pascal strings inside the first of six pad subrecords. All primitive
    tags and every other subrecord are copied verbatim, including text, pad
    geometry, model transforms and any unknown bytes within known records.
    Existing physical pads with the same designator are renamed together.
    Missing source names, merged designators and unknown primitive types fail.
    """
    if not mapping:
        raise ValueError("A nonempty pad-designator mapping is required")
    if any(not isinstance(old, str) or not isinstance(new, str) or not old or not new
           for old, new in mapping.items()):
        raise ValueError("Pad designators must be nonempty strings")
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("Pad renumbering must not merge distinct designators")
    names = footprint_pad_names(streams, name)
    if not set(mapping).issubset(names):
        raise ValueError("Pad designators not present: " + repr(set(mapping) - set(names)))
    renamed = {mapping.get(pad, pad) for pad in names}
    if len(renamed) != len(set(names)):
        raise ValueError("Renumbered pads collide with unchanged pad designators")
    storage = section_keys(streams).get(name, name)
    path = storage + "/Data"
    original = streams[path]
    first_name, _ = _record(original, 0)
    if _pascal(first_name) != name:
        raise ValueError("Footprint Data name disagrees with library index")
    output = bytearray()
    cursor = 0
    replacements = []
    for tag, _, _, spans in _footprint_primitives(original):
        if tag != 2:
            continue
        start, payload_start, end = spans[0]
        old = _pascal(original[payload_start:end])
        if old not in mapping:
            continue
        replacement = _pack_pascal(mapping[old])
        output.extend(original[cursor:start])
        output.extend(replacement)
        replacements.append((start, end, len(replacement)))
        cursor = end
    output.extend(original[cursor:])
    changed = bytes(output)
    # Independently compare every retained byte span; name lengths may change.
    old_offset = new_offset = 0
    for start, end, replacement_size in replacements:
        retained_size = start - old_offset
        if original[old_offset:start] != changed[new_offset:new_offset + retained_size]:
            raise AssertionError("Non-designator data changed during pad renumbering")
        old_offset = end
        new_offset += retained_size + replacement_size
    if original[old_offset:] != changed[new_offset:]:
        raise AssertionError("Trailing geometry changed during pad renumbering")
    result = dict(streams)
    result[path] = changed
    if footprint_pad_names(result, name) != [mapping.get(pad, pad) for pad in names]:
        raise AssertionError("Pad designators differ from requested mapping")
    return result
