#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE_SCRIPT = (
    REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_localized_change_whole_artifact_regression.py"
)
SOURCE_SPEC = REPO_ROOT / "Plan/06_QA_TESTING/WAVE64_LOCALIZED_CHANGE_WHOLE_ARTIFACT_REGRESSION_GATE_SPEC.md"
SOURCE_REQ_SCHEMA = (
    REPO_ROOT / "Plan/08_SCHEMAS/wave64_localized_change_whole_artifact_regression_request.schema.json"
)
SOURCE_REPORT_SCHEMA = (
    REPO_ROOT / "Plan/08_SCHEMAS/wave64_localized_change_whole_artifact_regression_report.schema.json"
)
SOURCE_RULES = REPO_ROOT / "Plan/10_REGISTRIES/wave64_localized_change_whole_artifact_regression_rules.json"
SOURCE_ROW033_SCHEMA = REPO_ROOT / "Plan/08_SCHEMAS/wave64_multimodal_scorecard_report.schema.json"
SOURCE_ROW032_SCHEMA = REPO_ROOT / "Plan/08_SCHEMAS/wave64_global_audio_review_report.schema.json"
SOURCE_WAVE33_CONTRACT = REPO_ROOT / "Plan/08_SCHEMAS/wave33_preview_qa_report.schema.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _binding(path: Path) -> dict[str, Any]:
    return {"path": str(path.resolve()), "sha256": _sha256(path), "bytes": path.stat().st_size}


