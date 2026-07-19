#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = ROOT / "Plan/08_SCHEMAS/visual_audio_event_manifest.schema.json"


def _base_manifest() -> dict:
    return {
        "schema_version": "1.0",
        "manifest_id": "manifest_row091_probe",
        "video_sha256": "a" * 64,
        "timeline": {
            "time_base": "1/24",
            "frame_count": 48,
            "duration_seconds": 2.0,
            "target_sample_rate_hz": 48000,
        },
        "detectors": [{"name": "contact_detector", "revision": "r1"}],
        "events": [
            {
                "event_id": "evt_001",
                "event_type": "footstep",
                "source_owner": "character_1",
                "target_owner": "floor_1",
                "start_frame": 10,
                "anchor_frame": 11,
                "end_frame": 12,
                "anchor_seconds": 0.458333,
                "anchor_sample": 22000,
                "material": "wood",
                "force_band": "medium",
                "expected_layers": ["foley_step"],
                "confidence": 0.85,
                "authority_ceiling": "technical",
                "evidence": [{"kind": "detector", "ref": "contact_detector"}],
            }
        ],
        "coverage": {
            "required_events": 1,
            "covered_events": 1,
            "silent_events": 0,
            "blocked_events": 0,
        },
        "rights_decision_sha256": "c" * 64,
    }


class Row091VisualAudioEventManifestSchemaStrictTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))

    def _errors(self, payload: dict) -> list[str]:
        return sorted(error.message for error in self.validator.iter_errors(payload))

    def test_valid_manifest_passes(self) -> None:
        self.assertEqual(self._errors(_base_manifest()), [])

    def test_regression_probe_fails_closed(self) -> None:
        payload = _base_manifest()
        payload["events"] = []
        payload["detectors"][0]["name"] = None
        payload["detectors"][0]["revision"] = []
        payload["coverage"]["required_events"] = "1"
        payload["coverage"]["covered_events"] = -1
        payload["coverage"]["silent_events"] = None
        payload["coverage"]["blocked_events"] = {"count": 0}
        payload["timeline"]["unexpected"] = True
        errors = self._errors(payload)
        self.assertGreaterEqual(len(errors), 8)


if __name__ == "__main__":
    unittest.main()
