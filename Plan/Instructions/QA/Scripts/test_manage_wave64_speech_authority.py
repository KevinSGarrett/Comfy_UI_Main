from __future__ import annotations

import importlib.util
import json
import math
import tempfile
import unittest
import wave
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "manage_wave64_speech_authority.py"
SPEC = importlib.util.spec_from_file_location("speech_authority", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


TRAITS = {
    "timbre": "clear",
    "accent": "American English",
    "pitch": "mid",
    "pace_wpm": 160,
    "delivery_style": "narrative",
    "intensity": "controlled",
    "pronunciation": {},
    "continuity_lines": ["L001"],
}


def write_tone(path: Path, seconds: float = 2.0, sample_rate: int = 16000) -> None:
    frames = bytearray()
    for index in range(int(seconds * sample_rate)):
        sample = int(0.2 * 32767 * math.sin(2 * math.pi * 220 * index / sample_rate))
        frames.extend(sample.to_bytes(2, "little", signed=True))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(bytes(frames))


class SpeechAuthorityTests(unittest.TestCase):
    def test_json_authority_hash_is_stable_across_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            left = root / "left.json"
            right = root / "right.json"
            left.write_bytes(b'{\n  "pass": true\n}\n')
            right.write_bytes(b'{\r\n  "pass": true\r\n}\r\n')
            self.assertEqual(MODULE.sha256_text_file_lf(left), MODULE.sha256_text_file_lf(right))

    def test_authority_registry_rejects_false_completion_drift(self) -> None:
        value = {
            "row_scope": [f"TRK-W64-{number:03d}" for number in range(113, 118)],
            "completion_invariants": {
                "planning_is_runtime": True,
                "download_is_runtime_ready": False,
                "model_review_is_human_review": False,
                "intake_is_production_authority": False,
                "casting_is_production_authority": False,
                "single_metric_is_promotion": False,
                "row148_requires_all_mandatory_rows_pass": True,
            },
            "authority_separation": {
                "final_production_authority_distinct_from_playback": True,
                "fabricated_human_metadata_allowed": False,
            },
            "content_based_suppression": False,
        }
        with self.assertRaises(MODULE.AuthorityError):
            MODULE.validate_authority_registry(value)

    def test_intake_preserves_source_and_creates_hash_bound_card(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "reference.wav"
            write_tone(source)
            before = MODULE.sha256_file(source)
            card, record = MODULE.intake_reference(
                root,
                source,
                "REF-001",
                "POOL",
                "1",
                "licensed_reference_match",
                "A clean reference line.",
                "en",
                "CC0-1.0",
                "test fixture",
                "",
                TRAITS,
            )
            self.assertEqual(before, MODULE.sha256_file(source))
            self.assertTrue(record["source_bytes_preserved"])
            self.assertTrue(record["acceptance"]["intake_pass"])
            self.assertFalse(card["production_authorized"])
            MODULE.validate_reference_card(card, root)

    def test_card_rejects_source_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "reference.wav"
            write_tone(source)
            card, _ = MODULE.intake_reference(
                root,
                source,
                "REF-002",
                "POOL",
                "1",
                "licensed_reference_match",
                "A clean reference line.",
                "en",
                "CC0-1.0",
                "test fixture",
                "",
                TRAITS,
            )
            card["source"]["sha256"] = "0" * 64
            with self.assertRaises(MODULE.AuthorityError):
                MODULE.validate_reference_card(card, root)

    def test_casting_cannot_authorize_without_runtime_continuity_and_authority(self) -> None:
        record = {
            "content_based_suppression": False,
            "candidates": [
                {
                    "candidate_id": "A",
                    "rights_valid": True,
                    "runtime_proven": False,
                    "continuity_tested": False,
                }
            ],
            "decision": {"selected_candidate_id": "A"},
            "authority": {
                "playback_review_pass": False,
                "final_production_authority_pass": False,
                "production_authorized": True,
            },
        }
        with self.assertRaises(MODULE.AuthorityError):
            MODULE.validate_casting_record(record)

    def test_repository_controls_are_fail_closed(self) -> None:
        root = Path(__file__).parents[4]
        evidence = MODULE.validate_batch(root)
        self.assertTrue(evidence["row_decisions"]["TRK-W64-113"]["pass_like"])
        self.assertFalse(evidence["row_decisions"]["TRK-W64-116"]["pass_like"])
        self.assertTrue(evidence["row_decisions"]["TRK-W64-117"]["pass_like"])
        self.assertFalse(evidence["boundaries"]["production_voice_authority_claimed"])

    def test_selected_adapter_requires_hash_bound_load_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / MODULE.ADAPTER_REGISTRY
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"content_based_suppression": False, "adapters": []}), encoding="utf-8")
            with self.assertRaises(MODULE.AuthorityError):
                MODULE.validate_selected_adapter(root)


if __name__ == "__main__":
    unittest.main()
