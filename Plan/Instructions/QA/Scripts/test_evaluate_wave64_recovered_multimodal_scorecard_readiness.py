#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / (
    "Plan/07_IMPLEMENTATION/scripts/"
    "evaluate_wave64_recovered_multimodal_scorecard_readiness.py"
)
SPEC = importlib.util.spec_from_file_location("row033_recovered_multimodal", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RecoveredMultimodalReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = MODULE.build_evidence(ROOT, "2026-07-14T11:06:01-05:00")

    def test_all_seven_roles_are_mapped_without_inventing_manifest(self) -> None:
        candidates = self.evidence["binding_candidates"]
        self.assertEqual(set(candidates), set(MODULE.CANDIDATE_PATHS))
        self.assertEqual(self.evidence["required_binding_count"], 7)
        self.assertEqual(self.evidence["mapping_decision"]["present_candidate_count"], 6)
        self.assertFalse(candidates["artifact_manifest_binding"]["present"])

    def test_image_and_video_do_not_gain_shared_lineage(self) -> None:
        for role in ("image_review_binding", "video_review_binding"):
            decision = self.evidence["binding_candidates"][role]
            self.assertFalse(decision["contract_compatible"])
            self.assertIn("shared_multimodal_lineage_missing", decision["blocking_reasons"])

    def test_recovered_audio_records_do_not_become_strict_reports(self) -> None:
        for role in MODULE.EXPECTED_AUDIO_SCHEMAS:
            decision = self.evidence["binding_candidates"][role]
            self.assertFalse(decision["contract_compatible"])
            self.assertIn("strict_report_schema_mismatch", decision["blocking_reasons"])
            self.assertIn("upstream_audio_row_blocked", decision["blocking_reasons"])

    def test_release_audit_does_not_become_row033_release_gate(self) -> None:
        decision = self.evidence["binding_candidates"]["release_gate_decision_binding"]
        self.assertFalse(decision["contract_compatible"])
        self.assertIn("row033_release_id_missing", decision["blocking_reasons"])
        self.assertIn(
            "release_decision_not_owned_by_row033_artifact",
            decision["blocking_reasons"],
        )

    def test_project_path_rejects_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            root.mkdir()
            outside = Path(directory) / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "path escapes project root"):
                MODULE.project_path(root, outside)

    def test_status_authority_and_external_boundaries_remain_fail_closed(self) -> None:
        self.assertEqual(
            self.evidence["status_decision"],
            "Blocked_Multimodal_Production_Review_Proof_Missing",
        )
        self.assertFalse(self.evidence["mapping_decision"]["eligible_for_strict_request"])
        self.assertFalse(self.evidence["mapping_decision"]["strict_producer_invoked"])
        self.assertEqual(
            self.evidence["authority_state"][
                "approved_production_authority_object_count"
            ],
            0,
        )
        for key in (
            "generation_executed",
            "media_modified",
            "lineage_or_release_identity_invented",
            "aws_contacted",
            "ec2_started",
            "mask_or_wave71_touched",
            "jira_mutated",
        ):
            self.assertFalse(self.evidence["boundaries"][key], key)


if __name__ == "__main__":
    unittest.main()
