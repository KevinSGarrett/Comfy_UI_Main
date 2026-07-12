from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PLAN = ROOT / "Plan"
VALIDATOR = PLAN / "07_IMPLEMENTATION/scripts/validate_image_hyperreal_visual_certification.py"
EXAMPLE = PLAN / "09_EXAMPLES/image_hyperreal_visual_certification.example.json"
PROMOTION = PLAN / "07_IMPLEMENTATION/manifests/generated/W69_LOCAL_IMAGE_QA_ORCHESTRATOR_PROMOTION_MANIFEST_20260707T102500-0500.json"
PROMOTION_SUPERSEDED = PLAN / "07_IMPLEMENTATION/manifests/generated/W69_LOCAL_IMAGE_QA_ORCHESTRATOR_PROMOTION_MANIFEST_SUPERSEDED_20260707T103500-0500.json"


def run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(VALIDATOR), "--input", str(path)], cwd=ROOT, capture_output=True, text=True, check=False)


class ImageHyperrealVisualCertificationTests(unittest.TestCase):
    def test_current_blocked_example_validates(self):
        result = run(EXAMPLE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_promotion_without_outputs_is_rejected(self):
        value = self.promotable()
        value["promotion_decision"]["promoted_outputs"] = []
        self.assert_rejected(value, "nonempty hash-bound promoted outputs")

    def test_promotion_with_incomplete_upstream_is_rejected(self):
        value = self.promotable()
        value["upstream_quality_rows"][0]["row_complete"] = False
        self.assert_rejected(value, "complete upstream quality rows")

    def test_promotion_without_prompt_reference_is_rejected(self):
        value = self.promotable()
        value["prompt_alignment"]["prompt_reference"] = None
        self.assert_rejected(value, "explicit prompt alignment evidence")

    def test_promotion_below_visual_threshold_is_rejected(self):
        value = self.promotable()
        value["visual_review_scorecard"]["average_score"] = 3.9
        self.assert_rejected(value, "strict visual score threshold")

    def test_bad_artifact_hash_is_rejected(self):
        value = self.promotable()
        value["artifact_hash_manifest"]["artifacts"][0]["sha256"] = "bad"
        self.assert_rejected(value, "sha256 is invalid")

    def test_fully_bound_synthetic_promotion_validates(self):
        value = self.promotable()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cert.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            result = run(path)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_current_promotion_manifests_have_no_promoted_outputs(self):
        for path in (PROMOTION, PROMOTION_SUPERSEDED):
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            self.assertFalse(value["promotion_allowed"])
            self.assertEqual(value["promoted_outputs"], [])

    def promotable(self) -> dict:
        value = json.loads(EXAMPLE.read_text(encoding="utf-8-sig"))
        artifact_path = "outputs/example.png"
        for gate in ("technical_image_qa", "visual_review_scorecard", "prompt_alignment", "artifact_hash_manifest"):
            value[gate]["status"] = "pass"
            value[gate]["evidence_paths"] = ["evidence/example.json"]
        value["visual_review_scorecard"].update({"average_score": 4.2, "minimum_category_score": 3, "blocking_defects": []})
        value["prompt_alignment"].update({"prompt_reference": "prompts/example.json", "alignment_result": "pass"})
        value["artifact_hash_manifest"]["artifacts"] = [{"path": artifact_path, "sha256": "a" * 64}]
        value["promotion_decision"].update({"decision": "promoted", "promoted_outputs": [artifact_path]})
        for row in value["upstream_quality_rows"]:
            row["row_complete"] = True
            row["status"] = "complete"
        return value

    def assert_rejected(self, value: dict, message: str):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cert.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            result = run(path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(message, result.stdout)


if __name__ == "__main__":
    unittest.main()
