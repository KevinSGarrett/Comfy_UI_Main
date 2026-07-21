from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
COMPILER_PATH = (
    ROOT
    / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_multimodal_job_contract.py"
)
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


def load_compiler():
    spec = importlib.util.spec_from_file_location("w64_aqa_contract_compiler", COMPILER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_draft(modality: str = "image") -> dict:
    roles = [
        {
            "role_id": "W64-AQA-ROLE-DETERMINISTIC",
            "authority": "deterministic",
            "can_approve": True,
            "required": True,
        },
        {
            "role_id": "W64-AQA-ROLE-PRIMARY-VISUAL",
            "authority": "primary",
            "can_approve": True,
            "required": True,
        },
        {
            "role_id": "W64-AQA-ROLE-INDEPENDENT-JUROR",
            "authority": "independent_juror",
            "can_approve": True,
            "required": True,
        },
        {
            "role_id": "W64-AQA-ROLE-FAST-TRIAGE",
            "authority": "triage",
            "can_approve": False,
            "required": False,
        },
    ]
    bindings = [
        {
            "role_id": role["role_id"],
            "model_id": f"synthetic-fixture/{role['authority']}",
            "checkpoint_sha256": SHA_B,
            "runtime_digest": "synthetic-runtime-fixture",
            "qualification_state": "QUALIFIED",
        }
        for role in roles
        if role["required"]
    ]
    draft = {
        "schema_version": "wave64.aqa.job_contract.v1",
        "job_id": "W64-AQA-JOB-contract-test",
        "revision": 1,
        "created_at": "2026-07-21T19:00:00Z",
        "modality": modality,
        "execution_mode": "production_release",
        "requested_outputs": [
            {
                "output_id": "primary",
                "media_type": "image/png",
                "durable_relative_path": "aqa/jobs/contract-test/primary.png",
            }
        ],
        "quality_profile": {
            "profile_id": "synthetic-contract-fixture-v1",
            "hard_gates": [
                {
                    "gate_id": "decode",
                    "metric": "decode_success",
                    "operator": "eq",
                    "threshold": True,
                    "on_failure": "REJECT",
                }
            ],
            "review_roles": roles,
            "required_approval_roles": [role["role_id"] for role in roles if role["required"]],
        },
        "resource_budget": {
            "max_gpu_seconds": 600,
            "max_gpu_hour_usd": 2.0,
            "max_output_bytes": 104857600,
            "deadline_seconds": 1200,
            "secondary_burst": {
                "enabled": False,
                "max_cost_usd": 0,
                "max_seconds": 0,
                "idle_ttl_seconds": 0,
                "eligible_gpu_classes": [],
            },
        },
        "attempt_policy": {
            "max_repairs_per_defect": 2,
            "max_total_generations": 4,
            "max_no_progress_cycles": 2,
        },
        "authority_policy": {
            "generation_host": "runpod_only",
            "ec2_allowed": False,
            "local_comfyui_allowed": False,
            "triage_can_approve": False,
            "model_can_promote": False,
            "workflow_model_proposal_only": True,
            "secrets_visible_to_models": False,
            "external_inference_allowed": False,
        },
        "rollback_policy": {
            "revert_on_regression": True,
            "promotion_requires_replay": True,
            "retain_failed_evidence": True,
            "previous_accepted_artifact_sha256": None,
        },
        "provenance": {
            "workflow_sha256": SHA_A,
            "input_artifacts": [],
            "model_bindings": bindings,
            "calibration_ids": ["synthetic-calibration-fixture-v1"],
        },
        "image_spec": {"width": 1024, "height": 1024, "color_space": "sRGB", "alpha_required": False},
    }
    if modality == "mask":
        draft["mask_spec"] = {
            "target_binding": "character.face",
            "golden_reference_sha256": SHA_C,
            "alpha_mode": "both",
            "temporal_consistency_required": False,
        }
    return draft


def test_compiles_and_verifies_deterministically() -> None:
    compiler = load_compiler()
    first = compiler.compile_contract(valid_draft())
    second = compiler.compile_contract(valid_draft())
    assert first == second
    assert first["preflight_disposition"] == "READY_FOR_LEASE"
    compiler.verify_contract(first)


def test_unqualified_required_role_compiles_to_hold() -> None:
    compiler = load_compiler()
    draft = valid_draft()
    draft["provenance"]["model_bindings"][2]["qualification_state"] = "BLOCKED_UNQUALIFIED"
    contract = compiler.compile_contract(draft)
    assert contract["preflight_disposition"] == "HOLD_UNQUALIFIED_REQUIRED_ROLE"
    compiler.verify_contract(contract)


def test_current_32b_lane_can_run_shadow_without_product_authority() -> None:
    compiler = load_compiler()
    draft = valid_draft()
    strict_role = {
        "role_id": "W64-AQA-ROLE-STRICT-VISUAL",
        "authority": "strict",
        "can_approve": True,
        "required": True,
    }
    deterministic = draft["quality_profile"]["review_roles"][0]
    triage = draft["quality_profile"]["review_roles"][3]
    draft["execution_mode"] = "shadow_qualification"
    draft["quality_profile"]["review_roles"] = [deterministic, strict_role, triage]
    draft["quality_profile"]["required_approval_roles"] = [
        "W64-AQA-ROLE-DETERMINISTIC",
        "W64-AQA-ROLE-STRICT-VISUAL",
    ]
    draft["provenance"]["model_bindings"] = [
        draft["provenance"]["model_bindings"][0],
        {
            "role_id": "W64-AQA-ROLE-STRICT-VISUAL",
            "model_id": "qwen2.5vl:32b",
            "checkpoint_sha256": SHA_C,
            "runtime_digest": "synthetic-current-pod-fixture",
            "qualification_state": "QUALIFIED",
        },
    ]
    contract = compiler.compile_contract(draft)
    assert contract["preflight_disposition"] == "READY_FOR_LEASE"
    assert contract["promotion_disposition"] == "EVIDENCE_ONLY"
    compiler.verify_contract(contract)


def test_workflow_shadow_requires_deterministic_role_without_visual_semantic_authority() -> None:
    compiler = load_compiler()
    draft = valid_draft("workflow")
    deterministic = draft["quality_profile"]["review_roles"][0]
    workflow_engineer = {
        "role_id": "W64-AQA-ROLE-WORKFLOW-ENGINEER",
        "authority": "workflow",
        "can_approve": False,
        "required": False,
    }
    draft["execution_mode"] = "shadow_qualification"
    draft["quality_profile"]["review_roles"] = [deterministic, workflow_engineer]
    draft["quality_profile"]["required_approval_roles"] = [
        "W64-AQA-ROLE-DETERMINISTIC"
    ]
    draft["provenance"]["model_bindings"] = [
        draft["provenance"]["model_bindings"][0]
    ]
    draft["workflow_spec"] = {
        "object_info_sha256": SHA_C,
        "patch_allowlist_id": "W64-AQA-WORKFLOW-PATCH-ALLOWLIST-001",
        "sandbox_required": True,
        "regression_suite_id": "w64-aqa-shadow-resize-v1",
    }
    contract = compiler.compile_contract(draft)
    assert contract["preflight_disposition"] == "READY_FOR_LEASE"
    assert contract["promotion_disposition"] == "EVIDENCE_ONLY"
    assert contract["quality_profile"]["required_approval_roles"] == [
        "W64-AQA-ROLE-DETERMINISTIC"
    ]
    compiler.verify_contract(contract)


def test_audio_shadow_runs_deterministic_stage_without_false_visual_authority() -> None:
    compiler = load_compiler()
    draft = valid_draft("audio")
    deterministic = draft["quality_profile"]["review_roles"][0]
    audio_semantic = {
        "role_id": "W64-AQA-ROLE-AUDIO-SEMANTIC",
        "authority": "audio_semantic",
        "can_approve": False,
        "required": False,
    }
    draft["execution_mode"] = "shadow_qualification"
    draft["quality_profile"]["review_roles"] = [deterministic, audio_semantic]
    draft["quality_profile"]["required_approval_roles"] = [
        "W64-AQA-ROLE-DETERMINISTIC"
    ]
    draft["provenance"]["model_bindings"] = [
        draft["provenance"]["model_bindings"][0]
    ]
    draft.pop("image_spec")
    draft["audio_spec"] = {
        "sample_rate_hz": 48000,
        "channels": 2,
        "duration_seconds": 2.0,
        "lufs_target": -18.0,
    }
    contract = compiler.compile_contract(draft)
    assert contract["preflight_disposition"] == "READY_FOR_LEASE"
    assert contract["quality_profile"]["required_approval_roles"] == [
        "W64-AQA-ROLE-DETERMINISTIC"
    ]
    assert "W64-AQA-ROLE-STRICT-VISUAL" not in {
        role["role_id"] for role in contract["quality_profile"]["review_roles"]
    }
    compiler.verify_contract(contract)


def test_audio_production_requires_semantic_audio_and_independent_juror() -> None:
    compiler = load_compiler()
    draft = valid_draft("audio")
    draft.pop("image_spec")
    draft["audio_spec"] = {
        "sample_rate_hz": 48000,
        "channels": 2,
        "duration_seconds": 2.0,
        "lufs_target": -18.0,
    }
    draft["quality_profile"]["review_roles"][1] = {
        "role_id": "W64-AQA-ROLE-AUDIO-SEMANTIC",
        "authority": "audio_semantic",
        "can_approve": True,
        "required": True,
    }
    draft["quality_profile"]["required_approval_roles"] = [
        "W64-AQA-ROLE-DETERMINISTIC",
        "W64-AQA-ROLE-AUDIO-SEMANTIC",
        "W64-AQA-ROLE-INDEPENDENT-JUROR",
    ]
    draft["provenance"]["model_bindings"][1]["role_id"] = (
        "W64-AQA-ROLE-AUDIO-SEMANTIC"
    )
    contract = compiler.compile_contract(draft)
    compiler.verify_contract(contract)

    missing_semantic = copy.deepcopy(draft)
    missing_semantic["quality_profile"]["required_approval_roles"].remove(
        "W64-AQA-ROLE-AUDIO-SEMANTIC"
    )
    with pytest.raises(compiler.ContractError, match="selected execution mode"):
        compiler.compile_contract(missing_semantic)


def test_av_technical_shadow_is_deterministic_without_fabricated_semantics() -> None:
    compiler = load_compiler()
    draft = valid_draft("av")
    deterministic = draft["quality_profile"]["review_roles"][0]
    strict_visual = {
        "role_id": "W64-AQA-ROLE-STRICT-VISUAL",
        "authority": "strict",
        "can_approve": False,
        "required": False,
    }
    audio_semantic = {
        "role_id": "W64-AQA-ROLE-AUDIO-SEMANTIC",
        "authority": "audio_semantic",
        "can_approve": False,
        "required": False,
    }
    draft["execution_mode"] = "shadow_qualification"
    draft["quality_profile"]["review_roles"] = [
        deterministic,
        strict_visual,
        audio_semantic,
    ]
    draft["quality_profile"]["required_approval_roles"] = [
        "W64-AQA-ROLE-DETERMINISTIC"
    ]
    draft["provenance"]["model_bindings"] = [
        draft["provenance"]["model_bindings"][0]
    ]
    draft["video_spec"] = {
        "width": 480,
        "height": 640,
        "fps": 24.0,
        "duration_seconds": 2.04,
        "sample_policy": "all_frames",
    }
    draft["audio_spec"] = {
        "sample_rate_hz": 48000,
        "channels": 2,
        "duration_seconds": 2.04,
        "lufs_target": -18.0,
    }
    draft["av_spec"] = {"max_sync_error_ms": 50.0, "alignment_required": True}
    contract = compiler.compile_contract(draft)
    assert contract["preflight_disposition"] == "READY_FOR_LEASE"
    assert contract["quality_profile"]["required_approval_roles"] == [
        "W64-AQA-ROLE-DETERMINISTIC"
    ]
    assert all(
        role["can_approve"] is False
        for role in contract["quality_profile"]["review_roles"]
        if role["role_id"] != "W64-AQA-ROLE-DETERMINISTIC"
    )
    compiler.verify_contract(contract)


def test_tampering_breaks_immutable_identity() -> None:
    compiler = load_compiler()
    contract = compiler.compile_contract(valid_draft())
    contract["resource_budget"]["max_gpu_seconds"] += 1
    with pytest.raises(compiler.ContractError, match="contract_id"):
        compiler.verify_contract(contract)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda draft: draft["authority_policy"].update({"ec2_allowed": True}), "schema violation"),
        (lambda draft: draft["attempt_policy"].update({"max_total_generations": 5}), "schema violation"),
        (
            lambda draft: draft["quality_profile"]["review_roles"][3].update({"can_approve": True}),
            "triage roles can never approve",
        ),
        (
            lambda draft: draft["quality_profile"].update(
                {"required_approval_roles": ["W64-AQA-ROLE-DETERMINISTIC", "W64-AQA-ROLE-PRIMARY-VISUAL"]}
            ),
                "selected execution mode",
        ),
        (
            lambda draft: draft["requested_outputs"][0].update(
                {"durable_relative_path": "../secret.txt"}
            ),
            "schema violation",
        ),
    ],
)
def test_fail_closed_negative_contracts(mutation, message: str) -> None:
    compiler = load_compiler()
    draft = valid_draft()
    mutation(draft)
    with pytest.raises(compiler.ContractError, match=message):
        compiler.compile_contract(draft)


def test_mask_contract_requires_golden_binding() -> None:
    compiler = load_compiler()
    draft = valid_draft("mask")
    contract = compiler.compile_contract(draft)
    compiler.verify_contract(contract)
    broken = copy.deepcopy(draft)
    del broken["mask_spec"]["golden_reference_sha256"]
    with pytest.raises(compiler.ContractError, match="schema violation"):
        compiler.compile_contract(broken)
