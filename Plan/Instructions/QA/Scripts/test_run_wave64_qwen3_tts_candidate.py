from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "run_wave64_qwen3_tts_candidate.py"
SPEC = importlib.util.spec_from_file_location("qwen_candidate", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def plan() -> dict:
    return {
        "generation_executed": False,
        "production_ready": False,
        "normalization": {"normalized_text": "We hold the frame steady and move on the beat."},
        "pronunciation": {"pass": True},
        "performance": {"taxonomy_conflation": False},
        "duration": {"pass": True, "spoken_content_trim_allowed": False},
    }


class QwenCandidateRunnerTests(unittest.TestCase):
    def test_plan_validation_requires_no_truncation_and_no_promotion(self) -> None:
        self.assertEqual("We hold the frame steady and move on the beat.", MODULE.validate_plan(plan()))
        invalid = plan()
        invalid["duration"]["spoken_content_trim_allowed"] = True
        with self.assertRaisesRegex(MODULE.CandidateError, "trimming"):
            MODULE.validate_plan(invalid)

    def test_candidate_paths_are_seed_specific(self) -> None:
        wav, manifest = MODULE.candidate_paths(Path("out"), 12345)
        self.assertEqual("qwen3_tts_voicedesign_seed12345.wav", wav.name)
        self.assertEqual("qwen3_tts_voicedesign_seed12345.manifest.json", manifest.name)

    def test_model_verification_rejects_missing_exact_file_set(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(MODULE.CandidateError, "size mismatch"):
                MODULE.verify_model_files(Path(temporary))


if __name__ == "__main__":
    unittest.main()
