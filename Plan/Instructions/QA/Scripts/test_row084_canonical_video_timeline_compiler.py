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
MUX_PREP_SCHEMA = ROOT / "Plan/08_SCHEMAS/canonical_video_timeline_mux_prep_receipt.schema.json"
HELD_OUT_MATRIX_SCHEMA = (
    ROOT / "Plan/08_SCHEMAS/canonical_video_timeline_held_out_roundtrip_matrix.schema.json"
)
HELD_OUT_MUX_DRY_RUN_SCHEMA = (
    ROOT / "Plan/08_SCHEMAS/canonical_video_timeline_held_out_mux_dry_run_matrix.schema.json"
)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fixed_packet(
    *,
    frame_count: int = 24,
    fps_num: int = 24,
    fps_den: int = 1,
    timeline_id: str = "row084_fixed_fixture",
    video_sha256: str | None = None,
    container_sha256: str | None = None,
    audio_stream_sha256: str | None = None,
    audio_stream_index: int | None = None,
    dependency_complete: bool = False,
    provenance_fixture: str = "row084_unit",
) -> dict:
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
        "timeline_id": timeline_id,
        "revision": "r001",
        "source_binding": {
            "video_sha256": video_sha256 or ("a" * 64),
            "stream_index": 0,
            "container_sha256": container_sha256,
            "audio_stream_sha256": audio_stream_sha256,
            "audio_stream_index": audio_stream_index,
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
        "dependency_authority": {"row067_complete": dependency_complete},
        "runtime_authority": {
            "mux_replay_proof_present": False,
            "combined_visual_review_present": False,
            "fixed_vfr_benchmark_pass": False,
        },
        "provenance": {"fixture": provenance_fixture},
    }


def _vfr_cut_packet(
    *,
    timeline_id: str = "row084_vfr_cut_fixture",
    video_sha256: str | None = None,
    container_sha256: str | None = None,
    audio_stream_sha256: str | None = None,
    audio_stream_index: int | None = None,
    provenance_fixture: str = "row084_vfr_cut_unit",
) -> dict:
    """Two contiguous VFR segments (24fps then 30fps) with a mid-timeline hard cut ledger."""
    sample_rate = 48000
    # 12 frames @ 24fps + 12 frames @ 30fps
    segments = [
        {
            "segment_id": "seg_24",
            "start_frame": 0,
            "end_frame_exclusive": 12,
            "timebase_numerator": 1,
            "timebase_denominator": 24,
        },
        {
            "segment_id": "seg_30",
            "start_frame": 12,
            "end_frame_exclusive": 24,
            "timebase_numerator": 1,
            "timebase_denominator": 30,
        },
    ]
    frames = []
    # Synthetic PTS uses per-segment timebase ticks accumulated across the timeline.
    pts_cursor = 0
    for idx in range(24):
        frames.append(
            {
                "frame_index": idx,
                "source_pts": pts_cursor,
                "duration_pts": 1,
            }
        )
        pts_cursor += 1
    end_seconds = (12 * 1 / 24.0) + (12 * 1 / 30.0)
    end_sample = int(round(end_seconds * sample_rate))
    return {
        "schema_version": "1.0.0",
        "timeline_id": timeline_id,
        "revision": "r002",
        "source_binding": {
            "video_sha256": video_sha256 or ("b" * 64),
            "stream_index": 0,
            "container_sha256": container_sha256,
            "audio_stream_sha256": audio_stream_sha256,
            "audio_stream_index": audio_stream_index,
        },
        "clock_span": {
            "clock_id": "clock_vfr_fixture",
            "timebase_numerator": 1,
            "timebase_denominator": 24,
            "start_pts": 0,
            "end_pts_exclusive": pts_cursor,
            "start_frame": 0,
            "end_frame_exclusive": 24,
            "start_sample": 0,
            "end_sample_exclusive": end_sample,
            "frame_rate_numerator": 24,
            "frame_rate_denominator": 1,
            "sample_rate_hz": sample_rate,
            "rounding_policy": "nearest_ties_to_even",
        },
        "frame_rate_mode": "vfr",
        "frame_table": frames,
        "vfr_segments": segments,
        "cut_epochs": [
            {
                "cut_id": "cut_hard_boundary",
                "frame_index": 12,
                "cut_kind": "hard",
                "algorithm_id": "fixture_ledger_v1",
                "confidence": 1.0,
            }
        ],
        "missing_frames": [],
        "camera_motion_policy": "not_evaluated",
        "tolerances": {
            "max_frame_residual": 0.0,
            "max_sample_residual": 1.0,
            "max_seconds_residual": 1.0 / sample_rate,
        },
        "dependency_authority": {"row067_complete": True},
        "runtime_authority": {
            "mux_replay_proof_present": False,
            "combined_visual_review_present": False,
            "fixed_vfr_benchmark_pass": False,
        },
        "provenance": {"fixture": provenance_fixture},
    }


