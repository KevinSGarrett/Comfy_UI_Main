#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/audio_clip_preparation_manifest.schema.json"
VALIDATOR_PATH = (
    ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_audio_clip_preparation_manifest.py"
)


def _load_validator_module():
    spec = importlib.util.spec_from_file_location(
        "validate_wave64_audio_clip_preparation_manifest", VALIDATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load validator from {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


VALIDATOR = _load_validator_module()


def _sha(n: int = 1) -> str:
    return f"{n:064x}"


def _base_manifest() -> dict:
    source_hash = _sha(1)
    pcm_hash = _sha(2)
    target_hash = _sha(3)
    target_pcm = _sha(4)
    return {
        "schema_version": "1.0",
        "preparation_id": "prep_row093_probe",
        "source": {
            "path": "fixtures/source.wav",
            "sha256": source_hash,
            "canonical_pcm_sha256": pcm_hash,
            "segment_start_sample": 1000,
            "segment_end_sample": 5000,
        },
        "target": {
            "path": "derivatives/prepared.wav",
            "sha256": target_hash,
            "canonical_pcm_sha256": target_pcm,
            "sample_rate_hz": 48000,
            "channels": 2,
        },
        "transforms": [
            {
                "operation": "segment",
                "parameters": {"start": 1000, "end": 5000},
                "implementation_revision": "row093-v1",
                "tool_identity": "wave64_clip_preparer",
                "input_sha256": pcm_hash,
                "output_sha256": _sha(5),
                "replay_digest_sha256": _sha(6),
            },
            {
                "operation": "resample",
                "parameters": {"target_hz": 48000},
                "implementation_revision": "row093-v1",
                "tool_identity": "wave64_clip_preparer",
                "input_sha256": _sha(5),
                "output_sha256": target_pcm,
                "replay_digest_sha256": _sha(7),
            },
        ],
        "anchor": {
            "source_sample": 1200,
            "target_sample": 200,
            "shift_samples": 0,
            "within_tolerance": True,
            "tolerance_samples": 2,
        },
        "tail": {
            "source_decay_end_sample": 4800,
            "target_decay_end_sample": 3800,
            "tail_preserved": True,
            "lost_tail_samples": 0,
        },
        "phase": {
            "polarity_inverted": False,
            "inter_channel_phase_error_degrees": 0.0,
            "within_tolerance": True,
            "tolerance_degrees": 5.0,
        },
        "validation": {"decision": "PASS", "defects": []},
    }


class Row093AudioClipPreparationManifestSchemaStrictTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = VALIDATOR.load_json(SCHEMA_PATH)

    def _errors(self, payload: dict) -> list[str]:
        return VALIDATOR.validate_manifest(payload, schema=self.schema)

    def test_valid_manifest_passes(self) -> None:
        self.assertEqual(self._errors(_base_manifest()), [])

    def test_empty_transform_chain_fails_closed(self) -> None:
        payload = _base_manifest()
        payload["transforms"] = []
        payload["validation"] = {
            "decision": "FAIL",
            "defects": [{"code": "EMPTY_TRANSFORMS", "message": "empty"}],
        }
        errors = self._errors(payload)
        self.assertTrue(any("transforms" in message.lower() or "nonempty" in message.lower() or "minItems" in message or "too short" in message.lower() for message in errors))

    def test_source_segment_reversed_fails_closed(self) -> None:
        payload = _base_manifest()
        payload["source"]["segment_start_sample"] = 5000
        payload["source"]["segment_end_sample"] = 1000
        payload["validation"] = {
            "decision": "FAIL",
            "defects": [{"code": "SEGMENT_REVERSED", "message": "reversed"}],
        }
        errors = self._errors(payload)
        self.assertTrue(
            any("segment_end_sample must be greater than" in message for message in errors)
        )

    def test_anchor_outside_tolerance_with_pass_fails_closed(self) -> None:
        payload = _base_manifest()
        payload["anchor"]["within_tolerance"] = False
        errors = self._errors(payload)
        self.assertGreaterEqual(len(errors), 1)

    def test_natural_tail_not_preserved_with_pass_fails_closed(self) -> None:
        payload = _base_manifest()
        payload["tail"]["tail_preserved"] = False
        errors = self._errors(payload)
        self.assertGreaterEqual(len(errors), 1)

    def test_negative_tail_samples_fails_closed(self) -> None:
        payload = _base_manifest()
        payload["tail"]["lost_tail_samples"] = -1
        payload["validation"] = {
            "decision": "FAIL",
            "defects": [{"code": "NEGATIVE_TAIL", "message": "negative"}],
        }
        errors = self._errors(payload)
        self.assertGreaterEqual(len(errors), 1)

    def test_arbitrary_validation_decision_fails_closed(self) -> None:
        payload = _base_manifest()
        payload["validation"]["decision"] = "SHIP_IT"
        errors = self._errors(payload)
        self.assertGreaterEqual(len(errors), 1)

    def test_phase_preservation_not_recorded_fails_closed(self) -> None:
        payload = _base_manifest()
        del payload["phase"]
        errors = self._errors(payload)
        self.assertTrue(any("phase" in message.lower() for message in errors))

    def test_adversarial_matrix_closes_prior_false_open_cases(self) -> None:
        cases = {
            "empty_transform_chain": self.test_empty_transform_chain_fails_closed,
            "source_segment_reversed": self.test_source_segment_reversed_fails_closed,
            "anchor_explicitly_outside_tolerance": self.test_anchor_outside_tolerance_with_pass_fails_closed,
            "natural_tail_explicitly_not_preserved": self.test_natural_tail_not_preserved_with_pass_fails_closed,
            "negative_tail_samples": self.test_negative_tail_samples_fails_closed,
            "arbitrary_validation_decision": self.test_arbitrary_validation_decision_fails_closed,
            "phase_preservation_not_recorded": self.test_phase_preservation_not_recorded_fails_closed,
        }
        for name, case in cases.items():
            with self.subTest(case=name):
                case()


if __name__ == "__main__":
    unittest.main()
