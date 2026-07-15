import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_mmaudio_review_mux.py"
SPEC = importlib.util.spec_from_file_location("build_wave64_mmaudio_review_mux", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)
EVIDENCE = ROOT / "Plan/Instructions/QA/Evidence/Wave64/W64_MMAUDIO_REVIEW_MUX_20260714T221311-0500.json"
TRACKER_EVIDENCE = ROOT / "Plan/Tracker/Evidence/Wave64/W64_MMAUDIO_REVIEW_MUX_20260714T221311-0500.json"


class BuildWave64MMAudioReviewMuxTests(unittest.TestCase):
    def test_sha256_and_exact_hash_acceptance(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.bin"
            path.write_bytes(b"exact media")
            expected = MODULE.sha256(path)
            self.assertEqual(MODULE.require_hash(path, expected, "fixture"), expected)

    def test_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.bin"
            path.write_bytes(b"exact media")
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                MODULE.require_hash(path, "0" * 64, "fixture")

    def test_duration_delta_uses_one_frame(self):
        self.assertAlmostEqual(MODULE.duration_delta_allowed(24.0), 1.0 / 24.0)

    def test_duration_delta_rejects_invalid_frame_rate(self):
        with self.assertRaisesRegex(ValueError, "frame rate must be positive"):
            MODULE.duration_delta_allowed(0)

    def test_video_duration_falls_back_to_decoded_frames(self):
        self.assertAlmostEqual(MODULE.resolved_video_duration(0, 49, 24.0), 49 / 24.0)

    def test_video_duration_prefers_stream_metadata(self):
        self.assertEqual(MODULE.resolved_video_duration(2.04, 49, 24.0), 2.04)

    def test_video_duration_fails_when_unresolvable(self):
        with self.assertRaisesRegex(ValueError, "cannot be resolved"):
            MODULE.resolved_video_duration(0, 0, 24.0)

    def test_pyav_dependency_is_lazy(self):
        self.assertTrue(callable(MODULE._load_av))

    def test_published_evidence_mirror_is_exact(self):
        self.assertEqual(EVIDENCE.read_bytes(), TRACKER_EVIDENCE.read_bytes())

    def test_published_artifact_hashes_match_evidence(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        for name in ("review_mux", "manifest", "contact_sheet"):
            binding = evidence["outputs"][name]
            self.assertEqual(MODULE.sha256(ROOT / binding["path"]), binding["sha256"])

    def test_published_packet_passes_without_overclaim(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        acceptance = evidence["acceptance"]
        self.assertTrue(acceptance["hash_bound_review_mux_present"])
        self.assertTrue(acceptance["technical_mux_pass"])
        self.assertTrue(acceptance["visual_decode_review_pass"])
        self.assertFalse(acceptance["independent_perceptual_playback_review_present"])
        self.assertFalse(acceptance["contact_owner_alignment_present"])
        self.assertFalse(acceptance["production_audio_certification_allowed"])
        self.assertFalse(evidence["row_complete"])


if __name__ == "__main__":
    unittest.main()