def _held_out_matrix_packet(*, with_stream_identities: bool = False) -> dict:
    """Held-out partition matrix: fixed, fractional, and VFR cases with distinct bindings."""
    if with_stream_identities:
        fixed_kwargs = {
            "container_sha256": "1" * 64,
            "audio_stream_sha256": "2" * 64,
            "audio_stream_index": 1,
        }
        fractional_kwargs = {
            "container_sha256": "3" * 64,
            "audio_stream_sha256": "4" * 64,
            "audio_stream_index": 1,
        }
        vfr_kwargs = {
            "container_sha256": "5" * 64,
            "audio_stream_sha256": "6" * 64,
            "audio_stream_index": 1,
        }
        matrix_id = "row084_held_out_mux_dry_run_matrix_v1"
        revision = "m002"
        provenance_fixture = "row084_held_out_mux_dry_run_matrix"
    else:
        fixed_kwargs = {}
        fractional_kwargs = {}
        vfr_kwargs = {}
        matrix_id = "row084_held_out_fixed_vfr_roundtrip_matrix_v1"
        revision = "m001"
        provenance_fixture = "row084_held_out_matrix"
    return {
        "schema_version": "1.0.0",
        "matrix_id": matrix_id,
        "revision": revision,
        "cases": [
            {
                "case_id": "held_out_fixed_24",
                "partition": "held_out",
                "timeline_packet": _fixed_packet(
                    frame_count=16,
                    fps_num=24,
                    fps_den=1,
                    timeline_id="row084_held_out_fixed_24",
                    video_sha256="c" * 64,
                    dependency_complete=True,
                    provenance_fixture="row084_held_out_fixed_24",
                    **fixed_kwargs,
                ),
            },
            {
                "case_id": "held_out_fractional_ntsc",
                "partition": "held_out",
                "timeline_packet": _fixed_packet(
                    frame_count=10,
                    fps_num=24000,
                    fps_den=1001,
                    timeline_id="row084_held_out_fractional_ntsc",
                    video_sha256="d" * 64,
                    dependency_complete=True,
                    provenance_fixture="row084_held_out_fractional_ntsc",
                    **fractional_kwargs,
                ),
            },
            {
                "case_id": "held_out_vfr_24_30",
                "partition": "held_out",
                "timeline_packet": _vfr_cut_packet(
                    timeline_id="row084_held_out_vfr_24_30",
                    video_sha256="e" * 64,
                    provenance_fixture="row084_held_out_vfr_24_30",
                    **vfr_kwargs,
                ),
            },
        ],
        "provenance": {"fixture": provenance_fixture},
    }


class Row084CanonicalVideoTimelineCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.timeline_validator = Draft202012Validator(json.loads(TIMELINE_SCHEMA.read_text(encoding="utf-8")))
        self.mux_prep_validator = Draft202012Validator(json.loads(MUX_PREP_SCHEMA.read_text(encoding="utf-8")))
        self.matrix_validator = Draft202012Validator(
            json.loads(HELD_OUT_MATRIX_SCHEMA.read_text(encoding="utf-8"))
        )
        self.mux_dry_run_validator = Draft202012Validator(
            json.loads(HELD_OUT_MUX_DRY_RUN_SCHEMA.read_text(encoding="utf-8"))
        )
        self.clock_span_schema = json.loads(CLOCK_SPAN_SCHEMA.read_text(encoding="utf-8"))

    def _run_compile(
        self,
        packet: dict,
        *,
        expect_ok: bool,
        mode: str = "timeline",
    ) -> tuple[subprocess.completedProcess[str], dict | None]:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path = tmpdir / "timeline_packet.json"
            output_path = tmpdir / "timeline_receipt.json"
            _write_json(packet_path, packet)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(COMPILER),
                    "--mode",
                    mode,
                    "--input",
                    str(packet_path),
                    "--output",
                    str(output_path),
                ],
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

    def test_vfr_segment_map_with_cut_epochs_compiles_technical_partial(self) -> None:
        packet = _vfr_cut_packet()
        _, receipt = self._run_compile(packet, expect_ok=True)
        assert receipt is not None
        self.timeline_validator.validate(receipt)
        self.assertEqual(receipt["frame_rate_mode"], "vfr")
        self.assertEqual(receipt["authority_ceiling"], "technical")
        self.assertEqual(receipt["status"], "technical_partial")
        self.assertFalse(receipt["row_complete"])
        self.assertFalse(receipt["production_completion_allowed"])
        self.assertTrue(receipt["dependency_authority"]["row067_complete"])
        self.assertFalse(receipt["runtime_authority"]["mux_replay_proof_present"])
        self.assertFalse(receipt["runtime_authority"]["fixed_vfr_benchmark_pass"])
        self.assertEqual(receipt["roundtrip_evidence"]["vfr_segment_count"], 2)
        self.assertEqual(receipt["roundtrip_evidence"]["cut_epoch_count"], 1)
        self.assertTrue(receipt["roundtrip_evidence"]["within_tolerance"])
        self.assertEqual(len(receipt["vfr_segments"]), 2)
        self.assertEqual(receipt["cut_epochs"][0]["frame_index"], 12)

    def test_vfr_segment_gap_is_rejected(self) -> None:
        packet = _vfr_cut_packet()
        packet["vfr_segments"][1]["start_frame"] = 13
        completed, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("unmapped frame gap", completed.stderr + completed.stdout)

    def test_cut_epoch_non_monotonic_is_rejected(self) -> None:
        packet = _vfr_cut_packet()
        packet["cut_epochs"] = [
            {
                "cut_id": "cut_b",
                "frame_index": 18,
                "cut_kind": "hard",
                "algorithm_id": "fixture_ledger_v1",
                "confidence": 0.9,
            },
            {
                "cut_id": "cut_a",
                "frame_index": 12,
                "cut_kind": "hard",
                "algorithm_id": "fixture_ledger_v1",
                "confidence": 0.9,
            },
        ]
        completed, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("strictly increasing", completed.stderr + completed.stdout)

    def test_dependency_unlock_raises_technical_partial_ceiling(self) -> None:
        packet = _fixed_packet()
        packet["dependency_authority"]["row067_complete"] = True
        _, receipt = self._run_compile(packet, expect_ok=True)
        assert receipt is not None
        self.assertEqual(receipt["authority_ceiling"], "technical")
        self.assertEqual(receipt["status"], "technical_partial")
        self.assertFalse(receipt["production_completion_allowed"])
        self.assertFalse(receipt["row_complete"])

    def test_mux_prep_scaffold_holds_mux_authority(self) -> None:
        packet = _fixed_packet(dependency_complete=True)
        packet["runtime_authority"]["mux_replay_proof_present"] = True
        _, receipt = self._run_compile(packet, expect_ok=True, mode="mux-prep")
        assert receipt is not None
        self.mux_prep_validator.validate(receipt)
        self.assertEqual(receipt["record_type"], "canonical_video_timeline_mux_prep_receipt")
        self.assertEqual(receipt["status"], "scaffold_hold")
        self.assertFalse(receipt["row_complete"])
        self.assertFalse(receipt["production_completion_allowed"])
        self.assertTrue(receipt["authority"]["scaffold_only"])
        self.assertFalse(receipt["authority"]["mux_replay_executed"])
        self.assertFalse(receipt["authority"]["mux_replay_proof_present"])
        self.assertFalse(receipt["authority"]["mux_authority_granted"])
        self.assertTrue(receipt["authority"]["upstream_mux_replay_claim_ignored"])
        self.assertTrue(receipt["authority"]["dry_run_plan_only"])
        self.assertFalse(receipt["authority"]["stream_identities_bound"])
        self.assertFalse(receipt["mux_prep"]["mux_command_executed"])
        self.assertFalse(receipt["mux_prep"]["mux_command_planned"])
        self.assertIsNone(receipt["mux_prep"]["audio_stream_binding"])
        self.assertIsNone(receipt["mux_prep"]["container_binding"])
        self.assertEqual(receipt["mux_prep"]["planned_frame_count"], 24)
        self.assertEqual(len(receipt["mux_prep_sha256"]), 64)
        self.assertEqual(len(receipt["dry_run_mux_plan_sha256"]), 64)

    def test_mux_prep_binds_audio_and_container_stream_identities(self) -> None:
        packet = _fixed_packet(
            dependency_complete=True,
            container_sha256="f" * 64,
            audio_stream_sha256="e" * 64,
            audio_stream_index=1,
        )
        _, receipt = self._run_compile(packet, expect_ok=True, mode="mux-prep")
        assert receipt is not None
        self.mux_prep_validator.validate(receipt)
        self.assertTrue(receipt["mux_prep"]["stream_identities_bound"])
        self.assertTrue(receipt["mux_prep"]["mux_command_planned"])
        self.assertFalse(receipt["mux_prep"]["mux_command_executed"])
        self.assertEqual(
            receipt["mux_prep"]["audio_stream_binding"],
            f"audio_stream_sha256:{'e' * 64};audio_stream_index:1",
        )
        self.assertEqual(
            receipt["mux_prep"]["container_binding"],
            f"container_sha256:{'f' * 64}",
        )
        self.assertTrue(receipt["authority"]["stream_identities_bound"])
        self.assertFalse(receipt["authority"]["mux_authority_granted"])
        self.assertFalse(receipt["row_complete"])
        # Deterministic dry-run digest across rebuilds (excludes created_at).
        _, receipt_b = self._run_compile(packet, expect_ok=True, mode="mux-prep")
        assert receipt_b is not None
        self.assertEqual(receipt["dry_run_mux_plan_sha256"], receipt_b["dry_run_mux_plan_sha256"])

    def test_held_out_fixed_vfr_roundtrip_matrix_compiles_without_benchmark_authority(self) -> None:
        packet = _held_out_matrix_packet()
        _, receipt = self._run_compile(packet, expect_ok=True, mode="held-out-matrix")
        assert receipt is not None
        self.matrix_validator.validate(receipt)
        self.assertEqual(receipt["record_type"], "canonical_video_timeline_held_out_roundtrip_matrix")
        self.assertEqual(receipt["status"], "fixture_matrix_partial")
        self.assertFalse(receipt["row_complete"])
        self.assertFalse(receipt["production_completion_allowed"])
        self.assertEqual(receipt["summary"]["case_count"], 3)
        self.assertEqual(receipt["summary"]["passed_count"], 3)
        self.assertTrue(receipt["summary"]["all_within_tolerance"])
        self.assertFalse(receipt["summary"]["mux_replay_included"])
        self.assertFalse(receipt["summary"]["runtime_media_decode_invoked"])
        self.assertFalse(receipt["summary"]["benchmark_authority_granted"])
        self.assertFalse(receipt["authority"]["fixed_vfr_benchmark_pass"])
        self.assertFalse(receipt["authority"]["mux_replay_proof_present"])
        modes = set(receipt["summary"]["modes_covered"])
        self.assertTrue({"fixed", "fractional", "vfr"}.issubset(modes) or {"fixed", "vfr"}.issubset(modes))
        self.assertIn("fractional", modes)
        self.assertIn("vfr", modes)
        self.assertTrue(all(case["partition"] == "held_out" for case in receipt["cases"]))
        self.assertTrue(all(case["within_tolerance"] for case in receipt["cases"]))
        self.assertTrue(all(case["row_complete"] is False for case in receipt["cases"]))

    def test_held_out_matrix_without_vfr_is_rejected(self) -> None:
        packet = _held_out_matrix_packet()
        packet["cases"] = packet["cases"][:2]  # fixed + fractional only
        completed, _ = self._run_compile(packet, expect_ok=False, mode="held-out-matrix")
        self.assertIn("requires at least one vfr case", completed.stderr + completed.stdout)

    def test_held_out_matrix_rejects_non_held_out_partition(self) -> None:
        packet = _held_out_matrix_packet()
        packet["cases"][0]["partition"] = "calibration"
        completed, _ = self._run_compile(packet, expect_ok=False, mode="held-out-matrix")
        self.assertIn("partition must equal held_out", completed.stderr + completed.stdout)

    def test_held_out_mux_dry_run_binds_stream_identities_and_hashes(self) -> None:
        packet = _held_out_matrix_packet(with_stream_identities=True)
        _, receipt = self._run_compile(packet, expect_ok=True, mode="held-out-mux-dry-run")
        assert receipt is not None
        self.mux_dry_run_validator.validate(receipt)
        self.assertEqual(
            receipt["record_type"], "canonical_video_timeline_held_out_mux_dry_run_matrix"
        )
        self.assertEqual(receipt["status"], "fixture_mux_dry_run_partial")
        self.assertFalse(receipt["row_complete"])
        self.assertFalse(receipt["production_completion_allowed"])
        self.assertTrue(receipt["summary"]["stream_identities_bound"])
        self.assertTrue(receipt["summary"]["dry_run_mux_hash_check_passed"])
        self.assertFalse(receipt["summary"]["mux_replay_included"])
        self.assertFalse(receipt["summary"]["visual_review_authority_granted"])
        self.assertFalse(receipt["authority"]["mux_replay_proof_present"])
        self.assertFalse(receipt["authority"]["combined_visual_review_present"])
        self.assertTrue(receipt["authority"]["dry_run_plan_only"])
        self.assertEqual(receipt["summary"]["case_count"], 3)
        digests = {case["dry_run_mux_plan_sha256"] for case in receipt["cases"]}
        self.assertEqual(len(digests), 3)
        self.assertTrue(all(case["stream_identities_bound"] for case in receipt["cases"]))
        self.assertTrue(all(case["mux_command_planned"] for case in receipt["cases"]))
        self.assertTrue(all(case["mux_command_executed"] is False for case in receipt["cases"]))
        self.assertTrue(all(case["dry_run_hash_deterministic"] for case in receipt["cases"]))
        self.assertTrue(all(case["row_complete"] is False for case in receipt["cases"]))
        # Rebuild proves deterministic per-case dry-run digests.
        _, receipt_b = self._run_compile(packet, expect_ok=True, mode="held-out-mux-dry-run")
        assert receipt_b is not None
        by_id_a = {case["case_id"]: case["dry_run_mux_plan_sha256"] for case in receipt["cases"]}
        by_id_b = {case["case_id"]: case["dry_run_mux_plan_sha256"] for case in receipt_b["cases"]}
        self.assertEqual(by_id_a, by_id_b)

    def test_held_out_mux_dry_run_rejects_missing_stream_identities(self) -> None:
        packet = _held_out_matrix_packet(with_stream_identities=False)
        completed, _ = self._run_compile(packet, expect_ok=False, mode="held-out-mux-dry-run")
        combined = completed.stderr + completed.stdout
        self.assertIn("mux dry-run requires source_binding.audio_stream_sha256", combined)


if __name__ == "__main__":
    unittest.main()
