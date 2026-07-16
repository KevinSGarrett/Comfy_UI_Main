#!/usr/bin/env python3
"""Focused regression tests for the Rows135, 136, and 138 evaluator."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np
import soundfile as sf


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_alignment_viseme_spatial.py"
SPEC = importlib.util.spec_from_file_location("wave64_alignment_viseme_spatial_evaluator", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Wave64AlignmentVisemeSpatialEvaluatorTests(unittest.TestCase):
    def test_spatial_inspection_detects_expected_motion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "spatial.wav"
            rate = 24000
            left = np.column_stack((np.ones(rate // 2) * 0.2, np.ones(rate // 2) * 0.05))
            right = np.column_stack((np.ones(rate // 2) * 0.05, np.ones(rate // 2) * 0.2))
            sf.write(str(path), np.vstack((left, right)).astype(np.float32), rate, subtype="PCM_24")
            metrics, _, observed_rate = MODULE.inspect_spatial(path)
            self.assertEqual(observed_rate, rate)
            self.assertTrue(metrics["trajectory_channel_motion_pass"])
            self.assertEqual(metrics["channels"], 2)
            self.assertEqual(metrics["clipping_ratio"], 0.0)

    def test_spatial_inspection_rejects_mono(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mono.wav"
            sf.write(str(path), np.zeros(24000, dtype=np.float32), 24000)
            with self.assertRaises(MODULE.EvaluationError):
                MODULE.inspect_spatial(path)

    def test_manifest_authority_claims_fail_closed(self) -> None:
        base = {
            "classification": MODULE.EXPECTED_MANIFEST_CLASSIFICATION,
            "source": {"sha256": MODULE.EXPECTED_SOURCE_SHA256, "transcript": MODULE.EXPECTED_TEXT, "source_unchanged_after_runtime": True},
            "row135": {"word_alignment_pass": True, "phoneme_alignment_pass": False, "row_complete": False, "alignment": {}},
            "row136": {"fixture_runtime_pass": True, "production_input_pass": False, "row_complete": False, "fixture": {}},
            "row138": {"row_complete": False, "output": {}},
            "boundaries": {
                "mms_grapheme_is_phoneme_authority": False,
                "fixture_is_production_alignment": False,
                "automated_metrics_are_human_playback": False,
                "production_ready": False,
                "aws_or_ec2_used": False,
                "mask_or_wave71_touched": False,
            },
        }
        for key in base["boundaries"]:
            invalid = copy.deepcopy(base)
            invalid["boundaries"][key] = True
            with self.assertRaises(MODULE.EvaluationError):
                MODULE.verify_runtime_manifest(invalid)

    def test_source_contains_required_blocked_gates(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"phoneme_authority_pass": False', source)
        self.assertIn('"independent_playback_review_pass": False', source)
        self.assertIn('"production_scene_authority_pass": False', source)
        self.assertIn('"row_complete": False', source)

    def test_evaluate_enforces_wer_speaker_and_clipping_thresholds_end_to_end(self) -> None:
        durable = ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/w64_alignment_viseme_spatial_20260715T235027-0500"
        source_audio = ROOT / "Plan/Instructions/Operations/Pulled_Back_Artifacts/w64_qwen3_tts_base_icl_clone_20260715T195516-0500/qwen3_tts_base_icl_clone_seed12401.wav"
        runner = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_alignment_viseme_spatial.py"
        adapter = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_cv3_eval_calibration.py"

        class FakeWhisper:
            def __init__(self, *_args):
                pass

            def transcribe(self, _path):
                return MODULE.EXPECTED_TEXT

        class FakeSpeaker:
            def __init__(self, *_args):
                pass

            def embedding(self, path):
                return str(path)

            def similarity(self, _left, _right):
                return 0.99

        fake_cv3 = SimpleNamespace(
            WHISPER_SHA256="1" * 64,
            ERES2NET_SHA256="2" * 64,
            require_hash=lambda *_args: None,
            WhisperEvaluator=FakeWhisper,
            SpeakerEvaluator=FakeSpeaker,
            normalized_wer=lambda expected, observed: 0.0 if expected == observed else 1.0,
        )

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            manifest = json.loads((durable / "wave64_alignment_viseme_spatial_runtime_manifest.json").read_text(encoding="utf-8"))
            bindings = {
                "source": source_audio,
                "alignment": durable / "row135_mms_fa_word_grapheme_alignment.json",
                "fixture": durable / "row136_viseme_coarticulation_fixture.json",
                "spatial": durable / "row138_l01_spatial_scene_pcm24_stereo.wav",
            }
            manifest["source"].update(MODULE.bind(bindings["source"], MODULE.EXPECTED_SOURCE_SHA256, "test source"))
            for key, target in (("alignment", manifest["row135"]["alignment"]), ("fixture", manifest["row136"]["fixture"]), ("spatial", manifest["row138"]["output"])):
                artifact = bindings[key]
                target.update({"path": str(artifact.resolve()), "sha256": MODULE.sha256_file(artifact), "bytes": artifact.stat().st_size})
            manifest_path = temporary / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            threshold_path = temporary / "threshold.json"

            def make_args(threshold: float = 0.3, max_wer: float = 0.2, max_clipping: float = 0.0001):
                threshold_path.write_text(json.dumps({"threshold_validation": {"threshold": threshold, "threshold_deployment_allowed_for_chain_specific_evaluation": True}}), encoding="utf-8")
                return SimpleNamespace(
                    manifest=manifest_path,
                    expected_manifest_sha256=MODULE.sha256_file(manifest_path),
                    runner_script=runner,
                    expected_runner_sha256=MODULE.sha256_file(runner),
                    cv3_adapter_script=adapter,
                    expected_cv3_adapter_sha256=MODULE.sha256_file(adapter),
                    speaker_threshold_evidence=threshold_path,
                    expected_speaker_threshold_evidence_sha256=MODULE.sha256_file(threshold_path),
                    cv3_root=temporary / "cv3",
                    whisper_model_dir=temporary / "whisper",
                    transformers_overlay=temporary / "overlay",
                    device="cpu",
                    max_wer=max_wer,
                    max_duration_delta_seconds=0.001,
                    max_clipping_ratio=max_clipping,
                )

            with mock.patch.object(MODULE, "load_module", return_value=fake_cv3):
                passed = MODULE.evaluate(make_args())
                self.assertEqual(MODULE.EXPECTED_MANIFEST_CLASSIFICATION, manifest["classification"])
                self.assertTrue(passed["gates"]["spatial_intelligibility_pass"])
                self.assertTrue(passed["gates"]["spatial_speaker_identity_pass"])
                with self.assertRaises(MODULE.EvaluationError):
                    MODULE.evaluate(make_args(max_wer=-1.0))
                with self.assertRaises(MODULE.EvaluationError):
                    MODULE.evaluate(make_args(max_clipping=-1.0))
                with self.assertRaises(MODULE.EvaluationError):
                    MODULE.evaluate(make_args(threshold=0.999))


if __name__ == "__main__":
    unittest.main()
