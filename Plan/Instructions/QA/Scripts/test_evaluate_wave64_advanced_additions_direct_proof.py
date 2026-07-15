#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_advanced_additions_direct_proof.py"
SPEC = importlib.util.spec_from_file_location("row056_direct_proof", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Row056DirectProofTests(unittest.TestCase):
    def build(self, root: Path) -> dict[str, Path]:
        artifact = root / "artifacts/clip.mp4"
        artifact.parent.mkdir(parents=True)
        artifact.write_bytes(b"bounded-video-proof")
        artifact_record = {"path": artifact.relative_to(root).as_posix(), "size_bytes": artifact.stat().st_size, "sha256": sha(artifact)}

        assets = []
        for name in MODULE.REVIEW_ASSETS:
            path = root / "runtime_artifacts/review" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"review-{name}".encode())
            assets.append({"path": path.relative_to(root).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha(path)})

        systems = []
        for system_id in sorted(MODULE.SYSTEM_IDS):
            systems.append(
                {
                    "system_id": system_id,
                    "mapping_state": "complete",
                    "required_capabilities": ["placeholder"],
                    "review_requirements": {"visual": ["placeholder"], "audio": []},
                    "runtime_promotion_state": "blocked_missing_direct_runtime_evidence",
                    "blockers": ["direct_runtime_proof_missing"],
                }
            )
        micro = next(record for record in systems if record["system_id"] == MODULE.MICRO)
        micro["required_capabilities"] = ["temporal_pose", "regional_motion", "sequence_consistency"]
        micro["review_requirements"]["visual"] = ["frame_sequence_review"]
        crosswalk = {"advanced_systems": systems, "runtime_promotion_state": "blocked"}

        runtime_path = root / "evidence/runtime.json"
        technical_path = root / "evidence/technical.json"
        visual_path = root / "evidence/visual.json"
        crosswalk_path = root / "registry/crosswalk.json"
        runtime = {
            "result": "pass_bounded_wan22_ti2v5b_target_runtime_smoke",
            "lane_id": "test-lane",
            "run_id": "test-run",
            "artifact": artifact_record,
            "execution_target": {"final_instance_state": "stopped"},
            "runtime_result": {"generation_executed": True, "prompt_schema_status": "pass", "prompt_schema_error_count": 0, "pullback_hashes_verified": True, "errors": []},
            "model_proofs": [
                {"filename": f"model-{index}", "size_bytes": index + 1, "sha256": f"{index + 1:064x}", "inventory_result": "ASSET_PRESENT_OK"}
                for index in range(3)
            ],
            "checks": {name: True for name in MODULE.RUNTIME_CHECKS},
            "boundaries": {
                "single_clip_only": True,
                "production_video_lane_certification_claimed": False,
                "gold_masks_consumed": False,
                "mask_or_geometry_authority_claimed": False,
                "wave71_activation_claimed": False,
                "jira_mutated": False,
            },
        }
        technical = {
            "runtime_evidence": runtime_path.relative_to(root).as_posix(),
            "lane_id": "test-lane",
            "run_id": "test-run",
            "artifact": artifact_record,
            "result": "pass_bounded_wan22_ti2v5b_target_runtime_technical_qa",
            "technical_pass": True,
            "failed_checks": [],
            "decode": {"frame_count": 49, "unique_decoded_frame_count": 49, "fps": 24, "duration_seconds": 2.04},
            "temporal_detectors": {"blackdetect_event_count": 0, "freezedetect_event_count": 0},
            "checks": {name: True for name in MODULE.TECHNICAL_CHECKS},
            "boundaries": {"production_video_lane_certification_claimed": False, "mask_or_geometry_authority_claimed": False},
        }
        visual = {
            "technical_qa": technical_path.relative_to(root).as_posix(),
            "lane_id": "test-lane",
            "run_id": "test-run",
            "artifact": artifact_record,
            "result": "pass_bounded_single_clip_direct_temporal_review",
            "visual_pass": True,
            "failed_checks": [],
            "reviewed_frames": [1, 7, 13, 19, 25, 31, 37, 43, 49],
            "review_assets": assets,
            "review_method": "direct_original_frame_review_plus_49_frame_contact_sheet_and_start_middle_end_region_crops",
            "checks": {name: True for name in MODULE.VISUAL_CHECKS},
            "boundaries": {
                "single_seed_single_source_single_profile": True,
                "long_duration_quality_claimed": False,
                "multiseed_robustness_claimed": False,
                "production_video_lane_certification_claimed": False,
                "gold_masks_consumed": False,
                "mask_or_geometry_authority_claimed": False,
                "wave71_activation_claimed": False,
                "jira_mutated": False,
            },
        }
        for path, payload in ((crosswalk_path, crosswalk), (runtime_path, runtime), (technical_path, technical), (visual_path, visual)):
            write_json(path, payload)
        return {"crosswalk": crosswalk_path, "runtime": runtime_path, "technical": technical_path, "visual": visual_path}

    def evaluate(self, root: Path, paths: dict[str, Path]) -> dict:
        return MODULE.build_evidence(root, paths, "2026-07-14T12:00:00-05:00")

    def mutate(self, path: Path, callback) -> None:
        payload = json.loads(path.read_text())
        callback(payload)
        write_json(path, payload)

    def add_fluid(self, root: Path, paths: dict[str, Path]) -> None:
        fluid_path = root / "evidence/fluid.json"
        fluid = {
            "tracker_id": MODULE.TRK,
            "item_id": MODULE.ITEM,
            "system_id": "fluid_body_state_continuity",
            "status": "BLOCKED_FLUID_STATE_SHOT_CONTINUITY_IDENTITY_DRIFT",
            "classification": "DIRECT_RUNTIME_REVIEW_EXECUTED_NO_ROUTE_PASSED_BOTH_STATE_AND_CONTINUITY",
            "runtime_chain": {"local_runtime_generation_count": 4, "route_count": 3, "candidate_retry_count": 0},
            "gates": {
                "model_or_runtime_capability_proof_present": True,
                "required_before_after_visual_evidence_present": True,
                "planned_state_achieved_by_at_least_one_route": True,
                "shot_continuity_achieved_by_at_least_one_route": True,
                "single_route_achieved_state_and_continuity": False,
                "bounded_direct_runtime_proof_pass": False,
                "production_certification_pass": False,
                "row_complete": False,
            },
            "direct_visual_reviews": [
                {"route": "same_seed_txt2img_pair", "decision": "fail_shot_continuity"},
                {"route": "baseline_anchored_low_denoise_img2img", "decision": "fail_planned_state_missing"},
                {"route": "deterministic_under_eye_masked_inpaint", "decision": "fail_identity_critical_eye_region_drift"},
            ],
            "boundaries": {
                "edit_region_mask_is_not_geometry_or_segmentation_truth": True,
                "mask_promotion": False,
                "content_based_suppression": False,
                "adult_or_nsfw_asset_visibility_restricted": False,
            },
        }
        write_json(fluid_path, fluid)
        paths["fluid"] = fluid_path

    def test_ledger_note_is_idempotent_and_cleans_legacy_fragments(self) -> None:
        legacy = (
            "existing note; Wave64 Row056 direct-proof reconciliation: existing WAN target-runtime clip, "
            "49-frame technical QA, and direct visual QA establish one bounded micro-motion proof; "
            "six systems remain fail-closed; no AWS action was rerun.; "
            "Wave64 Row056 direct-proof reconciliation: existing WAN target-runtime clip, 49-frame technical QA, "
            "and direct visual QA establish one bounded micro-motion proof"
        )
        cleaned = MODULE.append_unique(legacy, MODULE.LEDGER_NOTE)
        self.assertEqual(cleaned.count(MODULE.LEDGER_NOTE), 1)
        self.assertNotIn("six systems remain fail-closed", cleaned)
        self.assertEqual(MODULE.append_unique(cleaned, MODULE.LEDGER_NOTE), cleaned)

    def test_happy_path_advances_only_micro_motion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.evaluate(root, self.build(root))
            self.assertEqual(result["status"], MODULE.STATUS)
            self.assertFalse(result["row_complete"])
            self.assertEqual(result["proof_summary"]["bounded_direct_runtime_proof_pass"], 1)
            self.assertEqual(result["proof_summary"]["direct_runtime_proof_blocked"], 6)
            states = {record["system_id"]: record["runtime_promotion_state"] for record in result["advanced_systems"]}
            self.assertTrue(states[MODULE.MICRO].startswith("bounded_direct_runtime_proof_pass"))
            self.assertTrue(all(states[name].startswith("blocked") for name in MODULE.SYSTEM_IDS - {MODULE.MICRO}))
            self.assertFalse(result["claim_boundary"]["production_video_lane_certification"])

    def test_fluid_direct_review_replaces_one_missing_system_with_exact_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.build(root)
            self.add_fluid(root, paths)
            result = self.evaluate(root, paths)
            self.assertEqual(result["status"], MODULE.FLUID_STATUS)
            self.assertEqual(result["qa_decision"], MODULE.FLUID_DECISION)
            self.assertEqual(result["proof_summary"]["direct_runtime_review_fail"], 1)
            self.assertEqual(result["proof_summary"]["direct_runtime_proof_missing"], 5)
            fluid = next(record for record in result["advanced_systems"] if record["system_id"] == "fluid_body_state_continuity")
            self.assertEqual(fluid["runtime_promotion_state"], "bounded_direct_runtime_review_fail_shot_continuity")
            self.assertEqual(fluid["direct_proof_scope"]["candidate_retry_count"], 0)

    def test_fluid_direct_review_rejects_false_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.build(root)
            self.add_fluid(root, paths)
            self.mutate(paths["fluid"], lambda payload: payload["gates"].update({"single_route_achieved_state_and_continuity": True}))
            with self.assertRaisesRegex(ValueError, "fluid false promotion"):
                self.evaluate(root, paths)

    def test_fails_on_artifact_record_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.build(root)
            self.mutate(paths["technical"], lambda payload: payload["artifact"].update({"sha256": "0" * 64}))
            with self.assertRaisesRegex(ValueError, "artifact sha256 mismatch"):
                self.evaluate(root, paths)

    def test_fails_on_lane_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.build(root)
            self.mutate(paths["technical"], lambda payload: payload.update({"lane_id": "different-lane"}))
            with self.assertRaisesRegex(ValueError, "lane identity mismatch"):
                self.evaluate(root, paths)

    def test_fails_on_local_artifact_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.build(root)
            (root / "artifacts/clip.mp4").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "local artifact sha256 mismatch"):
                self.evaluate(root, paths)

    def test_fails_on_review_asset_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.build(root)
            (root / "runtime_artifacts/review/contact_sheet.png").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "visual asset sha256 mismatch"):
                self.evaluate(root, paths)

    def test_fails_when_instance_not_stopped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.build(root)
            self.mutate(paths["runtime"], lambda payload: payload["execution_target"].update({"final_instance_state": "running"}))
            with self.assertRaisesRegex(ValueError, "final instance state not stopped"):
                self.evaluate(root, paths)

    def test_fails_on_nonunique_frames(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.build(root)
            self.mutate(paths["technical"], lambda payload: payload["decode"].update({"unique_decoded_frame_count": 48}))
            with self.assertRaisesRegex(ValueError, "frame uniqueness proof failed"):
                self.evaluate(root, paths)

    def test_fails_on_visual_check(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.build(root)
            self.mutate(paths["visual"], lambda payload: payload["checks"].update({"hands_remain_anatomically_stable": False}))
            with self.assertRaisesRegex(ValueError, "visual checks not true"):
                self.evaluate(root, paths)

    def test_fails_on_production_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.build(root)
            self.mutate(paths["visual"], lambda payload: payload["boundaries"].update({"production_video_lane_certification_claimed": True}))
            with self.assertRaisesRegex(ValueError, "visual boundaries not false"):
                self.evaluate(root, paths)

    def test_fails_on_crosswalk_system_loss(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self.build(root)
            self.mutate(paths["crosswalk"], lambda payload: payload["advanced_systems"].pop())
            with self.assertRaisesRegex(ValueError, "exactly seven systems"):
                self.evaluate(root, paths)


if __name__ == "__main__":
    unittest.main()