class Wave64LocalizedChangeWholeArtifactRegressionStrictTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        for rel in (
            "Plan/06_QA_TESTING",
            "Plan/07_IMPLEMENTATION/scripts",
            "Plan/08_SCHEMAS",
            "Plan/10_REGISTRIES",
            "runtime_artifacts",
        ):
            (self.root / rel).mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE_SCRIPT, self.root / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_localized_change_whole_artifact_regression.py")
        shutil.copy2(SOURCE_SPEC, self.root / "Plan/06_QA_TESTING/WAVE64_LOCALIZED_CHANGE_WHOLE_ARTIFACT_REGRESSION_GATE_SPEC.md")
        shutil.copy2(SOURCE_REQ_SCHEMA, self.root / "Plan/08_SCHEMAS/wave64_localized_change_whole_artifact_regression_request.schema.json")
        shutil.copy2(SOURCE_REPORT_SCHEMA, self.root / "Plan/08_SCHEMAS/wave64_localized_change_whole_artifact_regression_report.schema.json")
        shutil.copy2(SOURCE_RULES, self.root / "Plan/10_REGISTRIES/wave64_localized_change_whole_artifact_regression_rules.json")
        shutil.copy2(SOURCE_ROW033_SCHEMA, self.root / "Plan/08_SCHEMAS/wave64_multimodal_scorecard_report.schema.json")
        shutil.copy2(SOURCE_ROW032_SCHEMA, self.root / "Plan/08_SCHEMAS/wave64_global_audio_review_report.schema.json")
        shutil.copy2(SOURCE_WAVE33_CONTRACT, self.root / "Plan/08_SCHEMAS/wave33_preview_qa_report.schema.json")

        self.paths = {
            "baseline_row033": self.root / "runtime_artifacts/baseline_row033.json",
            "candidate_row033": self.root / "runtime_artifacts/candidate_row033.json",
            "row032": self.root / "runtime_artifacts/row032.json",
            "wave33": self.root / "runtime_artifacts/wave33_preview.json",
            "baseline_manifest": self.root / "runtime_artifacts/baseline_manifest.json",
            "candidate_manifest": self.root / "runtime_artifacts/candidate_manifest.json",
            "failure_record": self.root / "runtime_artifacts/failure_record.json",
            "retest_record": self.root / "runtime_artifacts/retest_record.json",
            "delta": self.root / "runtime_artifacts/delta.json",
            "review": self.root / "runtime_artifacts/review.json",
            "runtime_proof": self.root / "runtime_artifacts/runtime_proof.json",
            "baseline_media": self.root / "runtime_artifacts/baseline_primary_media.wav",
            "candidate_media": self.root / "runtime_artifacts/candidate_primary_media.wav",
            "change_manifest": self.root / "runtime_artifacts/change_manifest.json",
            "request": self.root / "runtime_artifacts/request.json",
            "output": self.root / "runtime_artifacts/report.json",
        }
        self._create_base_fixtures()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _rules_path(self) -> Path:
        return self.root / "Plan/10_REGISTRIES/wave64_localized_change_whole_artifact_regression_rules.json"

    def _create_row033(self, artifact_id: str, run_id: str) -> dict[str, Any]:
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "schema_name": "wave64_multimodal_scorecard_report",
            "report_version": 1,
            "artifact_id": artifact_id,
            "reviewer_role": "Codex Desktop autonomous QA",
            "artifact_type": "multimodal_cross_review",
            "generation_test_method": "strict_fixture",
            "lineage": {
                "run_id": run_id,
                "scene_id": "scene_001",
                "shot_id": "shot_001",
                "take_id": "take_001",
                "is_synthetic": False,
                "lineage_match": True,
            },
            "artifact_bindings": {
                "image_review": {"path": "x", "sha256": "a" * 64, "bytes": 1},
                "video_review": {"path": "x", "sha256": "a" * 64, "bytes": 1},
                "strict_audio_report": {"path": "x", "sha256": "a" * 64, "bytes": 1},
                "global_audio_report": {"path": "x", "sha256": "a" * 64, "bytes": 1},
                "av_sync_report": {"path": "x", "sha256": "a" * 64, "bytes": 1},
                "artifact_manifest": {"path": "x", "sha256": "a" * 64, "bytes": 1},
                "release_gate_decision": {"path": "x", "sha256": "a" * 64, "bytes": 1},
            },
            "validation": {
                "request_schema_valid": True,
                "upstream_schema_contracts_valid": True,
                "production_authority_exact_match": True,
                "fixture_authority_exact_match": False,
                "authority_release_binding_valid": True,
                "authority_artifact_binding_valid": True,
                "release_gate_decision_ref_binding_valid": True,
                "source_identity_checks": ["ok"],
                "source_identity_match": True,
                "lineage_checks": ["ok"],
                "binding_checks": ["ok"],
            },
            "scorecard": {
                "categories": [{"category": "specification compliance", "score": 5, "derivation": "all pass"}],
                "required_categories": ["specification compliance"],
                "min_required_score": 3,
                "all_required_categories_meet_minimum": True,
            },
            "defects_summary": [],
            "approval_decision": "approved",
            "next_action": "continue",
            "blockers": [],
            "production_eligibility": {
                "eligible_for_production": True,
                "fixture_only_result": False,
                "authority_id": "prod_auth",
                "bundle_id": "prod_bundle",
            },
            "release_decision": {
                "promotion_decision": "release_runtime_certified",
                "classification": "canonical_release_allowed",
                "is_release_allowed": True,
            },
            "final_decision": {"status": "approved", "exit_code": 0},
            "decision_derivation": {
                "caller_claim_ignored": True,
                "caller_claim_matches_recomputed": True,
                "required_upstream_gates_pass": True,
                "missing_or_untrusted_dependencies": [],
                "present_failing_evidence": [],
                "nonblocking_defects": [],
            },
        }

    def _canonical_partitions(self) -> dict[str, Any]:
        return {
            "visual_domain": {
                "total_frames": 20,
                "width": 1920,
                "height": 1080,
                "timeline_start_frame": 0,
                "timeline_end_frame": 19,
            },
            "audio_domain": {
                "total_samples": 96000,
                "sample_rate_hz": 48000,
                "channel_count": 2,
                "duration_seconds": 2.0,
            },
            "visual_partitions": [
                {
                    "partition_id": "v_target",
                    "start_frame": 0,
                    "end_frame": 9,
                    "x": 0,
                    "y": 0,
                    "width": 1920,
                    "height": 1080,
                },
                {
                    "partition_id": "v_non_target",
                    "start_frame": 10,
                    "end_frame": 19,
                    "x": 0,
                    "y": 0,
                    "width": 1920,
                    "height": 1080,
                },
            ],
            "audio_partitions": [
                {
                    "partition_id": "a_target",
                    "start_sample": 0,
                    "end_sample": 47999,
                    "start_seconds": 0.0,
                    "end_seconds": 1.0,
                    "channel_start": 0,
                    "channel_end": 1,
                    "sample_rate_hz": 48000,
                    "channel_count": 2,
                },
                {
                    "partition_id": "a_non_target",
                    "start_sample": 48000,
                    "end_sample": 95999,
                    "start_seconds": 1.0,
                    "end_seconds": 2.0,
                    "channel_start": 0,
                    "channel_end": 1,
                    "sample_rate_hz": 48000,
                    "channel_count": 2,
                },
            ],
        }

    def _create_base_fixtures(self) -> None:
        self.paths["baseline_media"].write_bytes(b"BASELINE")
        self.paths["candidate_media"].write_bytes(b"CANDIDATE_CHANGED")
        _write_json(self.paths["baseline_row033"], self._create_row033("artifact_base", "run_base"))
        _write_json(self.paths["candidate_row033"], self._create_row033("artifact_cand", "run_cand"))
        _write_json(
            self.paths["row032"],
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "schema_name": "wave64_global_audio_review_report",
                "report_version": 1,
                "review_run_id": "run_review",
                "baseline_run_id": "run_base",
                "candidate_run_id": "run_cand",
                "is_synthetic": False,
                "capture_mode": "technical_capture",
                "artifact_bindings": {
                    "baseline_mix_wav": {"path": "x", "sha256": "a" * 64, "bytes": 10},
                    "candidate_mix_wav": {"path": "x", "sha256": "a" * 64, "bytes": 10},
                    "baseline_row031_strict_report": {"path": "x", "sha256": "a" * 64, "bytes": 1},
                    "candidate_row031_strict_report": {"path": "x", "sha256": "a" * 64, "bytes": 1},
                    "baseline_wave30_event_manifest": {"path": "x", "sha256": "a" * 64, "bytes": 1},
                    "candidate_wave30_event_manifest": {"path": "x", "sha256": "a" * 64, "bytes": 1},
                    "baseline_wave30_mix_manifest": {"path": "x", "sha256": "a" * 64, "bytes": 1},
                    "candidate_wave30_mix_manifest": {"path": "x", "sha256": "a" * 64, "bytes": 1},
                    "baseline_wave30_qa_report": {"path": "x", "sha256": "a" * 64, "bytes": 1},
                    "candidate_wave30_qa_report": {"path": "x", "sha256": "a" * 64, "bytes": 1},
                },
                "localized_change_context": {
                    "change_kind": "visual_localized",
                    "audio_change_expected": False,
                    "target_audio_event_ids": [],
                    "derived_non_target_audio_event_ids": [],
                    "derived_allowed_change_windows_seconds": [],
                    "caller_allowed_change_windows_seconds": [],
                },
                "gates": {
                    "full_duration_playback_review": "PASS",
                    "required_target_audio_check": "PASS",
                    "required_non_target_audio_scan": "PASS",
                    "clipping_noise_voice_ambience_foley_sync_check": "PASS",
                    "reject_on_any_global_audio_defect": "PASS",
                    "promotion_decision": "PASS",
                    "overall_pass": "PASS",
                },
                "computed_metrics": {
                    "outside_target_diff_rms": 0.0,
                    "outside_target_peak_delta": 0.0,
                    "inside_target_diff_rms_per_target": {},
                    "inside_target_diff_rms_min": 0.0,
                    "inside_target_diff_rms_max": 0.0,
                    "candidate_clipping_ratio": 0.0,
                    "candidate_click_ratio": 0.0,
                    "candidate_max_loudness_jump_db": 0.0,
                    "candidate_channel_imbalance_db": 0.0,
                    "candidate_duration_seconds": 1.0,
                    "evaluated_duration_seconds": 1.0,
                    "duration_delta_seconds": 0.0,
                    "worst_channel_index": 0,
                    "channel_count": 1,
                },
                "blockers": [],
                "review_lineage_blockers": [],
                "production_authority_evidence": {
                    "baseline_authority_match": True,
                    "bundle_authority_match": True,
                    "bundle_content_match": True,
                },
                "final_decision": {"overall_status": "PASS", "exit_code": 0},
            },
        )
        _write_json(
            self.paths["wave33"],
            {
                "schema_name": "wave33_preview_qa_report",
                "preview_qa_id": "w33qa-1",
                "preview_id": "preview-1",
                "artifacts": {},
                "candidate_artifact_id": "artifact_cand",
                "candidate_run_id": "run_cand",
                "scene_id": "scene_001",
                "shot_id": "shot_001",
                "take_id": "take_001",
                "scores": {"overall": 0.95},
                "failure_flags": {"blur": False, "artifact": False},
                "rerun_recommendation": "none",
                "promotion_decision": "pass_preview",
            },
        )
        canonical_ids = ["v_target", "v_non_target", "a_target", "a_non_target"]
        for key, artifact_id, run_id in (
            ("baseline_manifest", "artifact_base", "run_base"),
            ("candidate_manifest", "artifact_cand", "run_cand"),
        ):
            _write_json(
                self.paths[key],
                {
                    "schema_name": "wave64_artifact_manifest",
                    "artifact_id": artifact_id,
                    "run_id": run_id,
                    "scene_id": "scene_001",
                    "shot_id": "shot_001",
                    "take_id": "take_001",
                    "is_synthetic": False,
                    "primary_media": _binding(self.paths["baseline_media"] if key == "baseline_manifest" else self.paths["candidate_media"]),
                    "canonical_partition_digest": _sha256_of_obj(self._canonical_partitions()),
                    "partition_ids": canonical_ids,
                    "domain_descriptor": self._canonical_partitions(),
                },
            )
        for row_key, manifest_key in (
            ("baseline_row033", "baseline_manifest"),
            ("candidate_row033", "candidate_manifest"),
        ):
            row033 = json.loads(self.paths[row_key].read_text(encoding="utf-8"))
            row033["artifact_bindings"]["artifact_manifest"] = _binding(self.paths[manifest_key])
            _write_json(self.paths[row_key], row033)
        wave33 = json.loads(self.paths["wave33"].read_text(encoding="utf-8"))
        wave33["artifacts"] = {
            "candidate_primary_media": _binding(self.paths["candidate_media"]),
            "candidate_artifact_manifest_binding": _binding(self.paths["candidate_manifest"]),
        }
        _write_json(self.paths["wave33"], wave33)
        _write_json(
            self.paths["failure_record"],
            {
                "schema_name": "wave64_failure_record",
                "failure_id": "fail-1",
                "failure_classification": "artifact_quality",
                "severity": "high",
                "suspected_cause": "fixture",
                "change_hash": "b" * 64,
                "expected_result_hash": "c" * 64,
                "original_failure_binding": {"path": "", "sha256": "0" * 64, "bytes": 1},
            },
        )
        _write_json(
            self.paths["retest_record"],
            {
                "schema_name": "wave64_retest_record",
                "retest_id": "retest-1",
                "failure_id": "fail-1",
                "attempt_number": 1,
                "change_hash": "b" * 64,
                "expected_result_hash": "c" * 64,
                "material_change": True,
                "final_decision": "conditionally_approved",
            },
        )
        _write_json(
            self.paths["delta"],
            {
                "schema_name": "wave64_localized_change_whole_artifact_delta",
                "target_partition_ids": ["v_target", "a_target"],
                "non_target_partition_ids": ["v_non_target", "a_non_target"],
                "visual_alignment_transform_verified": True,
                "audio_alignment_transform_verified": True,
                "target_findings": [],
                "unrelated_findings": [],
                "baseline_primary_media": _binding(self.paths["baseline_media"]),
                "candidate_primary_media": _binding(self.paths["candidate_media"]),
                "canonical_partition_digest": _sha256_of_obj(self._canonical_partitions()),
            },
        )
        _write_json(
            self.paths["review"],
            {
                "schema_name": "wave64_localized_change_whole_artifact_review",
                "regression_id": "W64-034-regression",
                "change_id": "chg-001",
                "scene_id": "scene_001",
                "shot_id": "shot_001",
                "take_id": "take_001",
                "baseline_artifact_id": "artifact_base",
                "candidate_artifact_id": "artifact_cand",
                "baseline_run_id": "run_base",
                "candidate_run_id": "run_cand",
                "review_run_id": "run_review",
                "target_partition_ids": ["v_target", "a_target"],
                "non_target_partition_ids": ["v_non_target", "a_non_target"],
                "visual_alignment_transform_verified": True,
                "audio_alignment_transform_verified": True,
                "target_only_review": False,
                "candidate_masks_used_as_truth": False,
                "audio_target_proof": True,
                "audio_non_target_proof": True,
                "row032_no_audio_change_identity_proof": True,
                "target_findings": [],
                "unrelated_findings": [],
                "reviewer_identity": {
                    "reviewer_id": "reviewer-qa",
                    "reviewer_role": "Codex Desktop autonomous QA",
                },
                "baseline_primary_media": _binding(self.paths["baseline_media"]),
                "candidate_primary_media": _binding(self.paths["candidate_media"]),
                "canonical_partition_digest": _sha256_of_obj(self._canonical_partitions()),
                "change_manifest_binding": {"path": "", "sha256": "0" * 64, "bytes": 1},
            },
        )
        _write_json(
            self.paths["runtime_proof"],
            {
                "schema_name": "wave64_runtime_proof_record",
                "regression_id": "W64-034-regression",
                "change_id": "chg-001",
                "scene_id": "scene_001",
                "shot_id": "shot_001",
                "take_id": "take_001",
                "baseline_artifact_id": "artifact_base",
                "candidate_artifact_id": "artifact_cand",
                "baseline_run_id": "run_base",
                "candidate_run_id": "run_cand",
                "review_run_id": "run_review",
                "identity": {"producer_id": "producer-1"},
                "baseline_primary_media": _binding(self.paths["baseline_media"]),
                "candidate_primary_media": _binding(self.paths["candidate_media"]),
                "canonical_partition_digest": _sha256_of_obj(self._canonical_partitions()),
                "upstream_report_bindings": {
                    "row032_global_audio_report_binding": _binding(self.paths["row032"]),
                    "baseline_row033_report_binding": _binding(self.paths["baseline_row033"]),
                    "candidate_row033_report_binding": _binding(self.paths["candidate_row033"]),
                },
                "change_manifest_binding": {"path": "", "sha256": "0" * 64, "bytes": 1},
            },
        )
        _write_json(
            self.paths["change_manifest"],
            {
                "schema_name": "wave64_localized_change_manifest",
                "change_kind": "localized_edit",
                "audio_change_expected": False,
                "baseline_primary_media": _binding(self.paths["baseline_media"]),
                "candidate_primary_media": _binding(self.paths["candidate_media"]),
                "canonical_partition_digest": _sha256_of_obj(self._canonical_partitions()),
                "change_summary_hash": "b" * 64,
                "canonical_target_partition_ids": ["v_target", "a_target"],
                "partition_changes": [
                    {
                        "partition_id": "v_target",
                        "mapped_from_partition_id": "v_target",
                        "change_summary_hash": "b" * 64,
                        "before_sha256": "1" * 64,
                        "after_sha256": "2" * 64,
                        "before_region_hash": "3" * 64,
                        "after_region_hash": "4" * 64,
                        "visual_region": {"x": 0, "y": 0, "width": 1920, "height": 1080, "start_frame": 0, "end_frame": 9},
                        "audio_region": {
                            "start_sample": 0,
                            "end_sample": 47999,
                            "start_seconds": 0.0,
                            "end_seconds": 1.0,
                            "channel_start": 0,
                            "channel_end": 1,
                            "sample_rate_hz": 48000,
                            "channel_count": 2,
                        },
                    },
                    {
                        "partition_id": "a_target",
                        "mapped_from_partition_id": "a_target",
                        "change_summary_hash": "b" * 64,
                        "before_sha256": "5" * 64,
                        "after_sha256": "6" * 64,
                        "before_region_hash": "7" * 64,
                        "after_region_hash": "8" * 64,
                        "visual_region": {"x": 0, "y": 0, "width": 1920, "height": 1080, "start_frame": 0, "end_frame": 9},
                        "audio_region": {
                            "start_sample": 0,
                            "end_sample": 47999,
                            "start_seconds": 0.0,
                            "end_seconds": 1.0,
                            "channel_start": 0,
                            "channel_end": 1,
                            "sample_rate_hz": 48000,
                            "channel_count": 2,
                        },
                    },
                ],
            },
        )
        failure_record = json.loads(self.paths["failure_record"].read_text(encoding="utf-8"))
        failure_record["original_failure_binding"] = _binding(self.paths["failure_record"])
        _write_json(self.paths["failure_record"], failure_record)
        review = json.loads(self.paths["review"].read_text(encoding="utf-8"))
        review["change_manifest_binding"] = _binding(self.paths["change_manifest"])
        _write_json(self.paths["review"], review)
        runtime = json.loads(self.paths["runtime_proof"].read_text(encoding="utf-8"))
        runtime["change_manifest_binding"] = _binding(self.paths["change_manifest"])
        _write_json(self.paths["runtime_proof"], runtime)
        self.base_request = {
            "schema_name": "wave64_localized_change_whole_artifact_regression_request",
            "request_version": 3,
            "tracker_id": "TRK-W64-034",
            "item_id": "ITEM-W64-034",
            "regression_id": "W64-034-regression",
            "change_id": "chg-001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "take_id": "take_001",
            "baseline_artifact_id": "artifact_base",
            "candidate_artifact_id": "artifact_cand",
            "baseline_run_id": "run_base",
            "candidate_run_id": "run_cand",
            "review_run_id": "run_review",
            "change_kind": "localized_edit",
            "audio_change_expected": False,
            "production_authority_claim": {"authority_id": "prod_auth", "bundle_id": "prod_bundle"},
            "canonical_partitions": self._canonical_partitions(),
            "target_partition_ids": ["v_target", "a_target"],
            "non_target_partition_ids": ["v_non_target", "a_non_target"],
            "attempt_history": {
                "attempts": [],
                "attempt_history_digest": _sha256_of_obj([]),
                "deeper_diagnosis": {
                    "diagnosis_hash": "d" * 64,
                    "binding": _binding(self.paths["retest_record"]),
                },
                "new_direction_hash": "e" * 64,
            },
            "bindings": {
                "baseline_row033_report_binding": _binding(self.paths["baseline_row033"]),
                "candidate_row033_report_binding": _binding(self.paths["candidate_row033"]),
                "row032_global_audio_report_binding": _binding(self.paths["row032"]),
                "wave33_preview_qa_binding": _binding(self.paths["wave33"]),
                "baseline_artifact_manifest_binding": _binding(self.paths["baseline_manifest"]),
                "candidate_artifact_manifest_binding": _binding(self.paths["candidate_manifest"]),
                "failure_record_binding": _binding(self.paths["failure_record"]),
                "retest_record_binding": _binding(self.paths["retest_record"]),
                "whole_artifact_delta_binding": _binding(self.paths["delta"]),
                "whole_artifact_review_binding": _binding(self.paths["review"]),
                "runtime_proof_binding": _binding(self.paths["runtime_proof"]),
                "baseline_primary_media_binding": _binding(self.paths["baseline_media"]),
                "candidate_primary_media_binding": _binding(self.paths["candidate_media"]),
                "change_manifest_binding": _binding(self.paths["change_manifest"]),
            },
            "output_report_path": str(self.paths["output"].resolve()),
        }

    def _authority_object(self, request: dict[str, Any]) -> dict[str, Any]:
        authority = {
            "authority_id": request["production_authority_claim"]["authority_id"],
            "bundle_id": request["production_authority_claim"]["bundle_id"],
            "regression_id": request["regression_id"],
            "change_id": request["change_id"],
            "scene_id": request["scene_id"],
            "shot_id": request["shot_id"],
            "take_id": request["take_id"],
            "baseline_artifact_id": request["baseline_artifact_id"],
            "candidate_artifact_id": request["candidate_artifact_id"],
            "baseline_run_id": request["baseline_run_id"],
            "candidate_run_id": request["candidate_run_id"],
            "review_run_id": request["review_run_id"],
            "change_kind": request["change_kind"],
            "audio_change_expected": request["audio_change_expected"],
            "current_attempt_number": 1,
            "attempt_history_digest": request["attempt_history"]["attempt_history_digest"],
            "canonical_partition_digest": _sha256_of_obj(request["canonical_partitions"]),
            "producer_id": "producer-1",
            "reviewer_id": "reviewer-qa",
            "reviewer_role": "Codex Desktop autonomous QA",
            "change_summary_hash": "b" * 64,
            "input_bindings": {},
        }
        for key, binding in request["bindings"].items():
            authority["input_bindings"][key] = {
                "path": Path(binding["path"]).resolve().relative_to(self.root).as_posix(),
                "sha256": binding["sha256"],
                "bytes": binding["bytes"],
            }
        return authority

    def _set_authority(self, request: dict[str, Any], mode: str) -> None:
        rules = json.loads(self._rules_path().read_text(encoding="utf-8"))
        if mode == "none":
            rules["authority_rules"]["production_authority_exact_objects"] = []
            rules["authority_rules"]["fixture_authority_exact_objects"] = []
        elif mode == "fixture":
            rules["authority_rules"]["fixture_authority_exact_objects"] = [self._authority_object(request)]
            rules["authority_rules"]["production_authority_exact_objects"] = []
        elif mode == "production":
            rules["authority_rules"]["production_authority_exact_objects"] = [self._authority_object(request)]
            rules["authority_rules"]["fixture_authority_exact_objects"] = []
        else:
            raise ValueError(mode)
        _write_json(self._rules_path(), rules)

    def _run(self, request: dict[str, Any], authority_mode: str) -> subprocess.CompletedProcess[str]:
        if self.paths["output"].exists():
            self.paths["output"].unlink()
        self._set_authority(request, authority_mode)
        _write_json(self.paths["request"], request)
        return subprocess.run(
            [
                sys.executable,
                str(self.root / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_localized_change_whole_artifact_regression.py"),
                "--input",
                str(self.paths["request"]),
                "--output",
                str(self.paths["output"]),
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def _report(self) -> dict[str, Any]:
        return json.loads(self.paths["output"].read_text(encoding="utf-8"))

    def _run_blocked(self, request: dict[str, Any], authority_mode: str = "fixture") -> dict[str, Any]:
        result = self._run(request, authority_mode)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        report = self._report()
        self.assertEqual(report["decision"], "blocked")
        return report

    def _assert_record_schema_name_blocks(self, path_key: str, binding_name: str) -> None:
        record = json.loads(self.paths[path_key].read_text(encoding="utf-8"))
        record["schema_name"] = "wrong_contract"
        _write_json(self.paths[path_key], record)
        request = copy.deepcopy(self.base_request)
        request["bindings"][binding_name] = _binding(self.paths[path_key])
        report = self._run_blocked(request)
        self.assertTrue(any("schema_name mismatch" in blocker for blocker in report["blockers"]))

    def _attempt_fixture(
        self,
        number: int,
        similar: bool,
        diagnosis_hash: str | None = None,
        direction_hash: str | None = None,
    ) -> dict[str, Any]:
        attempt = _attempt(number, similar, diagnosis_hash, direction_hash)
        attempt["result_report_binding"] = _binding(self.paths["review"])
        return attempt

    def test_01_fixture_and_production_paths(self) -> None:
        fixture = self._run(copy.deepcopy(self.base_request), "fixture")
        self.assertEqual(fixture.returncode, 0, fixture.stdout + fixture.stderr)
        self.assertEqual(self._report()["decision"], "conditionally_approved")
        production = self._run(copy.deepcopy(self.base_request), "production")
        self.assertEqual(production.returncode, 0, production.stdout + production.stderr)
        self.assertEqual(self._report()["decision"], "approved")
    def test_02_change_kind_audio_contradiction_rejected_early(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["change_kind"] = "audio_repair"
        request["audio_change_expected"] = False
        result = self._run(request, "fixture")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.paths["output"].exists())

    def test_03_malformed_bound_json_blocks_not_exit1(self) -> None:
        self.paths["review"].write_text("{ bad json", encoding="utf-8")
        request = copy.deepcopy(self.base_request)
        request["bindings"]["whole_artifact_review_binding"] = _binding(self.paths["review"])
        report = self._run_blocked(request)
        self.assertTrue(any("malformed nested custom record" in b for b in report["blockers"]))

    def test_04_missing_dict_blocks(self) -> None:
        review = json.loads(self.paths["review"].read_text(encoding="utf-8"))
        review["reviewer_identity"] = []
        _write_json(self.paths["review"], review)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["whole_artifact_review_binding"] = _binding(self.paths["review"])
        self._run_blocked(request)

    def test_05_wrong_list_blocks(self) -> None:
        delta = json.loads(self.paths["delta"].read_text(encoding="utf-8"))
        delta["target_findings"] = {}
        _write_json(self.paths["delta"], delta)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["whole_artifact_delta_binding"] = _binding(self.paths["delta"])
        self._run_blocked(request)

    def test_06_missing_failure_record_field_blocks(self) -> None:
        failure = json.loads(self.paths["failure_record"].read_text(encoding="utf-8"))
        del failure["severity"]
        _write_json(self.paths["failure_record"], failure)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["failure_record_binding"] = _binding(self.paths["failure_record"])
        self._run_blocked(request)

    def test_07_unknown_custom_key_blocks(self) -> None:
        delta = json.loads(self.paths["delta"].read_text(encoding="utf-8"))
        delta["unknown"] = True
        _write_json(self.paths["delta"], delta)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["whole_artifact_delta_binding"] = _binding(self.paths["delta"])
        self._run_blocked(request)

    def test_08_truthy_string_bool_blocks(self) -> None:
        review = json.loads(self.paths["review"].read_text(encoding="utf-8"))
        review["candidate_masks_used_as_truth"] = "false"
        _write_json(self.paths["review"], review)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["whole_artifact_review_binding"] = _binding(self.paths["review"])
        self._run_blocked(request)

    def test_09_numeric_string_in_custom_record_blocks(self) -> None:
        review = json.loads(self.paths["review"].read_text(encoding="utf-8"))
        review["row032_no_audio_change_identity_proof"] = "1"
        _write_json(self.paths["review"], review)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["whole_artifact_review_binding"] = _binding(self.paths["review"])
        self._run_blocked(request)

    def test_10_visual_overlap_blocks(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["canonical_partitions"]["visual_partitions"][1]["start_frame"] = 9
        self._run_blocked(request)

    def test_11_visual_interior_gap_blocks(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["canonical_partitions"]["visual_partitions"][1]["start_frame"] = 11
        self._run_blocked(request)

    def test_12_visual_edge_gap_blocks(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["canonical_partitions"]["visual_partitions"][0]["start_frame"] = 1
        self._run_blocked(request)

    def test_13_audio_out_of_bounds_blocks(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["canonical_partitions"]["audio_partitions"][1]["end_sample"] = 96000
        self._run_blocked(request)

    def test_14_audio_timing_mismatch_blocks(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["canonical_partitions"]["audio_partitions"][0]["end_seconds"] = 1.1
        self._run_blocked(request)

    def test_15_audio_channel_mismatch_blocks(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["canonical_partitions"]["audio_partitions"][0]["channel_count"] = 1
        self._run_blocked(request)

    def test_16_duplicate_cross_domain_partition_id_blocks(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["canonical_partitions"]["audio_partitions"][0]["partition_id"] = "v_target"
        self._run_blocked(request)

    def test_17_manifest_media_mismatch_blocks(self) -> None:
        manifest = json.loads(self.paths["candidate_manifest"].read_text(encoding="utf-8"))
        manifest["primary_media"]["sha256"] = "0" * 64
        _write_json(self.paths["candidate_manifest"], manifest)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["candidate_artifact_manifest_binding"] = _binding(self.paths["candidate_manifest"])
        self._run_blocked(request)

    def test_18_delta_media_mismatch_blocks(self) -> None:
        delta = json.loads(self.paths["delta"].read_text(encoding="utf-8"))
        delta["candidate_primary_media"]["bytes"] = 1
        _write_json(self.paths["delta"], delta)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["whole_artifact_delta_binding"] = _binding(self.paths["delta"])
        self._run_blocked(request)

    def test_19_review_media_mismatch_blocks(self) -> None:
        review = json.loads(self.paths["review"].read_text(encoding="utf-8"))
        review["baseline_primary_media"]["sha256"] = "0" * 64
        _write_json(self.paths["review"], review)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["whole_artifact_review_binding"] = _binding(self.paths["review"])
        self._run_blocked(request)

    def test_20_runtime_media_mismatch_blocks(self) -> None:
        runtime = json.loads(self.paths["runtime_proof"].read_text(encoding="utf-8"))
        runtime["candidate_primary_media"]["path"] = "bad"
        _write_json(self.paths["runtime_proof"], runtime)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["runtime_proof_binding"] = _binding(self.paths["runtime_proof"])
        self._run_blocked(request)

    def test_21_change_manifest_target_mapping_mismatch_blocks(self) -> None:
        cm = json.loads(self.paths["change_manifest"].read_text(encoding="utf-8"))
        cm["partition_changes"][0]["partition_id"] = "v_non_target"
        _write_json(self.paths["change_manifest"], cm)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["change_manifest_binding"] = _binding(self.paths["change_manifest"])
        self._run_blocked(request)

    def test_22_change_manifest_hash_mismatch_blocks(self) -> None:
        cm = json.loads(self.paths["change_manifest"].read_text(encoding="utf-8"))
        cm["partition_changes"][0]["change_summary_hash"] = "f" * 64
        _write_json(self.paths["change_manifest"], cm)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["change_manifest_binding"] = _binding(self.paths["change_manifest"])
        self._run_blocked(request)

    def test_23_change_manifest_no_material_change_blocks(self) -> None:
        cm = json.loads(self.paths["change_manifest"].read_text(encoding="utf-8"))
        for change in cm["partition_changes"]:
            change["after_sha256"] = change["before_sha256"]
            change["after_region_hash"] = change["before_region_hash"]
        _write_json(self.paths["change_manifest"], cm)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["change_manifest_binding"] = _binding(self.paths["change_manifest"])
        report = self._run_blocked(request)
        self.assertFalse(report["recomputed_gate_results"]["before_after_delta"])

    def test_24_delta_only_unrelated_defect_rejected(self) -> None:
        delta = json.loads(self.paths["delta"].read_text(encoding="utf-8"))
        delta["unrelated_findings"] = [
            {
                "finding_id": "u1",
                "partition_id": "v_non_target",
                "classification": "artifact",
                "severity": "high",
                "baseline_present": False,
                "candidate_present": True,
                "disposition": "new_defect",
            }
        ]
        review = json.loads(self.paths["review"].read_text(encoding="utf-8"))
        review["unrelated_findings"] = copy.deepcopy(delta["unrelated_findings"])
        _write_json(self.paths["delta"], delta)
        _write_json(self.paths["review"], review)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["whole_artifact_delta_binding"] = _binding(self.paths["delta"])
        request["bindings"]["whole_artifact_review_binding"] = _binding(self.paths["review"])
        result = self._run(request, "fixture")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["decision"], "rejected")

    def test_25_finding_partition_mismatch_blocks(self) -> None:
        review = json.loads(self.paths["review"].read_text(encoding="utf-8"))
        review["target_findings"] = [
            {
                "finding_id": "t1",
                "partition_id": "unknown",
                "classification": "regression",
                "severity": "high",
                "baseline_present": False,
                "candidate_present": True,
                "disposition": "regression",
            }
        ]
        _write_json(self.paths["review"], review)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["whole_artifact_review_binding"] = _binding(self.paths["review"])
        self._run_blocked(request)

    def test_26_duplicate_finding_id_blocks(self) -> None:
        finding = {
            "finding_id": "dup",
            "partition_id": "v_target",
            "classification": "regression",
            "severity": "high",
            "baseline_present": False,
            "candidate_present": True,
            "disposition": "regression",
        }
        review = json.loads(self.paths["review"].read_text(encoding="utf-8"))
        review["target_findings"] = [finding]
        review["unrelated_findings"] = [dict(finding, partition_id="a_non_target")]
        _write_json(self.paths["review"], review)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["whole_artifact_review_binding"] = _binding(self.paths["review"])
        self._run_blocked(request)

    def test_27_row033_identity_mismatch_blocks(self) -> None:
        row = json.loads(self.paths["candidate_row033"].read_text(encoding="utf-8"))
        row["artifact_id"] = "wrong"
        _write_json(self.paths["candidate_row033"], row)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["candidate_row033_report_binding"] = _binding(self.paths["candidate_row033"])
        self._run_blocked(request)

    def test_28_row032_authority_boolean_false_rejects(self) -> None:
        row = json.loads(self.paths["row032"].read_text(encoding="utf-8"))
        row["production_authority_evidence"]["bundle_content_match"] = False
        _write_json(self.paths["row032"], row)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["row032_global_audio_report_binding"] = _binding(self.paths["row032"])
        result = self._run(request, "fixture")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["decision"], "rejected")

    def test_29_wave33_failure_flag_true_rejects(self) -> None:
        w = json.loads(self.paths["wave33"].read_text(encoding="utf-8"))
        w["failure_flags"]["blur"] = True
        _write_json(self.paths["wave33"], w)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["wave33_preview_qa_binding"] = _binding(self.paths["wave33"])
        result = self._run(request, "fixture")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["decision"], "rejected")

    def test_30_self_review_blocked(self) -> None:
        runtime = json.loads(self.paths["runtime_proof"].read_text(encoding="utf-8"))
        runtime["identity"]["producer_id"] = "reviewer-qa"
        _write_json(self.paths["runtime_proof"], runtime)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["runtime_proof_binding"] = _binding(self.paths["runtime_proof"])
        self._run_blocked(request)

    def test_31_nonsequential_attempt_numbers_block(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["attempt_history"]["attempts"] = [
            self._attempt_fixture(1, True),
            self._attempt_fixture(3, True),
        ]
        request["attempt_history"]["attempt_history_digest"] = _sha256_of_obj(request["attempt_history"]["attempts"])
        self._run_blocked(request)

    def test_32_attempt_history_digest_spoof_blocks(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["attempt_history"]["attempts"] = [self._attempt_fixture(1, True)]
        request["attempt_history"]["attempt_history_digest"] = "0" * 64
        self._run_blocked(request)

    def test_33_missing_material_change_blocks(self) -> None:
        retest = json.loads(self.paths["retest_record"].read_text(encoding="utf-8"))
        retest["material_change"] = False
        _write_json(self.paths["retest_record"], retest)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["retest_record_binding"] = _binding(self.paths["retest_record"])
        self._run_blocked(request)

    def test_34_diagnosis_reuse_blocks(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["attempt_history"]["attempts"] = [
            self._attempt_fixture(1, True, diagnosis_hash="d" * 64),
            self._attempt_fixture(2, True, diagnosis_hash="e" * 64),
        ]
        request["attempt_history"]["attempt_history_digest"] = _sha256_of_obj(request["attempt_history"]["attempts"])
        request["attempt_history"]["deeper_diagnosis"]["diagnosis_hash"] = "e" * 64
        self._run_blocked(request)

    def test_35_fifth_similar_failure_remains_blocked(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["attempt_history"]["attempts"] = [
            self._attempt_fixture(1, True, direction_hash="1" * 64),
            self._attempt_fixture(2, True, direction_hash="2" * 64),
            self._attempt_fixture(3, True, direction_hash="3" * 64),
            self._attempt_fixture(4, True, direction_hash="4" * 64),
        ]
        request["attempt_history"]["attempt_history_digest"] = _sha256_of_obj(request["attempt_history"]["attempts"])
        self._run_blocked(request)

    def test_36_duplicate_authority_pair_blocks(self) -> None:
        request = copy.deepcopy(self.base_request)
        rules = json.loads(self._rules_path().read_text(encoding="utf-8"))
        auth = self._authority_object(request)
        rules["authority_rules"]["production_authority_exact_objects"] = [auth]
        rules["authority_rules"]["fixture_authority_exact_objects"] = [copy.deepcopy(auth)]
        _write_json(self._rules_path(), rules)
        result = self._run(request, "none")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["decision"], "blocked")

    def test_37_report_policy_surface_present(self) -> None:
        self._run(copy.deepcopy(self.base_request), "fixture")
        report = self._report()
        self.assertIn("mask_authority_promoted", report["validation"])
        self.assertIn("candidate_masks_used_as_truth", report["validation"])
        self.assertIn("wave70_hard_gate_claimed", report["validation"])
        self.assertIn("wave71_activated", report["validation"])
        self.assertFalse(report["validation"]["mask_authority_promoted"])
        self.assertFalse(report["validation"]["candidate_masks_used_as_truth"])
        self.assertFalse(report["validation"]["wave70_hard_gate_claimed"])
        self.assertFalse(report["validation"]["wave71_activated"])

    def test_38_rejected_reports_preserve_blockers(self) -> None:
        review = json.loads(self.paths["review"].read_text(encoding="utf-8"))
        review["unrelated_findings"] = [
            {
                "finding_id": "u1",
                "partition_id": "v_non_target",
                "classification": "artifact",
                "severity": "high",
                "baseline_present": False,
                "candidate_present": True,
                "disposition": "new_defect",
            }
        ]
        row032 = json.loads(self.paths["row032"].read_text(encoding="utf-8"))
        row032["candidate_run_id"] = "wrong"
        _write_json(self.paths["review"], review)
        _write_json(self.paths["row032"], row032)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["whole_artifact_review_binding"] = _binding(self.paths["review"])
        request["bindings"]["row032_global_audio_report_binding"] = _binding(self.paths["row032"])
        result = self._run(request, "fixture")
        self.assertEqual(result.returncode, 2)
        report = self._report()
        self.assertEqual(report["decision"], "rejected")
        self.assertGreater(len(report["blockers"]), 0)

    def test_39_contradictory_finding_disposition_blocks(self) -> None:
        finding = {
            "finding_id": "persisting-but-labeled-pass",
            "partition_id": "v_target",
            "classification": "artifact",
            "severity": "high",
            "baseline_present": True,
            "candidate_present": True,
            "disposition": "pass",
        }
        for key in ("delta", "review"):
            record = json.loads(self.paths[key].read_text(encoding="utf-8"))
            record["target_findings"] = [copy.deepcopy(finding)]
            _write_json(self.paths[key], record)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["whole_artifact_delta_binding"] = _binding(self.paths["delta"])
        request["bindings"]["whole_artifact_review_binding"] = _binding(self.paths["review"])
        report = self._run_blocked(request)
        self.assertTrue(any("contradicts" in blocker for blocker in report["blockers"]))

    def test_40_byte_identical_primary_media_cannot_claim_material_change(self) -> None:
        request = copy.deepcopy(self.base_request)
        self.paths["candidate_media"].write_bytes(self.paths["baseline_media"].read_bytes())
        candidate_media_binding = _binding(self.paths["candidate_media"])

        candidate_manifest = json.loads(self.paths["candidate_manifest"].read_text(encoding="utf-8"))
        candidate_manifest["primary_media"] = candidate_media_binding
        _write_json(self.paths["candidate_manifest"], candidate_manifest)

        candidate_row033 = json.loads(self.paths["candidate_row033"].read_text(encoding="utf-8"))
        candidate_row033["artifact_bindings"]["artifact_manifest"] = _binding(self.paths["candidate_manifest"])
        _write_json(self.paths["candidate_row033"], candidate_row033)

        wave33 = json.loads(self.paths["wave33"].read_text(encoding="utf-8"))
        wave33["artifacts"]["candidate_primary_media"] = candidate_media_binding
        wave33["artifacts"]["candidate_artifact_manifest_binding"] = _binding(self.paths["candidate_manifest"])
        _write_json(self.paths["wave33"], wave33)

        change_manifest = json.loads(self.paths["change_manifest"].read_text(encoding="utf-8"))
        change_manifest["candidate_primary_media"] = candidate_media_binding
        _write_json(self.paths["change_manifest"], change_manifest)
        change_manifest_binding = _binding(self.paths["change_manifest"])

        delta = json.loads(self.paths["delta"].read_text(encoding="utf-8"))
        delta["candidate_primary_media"] = candidate_media_binding
        _write_json(self.paths["delta"], delta)

        review = json.loads(self.paths["review"].read_text(encoding="utf-8"))
        review["candidate_primary_media"] = candidate_media_binding
        review["change_manifest_binding"] = change_manifest_binding
        _write_json(self.paths["review"], review)

        runtime = json.loads(self.paths["runtime_proof"].read_text(encoding="utf-8"))
        runtime["candidate_primary_media"] = candidate_media_binding
        runtime["change_manifest_binding"] = change_manifest_binding
        runtime["upstream_report_bindings"]["candidate_row033_report_binding"] = _binding(
            self.paths["candidate_row033"]
        )
        _write_json(self.paths["runtime_proof"], runtime)

        request["bindings"]["candidate_primary_media_binding"] = candidate_media_binding
        request["bindings"]["candidate_artifact_manifest_binding"] = _binding(self.paths["candidate_manifest"])
        request["bindings"]["candidate_row033_report_binding"] = _binding(self.paths["candidate_row033"])
        request["bindings"]["wave33_preview_qa_binding"] = _binding(self.paths["wave33"])
        request["bindings"]["change_manifest_binding"] = change_manifest_binding
        request["bindings"]["whole_artifact_delta_binding"] = _binding(self.paths["delta"])
        request["bindings"]["whole_artifact_review_binding"] = _binding(self.paths["review"])
        request["bindings"]["runtime_proof_binding"] = _binding(self.paths["runtime_proof"])
        report = self._run_blocked(request)
        self.assertFalse(report["recomputed_gate_results"]["before_after_delta"])
        self.assertTrue(any("distinct baseline and candidate" in blocker for blocker in report["blockers"]))

    def test_41_attempt_policy_truth_surface_is_true_for_valid_history(self) -> None:
        result = self._run(copy.deepcopy(self.base_request), "fixture")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self._report()["protocol"]["attempt_policy_ok"])

    def test_42_delta_schema_name_mismatch_blocks(self) -> None:
        self._assert_record_schema_name_blocks("delta", "whole_artifact_delta_binding")

    def test_43_review_schema_name_mismatch_blocks(self) -> None:
        self._assert_record_schema_name_blocks("review", "whole_artifact_review_binding")

    def test_44_runtime_schema_name_mismatch_blocks(self) -> None:
        self._assert_record_schema_name_blocks("runtime_proof", "runtime_proof_binding")

    def test_45_failure_schema_name_mismatch_blocks(self) -> None:
        self._assert_record_schema_name_blocks("failure_record", "failure_record_binding")

    def test_46_retest_schema_name_mismatch_blocks(self) -> None:
        self._assert_record_schema_name_blocks("retest_record", "retest_record_binding")

    def test_47_target_finding_must_use_target_partition(self) -> None:
        finding = {
            "finding_id": "misfiled-target",
            "partition_id": "v_non_target",
            "classification": "artifact",
            "severity": "high",
            "baseline_present": False,
            "candidate_present": True,
            "disposition": "new_defect",
        }
        for key in ("delta", "review"):
            record = json.loads(self.paths[key].read_text(encoding="utf-8"))
            record["target_findings"] = [copy.deepcopy(finding)]
            _write_json(self.paths[key], record)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["whole_artifact_delta_binding"] = _binding(self.paths["delta"])
        request["bindings"]["whole_artifact_review_binding"] = _binding(self.paths["review"])
        self._run_blocked(request)

    def test_48_row033_source_identity_false_blocks(self) -> None:
        row = json.loads(self.paths["candidate_row033"].read_text(encoding="utf-8"))
        row["validation"]["source_identity_match"] = False
        _write_json(self.paths["candidate_row033"], row)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["candidate_row033_report_binding"] = _binding(self.paths["candidate_row033"])
        self._run_blocked(request)

    def test_49_row032_change_context_mismatch_blocks(self) -> None:
        row = json.loads(self.paths["row032"].read_text(encoding="utf-8"))
        row["localized_change_context"]["change_kind"] = "audio_localized"
        _write_json(self.paths["row032"], row)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["row032_global_audio_report_binding"] = _binding(self.paths["row032"])
        self._run_blocked(request)

    def test_50_row032_gate_failure_rejects(self) -> None:
        row = json.loads(self.paths["row032"].read_text(encoding="utf-8"))
        row["gates"]["overall_pass"] = "FAIL"
        _write_json(self.paths["row032"], row)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["row032_global_audio_report_binding"] = _binding(self.paths["row032"])
        result = self._run(request, "fixture")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(self._report()["decision"], "rejected")

    def test_51_untrusted_top_level_binding_blocks_with_report(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["bindings"]["candidate_primary_media_binding"]["sha256"] = "0" * 64
        result = self._run(request, "fixture")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        report = self._report()
        self.assertEqual(report["decision"], "blocked")
        self.assertTrue(any("untrusted top-level binding" in blocker for blocker in report["blockers"]))

    def test_52_wave33_schema_name_mismatch_blocks(self) -> None:
        wave33 = json.loads(self.paths["wave33"].read_text(encoding="utf-8"))
        wave33["schema_name"] = "wrong_contract"
        _write_json(self.paths["wave33"], wave33)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["wave33_preview_qa_binding"] = _binding(self.paths["wave33"])
        report = self._run_blocked(request)
        self.assertTrue(any("wave33 schema_name mismatch" in blocker for blocker in report["blockers"]))

    def test_53_wave33_canonical_artifact_binding_mismatch_blocks(self) -> None:
        wave33 = json.loads(self.paths["wave33"].read_text(encoding="utf-8"))
        wave33["artifacts"]["candidate_primary_media"]["sha256"] = "0" * 64
        _write_json(self.paths["wave33"], wave33)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["wave33_preview_qa_binding"] = _binding(self.paths["wave33"])
        self._run_blocked(request)

    def test_54_invalid_attempt_policy_reports_false(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["attempt_history"]["attempts"] = [self._attempt_fixture(2, True)]
        request["attempt_history"]["attempt_history_digest"] = _sha256_of_obj(
            request["attempt_history"]["attempts"]
        )
        report = self._run_blocked(request)
        self.assertFalse(report["protocol"]["attempt_policy_ok"])

    def test_55_unrelated_scan_and_reject_gates_are_distinct(self) -> None:
        finding = {
            "finding_id": "new-unrelated-defect",
            "partition_id": "v_non_target",
            "classification": "artifact",
            "severity": "high",
            "baseline_present": False,
            "candidate_present": True,
            "disposition": "new_defect",
        }
        for key in ("delta", "review"):
            record = json.loads(self.paths[key].read_text(encoding="utf-8"))
            record["unrelated_findings"] = [copy.deepcopy(finding)]
            _write_json(self.paths[key], record)
        request = copy.deepcopy(self.base_request)
        request["bindings"]["whole_artifact_delta_binding"] = _binding(self.paths["delta"])
        request["bindings"]["whole_artifact_review_binding"] = _binding(self.paths["review"])
        result = self._run(request, "fixture")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        report = self._report()
        self.assertEqual(report["decision"], "rejected")
        self.assertTrue(report["recomputed_gate_results"]["unrelated_defect_scan"])
        self.assertFalse(report["recomputed_gate_results"]["reject_on_new_defect"])

    def test_56_similarity_declaration_cannot_hide_identical_hash(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["attempt_history"]["attempts"] = [
            self._attempt_fixture(1, False),
            self._attempt_fixture(2, False),
        ]
        request["attempt_history"]["attempt_history_digest"] = _sha256_of_obj(
            request["attempt_history"]["attempts"]
        )
        report = self._run_blocked(request)
        self.assertEqual(report["protocol"]["similar_failure_count"], 2)
        self.assertTrue(any("contradicts change_summary_hash" in blocker for blocker in report["blockers"]))

    def test_57_fourth_similar_attempt_blocks_after_three_prior(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["attempt_history"]["attempts"] = [
            self._attempt_fixture(1, True, direction_hash="1" * 64),
            self._attempt_fixture(2, True, direction_hash="2" * 64),
            self._attempt_fixture(3, True, direction_hash="3" * 64),
        ]
        request["attempt_history"]["attempt_history_digest"] = _sha256_of_obj(
            request["attempt_history"]["attempts"]
        )
        report = self._run_blocked(request)
        self.assertEqual(report["protocol"]["similar_failure_count"], 3)
        self.assertTrue(any("block the fourth attempt" in blocker for blocker in report["blockers"]))

    def test_58_empty_authority_registry_preserves_explicit_blocker(self) -> None:
        result = self._run(copy.deepcopy(self.base_request), "none")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        report = self._report()
        self.assertEqual(report["decision"], "blocked")
        self.assertFalse(report["production_eligibility"]["eligible_for_production"])
        self.assertTrue(any("no exact production or fixture authority" in blocker for blocker in report["blockers"]))


def _sha256_of_obj(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _attempt(number: int, similar: bool, diagnosis_hash: str | None = None, direction_hash: str | None = None) -> dict[str, Any]:
    return {
        "attempt_number": number,
        "failure_classification": "artifact_quality",
        "severity": "high",
        "diagnosis_id": f"diag-{number}",
        "diagnosis_hash": diagnosis_hash or f"{number}" * 64,
        "change_hash": "9" * 64,
        "expected_result_hash": "8" * 64,
        "change_summary_hash": "b" * 64,
        "result": "failed",
        "result_report_binding": {"path": "runtime_artifacts/review.json", "sha256": "a" * 64, "bytes": 1},
        "similar_to_current": similar,
        "new_direction_hash": direction_hash or f"{number + 1}" * 64,
    }


if __name__ == "__main__":
    unittest.main()
