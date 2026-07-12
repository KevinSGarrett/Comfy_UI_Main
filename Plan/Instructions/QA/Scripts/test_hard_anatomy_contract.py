from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
COMPILE = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_hard_anatomy_repair_contract.py"
VALIDATE = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_hard_anatomy_repair_contract.py"
SCORE = ROOT / "Plan/07_IMPLEMENTATION/scripts/score_hard_anatomy_evidence.py"
EXAMPLE = ROOT / "Plan/09_EXAMPLES/wave20_hard_anatomy_repair_contract.example.json"
SCHEMA = ROOT / "Plan/08_SCHEMAS/hard_anatomy_repair_contract.schema.json"
GATES = ["anatomy_scorecard", "hands_feet_check", "face_teeth_eye_check", "hard_reject_on_deformation"]


def run(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, check=False)


def passing_gate(regions: tuple[str, ...] = ()) -> dict:
    gate = {"status": "pass", "evidence_paths": ["evidence.json"], "blockers": []}
    for region in regions:
        gate[region] = {"status": "pass", "inspectable": True}
    return gate


class HardAnatomyContractTests(unittest.TestCase):
    def test_schema_and_example_require_all_four_gates(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        example = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        self.assertTrue(set(GATES).issubset(schema["required"]))
        self.assertTrue(set(GATES).issubset(example))

    def test_compiler_preserves_example_gate_dispositions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "compiled.json"
            result = run(COMPILE, "--input", EXAMPLE, "--output", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            compiled = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(set(GATES).issubset(compiled))
            self.assertTrue(compiled["hard_reject_on_deformation"]["triggered"])
            self.assertFalse(compiled["hard_reject_on_deformation"]["promotion_allowed"])

    def test_compiler_defaults_missing_evidence_to_blocked_hard_reject(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request = Path(tmp) / "request.json"
            output = Path(tmp) / "compiled.json"
            request.write_text(json.dumps({"source_image_id": "img", "repair_regions": ["left_hand"], "crop_plans": [], "qa_goals": []}), encoding="utf-8")
            result = run(COMPILE, "--input", request, "--output", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            compiled = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(compiled["hands_feet_check"]["status"], "blocked")
            self.assertTrue(compiled["hard_reject_on_deformation"]["triggered"])
            self.assertFalse(compiled["hard_reject_on_deformation"]["promotion_allowed"])

    def test_validator_accepts_structurally_valid_blocked_contract(self) -> None:
        result = run(VALIDATE, "--input", EXAMPLE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_validator_rejects_promotion_when_required_gate_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            invalid = json.loads(EXAMPLE.read_text(encoding="utf-8"))
            invalid["hard_reject_on_deformation"].update({"triggered": False, "reasons": [], "promotion_allowed": True})
            path = Path(tmp) / "invalid.json"
            path.write_text(json.dumps(invalid), encoding="utf-8")
            result = run(VALIDATE, "--input", path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("promotion allowed", result.stdout)

    def test_validator_rejects_promotion_when_pass_region_is_not_inspectable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            invalid = json.loads(EXAMPLE.read_text(encoding="utf-8"))
            invalid["anatomy_scorecard"].update({"status": "pass", "evidence_paths": ["score.json"], "blockers": [], "local_score": 0.9, "global_score": 0.9})
            invalid["hands_feet_check"] = passing_gate(("hands", "feet"))
            invalid["face_teeth_eye_check"] = passing_gate(("face", "eyes", "teeth"))
            invalid["hands_feet_check"]["hands"]["inspectable"] = False
            invalid["hard_reject_on_deformation"] = {"enabled": True, "triggered": False, "reasons": [], "promotion_allowed": True}
            path = Path(tmp) / "invalid_inspectability.json"
            path.write_text(json.dumps(invalid), encoding="utf-8")
            result = run(VALIDATE, "--input", path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("promotion allowed", result.stdout)

    def test_scorer_hard_reject_overrides_passing_numeric_scores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "evidence.json"
            output_path = Path(tmp) / "report.json"
            evidence = json.loads(EXAMPLE.read_text(encoding="utf-8"))
            evidence.update({
                "local_anatomy_improved": True,
                "identity_preserved": True,
                "pose_preserved": True,
                "contact_preserved": True,
                "frame_preserved": True,
                "seam_blend_passed": True,
                "local_score": 1.0,
                "global_score": 1.0,
            })
            input_path.write_text(json.dumps(evidence), encoding="utf-8")
            result = run(SCORE, "--input", input_path, "--output", output_path)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertFalse(report["pass"])
            self.assertIn("hard_reject_on_deformation_triggered", report["automatic_fail_flags"])

    def test_scorer_passes_only_complete_regional_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "evidence.json"
            output_path = Path(tmp) / "report.json"
            evidence = {
                "local_anatomy_improved": True, "identity_preserved": True,
                "pose_preserved": True, "contact_preserved": True,
                "frame_preserved": True, "seam_blend_passed": True,
                "local_score": 0.9, "global_score": 0.9,
                "anatomy_scorecard": {**passing_gate(), "local_score": 0.9, "global_score": 0.9, "regional_checks": []},
                "hands_feet_check": passing_gate(("hands", "feet")),
                "face_teeth_eye_check": passing_gate(("face", "eyes", "teeth")),
                "hard_reject_on_deformation": {"enabled": True, "triggered": False, "reasons": [], "promotion_allowed": True},
            }
            input_path.write_text(json.dumps(evidence), encoding="utf-8")
            result = run(SCORE, "--input", input_path, "--output", output_path)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertTrue(report["pass"])
            self.assertEqual(report["automatic_fail_flags"], [])


if __name__ == "__main__":
    unittest.main()
