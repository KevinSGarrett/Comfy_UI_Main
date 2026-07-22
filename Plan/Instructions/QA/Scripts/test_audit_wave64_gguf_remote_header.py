from __future__ import annotations

import importlib.util
import struct
from pathlib import Path
from unittest import mock

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/audit_wave64_gguf_remote_header.py"
SPEC = importlib.util.spec_from_file_location("gguf_header_audit", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def gguf_string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return struct.pack("<Q", len(encoded)) + encoded


def synthetic_header() -> bytes:
    entries = [
        gguf_string("general.architecture") + struct.pack("<I", 8) + gguf_string("internvl"),
        gguf_string("split.count") + struct.pack("<II", 4, 3),
        gguf_string("tokenizer.ggml.tokens")
        + struct.pack("<IIQ", 9, 8, 2)
        + gguf_string("one")
        + gguf_string("two"),
    ]
    return b"GGUF" + struct.pack("<IQQ", 3, 42, len(entries)) + b"".join(entries)


def test_parser_extracts_selected_metadata_and_skips_unselected_array() -> None:
    result = MODULE.parse_gguf_metadata(synthetic_header())
    assert result["magic"] == "GGUF"
    assert result["version"] == 3
    assert result["tensor_count"] == 42
    assert result["selected_metadata"] == {
        "general.architecture": "internvl",
        "split.count": 3,
    }
    assert "tokenizer.ggml.tokens" in result["metadata_keys"]


def test_parser_fails_closed_when_bounded_header_is_truncated() -> None:
    with pytest.raises(MODULE.GGUFHeaderError, match="exceeds bounded header"):
        MODULE.parse_gguf_metadata(synthetic_header()[:-1])


class FakeResponse:
    def __init__(self, status: int, content_range: str, body: bytes) -> None:
        self.status = status
        self.headers = {"Content-Range": content_range}
        self.body = body

    def getcode(self) -> int:
        return self.status

    def read(self, count: int) -> bytes:
        return self.body[:count]

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_fetch_requires_partial_content_starting_at_zero() -> None:
    response = FakeResponse(200, "", synthetic_header())
    with mock.patch.object(MODULE.urllib.request, "urlopen", return_value=response):
        with pytest.raises(MODULE.GGUFHeaderError, match="range request rejected"):
            MODULE.fetch_bounded_header("https://example.invalid/model.gguf", max_bytes=4096)


def test_fetch_enforces_hard_response_cap() -> None:
    response = FakeResponse(206, "bytes 0-4095/9999", b"x" * 4097)
    with mock.patch.object(MODULE.urllib.request, "urlopen", return_value=response):
        with pytest.raises(MODULE.GGUFHeaderError, match="exceeded the bounded range"):
            MODULE.fetch_bounded_header("https://example.invalid/model.gguf", max_bytes=4096)
