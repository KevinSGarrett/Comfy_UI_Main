from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "compile_wave64_speech_planning_controls.py"
SPEC = importlib.util.spec_from_file_location("speech_planning", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


TOKENS = ["we", "hold", "the", "frame", "steady", "and", "move", "on", "the", "beat"]


def lexicon() -> dict:
    return {
        "registry_id": "test_lexicon",
        "language": "en-US",
        "entries": {token: [["P", "H", "1"]] for token in set(TOKENS)},
    }


def request() -> dict:
    return {
        "line_id": "line_001",
        "character_id": "C01",
        "voice_profile_id": "voice_c01",
        "text": "We hold the frame steady and move on the beat.",
        "language": "en-US",
        "emotion_class": "neutral",
        "delivery_style": "focused",
        "intensity": "low",
        "pace_wpm": 200,
        "emphasis": ["steady"],
        "articulation": "clear",
        "duration_target_seconds": 3.0,
        "duration_tolerance_seconds": 0.08,
    }


class SpeechPlanningControlTests(unittest.TestCase):
    def test_normalization_is_hash_bound_reversible_and_expands_supported_forms(self) -> None:
        result = MODULE.normalize_text(" Dr. Lane & 2 cameras on 07/15/2026. ", "en-US")
        self.assertEqual("Doctor Lane and two cameras on July fifteenth, two thousand twenty-six.", result["normalized_text"])
        self.assertTrue(result["reversible"])
        self.assertRegex(result["original_sha256"], r"^[a-f0-9]{64}$")
        self.assertGreaterEqual(len(result["transforms"]), 4)

    def test_unknown_language_fails_closed(self) -> None:
        with self.assertRaisesRegex(MODULE.PlanningError, "unsupported normalization language"):
            MODULE.normalize_text("Bonjour", "fr-FR")

    def test_pronunciation_unknown_and_ambiguous_tokens_fail_closed(self) -> None:
        value = lexicon()
        value["entries"]["the"] = [["DH", "AH0"], ["DH", "IY1"]]
        result = MODULE.compile_pronunciations(TOKENS + ["unknown"], value, "en-US")
        self.assertFalse(result["pass"])
        self.assertIn("the", result["ambiguous_tokens"])
        self.assertIn("unknown", result["unknown_tokens"])

    def test_performance_controls_remain_separate(self) -> None:
        result = MODULE.compile_performance(request())
        self.assertEqual("neutral", result["emotion_class"])
        self.assertEqual("focused", result["delivery_style"])
        self.assertFalse(result["taxonomy_conflation"])
        self.assertIn("delivery_style", result["unsupported_engine_controls"])
        self.assertEqual("structured_plan_compiled_adapter_mapping_pending", result["engine_mapping_status"])

    def test_duration_planner_never_trims_spoken_content(self) -> None:
        exact = MODULE.compile_duration(TOKENS, 200, 3.0, 0.08)
        self.assertEqual("native_timing", exact["decision"])
        self.assertFalse(exact["spoken_content_trim_allowed"])
        blocked = MODULE.compile_duration(TOKENS, 100, 2.0, 0.08)
        self.assertFalse(blocked["pass"])
        self.assertEqual("shot_contract_blocked_or_alternate_engine_required", blocked["decision"])

    def test_tournament_requires_two_candidate_proven_engines(self) -> None:
        registry = {
            "adapters": [
                {
                    "adapter_id": "qwen",
                    "engine_family": "qwen3_tts",
                    "runtime_status": "load_proven",
                    "license": {"id": "Apache-2.0"},
                    "content_based_suppression": False,
                    "capabilities": {"candidate_generation_proven": False},
                }
            ]
        }
        result = MODULE.evaluate_tournament(registry)
        self.assertFalse(result["comparative_tournament_pass"])
        self.assertIsNone(result["winner"])
        self.assertFalse(result["universal_engine_assumed"])
        self.assertEqual(8, len(result["required_benchmark_dimensions"]))
        self.assertIsNone(result["entries"][0]["benchmark_dimensions"]["voice_identity"])

    def test_end_to_end_plan_passes_controls_without_generation_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request_path = root / "request.json"
            adapter_path = root / "adapters.json"
            lexicon_path = root / "lexicon.json"
            request_path.write_text(json.dumps(request()), encoding="utf-8")
            adapter_path.write_text(
                json.dumps(
                    {
                        "adapters": [
                            {
                                "adapter_id": "qwen",
                                "engine_family": "qwen3_tts",
                                "runtime_status": "load_proven",
                                "license": {"id": "Apache-2.0"},
                                "content_based_suppression": False,
                                "capabilities": {"candidate_generation_proven": False},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            lexicon_path.write_text(json.dumps(lexicon()), encoding="utf-8")
            plan, evidence = MODULE.compile_controls(root, request_path, adapter_path, lexicon_path)
            self.assertTrue(plan["pronunciation"]["pass"])
            self.assertTrue(plan["duration"]["pass"])
            self.assertFalse(plan["generation_executed"])
            self.assertFalse(evidence["decisions"]["TRK-W64-118"]["pass_like"])
            for row in range(119, 123):
                self.assertTrue(evidence["decisions"][f"TRK-W64-{row:03d}"]["pass_like"])


if __name__ == "__main__":
    unittest.main()
