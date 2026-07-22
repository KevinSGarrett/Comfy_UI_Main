#!/usr/bin/env python3
"""Audit GGUF metadata through a bounded HTTP range request.

This tool is deliberately incapable of downloading a complete model.  It accepts
only a HTTP 206 response whose returned range starts at byte zero, reads at most
``--max-bytes``, and parses metadata without entering the tensor payload.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import urllib.request
from typing import Any


DEFAULT_MAX_BYTES = 8 * 1024 * 1024
MAX_METADATA_ENTRIES = 100_000
MAX_ARRAY_ELEMENTS = 10_000_000
MAX_STRING_BYTES = 16 * 1024 * 1024
MATERIALIZED_ARRAY_LIMIT = 256

VALUE_WIDTHS = {
    0: 1,  # uint8
    1: 1,  # int8
    2: 2,  # uint16
    3: 2,  # int16
    4: 4,  # uint32
    5: 4,  # int32
    6: 4,  # float32
    7: 1,  # bool
    10: 8,  # uint64
    11: 8,  # int64
    12: 8,  # float64
}
VALUE_FORMATS = {
    0: "<B",
    1: "<b",
    2: "<H",
    3: "<h",
    4: "<I",
    5: "<i",
    6: "<f",
    7: "<?",
    10: "<Q",
    11: "<q",
    12: "<d",
}
SELECTED_KEY = re.compile(
    r"^(general\.|split\.|clip\.|internvl\.|vision\.|projector\.|llama\.)",
    re.IGNORECASE,
)


class GGUFHeaderError(ValueError):
    """Raised when a remote range is unsafe or the GGUF metadata is malformed."""


class Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.offset = 0

    def take(self, count: int) -> bytes:
        if count < 0 or self.offset + count > len(self.data):
            raise GGUFHeaderError(
                f"metadata exceeds bounded header at offset {self.offset} "
                f"(need {count}, have {len(self.data) - self.offset})"
            )
        value = self.data[self.offset : self.offset + count]
        self.offset += count
        return value

    def unpack(self, fmt: str) -> Any:
        size = struct.calcsize(fmt)
        return struct.unpack(fmt, self.take(size))[0]

    def string(self, *, materialize: bool = True) -> str | None:
        size = self.unpack("<Q")
        if size > MAX_STRING_BYTES:
            raise GGUFHeaderError(f"string length {size} exceeds safety limit")
        raw = self.take(size)
        if not materialize:
            return None
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise GGUFHeaderError("metadata string is not UTF-8") from exc


def _read_value(reader: Reader, value_type: int, *, materialize: bool) -> Any:
    if value_type in VALUE_FORMATS:
        value = reader.unpack(VALUE_FORMATS[value_type])
        return value if materialize else None
    if value_type == 8:
        return reader.string(materialize=materialize)
    if value_type == 9:
        element_type = reader.unpack("<I")
        count = reader.unpack("<Q")
        if count > MAX_ARRAY_ELEMENTS:
            raise GGUFHeaderError(f"array length {count} exceeds safety limit")
        if not materialize and element_type in VALUE_WIDTHS:
            reader.take(count * VALUE_WIDTHS[element_type])
            return None
        keep = materialize and count <= MATERIALIZED_ARRAY_LIMIT
        values = [] if keep else None
        for _ in range(count):
            item = _read_value(reader, element_type, materialize=keep)
            if keep:
                values.append(item)
        if materialize and values is None:
            return {"element_count": count, "materialized": False}
        return values
    raise GGUFHeaderError(f"unsupported GGUF metadata value type {value_type}")


def parse_gguf_metadata(data: bytes) -> dict[str, Any]:
    reader = Reader(data)
    if reader.take(4) != b"GGUF":
        raise GGUFHeaderError("GGUF magic missing")
    version = reader.unpack("<I")
    if version not in (2, 3):
        raise GGUFHeaderError(f"unsupported GGUF version {version}")
    tensor_count = reader.unpack("<Q")
    metadata_count = reader.unpack("<Q")
    if metadata_count > MAX_METADATA_ENTRIES:
        raise GGUFHeaderError(f"metadata entry count {metadata_count} exceeds safety limit")

    selected: dict[str, Any] = {}
    keys: list[str] = []
    for _ in range(metadata_count):
        key = reader.string()
        assert key is not None
        keys.append(key)
        value_type = reader.unpack("<I")
        materialize = bool(SELECTED_KEY.match(key))
        value = _read_value(reader, value_type, materialize=materialize)
        if materialize:
            selected[key] = value

    return {
        "magic": "GGUF",
        "version": version,
        "tensor_count": tensor_count,
        "metadata_count": metadata_count,
        "metadata_end_offset": reader.offset,
        "metadata_keys": keys,
        "selected_metadata": selected,
    }


def fetch_bounded_header(url: str, *, max_bytes: int = DEFAULT_MAX_BYTES) -> tuple[bytes, dict[str, Any]]:
    if max_bytes < 24:
        raise GGUFHeaderError("max_bytes is too small for a GGUF header")
    request = urllib.request.Request(
        url,
        headers={"Range": f"bytes=0-{max_bytes - 1}", "User-Agent": "ComfyUI-W64-GGUF-header-audit/1"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - pinned HTTPS inputs
        status = getattr(response, "status", response.getcode())
        content_range = response.headers.get("Content-Range", "")
        if status != 206 or not content_range.lower().startswith("bytes 0-"):
            raise GGUFHeaderError(
                f"range request rejected: status={status}, content_range={content_range!r}"
            )
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise GGUFHeaderError("server exceeded the bounded range response")
    return data, {
        "http_status": status,
        "content_range": content_range,
        "received_bytes": len(data),
        "max_bytes": max_bytes,
    }


def audit_url(label: str, url: str, *, max_bytes: int) -> dict[str, Any]:
    data, transport = fetch_bounded_header(url, max_bytes=max_bytes)
    parsed = parse_gguf_metadata(data)
    return {"label": label, "url": url, "transport": transport, "gguf": parsed}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", nargs=2, metavar=("LABEL", "URL"), required=True)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    args = parser.parse_args()
    report = {
        "schema_version": 1,
        "policy": "HTTP_206_BYTE_ZERO_HARD_CAP_METADATA_ONLY_NO_TENSOR_PAYLOAD",
        "sources": [audit_url(label, url, max_bytes=args.max_bytes) for label, url in args.source],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
