#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[4]
COMPILER = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_canonical_video_timeline.py"
TIMELINE_SCHEMA = ROOT / "Plan/08_SCHEMAS/canonical_video_timeline.schema.json"
CLOCK_SPAN_SCHEMA = ROOT / "Plan/08_SCHEMAS/canonical_media_clock_span.schema.json"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fixed_packet(*, frame_count: int = 24, fps_num: int = 24, fps_den: int = 1) -> dict:
    sample_rate = 48000
    frames = []
    for idx in range(frame_count):
        frames.append(
            {
                "frame_index": idx,
                "source_pts": idx * fps_den,
                "duration_pts": fps_den,
            }
        )
    end_sample = int(round((frame_count * fps_den / float(fps_num)) * sample_rate))
    return {
        "schema_version": "1.0.0",
        "timeline_id": "row084_fixed_fixture",
        "revision": "r001",
        "source_binding": {
            "video_sha256": "a" * 64,
            "stream_index": 0,
            "container_sha256": None,
        },
        "clock_span": {
            "clock_id": "clock_fixed",
            "timebase_numerator": fps_den,
            "timebase_denominator": fps_num,
            "start_pts": 0,
            "end_pts_exclusive": frame_count * fps_den,
            "start_frame": 0,
            "end_frame_exclusive": frame_count,
            "start_sample": 0,
            "end_sample_exclusive": end_sample,
            "frame_rate_numerator": fps_num,
            "frame_rate_denominator": fps_den,
            "sample_rate_hz": sample_rate,
            "rounding_policy": "nearest_ties_to_even",
        },
        "frame_rate_mode": "fixed" if fps_den == 1 else "fractional",
        "frame_table": frames,
        "vfr_segments": [],
        "cut_epochs": [],
        "missing_frames": [],
        "camera_motion_policy": "not_evaluated",
        "tolerances": {
            "max_frame_residual": 0.0,
            "max_sample_residual": 1.0,
            "max_seconds_residual": 1.0 / sample_rate,
        },
        "dependency_authority": {"row067_complete": False},
        "runtime_authority": {
            "mux_replay_proof_present": False,
            "combined_visual_review_present": False,
            "fixed_vfr_benchmark_pass": False,
        },
        "provenance": {"fixture": "row084_unit"},
    }


class Row084CanonicalVideoTimelineCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.timeline_validator = Draft202012Validator(json.loads(TIMELINE_SCHEMA.read_text(encoding="utf-8")))
        self.clock_span_schema = json.loads(CLOCK_SPAN_SCHEMA.read_text(encoding="utf-8"))

    def _run_compile(self, packet: dict, *, expect_ok: bool) -> tuple[subprocess.CompletedProcess[str], dict | None]:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path = tmpdir / "timeline_packet.json"
            output_path = tmpdir / "timeline_receipt.json"
            _write_json(packet_path, packet)
            completed = subprocess.run(
                [sys.executable, str(COMPILER), "--input", str(packet_path), "--output", str(output_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            if expect_ok:
                self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
                receipt = json.loads(output_path.read_text(encoding="utf-8"))
                return completed, receipt
            self.assertNotEqual(completed.returncode, 0, completed.stdout)
            return completed, None

    def test_fixed_rate_roundtrip_compiles_and_holds_completion(self) -> None:
        packet = _fixed_packet(frame_count=24, fps_num=24, fps_den=1)
        _, receipt = self._run_compile(packet, expect_ok=True)
        assert receipt is not None
        self.timeline_validator.validate(receipt)
        self.assertFalse(receipt["row_complete"])
        self.assertFalse(receipt["production_completion_allowed"])
        self.assertEqual(receipt["authority_ceiling"], "candidate")
        self.assertTrue(receipt["roundtrip_evidence"]["within_tolerance"])
        self.assertEqual(receipt["roundtrip_evidence"]["checked_frame_count"], 24)

    def test_fractional_ntsc_roundtrip_compiles(self) -> None:
        packet = _fixed_packet(frame_count=10, fps_num=24000, fps_den=1001)
        _, receipt = self._run_compile(packet, expect_ok=True)
        assert receipt is not None
        self.assertEqual(receipt["frame_rate_mode"], "fractional")
        self.assertTrue(receipt["roundtrip_evidence"]["within_tolerance"])

    def test_reversed_pts_span_is_rejected(self) -> None:
        packet = _fixed_packet()
        packet["clock_span"]["start_pts"] = packet["clock_span"]["end_pts_exclusive"]
        completed, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("start_pts must precede end_pts_exclusive", completed.stderr + completed.stdout)

    def test_vfr_without_segments_is_rejected(self) -> None:
        packet = _fixed_packet()
        packet["frame_rate_mode"] = "vfr"
        packet["vfr_segments"] = []
        completed, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("vfr frame_rate_mode requires a non-empty vfr_segments map", completed.stderr + completed.stdout)

    def test_unsupported_sample_rate_is_rejected(self) -> None:
        packet = _fixed_packet()
        packet["clock_span"]["sample_rate_hz"] = 44100
        completed, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("sample_rate_hz unsupported", completed.stderr + completed.stdout)

    def test_non_monotonic_pts_is_rejected(self) -> None:
        packet = _fixed_packet(frame_count=3)
        packet["frame_table"][0]["source_pts"] = 10
        packet["frame_table"][1]["source_pts"] = 5
        completed, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("monotonic", completed.stderr + completed.stdout)

    def test_clock_span_schema_requires_rates_and_endpoints(self) -> None:
        required = set(self.clock_span_schema["required"])
        self.assertTrue(
            {
                "start_frame",
                "end_frame_exclusive",
                "start_sample",
                "end_sample_exclusive",
                "frame_rate",
                "sample_rate_hz",
            }.issubset(required)
        )
        frame_rate_schema = self.clock_span_schema["properties"]["frame_rate"]
        sample_rate_schema = self.clock_span_schema["properties"]["sample_rate_hz"]
        self.assertEqual(frame_rate_schema["type"], "number")
        self.assertEqual(sample_rate_schema["type"], "integer")
        self.assertNotEqual(frame_rate_schema.get("type"), ["number", "null"])
        self.assertNotEqual(sample_rate_schema.get("type"), ["integer", "null"])
        # Validate rate/endpoint field schemas without resolving external provenance $refs.
        self.assertTrue(list(Draft202012Validator(frame_rate_schema).iter_errors(None)))
        self.assertTrue(list(Draft202012Validator(sample_rate_schema).iter_errors(None)))
        self.assertFalse(list(Draft202012Validator(frame_rate_schema).iter_errors(24.0)))
        self.assertFalse(list(Draft202012Validator(sample_rate_schema).iter_errors(48000)))

    def test_dependency_hold_keeps_candidate_ceiling(self) -> None:
        packet = _fixed_packet()
        packet["dependency_authority"]["row067_complete"] = False
        packet["runtime_authority"] = {
            "mux_replay_proof_present": True,
            "combined_visual_review_present": True,
            "fixed_vfr_benchmark_pass": True,
        }
        _, receipt = self._run_compile(packet, expect_ok=True)
        assert receipt is not None
        self.assertEqual(receipt["authority_ceiling"], "candidate")
        self.assertFalse(receipt["production_completion_allowed"])
        self.assertFalse(receipt["row_complete"])


if __name__ == "__main__":
    unittest.main()
