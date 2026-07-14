from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_video_artifact_technical_qa.py"
VIDEO_PATH = ROOT / (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "aws_gpu_workflow_smoke_20260714T002123-0500/images/"
    "12_wan22_ti2v5b_fullbody_seed2271301_00001_.mp4"
)
EXPECTED_SHA256 = "546da2e7d8ce3afaa02565913cef8008d3d45a2adb70d4449bab7f167c75b50d"


spec = importlib.util.spec_from_file_location("evaluate_video_artifact_technical_qa", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class VideoArtifactTechnicalQATest(unittest.TestCase):
    def test_completed_wan_baseline_passes(self) -> None:
        result = module.evaluate_video(
            VIDEO_PATH,
            expected_sha256=EXPECTED_SHA256,
            expected_width=480,
            expected_height=640,
            expected_frame_count=49,
            expected_fps=24,
        )
        self.assertTrue(result["technical_pass"])
        self.assertEqual(result["failed_checks"], [])
        self.assertEqual(result["decoder"]["decoded_frame_count"], 49)
        self.assertEqual(result["decoder"]["unique_decoded_frame_count"], 49)

    def test_wrong_hash_fails_closed(self) -> None:
        result = module.evaluate_video(VIDEO_PATH, expected_sha256="0" * 64)
        self.assertFalse(result["technical_pass"])
        self.assertIn("artifact_sha256_matches", result["failed_checks"])

    def test_wrong_frame_count_fails_closed(self) -> None:
        result = module.evaluate_video(VIDEO_PATH, expected_frame_count=50)
        self.assertFalse(result["technical_pass"])
        self.assertIn("frame_count_exact", result["failed_checks"])

    def test_freeze_detector_fails_closed_when_threshold_is_exceeded(self) -> None:
        result = module.evaluate_video(
            VIDEO_PATH,
            freeze_mae_threshold=1.0,
            max_freeze_run_frames=0,
        )
        self.assertFalse(result["technical_pass"])
        self.assertIn("freeze_run_within_limit", result["failed_checks"])

    def test_atomic_writer_publishes_valid_record(self) -> None:
        result = module.evaluate_video(VIDEO_PATH, expected_sha256=EXPECTED_SHA256)
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = Path(temp_dir) / "technical_qa.json"
            module.write_json_atomic(result, out_path)
            self.assertTrue(out_path.is_file())
            self.assertGreater(out_path.stat().st_size, 100)


if __name__ == "__main__":
    unittest.main()
