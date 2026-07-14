#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / (
    "Plan/07_IMPLEMENTATION/scripts/"
    "evaluate_wave64_recovered_foley_packet_readiness.py"
)
SPEC = importlib.util.spec_from_file_location("row028_recovered_foley", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RecoveredFoleyPacketReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = MODULE.build_evidence(ROOT, "2026-07-14T07:30:00-05:00")

    def test_two_real_foley_wavs_are_hash_verified(self) -> None:
        candidates = self.evidence["recovered_wav_candidates"]
        self.assertEqual(len(candidates), 2)
        self.assertEqual(
            {item["role"] for item in candidates},
            {"sfx_foley_stem", "sfx_foley_original_generated"},
        )
        self.assertTrue(all(item["integrity_verified"] for item in candidates))
        self.assertTrue(all(not item["production_eligible"] for item in candidates))

    def test_legacy_event_sources_are_exactly_recovered(self) -> None:
        sources = self.evidence["recovered_legacy_event_sources"]
        self.assertEqual(set(sources), set(MODULE.LEGACY_SOURCE_RECORDS))
        self.assertTrue(all(item["source_bytes_preserved"] for item in sources.values()))

    def test_legacy_timing_and_ownership_align_without_claiming_force_authority(self) -> None:
        records = self.evidence["legacy_event_alignment"]
        self.assertEqual(len(records), 2)
        self.assertEqual({record["entity_id"] for record in records}, {"C01", "O01"})
        self.assertTrue(all(record["legacy_timing_and_owner_consistent"] for record in records))
        self.assertTrue(
            all(not record["strict_visual_contact_or_force_authority_proven"] for record in records)
        )

    def test_required_binding_gate_prevents_packet_fabrication(self) -> None:
        readiness = self.evidence["strict_packet_readiness"]
        self.assertFalse(readiness["packet_formable"])
        self.assertFalse(readiness["evaluator_invoked"])
        self.assertEqual(
            set(readiness["missing_required_bindings"]),
            set(MODULE.MISSING_REQUIRED_BINDINGS),
        )
        self.assertIsNone(readiness["shot_id"])
        self.assertIsNone(readiness["take_id"])

    def test_project_boundaries_preserve_autonomous_fail_closed_policy(self) -> None:
        boundaries = self.evidence["boundaries"]
        for key in (
            "generation_executed",
            "audio_modified",
            "strict_manifest_or_identity_fields_invented",
            "visual_contact_claimed",
            "force_event_authority_claimed",
            "manual_gold_mask_authority_claimed",
            "production_runtime_claimed",
            "production_av_review_claimed",
            "production_alignment_bundle_claimed",
            "aws_contacted",
            "ec2_started",
            "mask_or_wave71_touched",
            "jira_mutated",
        ):
            self.assertFalse(boundaries[key], key)

    def test_wav_metadata_uses_pcm_header(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sample.wav"
            with wave.open(str(path), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(8000)
                handle.writeframes(b"\0\0" * 80)
            metadata = MODULE.wav_metadata(path)
            self.assertEqual(metadata["duration_seconds"], 0.01)
            self.assertEqual(metadata["frames"], 80)


if __name__ == "__main__":
    unittest.main()
