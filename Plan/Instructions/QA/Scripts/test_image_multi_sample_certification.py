from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PLAN = ROOT / "Plan"
VALIDATOR = PLAN / "07_IMPLEMENTATION/scripts/validate_image_multi_sample_certification.py"
EXAMPLE = PLAN / "09_EXAMPLES/image_multi_sample_certification.example.json"


def run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(VALIDATOR), "--input", str(path)], cwd=ROOT, capture_output=True, text=True, check=False)


class ImageMultiSampleCertificationTests(unittest.TestCase):
    def test_current_blocked_example_validates(self):
        self.assert_valid(self.current())

    def test_fully_bound_portfolio_set_can_certify(self):
        self.assert_valid(self.certifiable())

    def test_fewer_than_three_samples_is_rejected(self):
        value = self.certifiable()
        value["multi_seed_sample_set"] = value["multi_seed_sample_set"][:2]
        self.assert_rejected(value, "at least three samples")

    def test_repeated_seed_is_rejected_for_certification(self):
        value = self.certifiable()
        value["multi_seed_sample_set"][2]["seed"] = value["multi_seed_sample_set"][0]["seed"]
        self.assert_rejected(value, "seed and prompt diversity")

    def test_single_prompt_is_rejected_for_certification(self):
        value = self.certifiable()
        prompt = value["multi_seed_sample_set"][0]["prompt_reference"]
        for sample in value["multi_seed_sample_set"]:
            sample["prompt_reference"] = prompt
        self.assert_rejected(value, "seed and prompt diversity")

    def test_aggregate_mismatch_is_rejected(self):
        value = self.certifiable()
        value["aggregate_score"]["mean"] = 5.0
        self.assert_rejected(value, "must match sample scores")

    def test_blocking_defect_is_rejected_for_certification(self):
        value = self.certifiable()
        value["multi_seed_sample_set"][0]["blocking_defects"] = ["broken_hand"]
        value["defect_rate_limit"].update({"blocking_defect_sample_count": 1, "rate": 1 / 3})
        self.assert_rejected(value, "zero blocking defects")

    def test_missing_target_runtime_is_rejected_for_certification(self):
        value = self.certifiable()
        value["multi_seed_sample_set"][1]["target_runtime_proof"] = False
        value["portfolio_certification_record"]["target_runtime_sample_count"] = 2
        self.assert_rejected(value, "target-runtime proof for every sample")

    def test_invalid_artifact_hash_is_rejected(self):
        value = self.certifiable()
        value["multi_seed_sample_set"][0]["artifact"]["sha256"] = "bad"
        self.assert_rejected(value, "artifact is invalid")

    def current(self) -> dict:
        return json.loads(EXAMPLE.read_text(encoding="utf-8-sig"))

    def certifiable(self) -> dict:
        value = self.current()
        for index, sample in enumerate(value["multi_seed_sample_set"]):
            sample["prompt_reference"] = f"prompts/prompt_{index % 2}.json"
            sample["target_runtime_proof"] = True
        value["portfolio_certification_record"].update({"decision": "certified", "certified_scope": "synthetic_test_scope", "target_runtime_sample_count": 3})
        return value

    def assert_valid(self, value: dict):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cert.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            result = run(path)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_rejected(self, value: dict, message: str):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cert.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            result = run(path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(message, result.stdout)


if __name__ == "__main__":
    unittest.main()
