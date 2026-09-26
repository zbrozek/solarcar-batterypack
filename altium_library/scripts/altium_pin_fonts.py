"""Normalize SchLib text fonts without rewriting symbol primitives.

The caller reads and writes the CFB container.  This module only updates its
FileHeader font table and components' PinTextData auxiliary streams; the Data
stream, pin geometry, electrical attributes, and other auxiliary streams stay
untouched.  The framing and default-position encoding were checked against the
Altium-authored symbols/ti/amc0x06m05-q1.SchLib in this repository.

PinTextData consists of two variable-length text styles (name, designator).
Bit 0 adds a 32-bit position margin, bit 4 adds a 16-bit font ID and 32-bit
color.  The format is also documented by the upstream implementation at:
https://github.com/wavenumber-eng/altium_monkey/blob/main/src/py/altium_monkey/altium_pintextdata_modifier.py
"""

from dataclasses import dataclass
import re
import struct
import zlib


@dataclass(frozen=True)
class PinFontUpdate:
    file_header: bytes
    pin_text_data: bytes
    pin_count: int
    font_id: int


def records(data: bytes):
    """Yield (flags, payload), rejecting truncated Altium record streams."""
    offset = 0
    while offset < len(data):
        if len(data) - offset < 4:
            raise ValueError("Truncated Altium record header")
        value = struct.unpack_from("<I", data, offset)[0]
        size, flags = value & 0xFFFFFF, value >> 24
        offset += 4
        if size > len(data) - offset:
            raise ValueError("Truncated Altium record payload")
        yield flags, data[offset:offset + size]
        offset += size


def _record(payload: bytes, flags: int = 0) -> bytes:
    if len(payload) > 0xFFFFFF or not 0 <= flags <= 255:
        raise ValueError("Invalid Altium record size or flags")
    return struct.pack("<I", len(payload) | flags << 24) + payload


def _params(payload: bytes) -> dict[bytes, bytes]:
    return {
        key.upper(): value
        for field in payload.rstrip(b"\0").split(b"|")
        if b"=" in field
        for key, value in [field.split(b"=", 1)]
    }


def _set_param(payload: bytes, key: bytes, value: bytes) -> bytes:
    """Change a field without reserializing unrelated parameter bytes."""
    pattern = rb"(?<=\|)" + re.escape(key) + rb"=[^|\x00]*"
    replacement = key + b"=" + value
    result, count = re.subn(pattern, lambda _: replacement, payload, flags=re.I)
    if count > 1:
        raise ValueError(f"Duplicate parameter {key!r}")
    if count:
        return result
    terminator = b"\0" if payload.endswith(b"\0") else b""
    body = payload[:-1] if terminator else payload
    return body + b"|" + replacement + terminator


def ensure_consolas_font(file_header: bytes) -> tuple[bytes, int]:
    """Reuse or append Consolas 8 bold, retaining every existing font entry."""
    if len(file_header) < 4:
        raise ValueError("Missing FileHeader record")
    size = struct.unpack_from("<I", file_header)[0]
    if size >> 24 or size > len(file_header) - 4:
        raise ValueError("Invalid FileHeader record")
    payload = file_header[4:4 + size]
    fields = _params(payload)
    count = int(fields.get(b"FONTIDCOUNT", b"0"))
    if not 0 <= count < 32767:
        raise ValueError("Font count outside signed 16-bit font ID range")
    for font_id in range(1, count + 1):
        suffix = str(font_id).encode("ascii")
        if (
            fields.get(b"FONTNAME" + suffix, b"").lower() == b"consolas"
            and fields.get(b"SIZE" + suffix) == b"8"
            and fields.get(b"BOLD" + suffix, b"F").upper() == b"T"
            and all(fields.get(style + suffix, b"F").upper() in (b"F", b"0")
                    for style in (b"ITALIC", b"UNDERLINE", b"STRIKEOUT"))
            and fields.get(b"ROTATION" + suffix, b"0") == b"0"
        ):
            return file_header, font_id
    font_id = count + 1
    suffix = str(font_id).encode("ascii")
    payload = _set_param(payload, b"FontIdCount", suffix)
    for key, value in ((b"Size", b"8"), (b"Bold", b"T"), (b"FontName", b"Consolas")):
        payload = _set_param(payload, key + suffix, value)
    return _record(payload) + file_header[4 + size:], font_id


