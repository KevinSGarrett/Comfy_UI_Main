#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/reconcile_wave64_row019_wan_pipeline.py"
SPEC = importlib.util.spec_from_file_location("row019_wan", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class Row019WanReconciliationTests(unittest.TestCase):
    def fixture(self, root: Path) -> dict[str, Path]:
        paths = {}
        for name, source in MODULE.SOURCES.items():
            target = root / "sources" / f"{name}.json"
            write(target, json.loads((ROOT / source).read_text(encoding="utf-8-sig")))
            paths[name] = target
        return paths

    def evaluate(self, root: Path, sources: dict[str, Path]):
        return MODULE.build(root, sources, "2026-07-14T13:05:00-05:00")

    def mutate(self, path: Path, callback) -> None:
        value = json.loads(path.read_text())
        callback(value)
        write(path, value)

    def test_happy_path_advances_bounded_wan_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.evaluate(root, self.fixture(root))
            self.assertFalse(result["row_complete"])
            self.assertTrue(result["acceptance_gates"]["bounded_primary_clip_direct_temporal_review"])
            self.assertFalse(result["acceptance_gates"]["keyframe_manifest"])
            self.assertTrue(result["acceptance_gates"]["loop_export_gate"])
            self.assertFalse(result["acceptance_gates"]["frame_repair_effectiveness"])
            self.assertTrue(result["acceptance_gates"]["repaired_candidate_present"])
            self.assertTrue(result["acceptance_gates"]["repair_runtime_proof"])
            self.assertTrue(result["acceptance_gates"]["before_after_visual_review"])
            self.assertFalse(result["acceptance_gates"]["repair_visual_acceptance"])
            self.assertTrue(result["acceptance_gates"]["strict_frame_sequence_visual_review"])
            self.assertFalse(result["repair_state"]["attempt_evidence"]["retry_allowed"])

    def test_rejects_runtime_certification_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["runtime"], lambda value: value["boundaries"].update({"production_video_lane_certification_claimed": True}))
            with self.assertRaisesRegex(ValueError, "overclaims certification"):
                self.evaluate(root, sources)

    def test_rejects_technical_certification_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["technical"], lambda value: value["boundaries"].update({"production_video_lane_certification_claimed": True}))
            with self.assertRaisesRegex(ValueError, "technical evidence overclaims certification"):
                self.evaluate(root, sources)

    def test_rejects_visual_scope_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["visual"], lambda value: value["boundaries"].update({"multiseed_robustness_claimed": True}))
            with self.assertRaisesRegex(ValueError, "overclaims multiseed robustness"):
                self.evaluate(root, sources)

    def test_rejects_visual_duration_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["visual"], lambda value: value["boundaries"].update({"long_duration_quality_claimed": True}))
            with self.assertRaisesRegex(ValueError, "overclaims duration quality"):
                self.evaluate(root, sources)

    def test_rejects_running_instance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["runtime"], lambda value: value["execution_target"].update({"final_instance_state": "running"}))
            with self.assertRaisesRegex(ValueError, "not stopped"):
                self.evaluate(root, sources)

    def test_rejects_frame_count_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["technical"], lambda value: value["decode"].update({"frame_count": 48}))
            with self.assertRaisesRegex(ValueError, "49-frame proof"):
                self.evaluate(root, sources)

    def test_rejects_failed_visual_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["visual"], lambda value: value.update({"visual_pass": False}))
            with self.assertRaisesRegex(ValueError, "visual QA did not pass"):
                self.evaluate(root, sources)

    def test_rejects_unsubstantiated_repair_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["repair"], lambda value: value["gate_results"].update({"repaired_candidate_present": True}))
            with self.assertRaisesRegex(ValueError, "repair unexpectedly proven"):
                self.evaluate(root, sources)

    def test_rejects_repair_attempt_visual_pass_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["repair_attempt"], lambda value: value["direct_visual_qa"].update({"direct_visual_acceptance_pass": True}))
            with self.assertRaisesRegex(ValueError, "visual failure proof missing"):
                self.evaluate(root, sources)

    def test_rejects_repair_attempt_retry_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["repair_attempt"], lambda value: value["execution_accounting"].update({"retry_allowed": True}))
            with self.assertRaisesRegex(ValueError, "incorrectly allows retry"):
                self.evaluate(root, sources)

    def test_rejects_repair_attempt_acceptance_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["repair_attempt"], lambda value: value["acceptance_gates"].update({"final_temporal_acceptance": True, "final_promotion": True}))
            with self.assertRaisesRegex(ValueError, "overclaims acceptance"):
                self.evaluate(root, sources)

    def test_rejects_multiple_repair_generations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["repair_attempt"], lambda value: value["execution_accounting"].update({"completed_generation_count": 2}))
            with self.assertRaisesRegex(ValueError, "execution count mismatch"):
                self.evaluate(root, sources)

    def test_rejects_identity_environment_preservation_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["repair_attempt"], lambda value: value["acceptance_gates"].update({"identity_environment_visual_preservation": True}))
            with self.assertRaisesRegex(ValueError, "visual preservation unexpectedly passed"):
                self.evaluate(root, sources)

    def test_rejects_unbound_repair_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["repair_attempt"], lambda value: value["candidate"].update({"sha256": ""}))
            with self.assertRaisesRegex(ValueError, "not hash-bound"):
                self.evaluate(root, sources)

    def test_rejects_missing_bounded_loop_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["loop"], lambda value: value["gate_results"].update({"bounded_gif_export_certification": False}))
            with self.assertRaisesRegex(ValueError, "bounded loop certification did not pass"):
                self.evaluate(root, sources)

    def test_rejects_promoted_shot_plan_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["shot_plan"], lambda value: value.update({"promotion_ready": True}))
            with self.assertRaisesRegex(ValueError, "shot plan promotion boundary missing"):
                self.evaluate(root, sources)

    def test_preserves_failed_animatediff_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.evaluate(root, self.fixture(root))
            self.assertFalse(result["historical_fallback_attempt"]["visual_temporal_pass"])
            self.assertEqual(result["historical_fallback_attempt"]["failed_frame_indexes"], [5, 6, 7])

    def test_note_normalization_is_idempotent(self) -> None:
        once = MODULE.normalize_note(f"old; {MODULE.NOTE}; {MODULE.NOTE}")
        self.assertEqual(MODULE.normalize_note(once), once)
        self.assertEqual(once.count("Wave64 Row019 repair-attempt integration:"), 1)


if __name__ == "__main__": unittest.main()
