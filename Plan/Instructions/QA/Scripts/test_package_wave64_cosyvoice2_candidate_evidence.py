#!/usr/bin/env python3
"""Tests for the fail-closed CosyVoice2 candidate evidence packager."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "07_IMPLEMENTATION/scripts/package_wave64_cosyvoice2_candidate_evidence.py"
)
SPEC = importlib.util.spec_from_file_location("package_cosyvoice2", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def runtime_payload(candidate_hash: str) -> dict:
    return {
        "engine": "CosyVoice2",
        "engine_source": {"license": "Apache-2.0"},
        "model": {
            "model_id": "FunAudioLLM/CosyVoice2-0.5B",
            "license": "Apache-2.0",
            "local_files_only": True,
        },
        "reference_speaker": {"sha256": "reference"},
        "runtime": {
            "runtime_executed": True,
            "onnx_available_providers": ["CPUExecutionProvider"],
        },
        "output": {
            "sha256": candidate_hash,
            "bytes": 422444,
            "pcm": {"duration_seconds": 8.8},
        },
        "gates": {
            "model_payload_hash_binding_pass": True,
            "source_code_identity_pass": True,
            "independent_reference_speaker_bound": True,
            "technical_audio_pass": True,
            "dialogue_timing_pass": False,
            "production_proof_authority_pass": False,
        },
        "boundaries": {"final_voice_certification_claimed": False},
    }


def evaluation_payload(candidate_hash: str, manifest_hash: str) -> dict:
    return {
        "status": "FAIL_COSYVOICE2_DIALOGUE_TIMING",
        "bindings": {
            "candidate": {"sha256": candidate_hash},
            "candidate_manifest": {"sha256": manifest_hash},
        },
        "candidate": {
            "normalized_wer": 4.8,
            "speaker_similarity": 0.3992827236652374,
            "validated_speaker_threshold": 0.33445611596107483,
            "duration_seconds": 8.8,
            "expected_duration_seconds": 3.0,
            "target_emotion": "focused",
            "target_intensity": "controlled",
        },
        "gates": {
            "candidate_asr_pass": False,
            "candidate_reference_speaker_identity_pass": True,
            "candidate_dnsmos_worst_reference_floor_pass": True,
            "candidate_dnsmos_quality_certification_pass": None,
            "dialogue_timing_pass": False,
            "target_emotion_taxonomy_supported": False,
            "target_intensity_taxonomy_supported": None,
            "target_intensity_taxonomy_status": "unmeasured_no_calibrated_intensity_evaluator",
            "independent_playback_review_pass": False,
            "production_proof_authority_pass": False,
            "row_complete": False,
            "final_voice_certification_pass": False,
        },
        "remaining_blockers": ["timing", "style", "playback"],
        "boundaries": {"production_promotion_claimed": False},
    }


class PackageCosyVoice2EvidenceTests(unittest.TestCase):
    def create_fixture(self, root: Path) -> dict:
        candidate = root / "candidate.wav"
        runner = root / "runner.py"
        evaluator = root / "evaluator.py"
        candidate.write_bytes(b"candidate")
        runner.write_text("runner\n", encoding="utf-8")
        evaluator.write_text("evaluator\n", encoding="utf-8")
        candidate_hash = MODULE.sha256(candidate)
        runtime = root / "runtime.json"
        runtime.write_text(json.dumps(runtime_payload(candidate_hash)), encoding="utf-8")
        runtime_hash = MODULE.sha256(runtime)
        evaluation = root / "evaluation.json"
        evaluation.write_text(
            json.dumps(evaluation_payload(candidate_hash, runtime_hash)), encoding="utf-8"
        )
        return {
            "candidate": candidate,
            "runtime": runtime,
            "evaluation": evaluation,
            "runner": runner,
            "evaluator": evaluator,
        }

    def patched_hashes(self, paths: dict):
        return patch.multiple(
            MODULE,
            CANDIDATE_SHA256=MODULE.sha256(paths["candidate"]),
            RUNTIME_MANIFEST_SHA256=MODULE.sha256(paths["runtime"]),
            EVALUATION_SHA256=MODULE.sha256(paths["evaluation"]),
            RUNNER_SHA256=MODULE.sha256(paths["runner"]),
            EVALUATOR_SHA256=MODULE.sha256(paths["evaluator"]),
        )

    def test_packages_rejected_candidate_without_promotion(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = self.create_fixture(root)
            with self.patched_hashes(paths):
                payload = MODULE.package(
                    paths["candidate"],
                    paths["runtime"],
                    paths["evaluation"],
                    paths["runner"],
                    paths["evaluator"],
                    root / "durable",
                )
            self.assertEqual(payload["status"], "FAIL_COSYVOICE2_CANDIDATE_REJECTED")
            self.assertTrue(payload["acceptance"]["candidate_reference_speaker_score_pass"])
            self.assertFalse(payload["acceptance"]["candidate_intelligibility_pass"])
            self.assertFalse(payload["acceptance"]["candidate_dialogue_timing_pass"])
            self.assertFalse(payload["acceptance"]["row_complete"])
            self.assertTrue(payload["decision"]["candidate_rejected"])

    def test_rejects_false_asr_promotion(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = self.create_fixture(root)
            payload = json.loads(paths["evaluation"].read_text(encoding="utf-8"))
            payload["gates"]["candidate_asr_pass"] = True
            paths["evaluation"].write_text(json.dumps(payload), encoding="utf-8")
            with self.patched_hashes(paths), self.assertRaisesRegex(ValueError, "fail-closed"):
                MODULE.package(
                    paths["candidate"],
                    paths["runtime"],
                    paths["evaluation"],
                    paths["runner"],
                    paths["evaluator"],
                    root / "durable",
                )

    def test_write_exact_keeps_mirrors_identical(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outputs = [root / "qa.json", root / "tracker.json"]
            digest = MODULE.write_exact({"row_complete": False}, outputs)
            self.assertEqual(MODULE.sha256(outputs[0]), digest)
            self.assertEqual(MODULE.sha256(outputs[1]), digest)


if __name__ == "__main__":
    unittest.main()
