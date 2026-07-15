from __future__ import annotations

import importlib.util
import json
import math
import tempfile
import unittest
import wave
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_model_backed_playback_review.py"
SPEC = importlib.util.spec_from_file_location("produce_wave64_model_backed_playback_review", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _registry() -> dict:
    return {
        "calibrated_emotion_labels": ["angry", "happy", "sad"],
        "calibrated_intensity_labels": [],
        "thresholds": {
            "wer_pass_max": 0.2,
            "exact_content_required": True,
            "clipped_sample_ratio_block_min": 0.001,
            "silence_ratio_block_min": 0.65,
            "dnsmos_ovrl_reference_min": 1.9,
            "dnsmos_ovrl_reference_median": 2.8,
            "dnsmos_ovrl_reference_max": 3.3,
        },
    }


def _audio_metrics(**overrides: float) -> dict:
    result = {
        "clipped_sample_ratio": 0.0,
        "silence_sample_ratio": 0.1,
        "max_transition_jump_db": 5.0,
    }
    result.update(overrides)
    return result


def _emotion(**overrides: object) -> dict:
    result = {
        "target_emotion": "happy",
        "target_intensity": "",
        "predicted_label": "happy",
        "predicted_score": 0.9,
    }
    result.update(overrides)
    return result


class ModelBackedPlaybackProducerTests(unittest.TestCase):
    def test_model_bundle_digest_is_order_independent(self) -> None:
        left = {"b": {"sha256": "b" * 64}, "a": {"sha256": "a" * 64}}
        right = {"a": {"sha256": "a" * 64}, "b": {"sha256": "b" * 64}}
        self.assertEqual(MODULE.model_bundle_sha256(left), MODULE.model_bundle_sha256(right))

    def test_exact_supported_line_is_proof_eligible(self) -> None:
        result = MODULE.build_decision(
            expected_text="We move on the beat.",
            observed_text="We move on the beat.",
            dnsmos={"OVRL": 3.1},
            emotion=_emotion(),
            audio_metrics=_audio_metrics(),
            registry=_registry(),
        )
        self.assertTrue(result["proof_eligible"])
        self.assertEqual(result["defects"], [])
        self.assertEqual(set(result["category_scores"]), MODULE.REQUIRED_CATEGORIES)
        self.assertTrue(all(value is not None for value in result["category_scores"].values()))

    def test_unsupported_style_hard_abstains_without_placeholder_score(self) -> None:
        result = MODULE.build_decision(
            expected_text="We move on the beat.",
            observed_text="We move on the beat.",
            dnsmos={"OVRL": 3.1},
            emotion=_emotion(target_emotion="focused", target_intensity="controlled", predicted_label="neutral"),
            audio_metrics=_audio_metrics(),
            registry=_registry(),
        )
        self.assertFalse(result["proof_eligible"])
        self.assertIsNone(result["category_scores"]["stylistic_fit"])
        self.assertEqual(
            result["unsupported_required_categories"],
            ["stylistic_fit.target_emotion", "stylistic_fit.target_intensity"],
        )

    def test_beat_to_b_is_critical_content_mismatch(self) -> None:
        result = MODULE.build_decision(
            expected_text="We hold the frame steady and move on the beat.",
            observed_text="We hold the frame steady and move on the B.",
            dnsmos={"OVRL": 3.058596703101282},
            emotion=_emotion(),
            audio_metrics=_audio_metrics(),
            registry=_registry(),
        )
        self.assertTrue(math.isclose(result["normalized_wer"], 0.1))
        self.assertIn("CRITICAL_CONTENT_MISMATCH", [defect["code"] for defect in result["defects"]])
        self.assertEqual(result["category_scores"]["content_correctness"], 0.0)

    def test_clipping_probe_is_blocking(self) -> None:
        result = MODULE.build_decision(
            expected_text="Clean line.",
            observed_text="Clean line.",
            dnsmos={"OVRL": 3.0},
            emotion=_emotion(),
            audio_metrics=_audio_metrics(clipped_sample_ratio=0.01),
            registry=_registry(),
        )
        self.assertIn("MAJOR_CLIPPING", [defect["code"] for defect in result["defects"]])
        self.assertEqual(result["category_scores"]["technical_consistency"], 0.0)

    def test_transition_metric_is_observational_without_calibrated_defect_rule(self) -> None:
        result = MODULE.build_decision(
            expected_text="Clean line.",
            observed_text="Clean line.",
            dnsmos={"OVRL": 3.0},
            emotion=_emotion(),
            audio_metrics=_audio_metrics(max_transition_jump_db=180.0),
            registry=_registry(),
        )
        self.assertNotIn("LOUDNESS_JUMP_UNFIT", [defect["code"] for defect in result["defects"]])
        self.assertEqual(result["category_scores"]["technical_consistency"], 5.0)

    def test_pcm_clipping_is_measured_from_audio_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_path = Path(temp_dir) / "clipped.wav"
            samples = [32767, -32768] * 800
            with wave.open(str(wav_path), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(16000)
                output.writeframes(b"".join(int(value).to_bytes(2, "little", signed=True) for value in samples))
            metrics = MODULE.read_audio_metrics(wav_path)
            self.assertGreater(metrics["clipped_sample_ratio"], 0.99)
            self.assertEqual(metrics["frames"], len(samples))

    def test_declared_lineage_binding_checks_bytes_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "contract.json"
            path.write_text('{"contract":true}\n', encoding="utf-8")
            record = {"path": str(path), "sha256": MODULE.sha256(path), "bytes": path.stat().st_size}
            self.assertEqual(MODULE.require_declared_binding(record, "contract")["sha256"], record["sha256"])
            record["bytes"] += 1
            with self.assertRaisesRegex(ValueError, "byte count mismatch"):
                MODULE.require_declared_binding(record, "contract")

    def test_production_registry_identity_is_not_a_production_authority(self) -> None:
        producer = json.loads(
            (REPO_ROOT / "Plan/10_REGISTRIES/wave64_model_backed_playback_producer_registry.json").read_text(
                encoding="utf-8"
            )
        )
        authority = json.loads(
            (REPO_ROOT / "Plan/10_REGISTRIES/wave64_strict_audio_review_authority_registry.json").read_text(
                encoding="utf-8"
            )
        )
        identity = producer["producer_identity"]
        self.assertEqual(authority["playback_review_allowlist"].count(identity), 1)
        self.assertFalse(
            any(
                record.get("authority_id") == identity["authority_id"]
                for record in authority["production_review_authorities"]
            )
        )
        self.assertNotIn(identity["model_sha256"], authority["production_review_bundle_allowlist"])


if __name__ == "__main__":
    unittest.main()
