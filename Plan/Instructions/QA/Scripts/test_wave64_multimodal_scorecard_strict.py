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
SOURCE_SCRIPT = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_multimodal_scorecard.py"
SOURCE_SPEC = REPO_ROOT / "Plan/06_QA_TESTING/WAVE64_MULTIMODAL_SCORECARD_GATE_SPEC.md"
SOURCE_REQUEST_SCHEMA = REPO_ROOT / "Plan/08_SCHEMAS/wave64_multimodal_scorecard_request.schema.json"
SOURCE_REPORT_SCHEMA = REPO_ROOT / "Plan/08_SCHEMAS/wave64_multimodal_scorecard_report.schema.json"
SOURCE_RULES = REPO_ROOT / "Plan/10_REGISTRIES/wave64_multimodal_scorecard_rules.json"
SOURCE_STRICT_AUDIO_SCHEMA = REPO_ROOT / "Plan/08_SCHEMAS/wave64_strict_audio_review_report.schema.json"
SOURCE_GLOBAL_AUDIO_SCHEMA = REPO_ROOT / "Plan/08_SCHEMAS/wave64_global_audio_review_report.schema.json"
SOURCE_AV_SYNC_SCHEMA = REPO_ROOT / "Plan/08_SCHEMAS/wave64_av_sync_certification_report.schema.json"
SOURCE_W34_MANIFEST = REPO_ROOT / "Plan/08_SCHEMAS/wave34_release_manifest.schema.json"
SOURCE_W34_DECISION = REPO_ROOT / "Plan/08_SCHEMAS/wave34_release_gate_decision.schema.json"
RELEASE_ALLOWED = {
    "release_architecture_pack",
    "release_runtime_certified",
    "release_with_runtime_boundaries",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _binding(path: Path) -> dict[str, Any]:
    return {"path": str(path.resolve()), "sha256": _sha256(path), "bytes": path.stat().st_size}


def _canonical_promotion_decisions(decision_schema: dict[str, Any]) -> set[str]:
    found: set[str] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                lowered = key.lower()
                if "promotion" in lowered and isinstance(value, list):
                    if all(isinstance(item, str) and item.strip() for item in value):
                        for item in value:
                            found.add(item.strip())
                if key == "promotion_decision" and isinstance(value, dict):
                    enum_values = value.get("enum")
                    if isinstance(enum_values, list):
                        for item in enum_values:
                            if isinstance(item, str):
                                found.add(item.strip())
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(decision_schema)
    return found


class Wave64MultimodalScorecardStrictTests(unittest.TestCase):
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
        shutil.copy2(SOURCE_SCRIPT, self.root / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_multimodal_scorecard.py")
        shutil.copy2(SOURCE_SPEC, self.root / "Plan/06_QA_TESTING/WAVE64_MULTIMODAL_SCORECARD_GATE_SPEC.md")
        shutil.copy2(SOURCE_REQUEST_SCHEMA, self.root / "Plan/08_SCHEMAS/wave64_multimodal_scorecard_request.schema.json")
        shutil.copy2(SOURCE_REPORT_SCHEMA, self.root / "Plan/08_SCHEMAS/wave64_multimodal_scorecard_report.schema.json")
        shutil.copy2(SOURCE_RULES, self.root / "Plan/10_REGISTRIES/wave64_multimodal_scorecard_rules.json")
        shutil.copy2(SOURCE_STRICT_AUDIO_SCHEMA, self.root / "Plan/08_SCHEMAS/wave64_strict_audio_review_report.schema.json")
        shutil.copy2(SOURCE_GLOBAL_AUDIO_SCHEMA, self.root / "Plan/08_SCHEMAS/wave64_global_audio_review_report.schema.json")
        shutil.copy2(SOURCE_AV_SYNC_SCHEMA, self.root / "Plan/08_SCHEMAS/wave64_av_sync_certification_report.schema.json")
        shutil.copy2(SOURCE_W34_MANIFEST, self.root / "Plan/08_SCHEMAS/wave34_release_manifest.schema.json")
        shutil.copy2(SOURCE_W34_DECISION, self.root / "Plan/08_SCHEMAS/wave34_release_gate_decision.schema.json")

        self.image_path = self.root / "runtime_artifacts/image.json"
        self.video_path = self.root / "runtime_artifacts/video.json"
        self.strict_audio_path = self.root / "runtime_artifacts/strict_audio.json"
        self.global_audio_path = self.root / "runtime_artifacts/global_audio.json"
        self.av_sync_path = self.root / "runtime_artifacts/av_sync.json"
        self.manifest_path = self.root / "runtime_artifacts/release_manifest.json"
        self.release_path = self.root / "runtime_artifacts/release_decision.json"
        self.request_path = self.root / "runtime_artifacts/request.json"
        self.output_path = self.root / "runtime_artifacts/report.json"
        self._create_base_fixtures()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _create_base_fixtures(self) -> None:
        lineage = {"run_id": "run_001", "scene_id": "scene_001", "shot_id": "shot_001", "take_id": "take_001", "is_synthetic": False}
        image = {
            "schema_version": "1.0",
            "evidence_id": "ITEM-W64-033",
            "tracker_id": "TRK-W64-018",
            "item_id": "ITEM-W64-018",
            "status_decision": "Pass_Image",
            "overall_pass": True,
            "technical_pass": True,
            "acceptance_gates": {
                "camera_spec_check": True,
                "crop_boundary_check": True,
                "visual_runtime_ready": True,
                "image_realism_check": True,
                "anatomy_check": True,
                "hyperreal_visual_review": True,
                "global_visual_review": True,
                "multi_sample_certification": True,
                "prompt_alignment_check": True,
                "contamination_resistance_check": True,
            },
            "strict_decision": {"row_complete": True},
            "lineage": lineage,
            "blockers": [],
        }
        video = {
            "schema_version": "1.0",
            "evidence_id": "ITEM-W64-033",
            "tracker_id": "TRK-W64-021",
            "item_id": "ITEM-W64-021",
            "status_decision": "Pass_Video",
            "overall_pass": True,
            "acceptance_gates": {
                "per_frame_qa": True,
                "temporal_identity_check": True,
                "flicker_detection": True,
                "motion_consistency": True,
                "frame_grid_and_playback_visual_review": True,
                "runtime_proof": True,
                "final_temporal_visual_pass": True,
            },
            "strict_decision": {"row_complete": True},
            "lineage": lineage,
            "blockers": [],
        }
        strict_audio = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "schema_name": "wave64_strict_audio_review_report",
            "report_version": 1,
            "run_id": "run_001",
            "is_synthetic": False,
            "capture_mode": "technical_capture",
            "artifact_bindings": {
                "mix_wav": {"path": str(self.image_path), "sha256": "0" * 64, "bytes": 1},
                "wave30_event_manifest": {"path": str(self.video_path), "sha256": "0" * 64, "bytes": 1},
                "wave30_mix_manifest": {"path": str(self.video_path), "sha256": "0" * 64, "bytes": 1},
                "wave30_qa_report": {"path": str(self.video_path), "sha256": "0" * 64, "bytes": 1},
                "prompt_reference": {"path": str(self.video_path), "sha256": "0" * 64, "bytes": 1},
                "prompt_alignment_proof": {"path": str(self.video_path), "sha256": "0" * 64, "bytes": 1}
            },
            "gates": {
                "audio_metadata_check": "PASS",
                "playback_review": "PASS",
                "prompt_alignment": "PASS",
                "sync_evidence": "PASS",
                "promotion_decision": "PASS",
                "overall_pass": "PASS",
            },
            "computed_metrics": {
                "normalized_wer": 0.0,
                "wer_threshold": 0.25,
                "expected_attribute_coverage": True,
                "upstream_production_eligible": True,
                "sync_not_applicable_reason": None,
            },
            "producer_identities": {
                "prompt_alignment_producer_id": None,
                "playback_review_producer_id": None,
                "production_review_producer_id": None,
            },
            "blockers": [],
            "final_decision": {"overall_status": "PASS", "exit_code": 0},
        }
        global_audio = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "schema_name": "wave64_global_audio_review_report",
            "report_version": 1,
            "review_run_id": "run_001",
            "baseline_run_id": "run_base",
            "candidate_run_id": "run_cand",
            "is_synthetic": False,
            "capture_mode": "technical_capture",
            "artifact_bindings": {
                "baseline_mix_wav": {"path": str(self.image_path), "sha256": "0" * 64, "bytes": 1},
                "candidate_mix_wav": {"path": str(self.image_path), "sha256": "0" * 64, "bytes": 1},
                "baseline_row031_strict_report": {"path": str(self.image_path), "sha256": "0" * 64, "bytes": 1},
                "candidate_row031_strict_report": {"path": str(self.image_path), "sha256": "0" * 64, "bytes": 1},
                "baseline_wave30_event_manifest": {"path": str(self.image_path), "sha256": "0" * 64, "bytes": 1},
                "candidate_wave30_event_manifest": {"path": str(self.image_path), "sha256": "0" * 64, "bytes": 1},
                "baseline_wave30_mix_manifest": {"path": str(self.image_path), "sha256": "0" * 64, "bytes": 1},
                "candidate_wave30_mix_manifest": {"path": str(self.image_path), "sha256": "0" * 64, "bytes": 1},
                "baseline_wave30_qa_report": {"path": str(self.image_path), "sha256": "0" * 64, "bytes": 1},
                "candidate_wave30_qa_report": {"path": str(self.image_path), "sha256": "0" * 64, "bytes": 1}
            },
            "localized_change_context": {
                "change_kind": "audio_localized",
                "audio_change_expected": True,
                "target_audio_event_ids": ["evt_1"],
                "derived_non_target_audio_event_ids": ["evt_2"],
                "derived_allowed_change_windows_seconds": [{"start_seconds": 0.1, "end_seconds": 0.2}],
                "caller_allowed_change_windows_seconds": [{"start_seconds": 0.1, "end_seconds": 0.2}]
            },
            "gates": {
                "full_duration_playback_review": "PASS",
                "required_target_audio_check": "PASS",
                "required_non_target_audio_scan": "PASS",
                "clipping_noise_voice_ambience_foley_sync_check": "PASS",
                "reject_on_any_global_audio_defect": "PASS",
                "promotion_decision": "PASS",
                "overall_pass": "PASS"
            },
            "computed_metrics": {
                "outside_target_diff_rms": 0.0,
                "outside_target_peak_delta": 0.0,
                "inside_target_diff_rms_per_target": {"evt_1": 0.0},
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
                "channel_count": 1
            },
            "blockers": [],
            "review_lineage_blockers": [],
            "production_authority_evidence": {
                "baseline_authority_match": True,
                "bundle_authority_match": True,
                "bundle_content_match": True
            },
            "final_decision": {"overall_status": "PASS", "exit_code": 0}
        }
        av_sync = {
            "schema_name": "wave64_av_sync_certification_report",
            "report_version": 1,
            "run_id": "run_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "take_id": "take_001",
            "is_synthetic": False,
            "evidence_origin": "technical_capture",
            "pyav_version": "18.0.0",
            "request_binding": {"path": str(self.image_path), "sha256": "0" * 64},
            "artifact_bindings": {
                "source_video_artifact": {"path": str(self.image_path), "sha256": "0" * 64, "bytes": 1},
                "source_audio_mix_artifact": {"path": str(self.image_path), "sha256": "0" * 64, "bytes": 1},
                "final_mux_artifact": {"path": str(self.image_path), "sha256": "0" * 64, "bytes": 1},
                "wave30_event_manifest": {"path": str(self.image_path), "sha256": "0" * 64},
                "wave30_mix_manifest": {"path": str(self.image_path), "sha256": "0" * 64},
                "observed_anchor_measurement_proof": {"path": str(self.image_path), "sha256": "0" * 64},
                "playback_proof": None,
                "runtime_proof": None,
                "production_certification_bundle": None,
                "wave64_gate_registry": {"path": str(self.image_path), "sha256": "0" * 64}
            },
            "metrics": {
                "source_video_decode": {
                    "container_format": "matroska,webm",
                    "stream_count_video": 1,
                    "stream_count_audio": 1,
                    "codec": "h264",
                    "time_base": 0.04,
                    "frame_rate": 25.0,
                    "width": 512,
                    "height": 512,
                    "frame_count": 25,
                    "first_pts_seconds": 0.0,
                    "last_pts_seconds": 0.96,
                    "duration_seconds": 1.0,
                    "packet_pts_monotonic": True,
                    "frame_pts_monotonic": True,
                    "missing_packet_pts_count": 0,
                    "missing_frame_pts_count": 0,
                    "decoded_video_hash": "0" * 64
                },
                "mux_video_decode": {
                    "container_format": "matroska,webm",
                    "stream_count_video": 1,
                    "stream_count_audio": 1,
                    "codec": "h264",
                    "time_base": 0.04,
                    "frame_rate": 25.0,
                    "width": 512,
                    "height": 512,
                    "frame_count": 25,
                    "first_pts_seconds": 0.0,
                    "last_pts_seconds": 0.96,
                    "duration_seconds": 1.0,
                    "packet_pts_monotonic": True,
                    "frame_pts_monotonic": True,
                    "missing_packet_pts_count": 0,
                    "missing_frame_pts_count": 0,
                    "decoded_video_hash": "0" * 64
                },
                "source_audio_decode": {
                    "stream_count_audio": 1,
                    "codec": "pcm_s16le",
                    "time_base": 0.0000625,
                    "sample_rate_hz": 16000,
                    "channels": 1,
                    "channel_layout": "mono",
                    "sample_count": 16000,
                    "first_pts_seconds": 0.0,
                    "last_pts_seconds": 0.9999,
                    "duration_seconds": 1.0,
                    "packet_pts_monotonic": True,
                    "frame_pts_monotonic": True,
                    "missing_packet_pts_count": 0,
                    "missing_frame_pts_count": 0,
                    "decoded_audio_hash": "0" * 64
                },
                "mux_audio_decode": {
                    "stream_count_audio": 1,
                    "codec": "aac",
                    "time_base": 0.0000625,
                    "sample_rate_hz": 16000,
                    "channels": 1,
                    "channel_layout": "mono",
                    "sample_count": 16000,
                    "first_pts_seconds": 0.0,
                    "last_pts_seconds": 0.9999,
                    "duration_seconds": 1.0,
                    "packet_pts_monotonic": True,
                    "frame_pts_monotonic": True,
                    "missing_packet_pts_count": 0,
                    "missing_frame_pts_count": 0,
                    "decoded_audio_hash": "0" * 64
                },
                "lineage": {
                    "video_hash_match": True,
                    "audio_hash_match": True,
                    "video_frame_count_match": True,
                    "audio_sample_count_match": True,
                    "stream_count_match": True,
                    "video_codec_match": True,
                    "audio_codec_match": True
                },
                "sync": {
                    "audio_start_offset_seconds": 0.0,
                    "endpoint_delta_seconds": 0.0,
                    "cumulative_endpoint_drift_seconds": 0.0
                },
                "anchors": {
                    "required_anchor_event_count": 1,
                    "observed_anchor_count": 1,
                    "missing_anchor_count": 0,
                    "extra_anchor_count": 0,
                    "duplicate_anchor_count": 0,
                    "measurement_producer": None
                },
                "proofs": {
                    "playback_producer": None,
                    "runtime_producer": None
                }
            },
            "gates": {
                "sync_offset_threshold": {"status": "PASS", "blockers": [], "artifact_bindings": []},
                "drift_check": {"status": "PASS", "blockers": [], "artifact_bindings": []},
                "mux_manifest": {"status": "PASS", "blockers": [], "artifact_bindings": []},
                "event_owner_alignment": {"status": "PASS", "blockers": [], "artifact_bindings": []},
                "av_review_record": {"status": "PASS", "blockers": [], "artifact_bindings": []},
                "production_runtime_proof": {"status": "PASS", "blockers": [], "artifact_bindings": []},
                "production_av_sync_authority": {"status": "PASS", "blockers": [], "artifact_bindings": []},
                "overall_pass": {"status": "PASS", "blockers": [], "artifact_bindings": []}
            },
            "blockers": [],
            "overall_pass": True
        }
        manifest = {
            "release_id": "rel_001",
            "release_type": "runtime",
            "pack_root": "runtime_artifacts/release",
            "file_count": 7,
            "json_count": 7,
            "script_count": 1,
            "main_flow_inventory": [],
            "source_inputs": [],
            "added_wave34_files": [],
            "proof_boundaries": {},
            "validation_report_ref": "validation.json",
            "handoff_ref": "handoff.json",
            "release_gate_decision_ref": "release_decision.json"
        }
        release = {
            "decision_id": "dec_001",
            "release_id": "rel_001",
            "app_mode_status": "pass",
            "orchestrator_status": "pass",
            "local_proof_status": "pass",
            "ec2_proof_status": "pass",
            "qa_certification_status": "pass",
            "manifest_status": "pass",
            "runtime_boundary_statuses": {},
            "blocked_reasons": [],
            "promotion_decision": "release_runtime_certified"
        }

        _write_json(self.image_path, image)
        _write_json(self.video_path, video)
        _write_json(self.strict_audio_path, strict_audio)
        _write_json(self.global_audio_path, global_audio)
        _write_json(self.av_sync_path, av_sync)
        _write_json(self.manifest_path, manifest)
        _write_json(self.release_path, release)
        self.base_request = {
            "schema_name": "wave64_multimodal_scorecard_request",
            "request_version": 1,
            "artifact_id": "ITEM-W64-033",
            "run_id": "run_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "take_id": "take_001",
            "artifact_type": "multimodal_cross_review",
            "generation_test_method": "strict_fixture",
            "is_synthetic": False,
            "image_review_binding": _binding(self.image_path),
            "video_review_binding": _binding(self.video_path),
            "strict_audio_report_binding": _binding(self.strict_audio_path),
            "global_audio_report_binding": _binding(self.global_audio_path),
            "av_sync_report_binding": _binding(self.av_sync_path),
            "artifact_manifest_binding": _binding(self.manifest_path),
            "release_gate_decision_binding": _binding(self.release_path),
            "production_authority_claim": {
                "authority_id": "fixture_auth",
                "bundle_id": "fixture_bundle"
            },
            "caller_claimed_approval_decision": "approved",
            "output_report_path": str(self.output_path.resolve())
        }

    def _run(
        self,
        request: dict[str, Any],
        *,
        raw_json: str | None = None,
        preserve_output: bool = False,
        authority_mode: str = "fixture_exact",
    ) -> subprocess.CompletedProcess[str]:
        if self.output_path.exists() and not preserve_output:
            self.output_path.unlink()
        self._set_authority_mode(request, authority_mode)
        if raw_json is not None:
            self.request_path.write_text(raw_json, encoding="utf-8")
        else:
            _write_json(self.request_path, request)
        return subprocess.run(
            [
                sys.executable,
                str(self.root / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_multimodal_scorecard.py"),
                "--input",
                str(self.request_path),
                "--output",
                str(self.output_path),
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def _report(self) -> dict[str, Any]:
        return json.loads(self.output_path.read_text(encoding="utf-8"))

    def _rules_path(self) -> Path:
        return self.root / "Plan/10_REGISTRIES/wave64_multimodal_scorecard_rules.json"

    def _relative_binding(self, binding: dict[str, Any]) -> dict[str, Any]:
        path = Path(binding["path"]).resolve().relative_to(self.root).as_posix()
        return {"path": path, "sha256": binding["sha256"], "bytes": binding["bytes"]}

    def _build_exact_authority_object(self, request: dict[str, Any], *, authority_id: str, bundle_id: str) -> dict[str, Any]:
        release_payload = json.loads(self.release_path.read_text(encoding="utf-8"))
        return {
            "authority_id": authority_id,
            "bundle_id": bundle_id,
            "artifact_id": request["artifact_id"],
            "run_id": request["run_id"],
            "scene_id": request["scene_id"],
            "shot_id": request["shot_id"],
            "take_id": request["take_id"],
            "release_id": release_payload["release_id"],
            "is_synthetic": request["is_synthetic"],
            "input_bindings": {
                "image_review_binding": self._relative_binding(request["image_review_binding"]),
                "video_review_binding": self._relative_binding(request["video_review_binding"]),
                "strict_audio_report_binding": self._relative_binding(request["strict_audio_report_binding"]),
                "global_audio_report_binding": self._relative_binding(request["global_audio_report_binding"]),
                "av_sync_report_binding": self._relative_binding(request["av_sync_report_binding"]),
                "artifact_manifest_binding": self._relative_binding(request["artifact_manifest_binding"]),
                "release_gate_decision_binding": self._relative_binding(request["release_gate_decision_binding"]),
            },
        }

    def _set_authority_mode(self, request: dict[str, Any], mode: str) -> None:
        rules_path = self._rules_path()
        rules = json.loads(rules_path.read_text(encoding="utf-8"))
        if mode == "keep":
            return
        if mode == "none":
            rules["authority_rules"]["production_authority_exact_objects"] = []
            rules["authority_rules"]["fixture_authority_exact_objects"] = []
            _write_json(rules_path, rules)
            return
        claim = request["production_authority_claim"]
        authority_id = claim["authority_id"]
        bundle_id = claim["bundle_id"]
        exact = self._build_exact_authority_object(request, authority_id=authority_id, bundle_id=bundle_id)
        if mode == "fixture_exact":
            rules["authority_rules"]["fixture_authority_exact_objects"] = [exact]
            rules["authority_rules"]["production_authority_exact_objects"] = []
        elif mode == "production_exact":
            exact["expected_strict_audio_producer_ids"] = {
                "prompt_alignment_producer_id": "prod_authority_prompt",
                "playback_review_producer_id": "prod_authority_playback",
                "production_review_producer_id": "prod_authority_release",
            }
            rules["authority_rules"]["production_authority_exact_objects"] = [exact]
            rules["authority_rules"]["fixture_authority_exact_objects"] = []
        else:
            raise ValueError(f"unsupported authority mode: {mode}")
        _write_json(rules_path, rules)

    def test_missing_file_rejected(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["image_review_binding"]["path"] = str((self.root / "runtime_artifacts/does_not_exist.json").resolve())
        self.assertEqual(self._run(request).returncode, 1)

    def test_hash_and_byte_mismatch_rejected(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["video_review_binding"]["sha256"] = "0" * 64
        self.assertEqual(self._run(request).returncode, 1)
        request = copy.deepcopy(self.base_request)
        request["video_review_binding"]["bytes"] += 1
        self.assertEqual(self._run(request).returncode, 1)

    def test_schema_mismatch_and_unknown_key_rejected(self) -> None:
        strict = json.loads(self.strict_audio_path.read_text(encoding="utf-8"))
        strict["schema_name"] = "wrong"
        _write_json(self.strict_audio_path, strict)
        request = copy.deepcopy(self.base_request)
        request["strict_audio_report_binding"] = _binding(self.strict_audio_path)
        self.assertEqual(self._run(request).returncode, 1)

        request = copy.deepcopy(self.base_request)
        request["unknown_key"] = True
        self.assertEqual(self._run(request).returncode, 1)

    def test_duplicate_and_nonfinite_request_json_rejected(self) -> None:
        base = json.dumps(copy.deepcopy(self.base_request))
        duplicate = base[:-1] + ',"run_id":"duplicate"}'
        self.assertEqual(self._run(copy.deepcopy(self.base_request), raw_json=duplicate).returncode, 1)

        nonfinite = base[:-1] + ',"bad":NaN}'
        self.assertEqual(self._run(copy.deepcopy(self.base_request), raw_json=nonfinite).returncode, 1)

    def test_traversal_and_symlink_escape_rejected(self) -> None:
        outside_dir = Path(tempfile.mkdtemp()).resolve()
        outside_file = outside_dir / "outside.json"
        outside_file.write_text("{}", encoding="utf-8")
        request = copy.deepcopy(self.base_request)
        request["image_review_binding"] = {"path": str(outside_file), "sha256": _sha256(outside_file), "bytes": outside_file.stat().st_size}
        self.assertEqual(self._run(request, authority_mode="none").returncode, 1)

        link_path = self.root / "runtime_artifacts/link_outside.json"
        try:
            link_path.symlink_to(outside_file)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unsupported on this platform")
        request = copy.deepcopy(self.base_request)
        request["image_review_binding"] = {"path": str(link_path.resolve()), "sha256": _sha256(outside_file), "bytes": outside_file.stat().st_size}
        self.assertEqual(self._run(request, authority_mode="none").returncode, 1)

    def test_mixed_lineage_and_untrusted_authority_blocked(self) -> None:
        video = json.loads(self.video_path.read_text(encoding="utf-8"))
        video["lineage"]["run_id"] = "wrong"
        _write_json(self.video_path, video)
        request = copy.deepcopy(self.base_request)
        request["video_review_binding"] = _binding(self.video_path)
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        report = self._report()
        self.assertEqual(report["approval_decision"], "blocked")

    def test_caller_injected_approval_is_ignored(self) -> None:
        image = json.loads(self.image_path.read_text(encoding="utf-8"))
        image["acceptance_gates"]["visual_runtime_ready"] = False
        _write_json(self.image_path, image)
        request = copy.deepcopy(self.base_request)
        request["image_review_binding"] = _binding(self.image_path)
        request["caller_claimed_approval_decision"] = "approved"
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        report = self._report()
        self.assertNotEqual(report["approval_decision"], "approved")
        self.assertTrue(report["decision_derivation"]["caller_claim_ignored"])

    def test_synthetic_production_claim_blocked(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["is_synthetic"] = True
        result = self._run(request, authority_mode="production_exact")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "blocked")

    def test_modality_pass_with_avsync_blocked_is_not_approved(self) -> None:
        av = json.loads(self.av_sync_path.read_text(encoding="utf-8"))
        av["gates"]["production_runtime_proof"]["status"] = "BLOCKED"
        _write_json(self.av_sync_path, av)
        request = copy.deepcopy(self.base_request)
        request["av_sync_report_binding"] = _binding(self.av_sync_path)
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        self.assertIn(self._report()["approval_decision"], {"rejected", "blocked"})

    def test_category_under_three_rejected(self) -> None:
        video = json.loads(self.video_path.read_text(encoding="utf-8"))
        video["acceptance_gates"]["temporal_identity_check"] = False
        video["acceptance_gates"]["motion_consistency"] = False
        _write_json(self.video_path, video)
        request = copy.deepcopy(self.base_request)
        request["video_review_binding"] = _binding(self.video_path)
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "rejected")

    def test_blocking_defect_and_incomplete_legacy_contract(self) -> None:
        strict = json.loads(self.strict_audio_path.read_text(encoding="utf-8"))
        strict["blockers"] = ["missing production playback evidence"]
        _write_json(self.strict_audio_path, strict)
        request = copy.deepcopy(self.base_request)
        request["strict_audio_report_binding"] = _binding(self.strict_audio_path)
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "blocked")

        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest.pop("release_id")
        _write_json(self.manifest_path, manifest)
        request = copy.deepcopy(self.base_request)
        request["artifact_manifest_binding"] = _binding(self.manifest_path)
        request["strict_audio_report_binding"] = _binding(self.strict_audio_path)
        self.assertEqual(self._run(request).returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "blocked")

    def test_fixture_only_authority_can_reach_exit_zero_nonproduction(self) -> None:
        request = copy.deepcopy(self.base_request)
        result = self._run(request)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = self._report()
        self.assertEqual(report["approval_decision"], "conditionally_approved")
        self.assertTrue(report["production_eligibility"]["fixture_only_result"])
        self.assertFalse(report["production_eligibility"]["eligible_for_production"])

    def test_output_collision_and_atomic_write(self) -> None:
        source = SOURCE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("os.fsync(handle.fileno())", source)
        self.assertIn("os.link(temporary, path)", source)
        self.assertNotIn("temp_path.replace(path)", source)
        self.output_path.write_text('{"preexisting": true}\n', encoding="utf-8")
        request = copy.deepcopy(self.base_request)
        self.assertEqual(self._run(request, preserve_output=True).returncode, 1)
        self.assertEqual(self.output_path.read_text(encoding="utf-8"), '{"preexisting": true}\n')

        if self.output_path.exists():
            self.output_path.unlink()
        bad = copy.deepcopy(self.base_request)
        bad["request_version"] = 999
        self.assertEqual(self._run(bad).returncode, 1)
        self.assertFalse(self.output_path.exists())

    def test_deterministic_recomputation(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["caller_claimed_approval_decision"] = "approved"
        first = self._run(request)
        self.assertEqual(first.returncode, 0)
        first_report = self._report()

        request["caller_claimed_approval_decision"] = "blocked"
        second = self._run(request)
        self.assertEqual(second.returncode, 0)
        second_report = self._report()

        self.assertEqual(first_report["approval_decision"], second_report["approval_decision"])
        self.assertEqual(first_report["scorecard"]["categories"], second_report["scorecard"]["categories"])

    def test_cross_product_authority_mapping_rejected(self) -> None:
        request = copy.deepcopy(self.base_request)
        rules_path = self._rules_path()
        rules = json.loads(rules_path.read_text(encoding="utf-8"))
        obj_a = self._build_exact_authority_object(request, authority_id="auth_a", bundle_id="bundle_a")
        obj_b = self._build_exact_authority_object(request, authority_id="auth_a", bundle_id="bundle_b")
        obj_c = self._build_exact_authority_object(request, authority_id="auth_b", bundle_id="bundle_a")
        rules["authority_rules"]["fixture_authority_exact_objects"] = [obj_a, obj_b, obj_c]
        rules["authority_rules"]["production_authority_exact_objects"] = []
        _write_json(rules_path, rules)
        request["production_authority_claim"] = {"authority_id": "auth_a", "bundle_id": "bundle_a"}
        result = self._run(request, authority_mode="keep")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "blocked")

    def test_exact_authority_wrong_binding_is_blocked(self) -> None:
        request = copy.deepcopy(self.base_request)
        rules_path = self._rules_path()
        rules = json.loads(rules_path.read_text(encoding="utf-8"))
        exact = self._build_exact_authority_object(request, authority_id="fixture_auth", bundle_id="fixture_bundle")
        exact["input_bindings"]["video_review_binding"]["sha256"] = "0" * 64
        rules["authority_rules"]["fixture_authority_exact_objects"] = [exact]
        _write_json(rules_path, rules)
        result = self._run(request, authority_mode="keep")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "blocked")

    def test_release_id_mismatch_blocked(self) -> None:
        release = json.loads(self.release_path.read_text(encoding="utf-8"))
        release["release_id"] = "rel_mismatch"
        _write_json(self.release_path, release)
        request = copy.deepcopy(self.base_request)
        request["release_gate_decision_binding"] = _binding(self.release_path)
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "blocked")

    def test_exact_release_but_wrong_artifact_lineage_blocked(self) -> None:
        request = copy.deepcopy(self.base_request)
        rules_path = self._rules_path()
        rules = json.loads(rules_path.read_text(encoding="utf-8"))
        exact = self._build_exact_authority_object(request, authority_id="fixture_auth", bundle_id="fixture_bundle")
        exact["artifact_id"] = "wrong_artifact"
        exact["run_id"] = "wrong_run"
        rules["authority_rules"]["fixture_authority_exact_objects"] = [exact]
        _write_json(rules_path, rules)
        result = self._run(request, authority_mode="keep")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "blocked")

    def test_strict_and_global_audio_synthetic_mismatch_blocked(self) -> None:
        strict = json.loads(self.strict_audio_path.read_text(encoding="utf-8"))
        strict["is_synthetic"] = True
        _write_json(self.strict_audio_path, strict)
        global_audio = json.loads(self.global_audio_path.read_text(encoding="utf-8"))
        global_audio["is_synthetic"] = True
        _write_json(self.global_audio_path, global_audio)
        request = copy.deepcopy(self.base_request)
        request["strict_audio_report_binding"] = _binding(self.strict_audio_path)
        request["global_audio_report_binding"] = _binding(self.global_audio_path)
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "blocked")

    def test_global_authority_false_booleans_block_production(self) -> None:
        strict = json.loads(self.strict_audio_path.read_text(encoding="utf-8"))
        strict["producer_identities"] = {
            "prompt_alignment_producer_id": {
                "proof_kind": "prompt_alignment",
                "producer_id": "prod_prompt_reviewer",
                "engine": "engine",
                "model": "model",
                "model_version": "1",
                "model_sha256": "a" * 64,
                "authority_id": "prod_authority_prompt",
                "synthetic_only": False,
            },
            "playback_review_producer_id": {
                "proof_kind": "playback_review",
                "producer_id": "prod_playback_reviewer",
                "engine": "engine",
                "model": "model",
                "model_version": "1",
                "model_sha256": "b" * 64,
                "authority_id": "prod_authority_playback",
                "synthetic_only": False,
            },
            "production_review_producer_id": {
                "proof_kind": "production_review",
                "producer_id": "prod_release_reviewer",
                "engine": "engine",
                "model": "model",
                "model_version": "1",
                "model_sha256": "c" * 64,
                "authority_id": "prod_authority_release",
                "synthetic_only": False,
            },
        }
        _write_json(self.strict_audio_path, strict)
        global_audio = json.loads(self.global_audio_path.read_text(encoding="utf-8"))
        global_audio["production_authority_evidence"]["bundle_content_match"] = False
        _write_json(self.global_audio_path, global_audio)
        request = copy.deepcopy(self.base_request)
        request["strict_audio_report_binding"] = _binding(self.strict_audio_path)
        request["global_audio_report_binding"] = _binding(self.global_audio_path)
        result = self._run(request, authority_mode="production_exact")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "blocked")

    def test_synthetic_producer_identity_blocks_production(self) -> None:
        strict = json.loads(self.strict_audio_path.read_text(encoding="utf-8"))
        strict["producer_identities"] = {
            "prompt_alignment_producer_id": {
                "proof_kind": "prompt_alignment",
                "producer_id": "synthetic_prompt",
                "engine": "engine",
                "model": "model",
                "model_version": "1",
                "model_sha256": "d" * 64,
                "authority_id": "prod_authority_prompt",
                "synthetic_only": True,
            },
            "playback_review_producer_id": {
                "proof_kind": "playback_review",
                "producer_id": "prod_playback_reviewer",
                "engine": "engine",
                "model": "model",
                "model_version": "1",
                "model_sha256": "e" * 64,
                "authority_id": "prod_authority_playback",
                "synthetic_only": False,
            },
            "production_review_producer_id": {
                "proof_kind": "production_review",
                "producer_id": "prod_release_reviewer",
                "engine": "engine",
                "model": "model",
                "model_version": "1",
                "model_sha256": "f" * 64,
                "authority_id": "prod_authority_release",
                "synthetic_only": False,
            },
        }
        _write_json(self.strict_audio_path, strict)
        request = copy.deepcopy(self.base_request)
        request["strict_audio_report_binding"] = _binding(self.strict_audio_path)
        result = self._run(request, authority_mode="production_exact")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "blocked")

    def test_malformed_legacy_types_and_promotion_decision_blocked_exit2(self) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["file_count"] = -1
        manifest["main_flow_inventory"] = {}
        _write_json(self.manifest_path, manifest)
        release = json.loads(self.release_path.read_text(encoding="utf-8"))
        release["blocked_reasons"] = "not-a-list"
        release["promotion_decision"] = "totally_unknown_decision"
        _write_json(self.release_path, release)
        request = copy.deepcopy(self.base_request)
        request["artifact_manifest_binding"] = _binding(self.manifest_path)
        request["release_gate_decision_binding"] = _binding(self.release_path)
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "blocked")

    def test_free_text_blocker_keyword_does_not_change_classification(self) -> None:
        image = json.loads(self.image_path.read_text(encoding="utf-8"))
        image["acceptance_gates"]["visual_runtime_ready"] = False
        image["blockers"] = [{"reason": "missing authority but free-text only"}]
        _write_json(self.image_path, image)
        request = copy.deepcopy(self.base_request)
        request["image_review_binding"] = _binding(self.image_path)
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "blocked")

    def test_missing_image_video_lineage_is_blocked_exit2(self) -> None:
        image = json.loads(self.image_path.read_text(encoding="utf-8"))
        video = json.loads(self.video_path.read_text(encoding="utf-8"))
        image.pop("lineage", None)
        video.pop("lineage", None)
        _write_json(self.image_path, image)
        _write_json(self.video_path, video)
        request = copy.deepcopy(self.base_request)
        request["image_review_binding"] = _binding(self.image_path)
        request["video_review_binding"] = _binding(self.video_path)
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "blocked")

    def test_duplicate_authority_pair_rejected(self) -> None:
        request = copy.deepcopy(self.base_request)
        rules_path = self._rules_path()
        rules = json.loads(rules_path.read_text(encoding="utf-8"))
        dup = self._build_exact_authority_object(request, authority_id="fixture_auth", bundle_id="fixture_bundle")
        rules["authority_rules"]["fixture_authority_exact_objects"] = [dup, copy.deepcopy(dup)]
        _write_json(rules_path, rules)
        result = self._run(request, authority_mode="keep")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "blocked")

    def test_malformed_image_video_nested_types_blocked_exit2(self) -> None:
        image = json.loads(self.image_path.read_text(encoding="utf-8"))
        image["acceptance_gates"] = "not-an-object"
        image["strict_decision"] = "bad"
        image["lineage"] = "bad"
        _write_json(self.image_path, image)
        video = json.loads(self.video_path.read_text(encoding="utf-8"))
        video["acceptance_gates"]["motion_consistency"] = "PASS"
        video["strict_decision"] = []
        _write_json(self.video_path, video)
        request = copy.deepcopy(self.base_request)
        request["image_review_binding"] = _binding(self.image_path)
        request["video_review_binding"] = _binding(self.video_path)
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "blocked")

    def test_camera_only_image_evidence_is_blocked(self) -> None:
        image = json.loads(self.image_path.read_text(encoding="utf-8"))
        image["acceptance_gates"] = {
            "camera_spec_check": True,
            "crop_boundary_check": True,
            "visual_runtime_ready": True,
        }
        _write_json(self.image_path, image)
        request = copy.deepcopy(self.base_request)
        request["image_review_binding"] = _binding(self.image_path)
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "blocked")

    def test_individual_image_realism_prompt_gates_failing_rejected(self) -> None:
        gates_to_fail = [
            "image_realism_check",
            "anatomy_check",
            "global_visual_review",
            "multi_sample_certification",
            "prompt_alignment_check",
            "contamination_resistance_check",
        ]
        for gate in gates_to_fail:
            with self.subTest(gate=gate):
                self._create_base_fixtures()
                image = json.loads(self.image_path.read_text(encoding="utf-8"))
                image["acceptance_gates"][gate] = False
                _write_json(self.image_path, image)
                request = copy.deepcopy(self.base_request)
                request["image_review_binding"] = _binding(self.image_path)
                result = self._run(request)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(self._report()["approval_decision"], "rejected")

    def test_wrong_tracker_item_and_source_artifact_ids_blocked(self) -> None:
        image = json.loads(self.image_path.read_text(encoding="utf-8"))
        image["tracker_id"] = "TRK-W64-WRONG"
        image["item_id"] = "ITEM-W64-WRONG"
        image["evidence_id"] = "OTHER-ARTIFACT"
        _write_json(self.image_path, image)
        video = json.loads(self.video_path.read_text(encoding="utf-8"))
        video["tracker_id"] = "TRK-W64-WRONG"
        video["item_id"] = "ITEM-W64-WRONG"
        video["evidence_id"] = "OTHER-ARTIFACT"
        _write_json(self.video_path, video)
        request = copy.deepcopy(self.base_request)
        request["image_review_binding"] = _binding(self.image_path)
        request["video_review_binding"] = _binding(self.video_path)
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "blocked")

    def test_wrong_release_gate_decision_ref_blocked(self) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["release_gate_decision_ref"] = "other/release_decision.json"
        _write_json(self.manifest_path, manifest)
        request = copy.deepcopy(self.base_request)
        request["artifact_manifest_binding"] = _binding(self.manifest_path)
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["approval_decision"], "blocked")

    def test_canonical_non_release_promotion_decisions_classified(self) -> None:
        decision_schema = json.loads((self.root / "Plan/08_SCHEMAS/wave34_release_gate_decision.schema.json").read_text(encoding="utf-8"))
        canonical = _canonical_promotion_decisions(decision_schema)
        self.assertTrue(canonical)
        to_test = sorted(canonical - RELEASE_ALLOWED)
        for promotion_decision in to_test:
            with self.subTest(promotion_decision=promotion_decision):
                self._create_base_fixtures()
                release = json.loads(self.release_path.read_text(encoding="utf-8"))
                release["promotion_decision"] = promotion_decision
                _write_json(self.release_path, release)
                request = copy.deepcopy(self.base_request)
                request["release_gate_decision_binding"] = _binding(self.release_path)
                result = self._run(request)
                report = self._report()
                self.assertEqual(result.returncode, 2)
                if promotion_decision == "blocked_missing_proof":
                    self.assertEqual(report["approval_decision"], "blocked")
                    self.assertEqual(report["release_decision"]["classification"], "canonical_blocked_missing_proof")
                elif promotion_decision in {"repair_required", "blocked_failed_QA"}:
                    self.assertEqual(report["approval_decision"], "rejected")
                    self.assertEqual(report["release_decision"]["classification"], "canonical_present_failure")
                else:
                    self.assertEqual(report["approval_decision"], "rejected")
                    self.assertEqual(report["release_decision"]["classification"], "canonical_non_release")

    def test_unknown_promotion_decision_is_blocked_dependency(self) -> None:
        release = json.loads(self.release_path.read_text(encoding="utf-8"))
        release["promotion_decision"] = "unknown_value_not_in_schema"
        _write_json(self.release_path, release)
        request = copy.deepcopy(self.base_request)
        request["release_gate_decision_binding"] = _binding(self.release_path)
        result = self._run(request)
        report = self._report()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report["approval_decision"], "blocked")
        self.assertEqual(report["release_decision"]["classification"], "unknown_or_ill_typed")

    def test_exact_production_authority_fixture_contract_reachability(self) -> None:
        request = copy.deepcopy(self.base_request)
        strict = json.loads(self.strict_audio_path.read_text(encoding="utf-8"))
        strict["producer_identities"] = {
            "prompt_alignment_producer_id": {
                "proof_kind": "prompt_alignment",
                "producer_id": "prod_prompt_reviewer",
                "engine": "engine",
                "model": "model",
                "model_version": "1",
                "model_sha256": "a" * 64,
                "authority_id": "prod_authority_prompt",
                "synthetic_only": False,
            },
            "playback_review_producer_id": {
                "proof_kind": "playback_review",
                "producer_id": "prod_playback_reviewer",
                "engine": "engine",
                "model": "model",
                "model_version": "1",
                "model_sha256": "b" * 64,
                "authority_id": "prod_authority_playback",
                "synthetic_only": False,
            },
            "production_review_producer_id": {
                "proof_kind": "production_review",
                "producer_id": "prod_release_reviewer",
                "engine": "engine",
                "model": "model",
                "model_version": "1",
                "model_sha256": "c" * 64,
                "authority_id": "prod_authority_release",
                "synthetic_only": False,
            },
        }
        _write_json(self.strict_audio_path, strict)
        request["strict_audio_report_binding"] = _binding(self.strict_audio_path)
        result = self._run(request, authority_mode="production_exact")
        report = self._report()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["approval_decision"], "approved")
        self.assertTrue(report["production_eligibility"]["eligible_for_production"])
        self.assertFalse(report["production_eligibility"]["fixture_only_result"])

    def test_canonical_registry_production_and_fixture_arrays_remain_empty(self) -> None:
        rules = json.loads(SOURCE_RULES.read_text(encoding="utf-8"))
        self.assertEqual(rules["authority_rules"]["production_authority_exact_objects"], [])
        self.assertEqual(rules["authority_rules"]["fixture_authority_exact_objects"], [])


if __name__ == "__main__":
    unittest.main()
