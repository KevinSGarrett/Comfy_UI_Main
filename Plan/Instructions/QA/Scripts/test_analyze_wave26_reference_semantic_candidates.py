from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import jsonschema
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "Plan/07_IMPLEMENTATION/scripts"))
import analyze_wave26_reference_semantic_candidates as analyzer
INGEST = ROOT / "Plan/07_IMPLEMENTATION/scripts/ingest_wave26_reference_video.py"
ANALYZE = ROOT / "Plan/07_IMPLEMENTATION/scripts/analyze_wave26_reference_semantic_candidates.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/wave26_reference_semantic_candidates.schema.json"
THRESHOLDS = ROOT / "Plan/10_REGISTRIES/wave26_reference_semantic_candidate_thresholds.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReferenceSemanticCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)
        self.video = self.work / "reference.avi"
        self._write_video(self.video, 12)
        self.ingest = self.work / "ingest"
        result = self._run_ingest(self.video, self.ingest, "all_frames_short_clip")
        self.assertEqual(result.returncode, 0, result.stderr)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_video(self, path: Path, count: int) -> None:
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 6.0, (96, 64))
        self.assertTrue(writer.isOpened())
        first = None
        for index in range(count):
            frame = np.zeros((64, 96, 3), dtype=np.uint8)
            background = 30 if index < 6 else 190
            frame[:] = (background, background // 2, 20)
            cv2.rectangle(frame, (5 + index * 4, 20), (20 + index * 4, 40), (240, 220, 80), -1)
            if index == 0:
                first = frame.copy()
            if index == count - 1 and count > 3:
                frame = first
            writer.write(frame)
        writer.release()

    def _run_ingest(self, video: Path, output: Path, profile: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(INGEST), "--source-video", str(video), "--output-dir", str(output), "--extraction-profile-id", profile, "--audio-present", "false"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )

    def _run(self, output: Path, ingest: Path | None = None, thresholds: Path | None = None) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(ANALYZE), "--ingest-dir", str(ingest or self.ingest), "--output", str(output), "--root", str(ROOT)]
        if thresholds is not None:
            command += ["--thresholds", str(thresholds)]
        return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)

    def _update_frame_manifest_binding(self) -> None:
        evidence_path = self.ingest / "wave26_reference_video_ingest_evidence.json"
        evidence = json.loads(evidence_path.read_text())
        manifest = self.ingest / evidence["artifacts"]["frame_manifest_path"]
        evidence["artifacts"]["frame_manifest_sha256"] = sha256(manifest)
        evidence["artifacts"]["frame_manifest_bytes"] = manifest.stat().st_size
        evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def test_candidate_analysis_passes_schema_and_keeps_nonclaims_false(self) -> None:
        output = self.work / "candidates.json"
        result = self._run(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(output.read_text())
        jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text())).validate(payload)
        self.assertTrue(payload["claims"]["motion_peak_sampling_ready"])
        self.assertTrue(payload["claims"]["shot_boundary_sampling_ready"])
        self.assertTrue(payload["claims"]["loop_candidate_sampling_ready"])
        for key, value in payload["claims"].items():
            if not key.endswith("sampling_ready") or key == "contact_phase_sampling_ready":
                self.assertFalse(value)

    def test_expected_motion_shot_and_loop_candidates_are_detected(self) -> None:
        output = self.work / "candidates.json"
        self.assertEqual(self._run(output).returncode, 0)
        payload = json.loads(output.read_text())
        self.assertGreater(len(payload["motion_peak_candidates"]), 0)
        self.assertGreater(len(payload["shot_boundary_candidates"]), 0)
        self.assertGreater(len(payload["loop_candidates"]), 0)

    def test_repeated_analysis_is_byte_deterministic(self) -> None:
        first, second = self.work / "first.json", self.work / "second.json"
        self.assertEqual(self._run(first).returncode, 0)
        self.assertEqual(self._run(second).returncode, 0)
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_tampered_frame_is_rejected_without_output(self) -> None:
        (self.ingest / "frames/frame_000005.png").write_bytes(b"tampered")
        output = self.work / "candidates.json"
        result = self._run(output)
        self.assertEqual(result.returncode, 2)
        self.assertIn("frame PNG binding failed", result.stderr)
        self.assertFalse(output.exists())

    def test_tampered_reference_manifest_is_rejected(self) -> None:
        manifest = self.ingest / "reference_video_manifest.json"
        manifest.write_text(manifest.read_text().replace("all_frames_short_clip", "sample_every_n"), encoding="utf-8")
        result = self._run(self.work / "candidates.json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("artifact binding failed", result.stderr)

    def test_sampled_ingest_is_rejected_as_incomplete_timeline(self) -> None:
        sampled = self.work / "sampled"
        result = self._run_ingest(self.video, sampled, "sample_every_n")
        self.assertEqual(result.returncode, 0, result.stderr)
        analyzed = self._run(self.work / "candidates.json", ingest=sampled)
        self.assertEqual(analyzed.returncode, 2)
        self.assertIn("all_frames_short_clip", analyzed.stderr)

    def test_nonfinite_threshold_is_rejected(self) -> None:
        threshold = self.work / "thresholds.json"
        threshold.write_text(THRESHOLDS.read_text().replace("0.002", "NaN", 1), encoding="utf-8")
        result = self._run(self.work / "candidates.json", thresholds=threshold)
        self.assertEqual(result.returncode, 2)
        self.assertIn("non-finite", result.stderr)

    def test_existing_output_is_preserved(self) -> None:
        output = self.work / "candidates.json"
        output.write_text("keep", encoding="utf-8")
        result = self._run(output)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(output.read_text(), "keep")

    def test_reordered_frame_manifest_is_rejected_after_rebinding(self) -> None:
        manifest = self.ingest / "frame_manifest.jsonl"
        lines = manifest.read_text().splitlines()
        lines[1], lines[2] = lines[2], lines[1]
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self._update_frame_manifest_binding()
        result = self._run(self.work / "candidates.json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("contiguous and ordered", result.stderr)

    def test_two_frame_ingest_is_rejected_as_nonsemantic(self) -> None:
        short_video = self.work / "short.avi"
        self._write_video(short_video, 2)
        short_ingest = self.work / "short-ingest"
        result = self._run_ingest(short_video, short_ingest, "all_frames_short_clip")
        self.assertEqual(result.returncode, 0, result.stderr)
        analyzed = self._run(self.work / "candidates.json", ingest=short_ingest)
        self.assertEqual(analyzed.returncode, 2)
        self.assertIn("at least 3", analyzed.stderr)

    def test_motion_and_shot_reason_code_branches(self) -> None:
        thresholds = json.loads(THRESHOLDS.read_text())
        records = [{"timestamp_seconds": float(index)} for index in range(5)]
        metrics = [
            {"to_frame": 1, "timestamp_seconds": 1.0, "flow_p95_diagonal_ratio": 0.003, "direction_change_degrees": None, "luma_mae_percent": 23.0, "histogram_bhattacharyya": 0.1},
            {"to_frame": 2, "timestamp_seconds": 2.0, "flow_p95_diagonal_ratio": 0.005, "direction_change_degrees": 70.0, "luma_mae_percent": 1.0, "histogram_bhattacharyya": 0.4},
            {"to_frame": 3, "timestamp_seconds": 3.0, "flow_p95_diagonal_ratio": 0.001, "direction_change_degrees": 90.0, "luma_mae_percent": 23.0, "histogram_bhattacharyya": 0.4},
            {"to_frame": 4, "timestamp_seconds": 4.0, "flow_p95_diagonal_ratio": 0.004, "direction_change_degrees": None, "luma_mae_percent": 1.0, "histogram_bhattacharyya": 0.1},
        ]
        histogram = np.zeros((64, 1), dtype=np.float32)
        histogram[0, 0] = 1.0
        descriptor = np.zeros((32, 32), dtype=np.float32)
        motion, shots, _ = analyzer._candidates(records, metrics, [histogram] * 5, [descriptor] * 5, thresholds)
        self.assertEqual({item["reason"] for item in motion}, {"local_motion_peak", "direction_change", "local_motion_peak_and_direction_change"})
        self.assertEqual({item["reason"] for item in shots}, {"luma_threshold", "histogram_threshold", "luma_and_histogram_threshold"})

    def test_loop_candidates_are_ranked_and_capped(self) -> None:
        thresholds = json.loads(THRESHOLDS.read_text())
        thresholds["loop_candidate"]["maximum_candidates"] = 2
        records = [{"timestamp_seconds": float(index)} for index in range(5)]
        metrics = [{"to_frame": index, "timestamp_seconds": float(index), "flow_p95_diagonal_ratio": 0.0, "direction_change_degrees": None, "luma_mae_percent": 0.0, "histogram_bhattacharyya": 0.0} for index in range(1, 5)]
        histogram = np.zeros((64, 1), dtype=np.float32)
        histogram[0, 0] = 1.0
        descriptor = np.zeros((32, 32), dtype=np.float32)
        _, _, loops = analyzer._candidates(records, metrics, [histogram] * 5, [descriptor] * 5, thresholds)
        self.assertEqual(len(loops), 2)
        self.assertEqual((loops[0]["start_frame"], loops[0]["end_frame"]), (0, 4))
        self.assertIn("endpoint_descriptor_luma_mae_percent", loops[0])


if __name__ == "__main__":
    unittest.main()
