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
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/analyze_wave27_frame_continuity.py"
METRICS_SCHEMA = ROOT / "Plan/08_SCHEMAS/wave27_frame_continuity_metrics.schema.json"
sys.path.insert(0, str(ROOT / "Plan/07_IMPLEMENTATION/scripts"))
from prepare_wave27_strict_visual_review_packet import _parse_strict_evidence_payload


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sequence_sha(frames: list[dict]) -> str:
    payload = [
        {
            "frame_index": item["frame_index"],
            "time_seconds": float(item["time_seconds"]),
            "artifact_path": item["artifact_path"],
            "artifact_sha256": item["artifact_sha256"],
            "artifact_bytes": item["artifact_bytes"],
        }
        for item in frames
    ]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


class FrameContinuityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)
        self.base = np.zeros((96, 128, 3), dtype=np.uint8)
        cv2.rectangle(self.base, (12, 10), (90, 72), (70, 180, 230), -1)
        cv2.circle(self.base, (80, 50), 18, (240, 40, 120), -1)
        cv2.line(self.base, (0, 90), (127, 4), (255, 255, 255), 2)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def manifest(self, images: list[np.ndarray], static: bool = True, extension: str = "png") -> Path:
        frames = []
        for index, image in enumerate(images):
            path = self.work / f"frame_{index:03d}.{extension}"
            self.assertTrue(cv2.imwrite(str(path), image))
            camera = {"lens": "35mm"}
            if static:
                camera["temporal_motion_mode"] = "static"
            frames.append(
                {
                    "frame_index": index,
                    "time_seconds": index / 12.0,
                    "source_route": "unit",
                    "engine_name": "unit",
                    "shot_id": "shot-unit",
                    "visible_characters": ["subject"],
                    "camera_state": camera,
                    "qa_scores": {},
                    "repair_status": "none",
                    "artifact_path": path.name,
                    "artifact_sha256": sha256(path),
                    "artifact_bytes": path.stat().st_size,
                }
            )
        payload = {
            "schema_name": "wave27_frame_manifest",
            "manifest_version": 1,
            "frame_count": len(frames),
            "frames": frames,
            "sequence_sha256": sequence_sha(frames),
        }
        path = self.work / "manifest.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path

    def run_tool(self, manifest: Path, output: Path, thresholds: Path | None = None) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(SCRIPT), "--manifest", str(manifest), "--output-dir", str(output), "--root", str(ROOT)]
        if thresholds is not None:
            command += ["--thresholds", str(thresholds)]
        return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)

    def test_identical_static_frames_pass_bounded_categories(self) -> None:
        output = self.work / "out"
        result = self.run_tool(self.manifest([self.base, self.base.copy()]), output)
        self.assertEqual(result.returncode, 0, result.stderr)
        for category in ("motion_analysis", "object_background_camera_analysis"):
            evidence_path = output / f"{category}.json"
            evidence = json.loads(evidence_path.read_text())
            self.assertEqual(set(evidence), {"evidence_type", "sequence_sha256", "result", "notes"})
            self.assertEqual(evidence["result"], "pass")
            parsed = _parse_strict_evidence_payload(evidence_path, category, evidence["sequence_sha256"])
            self.assertEqual(parsed, ("pass", True, True, True))
        metrics = json.loads((output / "temporal_continuity_metrics.json").read_text())
        jsonschema.Draft202012Validator(json.loads(METRICS_SCHEMA.read_text())).validate(metrics)
        self.assertTrue(all(value is False for value in metrics["non_claims"].values()))

    def test_repeated_analysis_is_byte_deterministic(self) -> None:
        manifest = self.manifest([self.base, self.base.copy()])
        first, second = self.work / "first", self.work / "second"
        self.assertEqual(self.run_tool(manifest, first).returncode, 0)
        self.assertEqual(self.run_tool(manifest, second).returncode, 0)
        for name in ("temporal_continuity_metrics.json", "motion_analysis.json", "object_background_camera_analysis.json"):
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())

    def test_jpeg_decode_and_analysis_are_byte_deterministic(self) -> None:
        manifest = self.manifest([self.base, self.base.copy()], extension="jpg")
        first, second = self.work / "jpeg-first", self.work / "jpeg-second"
        self.assertEqual(self.run_tool(manifest, first).returncode, 0)
        self.assertEqual(self.run_tool(manifest, second).returncode, 0)
        for name in ("temporal_continuity_metrics.json", "motion_analysis.json", "object_background_camera_analysis.json"):
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())

    def test_missing_static_camera_declaration_fails_only_camera_category(self) -> None:
        output = self.work / "out"
        result = self.run_tool(self.manifest([self.base, self.base.copy()], static=False), output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((output / "motion_analysis.json").read_text())["result"], "pass")
        camera = json.loads((output / "object_background_camera_analysis.json").read_text())
        self.assertEqual(camera["result"], "fail")
        self.assertIn("planned_motion_unsupported", camera["notes"])

    def test_large_adjacent_change_fails_motion(self) -> None:
        output = self.work / "out"
        inverted = 255 - self.base
        result = self.run_tool(self.manifest([self.base, inverted]), output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((output / "motion_analysis.json").read_text())["result"], "fail")

    def test_tampered_frame_blocks_without_output(self) -> None:
        manifest = self.manifest([self.base, self.base.copy()])
        (self.work / "frame_001.png").write_bytes(b"tampered")
        output = self.work / "out"
        result = self.run_tool(manifest, output)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(output.exists())

    def test_single_frame_blocks_as_non_temporal(self) -> None:
        output = self.work / "out"
        result = self.run_tool(self.manifest([self.base]), output)
        self.assertEqual(result.returncode, 2)
        self.assertIn("at least 2", result.stderr)
        self.assertFalse(output.exists())

    def test_nonfinite_threshold_registry_blocks(self) -> None:
        threshold = self.work / "thresholds.json"
        source = (ROOT / "Plan/10_REGISTRIES/wave27_frame_continuity_thresholds.json").read_text()
        threshold.write_text(source.replace("30.0", "NaN", 1), encoding="utf-8")
        output = self.work / "out"
        result = self.run_tool(self.manifest([self.base, self.base.copy()]), output, threshold)
        self.assertEqual(result.returncode, 2)
        self.assertIn("non-finite", result.stderr)

    def test_existing_output_directory_is_never_overwritten(self) -> None:
        output = self.work / "out"
        output.mkdir()
        marker = output / "keep.txt"
        marker.write_text("keep", encoding="utf-8")
        result = self.run_tool(self.manifest([self.base, self.base.copy()]), output)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(marker.read_text(), "keep")

    def test_metrics_hash_is_bound_in_both_adapter_notes(self) -> None:
        output = self.work / "out"
        result = self.run_tool(self.manifest([self.base, self.base.copy()]), output)
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = sha256(output / "temporal_continuity_metrics.json")
        for category in ("motion_analysis", "object_background_camera_analysis"):
            notes = json.loads((output / f"{category}.json").read_text())["notes"]
            self.assertIn(f"metrics_sha256={expected}", notes)


if __name__ == "__main__":
    unittest.main()
