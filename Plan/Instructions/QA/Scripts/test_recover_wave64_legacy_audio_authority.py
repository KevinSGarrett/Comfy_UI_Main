#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/recover_wave64_legacy_audio_authority.py"
SPEC = importlib.util.spec_from_file_location("recover_row025_audio", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def box(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I4s", len(payload) + 8, kind) + payload


def handler(kind: bytes) -> bytes:
    return box(b"hdlr", b"\0\0\0\0" + b"\0\0\0\0" + kind + b"\0" * 12)


class LegacyAudioRecoveryTests(unittest.TestCase):
    def test_verify_spec_accepts_exact_pcm_wav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.wav"
            with wave.open(str(path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(8000)
                handle.writeframes(b"\0\0" * 80)
            spec = MODULE.ArtifactSpec(path, "audio", MODULE.digest(path), path.stat().st_size,
                                       (8000, 1, 2, 80), "test")
            record = MODULE.verify_spec(spec)
            self.assertEqual(record["wav_metadata"]["duration_seconds"], 0.01)

    def test_verify_spec_rejects_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.txt"
            path.write_text("actual", encoding="ascii")
            spec = MODULE.ArtifactSpec(path, "authority", "0" * 64)
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                MODULE.verify_spec(spec)

    def test_copy_verified_is_idempotent_for_same_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.txt"
            source.write_text("authority", encoding="ascii")
            spec = MODULE.ArtifactSpec(source, "authority", MODULE.digest(source), source.stat().st_size)
            first = MODULE.copy_verified(spec, root / "destination")
            second = MODULE.copy_verified(spec, root / "destination")
            self.assertEqual(first["sha256"], second["sha256"])

    def test_mp4_handler_parser_detects_audio_and_video(self) -> None:
        tracks = box(b"trak", box(b"mdia", handler(b"vide"))) + box(b"trak", box(b"mdia", handler(b"soun")))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "av.mp4"
            path.write_bytes(box(b"moov", tracks))
            self.assertEqual(MODULE.mp4_handler_types(path), {"vide", "soun"})

    def test_private_use_authority_requires_exact_policy_fields(self) -> None:
        rights = {
            "default_status": "private_personal_use_pre_authorized",
            "rules": ["This is a private personal-use project."],
        }
        self.assertTrue(MODULE.private_use_authority_present(rights))
        self.assertFalse(MODULE.private_use_authority_present({"project_use": "private_personal_use"}))

    def test_iter_boxes_rejects_truncated_box(self) -> None:
        self.assertEqual(list(MODULE.iter_boxes(struct.pack(">I4s", 64, b"moov") + b"x")), [])


if __name__ == "__main__":
    unittest.main()
