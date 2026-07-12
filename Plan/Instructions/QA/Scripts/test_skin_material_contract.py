from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PLAN = ROOT / "Plan"
VALIDATOR = PLAN / "07_IMPLEMENTATION/scripts/validate_skin_material_contract.py"
SCORER = PLAN / "07_IMPLEMENTATION/scripts/score_skin_material_evidence.py"
CONTRACT = PLAN / "09_EXAMPLES/wave18_skin_material_contract.example.json"
EVIDENCE = PLAN / "09_EXAMPLES/wave18_skin_material_evidence.example.json"


def run(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, capture_output=True, text=True, check=False)


class SkinMaterialContractTests(unittest.TestCase):
    def test_example_contract_validates(self):
        result = run(VALIDATOR, "--input", CONTRACT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unknown_profile_is_rejected(self):
        value = json.loads(CONTRACT.read_text(encoding="utf-8-sig"))
        value["surface_profile"] = "unknown_profile"
        self.assert_contract_rejected(value, "surface_profile is not registered")

    def test_empty_target_regions_are_rejected(self):
        value = json.loads(CONTRACT.read_text(encoding="utf-8-sig"))
        value["target_regions"] = []
        self.assert_contract_rejected(value, "target_regions must contain")

    def test_all_visual_gates_can_pass(self):
        value = self.passing_evidence()
        result, report = self.score(value)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(report["pass"])

    def test_broken_lighting_forces_failure(self):
        value = self.passing_evidence()
        value["lighting_consistency"] = {"status": "fail", "inspectable": True}
        result, report = self.score(value)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(report["pass"])
        self.assertIn("lighting_consistency", report["automatic_fail_flags"])

    def test_uninspectable_pass_forces_failure(self):
        value = self.passing_evidence()
        value["material_state_continuity"]["inspectable"] = False
        _, report = self.score(value)
        self.assertFalse(report["pass"])

    def test_out_of_range_score_is_rejected(self):
        value = self.passing_evidence()
        value["continuity_score"] = 2.0
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "evidence.json"
            output = Path(tmp) / "report.json"
            source.write_text(json.dumps(value), encoding="utf-8")
            result = run(SCORER, "--input", source, "--output", output)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())

    def test_noncertifying_visual_reference_forces_failure(self):
        value = self.passing_evidence()
        value["visual_qa_reference"]["certification_allowed"] = False
        _, report = self.score(value)
        self.assertFalse(report["pass"])
        self.assertIn("visual_score_threshold", report["automatic_fail_flags"])

    def assert_contract_rejected(self, value: dict, message: str):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contract.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            result = run(VALIDATOR, "--input", path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(message, result.stdout)

    def passing_evidence(self) -> dict:
        value = json.loads(EVIDENCE.read_text(encoding="utf-8-sig"))
        for gate in ("surface_texture_check", "lighting_consistency", "material_state_continuity"):
            value[gate] = {"status": "pass", "inspectable": True}
        value["visual_score_threshold"].update({"macro_review_status": "pass", "full_frame_review_status": "pass"})
        value["visual_qa_reference"]["qa_result"] = "pass"
        value["visual_qa_reference"]["certification_allowed"] = True
        return value

    def score(self, value: dict):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "evidence.json"
            output = Path(tmp) / "report.json"
            source.write_text(json.dumps(value), encoding="utf-8")
            result = run(SCORER, "--input", source, "--output", output)
            report = json.loads(output.read_text(encoding="utf-8"))
            return result, report


if __name__ == "__main__":
    unittest.main()
