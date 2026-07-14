#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/reconcile_wave64_audio_pipeline_aws_inventory.py"
SPEC = importlib.util.spec_from_file_location("row025_aws_inventory", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def box(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I4s", len(payload) + 8, kind) + payload


def handler(kind: bytes) -> bytes:
    return box(b"hdlr", b"\0\0\0\0" + b"\0\0\0\0" + kind + b"\0" * 12)


class Row025AwsInventoryTests(unittest.TestCase):
    def test_mp4_handler_parser_distinguishes_video_only(self) -> None:
        payload = box(b"ftyp", b"isom\0\0\0\0isom") + box(b"moov", box(b"trak", box(b"mdia", handler(b"vide"))))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "video.mp4"
            path.write_bytes(payload)
            self.assertEqual(MODULE.mp4_handler_types(path), {"vide"})

    def test_mp4_handler_parser_detects_audio_and_video(self) -> None:
        tracks = box(b"trak", box(b"mdia", handler(b"vide"))) + box(b"trak", box(b"mdia", handler(b"soun")))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.mp4"
            path.write_bytes(box(b"moov", tracks))
            self.assertEqual(MODULE.mp4_handler_types(path), {"vide", "soun"})

    def test_iter_boxes_rejects_truncated_box(self) -> None:
        self.assertEqual(list(MODULE.iter_boxes(struct.pack(">I4s", 64, b"moov") + b"x")), [])


if __name__ == "__main__":
    unittest.main()
