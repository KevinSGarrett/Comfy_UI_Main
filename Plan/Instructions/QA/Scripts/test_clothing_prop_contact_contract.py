from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PLAN = ROOT / "Plan"
COMPILER = PLAN / "07_IMPLEMENTATION/scripts/compile_clothing_prop_contact_contract.py"
VALIDATOR = PLAN / "07_IMPLEMENTATION/scripts/validate_clothing_prop_contact_contract.py"
SCORER = PLAN / "07_IMPLEMENTATION/scripts/score_clothing_prop_contact_evidence.py"
CONTRACT = PLAN / "09_EXAMPLES/wave19_clothing_prop_contact_contract.example.json"
EVIDENCE = PLAN / "09_EXAMPLES/wave19_clothing_prop_contact_evidence.example.json"


def run(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, capture_output=True, text=True, check=False)


class ClothingPropContactContractTests(unittest.TestCase):
    def test_example_contract_validates(self):
        result = run(VALIDATOR, "--input", CONTRACT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_empty_contact_edge_is_rejected(self):
        value = self.contract()
        value["contact_graph"] = [{}]
        self.assert_contract_rejected(value, "contact_graph[0].source")

    def test_unknown_contact_type_is_rejected(self):
        value = self.contract()
        value["contact_graph"][0]["type"] = "unknown_contact"
        self.assert_contract_rejected(value, "type is not registered")

    def test_empty_mask_id_is_rejected(self):
        value = self.contract()
        value["mask_ids"] = [""]
        self.assert_contract_rejected(value, "mask_ids must contain")

    def test_compiler_emits_exact_gate_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "contract.json"
            result = run(COMPILER, "--input", CONTRACT, "--output", output)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            compiled = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(compiled["required_evidence_gates"], ["contact_graph_check", "shadow_contact_check", "no_floating_check", "visual_reject_on_clip"])

    def test_all_gates_and_wave19_authority_can_pass(self):
        result, report = self.score(self.passing_evidence())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(report["pass"])

    def test_shadow_failure_hard_rejects(self):
        value = self.passing_evidence()
        value["shadow_contact_check"]["status"] = "fail"
        _, report = self.score(value)
        self.assertFalse(report["pass"])
        self.assertIn("required_gate_failure", report["automatic_fail_flags"])

    def test_detected_clip_hard_rejects(self):
        value = self.passing_evidence()
        value["visual_reject_on_clip"]["clip_detected"] = True
        _, report = self.score(value)
        self.assertFalse(report["pass"])
        self.assertIn("clip_detected", report["automatic_fail_flags"])

    def test_wave25_local_reference_cannot_certify_wave19(self):
        value = self.passing_evidence()
        value["visual_qa_reference"]["certification_scope"] = "wave25_local"
        value["visual_qa_reference"]["final_certification_allowed"] = False
        _, report = self.score(value)
        self.assertFalse(report["pass"])
        self.assertIn("wave19_visual_authority_missing", report["automatic_fail_flags"])

    def test_uninspectable_pass_hard_rejects(self):
        value = self.passing_evidence()
        value["contact_graph_check"]["inspectable"] = False
        _, report = self.score(value)
        self.assertFalse(report["pass"])

    def contract(self) -> dict:
        return json.loads(CONTRACT.read_text(encoding="utf-8-sig"))

    def passing_evidence(self) -> dict:
        value = json.loads(EVIDENCE.read_text(encoding="utf-8-sig"))
        for key in ("contact_graph_check", "shadow_contact_check", "no_floating_check", "visual_reject_on_clip", "fabric_material_continuity", "identity_pose_body_preserved"):
            value[key]["status"] = "pass"
            value[key]["inspectable"] = True
            value[key]["reason_codes"] = []
        value["visual_reject_on_clip"]["clip_detected"] = False
        value["visual_qa_reference"]["final_certification_allowed"] = True
        return value

    def assert_contract_rejected(self, value: dict, message: str):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contract.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            result = run(VALIDATOR, "--input", path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(message, result.stdout)

    def score(self, value: dict):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "evidence.json"
            output = Path(tmp) / "score.json"
            source.write_text(json.dumps(value), encoding="utf-8")
            result = run(SCORER, "--input", source, "--output", output)
            report = json.loads(output.read_text(encoding="utf-8"))
            return result, report


if __name__ == "__main__":
    unittest.main()