def pin_colors(component_data: bytes) -> list[int]:
    """Read pin count and inherited text colors without modifying pin records."""
    colors = []
    for flags, payload in records(component_data):
        if flags == 1 and payload[:1] == b"\x02":
            if len(payload) < 13:
                raise ValueError("Truncated binary pin")
            color_offset = 22 + payload[12]  # Pascal description at byte 12.
            if color_offset + 4 > len(payload):
                raise ValueError("Truncated binary pin color")
            colors.append(struct.unpack_from("<I", payload, color_offset)[0])
        elif flags == 0:
            fields = _params(payload)
            if fields.get(b"RECORD") == b"2":
                colors.append(int(fields.get(b"COLOR", b"0")))
    return colors


def read_pin_text_data(data: bytes | None) -> dict[int, bytes]:
    """Decode canonical PinTextData rows, keyed by zero-based pin ordinal."""
    if data is None:
        return {}
    parts = list(records(data))
    if not parts or parts[0][0] != 0:
        raise ValueError("Missing PinTextData header")
    header = _params(parts[0][1])
    if header.get(b"HEADER", b"").lower() != b"pintextdata":
        raise ValueError("Invalid PinTextData header")
    if int(header.get(b"WEIGHT", b"0")) != len(parts) - 1:
        raise ValueError("PinTextData Weight does not match entry count")
    result = {}
    for flags, payload in parts[1:]:
        if flags != 1 or len(payload) < 7 or payload[0] != 0xD0:
            raise ValueError("Invalid PinTextData compressed row")
        name_length = payload[1]
        length_offset = 2 + name_length
        if not name_length or length_offset + 4 > len(payload):
            raise ValueError("Invalid PinTextData ordinal framing")
        name = payload[2:length_offset]
        if not name.isdigit() or (len(name) > 1 and name.startswith(b"0")):
            raise ValueError("Noncanonical PinTextData ordinal")
        ordinal = int(name)
        if ordinal in result:
            raise ValueError("Duplicate PinTextData ordinal")
        compressed_length = struct.unpack_from("<I", payload, length_offset)[0]
        compressed = payload[length_offset + 4:]
        if compressed_length != len(compressed):
            raise ValueError("PinTextData compressed length mismatch")
        decoder = zlib.decompressobj()
        decoded = decoder.decompress(compressed, 4097)
        if len(decoded) > 4096 or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError("Invalid or oversized PinTextData zlib payload")
        result[ordinal] = decoded
    return result


def _text_style_parts(payload: bytes) -> list[tuple[int, bytes, bytes | None, bytes | None]]:
    """Keep all non-font data as bytes, including fractional position margins."""
    offset = 0
    result = []
    for _ in range(2):
        if offset == len(payload):
            raise ValueError("Missing pin name/designator text style")
        flags = payload[offset]
        offset += 1
        if flags & ~0x1F:
            raise ValueError("Unknown PinTextData style flags")
        size = (4 if flags & 1 else 0) + (6 if flags & 0x10 else 0)
        if len(payload) - offset < size:
            raise ValueError("Truncated PinTextData style")
        position = payload[offset:offset + 4] if flags & 1 else b""
        offset += len(position)
        font = payload[offset:offset + 2] if flags & 0x10 else None
        color = payload[offset + 2:offset + 6] if flags & 0x10 else None
        if font is not None:
            offset += 6
        result.append((flags, position, font, color))
    if offset != len(payload):
        raise ValueError("Unrecognized trailing PinTextData bytes")
    return result


def replace_pin_text_fonts(payload: bytes, font_id: int, inherited_color: int = 0) -> bytes:
    """Change only fonts, preserving custom colors, positions, and orientation."""
    if not 1 <= font_id <= 32767:
        raise ValueError("Font ID outside signed 16-bit range")
    result = bytearray()
    for flags, position, _old_font, color in _text_style_parts(payload):
        result += bytes([flags | 0x10]) + position + struct.pack("<h", font_id)
        result += color if color is not None else struct.pack("<I", inherited_color)
    return bytes(result)


def normalize_pin_fonts(
    file_header: bytes, component_data: bytes, pin_text_data: bytes | None = None,
) -> PinFontUpdate:
    """Return replacement streams setting every pin name/designator to Consolas 8 bold."""
    updated_header, font_id = ensure_consolas_font(file_header)
    colors = pin_colors(component_data)
    existing = read_pin_text_data(pin_text_data)
    if any(ordinal >= len(colors) for ordinal in existing):
        raise ValueError("PinTextData references a nonexistent pin")
    if pin_text_data is None:
        header = b"|HEADER=PinTextData|Weight=" + str(len(colors)).encode("ascii") + b"\0"
    else:
        header = next(records(pin_text_data))[1]
        header = _set_param(header, b"Weight", str(len(colors)).encode("ascii"))
    output = bytearray(_record(header))
    for ordinal, color in enumerate(colors):
        style = replace_pin_text_fonts(existing.get(ordinal, b"\0\0"), font_id, color)
        compressed = zlib.compress(style)
        name = str(ordinal).encode("ascii")
        row = b"\xd0" + bytes([len(name)]) + name + struct.pack("<I", len(compressed)) + compressed
        output += _record(row, 1)
    return PinFontUpdate(updated_header, bytes(output), len(colors), font_id)


