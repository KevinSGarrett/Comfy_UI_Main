from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import wave
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts/package_wave64_model_backed_playback_evidence.py"
SPEC = importlib.util.spec_from_file_location("package_wave64_model_backed_playback_evidence", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(b"\x00\x00" * 1600)


class PlaybackEvidencePackagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.original_path = self.root / "original.json"
        self.runtime_path = self.root / "runtime.json"
        self.proof_dir = self.root / "proof"
        self.raw_wav = self.root / "raw.wav"
        self.conformed_wav = self.proof_dir / "conformed.wav"
        _write_wav(self.raw_wav)
        _write_wav(self.conformed_wav)
        _write_json(
            self.original_path,
            {
                "status": "BLOCKED",
                "classification": "MODEL_BACKED_PLAYBACK_REVIEW_ABSTAINED_UNSUPPORTED_REQUIRED_CATEGORY",
                "proof_emitted": False,
                "bindings": {"candidate_audio": {"sha256": MODULE.ORIGINAL_CANDIDATE_SHA256}},
                "decision": {
                    "normalized_wer": 0.1,
                    "defects": [{"code": "CRITICAL_CONTENT_MISMATCH", "severity": "critical"}],
                    "unsupported_required_categories": [
                        "stylistic_fit.target_emotion",
                        "stylistic_fit.target_intensity",
                    ],
                    "category_scores": {"content_correctness": 0.0},
                },
            },
        )
        _write_json(
            self.runtime_path,
            {
                "runtime": {"seed": MODULE.EXPECTED_REPLACEMENT_SEED, "runtime_executed": True},
                "output": {
                    "path": str(self.raw_wav),
                    "sha256": MODULE.sha256(self.raw_wav),
                    "bytes": self.raw_wav.stat().st_size,
                },
            },
        )
        packet = {
            "result": "pass",
            "execution_passed": True,
            "verified_media": {"media_path": str(self.conformed_wav), "sha256": MODULE.sha256(self.conformed_wav)},
            "timeline_conformance": {"speech_truncated": False},
            "asr": {"pass": False, "normalized_wer": 0.7, "threshold": 0.2, "transcript": "wrong"},
        }
        _write_json(self.proof_dir / "packet_manifest.json", packet)
        _write_json(self.proof_dir / "dialogue_contract.json", {"schema": "fixture"})
        _write_json(self.proof_dir / "voice_profile.json", {"schema": "fixture"})

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_valid_negative_pair_passes_validation(self) -> None:
        result = MODULE.validate_inputs(self.original_path, self.runtime_path, self.proof_dir)
        self.assertEqual(result["replacement_packet"]["asr"]["normalized_wer"], 0.7)
        self.assertEqual(result["replacement_raw_wav"]["sha256"], MODULE.sha256(self.raw_wav))

    def test_replacement_with_passing_wer_is_rejected_by_negative_packager(self) -> None:
        packet_path = self.proof_dir / "packet_manifest.json"
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet["asr"]["pass"] = True
        packet["asr"]["normalized_wer"] = 0.0
        _write_json(packet_path, packet)
        with self.assertRaisesRegex(ValueError, "failed intelligibility gate"):
            MODULE.validate_inputs(self.original_path, self.runtime_path, self.proof_dir)

    def test_original_proof_emission_is_rejected(self) -> None:
        original = json.loads(self.original_path.read_text(encoding="utf-8"))
        original["proof_emitted"] = True
        _write_json(self.original_path, original)
        with self.assertRaisesRegex(ValueError, "no proof emitted"):
            MODULE.validate_inputs(self.original_path, self.runtime_path, self.proof_dir)


if __name__ == "__main__":
    unittest.main()