def validate_pin_fonts(file_header: bytes, component_data: bytes, pin_text_data: bytes) -> int:
    """Verify complete pin font coverage; return the number of verified pins."""
    fields = _params(next(records(file_header))[1])
    font_count = int(fields.get(b"FONTIDCOUNT", b"0"))
    count = len(pin_colors(component_data))
    entries = read_pin_text_data(pin_text_data)
    if set(entries) != set(range(count)):
        raise ValueError("PinTextData does not cover exactly every pin")
    for payload in entries.values():
        for flags, _position, font, _color in _text_style_parts(payload):
            font_id = struct.unpack("<h", font)[0] if font is not None else 0
            suffix = str(font_id).encode("ascii")
            if (not flags & 0x10 or not 1 <= font_id <= font_count
                    or fields.get(b"FONTNAME" + suffix, b"").lower() != b"consolas"
                    or fields.get(b"SIZE" + suffix) != b"8"
                    or fields.get(b"BOLD" + suffix, b"F").upper() != b"T"):
                raise ValueError("A pin name/designator does not use the requested font")
    return count


def normalize_font_table(file_header: bytes) -> bytes:
    """Set every existing font to Consolas 8 bold, keeping font IDs stable."""
    framed = list(records(file_header))
    if not framed or framed[0][0] != 0:
        raise ValueError("Missing FileHeader property record")
    payload = framed[0][1]
    fields = _params(payload)
    count = int(fields.get(b"FONTIDCOUNT", b"0"))
    if not 1 <= count <= 32767:
        raise ValueError("Expected an existing font table")
    for font_id in range(1, count + 1):
        suffix = str(font_id).encode("ascii")
        if b"FONTNAME" + suffix not in fields or b"SIZE" + suffix not in fields:
            raise ValueError("Incomplete font table entry: " + str(font_id))
        for name, value in ((b"FontName", b"Consolas"), (b"Size", b"8"), (b"Bold", b"T")):
            payload = _set_param(payload, name + suffix, value)
        # Keep orientation, underline, charset and other independent fields.
    return _record(payload) + file_header[4 + len(framed[0][1]):]


def normalize_symbol_fonts(streams: dict[str, bytes]) -> dict[str, bytes]:
    """Normalize all text, including hidden parameters, comments and pins.

    Every text primitive retains its FontID and complete Data record. Updating
    every font definition also covers default/inherited text styles. Existing
    pin styles retain their IDs, colors, margins and orientation byte-for-byte.
    """
    result = dict(streams)
    result["FileHeader"] = normalize_font_table(result["FileHeader"])
    validate_symbol_fonts(result)
    return result


def validate_symbol_fonts(streams: dict[str, bytes]) -> dict[str, int]:
    """Verify all font definitions and text references, including pin styles."""
    header = streams["FileHeader"]
    if normalize_font_table(header) != header:
        raise ValueError("A library font is not Consolas 8 bold")
    fields = _params(next(records(header))[1])
    font_count = int(fields[b"FONTIDCOUNT"])
    symbols = text_count = pin_count = 0
    for name, data in streams.items():
        if not name.endswith("/Data"):
            continue
        symbols += 1
        for flags, payload in records(data):
            if flags:
                continue
            properties = _params(payload)
            # Label, text frame, designator, parameter/comment. Also check
            # any other record carrying an explicit font reference.
            is_text = properties.get(b"RECORD") in (b"4", b"28", b"34", b"41")
            if is_text or b"FONTID" in properties:
                font_id = int(properties.get(b"FONTID", b"1"))
                if not 1 <= font_id <= font_count:
                    raise ValueError("Text references an invalid font ID: " + name)
                text_count += 1
        pins = len(pin_colors(data))
        pin_path = name[:-4] + "PinTextData"
        if pins or pin_path in streams:
            pin_count += validate_pin_fonts(header, data, streams[pin_path])
    if symbols != int(fields[b"COMPCOUNT"]):
        raise ValueError("Symbol count does not match the library index")
    return dict(symbols=symbols, text_records=text_count, pins=pin_count, font_entries=font_count)
