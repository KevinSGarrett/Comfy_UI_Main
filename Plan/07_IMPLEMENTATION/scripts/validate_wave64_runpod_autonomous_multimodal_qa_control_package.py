#!/usr/bin/env python3
"""Validate the additive W64-AQA project-control package."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PROGRAM = "W64-AQA"
EXPECTED_IDS = {f"W64-AQA-{number:03d}" for number in range(1, 20)}

PATHS = {
    "master": ROOT
    / "Plan/00_PROJECT_CONTROL/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_AND_CORRECTION_MASTER_PLAN.md",
    "architecture": ROOT
    / "Plan/02_TARGET_ARCHITECTURE/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_CONTROL_PLANE_ARCHITECTURE.md",
    "items": ROOT
    / "Plan/Items/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_ITEM_ROWS.csv",
    "tracker": ROOT
    / "Plan/Tracker/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_TRACKER_ROWS.csv",
    "requirements": ROOT
    / "Plan/Tracker/Waves/Wave64/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_REQUIREMENTS.json",
    "evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_EXTERNAL_STATE_RECONCILIATION_20260721.json",
    "capacity_evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_MULTIMODAL_QA_CAPACITY_OPTIONS_20260721.json",
    "current_prod_only_capacity_evidence": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_CURRENT_PROD_ONLY_CAPACITY_DECISION_20260722T031905Z.json",
    "current_pod_promoted_storage_evidence": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_CURRENT_POD_PROMOTED_STORAGE_RECONCILIATION_20260722.json",
    "phase_lease_shadow_evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_PHASE_LEASE_SHADOW_20260721.json",
    "phase_lease_runtime_canary_evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_PHASE_LEASE_RUNTIME_CANARY_20260721T213703Z.json",
    "strict_model_admission_hold_evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_STRICT_MODEL_ADMISSION_HOLD_20260721T215000Z.json",
    "strict_model_runtime_canary_evidence": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_STRICT_MODEL_RUNTIME_CANARY_20260722T032600Z.json",
    "e2e_shadow_rejected_integration_acceptance": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_E2E_SHADOW_20260722T033900Z/integration_acceptance.json",
    "e2e_shadow_accepted_integration_acceptance": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_E2E_SHADOW_20260722T034500Z/integration_acceptance.json",
    "shared_runpod_capacity_lease_adapter": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/shared_runpod_capacity_lease.py",
    "operations": ROOT
    / "Plan/Instructions/Operations/RUNPOD_AUTONOMOUS_MULTIMODAL_QA_OPERATING_PROTOCOL.md",
    "qa": ROOT
    / "Plan/Instructions/QA/RUNPOD_AUTONOMOUS_MULTIMODAL_QA_AND_BOUNDED_CORRECTION_PROTOCOL.md",
    "campaign_contract_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_campaign_contract.schema.json",
    "campaign_journal_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_campaign_journal.schema.json",
    "campaign_result_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_campaign_result.schema.json",
    "campaign_lease_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_campaign_lease.schema.json",
    "campaign_bulk_manifest_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_campaign_bulk_manifest.schema.json",
    "campaign_proposed_delta_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_campaign_proposed_delta.schema.json",
    "campaign_contract_compiler": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_campaign_contract.py",
    "campaign_bulk_manifest_compiler": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_campaign_bulk_manifest.py",
    "campaign_proposed_delta_compiler": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_campaign_proposed_delta.py",
    "campaign_executor": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_campaign.py",
    "campaign_cpu_shadow": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_campaign_cpu_shadow.py",
    "campaign_policy": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_campaign_policy.json",
    "campaign_role_registry": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_campaign_role_registry.json",
    "campaign_deterministic_role_reconciliation": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_CAMPAIGN_DETERMINISTIC_ROLE_RECONCILIATION_20260723T004500Z/integration_acceptance.json",
    "evidence_compiler_qualification_bundle_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_evidence_compiler_role_qualification_bundle.schema.json",
    "evidence_compiler_qualification_acceptance": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_EVIDENCE_COMPILER_ROLE_QUALIFICATION_20260722T235000Z/integration_acceptance.json",
    "campaign_multimodal_qa_registry": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_campaign_multimodal_qa_registry.json",
    "campaign_cpu_shadow_acceptance": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_AUTONOMOUS_CAMPAIGN_CPU_SHADOW_20260722T224015Z/integration_acceptance.json",
    "registry": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_multimodal_qa_role_registry.json",
    "role_package_inventory": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_role_package_inventory.json",
    "role_package_inventory_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_role_package_inventory.schema.json",
    "role_package_inventory_validator": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_runpod_autonomous_role_package_inventory.py",
    "role_package_identity_evidence": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_ROLE_PACKAGE_IDENTITY_QUALIFICATION_20260722T001002Z.json",
    "qwen36_dependency_preflight_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_qwen36_controller_dependency_preflight.schema.json",
    "qwen36_dependency_preflight_receipt": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_QWEN36_CONTROLLER_DEPENDENCY_PREFLIGHT_20260722T230000Z/remote_dependency_preflight.receipt.json",
    "qwen36_environment_reuse_admission_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_qwen36_controller_environment_reuse_admission.schema.json",
    "qwen36_attempted_environment_reuse_admission": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_QWEN36_CONTROLLER_IMPORT_CANARY_20260722T231000Z/attempted_environment_reuse_admission.json",
    "qwen36_import_canary_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_qwen36_controller_import_canary.schema.json",
    "qwen36_import_canary_receipt": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_QWEN36_CONTROLLER_IMPORT_CANARY_20260722T231000Z/remote_import_canary.receipt.json",
    "qwen36_environment_reuse_decision_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_qwen36_controller_environment_reuse_decision.schema.json",
    "qwen36_environment_reuse_decision": ROOT
    / "Plan/10_REGISTRIES/wave64_qwen36_controller_environment_reuse_decision.json",
    "qwen36_python_environment_admission_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_qwen36_controller_python_environment_admission.schema.json",
    "qwen36_python_environment_admission": ROOT
    / "Plan/10_REGISTRIES/wave64_qwen36_controller_python_environment_admission.json",
    "qwen36_python_environment_build_hold": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_QWEN36_CONTROLLER_ENVIRONMENT_BUILD_HOLD_20260722T231534Z/integration_acceptance.json",
    "model_install_admission_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_model_install_admission.schema.json",
    "qwen3_asr_install_admission": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_qwen3_asr_17b_install_admission.json",
    "model_install_admission_validator": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_runpod_model_install_admission.py",
    "model_package_installer": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/install_wave64_runpod_model_package.py",
    "qwen3_asr_install_admission_evidence": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_QWEN3_ASR_17B_INSTALL_ADMISSION_20260722T002600Z.json",
    "qwen3_asr_storage_install_evidence": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_QWEN3_ASR_17B_STORAGE_INSTALL_20260722T003615Z/evidence.json",
    "qwen3_asr_remote_install_receipt": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_QWEN3_ASR_17B_STORAGE_INSTALL_20260722T003615Z/remote_install_receipt.json",
    "qwen3_asr_dependency_preflight_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_qwen3_asr_dependency_preflight.schema.json",
    "qwen3_asr_dependency_preflight": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/preflight_wave64_qwen3_asr_dependencies.py",
    "qwen3_asr_dependency_preflight_evidence": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_QWEN3_ASR_17B_DEPENDENCY_PREFLIGHT_20260722T005102Z/evidence.json",
    "qwen3_asr_dependency_preflight_receipt": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_QWEN3_ASR_17B_DEPENDENCY_PREFLIGHT_20260722T005102Z/remote_dependency_preflight.receipt.json",
    "python_environment_admission_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_python_environment_admission.schema.json",
    "qwen3_asr_dependency_lock": ROOT
    / "Plan/10_REGISTRIES/Locks/wave64_qwen3_asr_0_0_6_py312_cu124.pylock.toml",
    "qwen3_asr_environment_admission": ROOT
    / "Plan/10_REGISTRIES/wave64_qwen3_asr_17b_dependency_environment_admission.json",
    "python_environment_admission_validator": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_runpod_python_environment_admission.py",
    "qwen3_asr_dependency_lock_evidence": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_QWEN3_ASR_17B_DEPENDENCY_LOCK_20260722T010000Z.json",
    "python_environment_build_receipt_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_python_environment_build_receipt.schema.json",
    "python_environment_build_receipt_validator": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_runpod_python_environment_build_receipt.py",
    "qwen3_asr_environment_build_evidence": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_QWEN3_ASR_17B_ENVIRONMENT_BUILD_20260722T010500Z/evidence.json",
    "qwen3_asr_environment_build_receipt": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_QWEN3_ASR_17B_ENVIRONMENT_BUILD_20260722T010500Z/remote_environment_build.receipt.json",
    "qwen3_asr_import_canary_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_qwen3_asr_import_canary.schema.json",
    "qwen3_asr_import_canary": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/canary_wave64_qwen3_asr_imports.py",
    "qwen3_asr_runtime_canary_receipt": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_QWEN3_ASR_RUNTIME_CANARY_20260722T035531Z/qwen3_asr_runtime_canary.json",
    "qwen3_asr_runtime_integration_acceptance": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_QWEN3_ASR_RUNTIME_CANARY_20260722T035531Z/integration_acceptance.json",
    "schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_multimodal_qa_decision.schema.json",
    "job_contract_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_multimodal_job_contract.schema.json",
    "job_contract_compiler": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_multimodal_job_contract.py",
    "phase_lease_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_multimodal_phase_lease.schema.json",
    "phase_lease_controller": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_phase_lease_controller.py",
    "image_measurement_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_image_measurement.schema.json",
    "image_measurement": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/measure_wave64_runpod_autonomous_image_quality.py",
    "image_shadow_evidence_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_image_shadow_evidence.schema.json",
    "image_shadow_evidence_producer": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_image_shadow_evidence.py",
    "image_shadow_evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_IMAGE_SHADOW_20260721T223341Z.json",
    "video_measurement_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_video_measurement.schema.json",
    "video_measurement": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/measure_wave64_runpod_autonomous_video_quality.py",
    "video_shadow_evidence_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_video_shadow_evidence.schema.json",
    "video_shadow_evidence_producer": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_video_shadow_evidence.py",
    "video_shadow_evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_VIDEO_SHADOW_20260721T224034Z.json",
    "audio_measurement_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_audio_measurement.schema.json",
    "audio_measurement": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/measure_wave64_runpod_autonomous_audio_quality.py",
    "audio_shadow_evidence_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_audio_shadow_evidence.schema.json",
    "audio_shadow_evidence_producer": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_audio_shadow_evidence.py",
    "audio_shadow_evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_AUDIO_SHADOW_20260721T221732Z.json",
    "av_shadow_evidence_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_av_shadow_evidence.schema.json",
    "av_shadow_evidence_producer": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_av_shadow_evidence.py",
    "av_shadow_evidence": ROOT
    / "Plan/Tracker/Evidence/WAVE64_RUNPOD_AUTONOMOUS_AV_SHADOW_20260721T222452Z.json",
    "mask_measurement_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_mask_measurement.schema.json",
    "mask_measurement": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/measure_wave64_runpod_autonomous_mask_quality.py",
    "maskfactory_consumer_contract_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_maskfactory_consumer_contract.schema.json",
    "maskfactory_consumer_contract_compiler": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_runpod_autonomous_maskfactory_consumer_contract.py",
    "tool_gateway_request_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_tool_gateway_request.schema.json",
    "tool_gateway_decision_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_tool_gateway_decision.schema.json",
    "tool_gateway_policy": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_tool_gateway_policy.json",
    "tool_gateway": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_runpod_autonomous_tool_gateway.py",
    "tool_executor_receipt_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_tool_executor_receipt.schema.json",
    "tool_executor_policy": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_tool_executor_policy.json",
    "tool_executor": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/execute_wave64_runpod_autonomous_readonly_tool.py",
    "tool_executor_fixture": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_TOOL_EXECUTOR_QUALIFICATION_20260721/jobs/W64-AQA-JOB-tool-executor-qualification/evidence/video_shadow_binding.json",
    "tool_executor_request": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_TOOL_EXECUTOR_QUALIFICATION_20260721/request.json",
    "tool_executor_decision": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_TOOL_EXECUTOR_QUALIFICATION_20260721/decision.json",
    "tool_executor_receipt": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_TOOL_EXECUTOR_QUALIFICATION_20260721/receipt.json",
    "tool_executor_qualification": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_TOOL_EXECUTOR_QUALIFICATION_20260721/qualification.json",
    "workflow_patch_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_workflow_patch.schema.json",
    "workflow_validation_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_workflow_validation.schema.json",
    "workflow_input_receipt_bundle_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_workflow_input_receipt_bundle.schema.json",
    "workflow_patch_policy": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_workflow_patch_policy.json",
    "workflow_validator": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_runpod_autonomous_workflow.py",
    "workflow_receipt_shadow_producer": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_workflow_receipt_shadow.py",
    "workflow_receipt_shadow_bundle": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_WORKFLOW_RECEIPT_BOUND_SHADOW_20260721T231000Z/input_receipt_bundle.json",
    "workflow_receipt_shadow_validation": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_WORKFLOW_RECEIPT_BOUND_SHADOW_20260721T231000Z/workflow_validation.json",
    "workflow_receipt_shadow_evidence": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_WORKFLOW_RECEIPT_BOUND_SHADOW_20260721T231000Z/evidence.json",
    "workflow_tool_execution_receipt_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_workflow_tool_execution_receipt.schema.json",
    "workflow_tool_executor_policy": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_workflow_tool_executor_policy.json",
    "workflow_tool_executor": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/execute_wave64_runpod_autonomous_workflow_tool.py",
    "workflow_tool_qualification_evidence": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_WORKFLOW_LOGICAL_TOOL_QUALIFICATION_20260721T232000Z/evidence.json",
    "workflow_inspect_execution_receipt": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_WORKFLOW_LOGICAL_TOOL_QUALIFICATION_20260721T232000Z/workflow_inspect.receipt.json",
    "validator_run_execution_receipt": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_WORKFLOW_LOGICAL_TOOL_QUALIFICATION_20260721T232000Z/validator_run.receipt.json",
    "workflow_candidate_staging_receipt_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_workflow_candidate_staging_receipt.schema.json",
    "workflow_candidate_stager_policy": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_workflow_candidate_stager_policy.json",
    "workflow_candidate_stager": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/stage_wave64_runpod_autonomous_workflow_candidate.py",
    "workflow_candidate_staging_evidence": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_WORKFLOW_CANDIDATE_STAGING_20260721T232803Z/evidence.json",
    "workflow_candidate_staging_receipt": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_WORKFLOW_CANDIDATE_STAGING_20260721T232803Z/receipts/candidate_write.receipt.json",
    "s3_object_staging_receipt_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_s3_object_staging_receipt.schema.json",
    "s3_evidence_staging_policy": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_s3_evidence_staging_policy.json",
    "infrastructure_reconciliation_payload": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_INFRASTRUCTURE_RECONCILIATION_PAYLOAD_20260721T233456Z.json",
    "s3_object_staging_receipt": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_S3_OBJECT_STAGING_RECEIPT_20260721T233801Z.json",
    "s3_bundle_transaction_receipt_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_s3_bundle_transaction_receipt.schema.json",
    "s3_bundle_transaction_policy": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_s3_bundle_transaction_policy.json",
    "s3_bundle_transaction_evidence": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_S3_BUNDLE_TRANSACTION_20260721T234740Z/evidence.json",
    "s3_bundle_transaction_receipt": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_S3_BUNDLE_TRANSACTION_20260721T234740Z/transaction.receipt.json",
    "s3_bundle_transaction_replay_receipt": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_S3_BUNDLE_TRANSACTION_20260721T234740Z/transaction.replay.receipt.json",
    "s3_git_binding_receipt_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_s3_git_binding_receipt.schema.json",
    "s3_git_binding_policy": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_s3_git_binding_policy.json",
    "s3_git_binding_payload": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_S3_GIT_BINDING_PAYLOAD_20260721T235517Z.json",
    "s3_git_binding_receipt": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_S3_GIT_BINDING_RECEIPT_20260721T235517Z.json",
    "correction_measurement_receipt_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_correction_measurement_receipt.schema.json",
    "correction_sandbox_receipt_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_correction_sandbox_receipt.schema.json",
    "correction_transaction_receipt_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_correction_transaction_receipt.schema.json",
    "correction_transaction_policy": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_correction_transaction_policy.json",
    "correction_transaction_evidence": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_CORRECTION_TRANSACTION_20260722T000248Z/evidence.json",
    "correction_transaction_receipt": ROOT
    / "Plan/Tracker/Evidence/W64_AQA_CORRECTION_TRANSACTION_20260722T000248Z/journal/0001.receipt.json",
    "correction_attempt_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_correction_attempt.schema.json",
    "correction_state_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_correction_state.schema.json",
    "correction_policy": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_correction_policy.py",
    "evidence_bundle_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_evidence_bundle.schema.json",
    "promotion_transaction_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_promotion_transaction.schema.json",
    "evidence_bundle_compiler": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/compile_and_replay_wave64_runpod_autonomous_evidence_bundle.py",
    "role_qualification_report_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_role_qualification_report.schema.json",
    "role_qualification_certificate_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_role_qualification_certificate.schema.json",
    "role_drift_decision_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_role_drift_decision.schema.json",
    "role_qualification_compiler": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/compile_and_evaluate_wave64_runpod_autonomous_role_qualification.py",
    "migration_event_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_one_pod_migration_event.schema.json",
    "migration_state_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_one_pod_migration_state.schema.json",
    "migration_policy": ROOT
    / "Plan/10_REGISTRIES/wave64_runpod_autonomous_one_pod_migration_policy.json",
    "migration_controller": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_one_pod_migration_controller.py",
    "reviewer_observation_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_reviewer_observation.schema.json",
    "review_authority_decision_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_review_authority_decision.schema.json",
    "review_authority_evaluator": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_runpod_autonomous_review_authority.py",
    "review_disagreement_decision_schema": ROOT
    / "Plan/08_SCHEMAS/runpod_autonomous_review_disagreement_decision.schema.json",
    "review_disagreement_resolver": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/resolve_wave64_runpod_autonomous_review_disagreement.py",
    "phase_lease_runtime_canary_producer": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_phase_lease_runtime_canary.py",
    "strict_model_runtime_canary_producer": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_runpod_autonomous_strict_model_runtime_canary.py",
    "e2e_shadow_job_runner": ROOT
    / "Plan/07_IMPLEMENTATION/scripts/run_wave64_runpod_autonomous_e2e_shadow_job.py",
}

SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\bgh[opusr]_[A-Za-z0-9]{20,}\b"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "runpod_bearer": re.compile(r"(?i)bearer\s+[A-Za-z0-9_-]{24,}"),
}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def recompute_self_hash(document: dict[str, Any], field: str) -> str:
    candidate = dict(document)
    candidate[field] = "0" * 64
    return hashlib.sha256(
        json.dumps(candidate, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def canonical_text_sha256(path: Path) -> str:
    """Hash repository text independent of Windows checkout line endings."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def collect_errors() -> list[str]:
    errors: list[str] = []
    missing = [str(path.relative_to(ROOT)) for path in PATHS.values() if not path.is_file()]
    if missing:
        return [f"missing required file: {path}" for path in missing]

    try:
        items = load_csv(PATHS["items"])
        tracker = load_csv(PATHS["tracker"])
        requirements = load_json(PATHS["requirements"])
        evidence = load_json(PATHS["evidence"])
        capacity_evidence = load_json(PATHS["capacity_evidence"])
        promoted_storage_evidence = load_json(
            PATHS["current_pod_promoted_storage_evidence"]
        )
        phase_lease_shadow_evidence = load_json(PATHS["phase_lease_shadow_evidence"])
        phase_lease_runtime_canary_evidence = load_json(
            PATHS["phase_lease_runtime_canary_evidence"]
        )
        strict_model_admission_hold_evidence = load_json(
            PATHS["strict_model_admission_hold_evidence"]
        )
        registry = load_json(PATHS["registry"])
        campaign_role_registry = load_json(PATHS["campaign_role_registry"])
        campaign_deterministic_role_reconciliation = load_json(
            PATHS["campaign_deterministic_role_reconciliation"]
        )
        evidence_compiler_qualification_bundle_schema = load_json(
            PATHS["evidence_compiler_qualification_bundle_schema"]
        )
        evidence_compiler_qualification_acceptance = load_json(
            PATHS["evidence_compiler_qualification_acceptance"]
        )
        role_package_inventory = load_json(PATHS["role_package_inventory"])
        role_package_inventory_schema = load_json(PATHS["role_package_inventory_schema"])
        role_package_identity_evidence = load_json(PATHS["role_package_identity_evidence"])
        qwen36_dependency_preflight_schema = load_json(PATHS["qwen36_dependency_preflight_schema"])
        qwen36_dependency_preflight_receipt = load_json(PATHS["qwen36_dependency_preflight_receipt"])
        qwen36_environment_reuse_admission_schema = load_json(PATHS["qwen36_environment_reuse_admission_schema"])
        qwen36_attempted_environment_reuse_admission = load_json(PATHS["qwen36_attempted_environment_reuse_admission"])
        qwen36_import_canary_schema = load_json(PATHS["qwen36_import_canary_schema"])
        qwen36_import_canary_receipt = load_json(PATHS["qwen36_import_canary_receipt"])
        qwen36_environment_reuse_decision_schema = load_json(PATHS["qwen36_environment_reuse_decision_schema"])
        qwen36_environment_reuse_decision = load_json(PATHS["qwen36_environment_reuse_decision"])
        qwen36_python_environment_admission_schema = load_json(PATHS["qwen36_python_environment_admission_schema"])
        qwen36_python_environment_admission = load_json(PATHS["qwen36_python_environment_admission"])
        qwen36_python_environment_build_hold = load_json(PATHS["qwen36_python_environment_build_hold"])
        model_install_admission_schema = load_json(PATHS["model_install_admission_schema"])
        qwen3_asr_install_admission = load_json(PATHS["qwen3_asr_install_admission"])
        qwen3_asr_install_admission_evidence = load_json(PATHS["qwen3_asr_install_admission_evidence"])
        qwen3_asr_storage_install_evidence = load_json(PATHS["qwen3_asr_storage_install_evidence"])
        qwen3_asr_remote_install_receipt = load_json(PATHS["qwen3_asr_remote_install_receipt"])
        qwen3_asr_dependency_preflight_schema = load_json(PATHS["qwen3_asr_dependency_preflight_schema"])
        qwen3_asr_dependency_preflight_evidence = load_json(PATHS["qwen3_asr_dependency_preflight_evidence"])
        qwen3_asr_dependency_preflight_receipt = load_json(PATHS["qwen3_asr_dependency_preflight_receipt"])
        python_environment_admission_schema = load_json(PATHS["python_environment_admission_schema"])
        qwen3_asr_environment_admission = load_json(PATHS["qwen3_asr_environment_admission"])
        qwen3_asr_dependency_lock_evidence = load_json(PATHS["qwen3_asr_dependency_lock_evidence"])
        python_environment_build_receipt_schema = load_json(PATHS["python_environment_build_receipt_schema"])
        qwen3_asr_environment_build_evidence = load_json(PATHS["qwen3_asr_environment_build_evidence"])
        qwen3_asr_environment_build_receipt = load_json(PATHS["qwen3_asr_environment_build_receipt"])
        qwen3_asr_import_canary_schema = load_json(PATHS["qwen3_asr_import_canary_schema"])
        qwen3_asr_runtime_canary_receipt = load_json(
            PATHS["qwen3_asr_runtime_canary_receipt"]
        )
        qwen3_asr_runtime_integration_acceptance = load_json(
            PATHS["qwen3_asr_runtime_integration_acceptance"]
        )
        schema = load_json(PATHS["schema"])
        job_contract_schema = load_json(PATHS["job_contract_schema"])
        phase_lease_schema = load_json(PATHS["phase_lease_schema"])
        image_measurement_schema = load_json(PATHS["image_measurement_schema"])
        image_shadow_evidence_schema = load_json(PATHS["image_shadow_evidence_schema"])
        image_shadow_evidence = load_json(PATHS["image_shadow_evidence"])
        video_measurement_schema = load_json(PATHS["video_measurement_schema"])
        video_shadow_evidence_schema = load_json(PATHS["video_shadow_evidence_schema"])
        video_shadow_evidence = load_json(PATHS["video_shadow_evidence"])
        audio_measurement_schema = load_json(PATHS["audio_measurement_schema"])
        audio_shadow_evidence_schema = load_json(PATHS["audio_shadow_evidence_schema"])
        audio_shadow_evidence = load_json(PATHS["audio_shadow_evidence"])
        av_shadow_evidence_schema = load_json(PATHS["av_shadow_evidence_schema"])
        av_shadow_evidence = load_json(PATHS["av_shadow_evidence"])
        mask_measurement_schema = load_json(PATHS["mask_measurement_schema"])
        maskfactory_consumer_contract_schema = load_json(
            PATHS["maskfactory_consumer_contract_schema"]
        )
        tool_gateway_request_schema = load_json(PATHS["tool_gateway_request_schema"])
        tool_gateway_decision_schema = load_json(PATHS["tool_gateway_decision_schema"])
        tool_gateway_policy = load_json(PATHS["tool_gateway_policy"])
        tool_executor_receipt_schema = load_json(PATHS["tool_executor_receipt_schema"])
        tool_executor_policy = load_json(PATHS["tool_executor_policy"])
        tool_executor_fixture = load_json(PATHS["tool_executor_fixture"])
        tool_executor_request = load_json(PATHS["tool_executor_request"])
        tool_executor_decision = load_json(PATHS["tool_executor_decision"])
        tool_executor_receipt = load_json(PATHS["tool_executor_receipt"])
        tool_executor_qualification = load_json(PATHS["tool_executor_qualification"])
        workflow_patch_schema = load_json(PATHS["workflow_patch_schema"])
        workflow_validation_schema = load_json(PATHS["workflow_validation_schema"])
        workflow_input_receipt_bundle_schema = load_json(PATHS["workflow_input_receipt_bundle_schema"])
        workflow_patch_policy = load_json(PATHS["workflow_patch_policy"])
        workflow_receipt_shadow_bundle = load_json(PATHS["workflow_receipt_shadow_bundle"])
        workflow_receipt_shadow_validation = load_json(PATHS["workflow_receipt_shadow_validation"])
        workflow_receipt_shadow_evidence = load_json(PATHS["workflow_receipt_shadow_evidence"])
        workflow_tool_execution_receipt_schema = load_json(PATHS["workflow_tool_execution_receipt_schema"])
        workflow_tool_executor_policy = load_json(PATHS["workflow_tool_executor_policy"])
        workflow_tool_qualification_evidence = load_json(PATHS["workflow_tool_qualification_evidence"])
        workflow_inspect_execution_receipt = load_json(PATHS["workflow_inspect_execution_receipt"])
        validator_run_execution_receipt = load_json(PATHS["validator_run_execution_receipt"])
        workflow_candidate_staging_receipt_schema = load_json(PATHS["workflow_candidate_staging_receipt_schema"])
        workflow_candidate_stager_policy = load_json(PATHS["workflow_candidate_stager_policy"])
        workflow_candidate_staging_evidence = load_json(PATHS["workflow_candidate_staging_evidence"])
        workflow_candidate_staging_receipt = load_json(PATHS["workflow_candidate_staging_receipt"])
        s3_object_staging_receipt_schema = load_json(PATHS["s3_object_staging_receipt_schema"])
        s3_evidence_staging_policy = load_json(PATHS["s3_evidence_staging_policy"])
        infrastructure_reconciliation_payload = load_json(PATHS["infrastructure_reconciliation_payload"])
        s3_object_staging_receipt = load_json(PATHS["s3_object_staging_receipt"])
        s3_bundle_transaction_receipt_schema = load_json(PATHS["s3_bundle_transaction_receipt_schema"])
        s3_bundle_transaction_policy = load_json(PATHS["s3_bundle_transaction_policy"])
        s3_bundle_transaction_evidence = load_json(PATHS["s3_bundle_transaction_evidence"])
        s3_bundle_transaction_receipt = load_json(PATHS["s3_bundle_transaction_receipt"])
        s3_bundle_transaction_replay_receipt = load_json(PATHS["s3_bundle_transaction_replay_receipt"])
        s3_git_binding_receipt_schema = load_json(PATHS["s3_git_binding_receipt_schema"])
        s3_git_binding_policy = load_json(PATHS["s3_git_binding_policy"])
        s3_git_binding_payload = load_json(PATHS["s3_git_binding_payload"])
        s3_git_binding_receipt = load_json(PATHS["s3_git_binding_receipt"])
        correction_measurement_receipt_schema = load_json(PATHS["correction_measurement_receipt_schema"])
        correction_sandbox_receipt_schema = load_json(PATHS["correction_sandbox_receipt_schema"])
        correction_transaction_receipt_schema = load_json(PATHS["correction_transaction_receipt_schema"])
        correction_transaction_policy = load_json(PATHS["correction_transaction_policy"])
        correction_transaction_evidence = load_json(PATHS["correction_transaction_evidence"])
        correction_transaction_receipt = load_json(PATHS["correction_transaction_receipt"])
        correction_attempt_schema = load_json(PATHS["correction_attempt_schema"])
        correction_state_schema = load_json(PATHS["correction_state_schema"])
        evidence_bundle_schema = load_json(PATHS["evidence_bundle_schema"])
        promotion_transaction_schema = load_json(PATHS["promotion_transaction_schema"])
        role_qualification_report_schema = load_json(PATHS["role_qualification_report_schema"])
        role_qualification_certificate_schema = load_json(PATHS["role_qualification_certificate_schema"])
        role_drift_decision_schema = load_json(PATHS["role_drift_decision_schema"])
        migration_event_schema = load_json(PATHS["migration_event_schema"])
        migration_state_schema = load_json(PATHS["migration_state_schema"])
        migration_policy = load_json(PATHS["migration_policy"])
        reviewer_observation_schema = load_json(PATHS["reviewer_observation_schema"])
        review_authority_decision_schema = load_json(PATHS["review_authority_decision_schema"])
        review_disagreement_decision_schema = load_json(PATHS["review_disagreement_decision_schema"])
    except (csv.Error, json.JSONDecodeError, OSError) as exc:
        return [f"parse failure: {exc}"]

    item_ids = {row.get("Item_ID", "") for row in items}
    tracker_ids = {row.get("Tracker_ID", "") for row in tracker}
    requirement_ids = {entry.get("id", "") for entry in requirements.get("requirements", [])}
    for label, observed in (
        ("items", item_ids),
        ("tracker", tracker_ids),
        ("requirements", requirement_ids),
    ):
        if observed != EXPECTED_IDS:
            errors.append(
                f"{label} ID parity failure: missing={sorted(EXPECTED_IDS - observed)} "
                f"extra={sorted(observed - EXPECTED_IDS)}"
            )

    if {row.get("Item_ID") for row in tracker} != EXPECTED_IDS:
        errors.append("tracker Item_ID references do not match the W64-AQA item set")

    promoted = promoted_storage_evidence.get("accepted_transfer_integrity", {})
    quarantine = promoted_storage_evidence.get("quarantine", {})
    promoted_truth = promoted_storage_evidence.get("qualification_truth", {})
    promoted_runtime = promoted_storage_evidence.get("runtime_policy", {})
    if (
        promoted.get("live_promoted_file_count") != 56
        or promoted.get("live_promoted_bytes") != 55804915269
        or promoted.get("hash_mismatch_count") != 0
        or promoted.get("symlink_alias_count") != 3
    ):
        errors.append("promoted-storage transfer-integrity summary mismatch")
    if (
        quarantine.get("wave42_file_count") != 77
        or quarantine.get("wave42_activated") is not False
        or quarantine.get("custom_node_repository_count") != 17
        or quarantine.get("dependencies_installed") is not False
        or quarantine.get("custom_nodes_activated") is not False
    ):
        errors.append("promoted-storage quarantine boundary mismatch")
    if (
        promoted_truth.get("storage_transfer_operational") is not True
        or promoted_truth.get("model_runtime_qualified") is not False
        or promoted_truth.get("workflow_qualified") is not False
        or promoted_truth.get("product_promotion") is not False
    ):
        errors.append("promoted-storage authority must remain transfer-only")
    if (
        promoted_runtime.get("sole_production_pod") != "1q4ji0gg1fkhvt"
        or promoted_runtime.get("alternative_pod_watching") is not False
        or promoted_runtime.get("alternative_pod_creation") is not False
        or promoted_runtime.get("external_inference") is not False
        or promoted_runtime.get("shared_coordinator_required") is not True
    ):
        errors.append("promoted-storage current-pod-only policy mismatch")

    if role_package_inventory.get("schema_version") != "wave64.aqa.role_package_inventory.v1":
        errors.append("role package inventory schema version mismatch")
    if role_package_inventory_schema.get("$id") != "runpod_autonomous_role_package_inventory.schema.json":
        errors.append("role package inventory schema identity mismatch")
    if model_install_admission_schema.get("$id") != "runpod_autonomous_model_install_admission.schema.json":
        errors.append("model install admission schema identity mismatch")
    if qwen3_asr_dependency_preflight_schema.get("$id") != "runpod_autonomous_qwen3_asr_dependency_preflight.schema.json":
        errors.append("Qwen3-ASR dependency preflight schema identity mismatch")
    if python_environment_admission_schema.get("$id") != "runpod_autonomous_python_environment_admission.schema.json":
        errors.append("Python environment admission schema identity mismatch")
    if python_environment_build_receipt_schema.get("$id") != "runpod_autonomous_python_environment_build_receipt.schema.json":
        errors.append("Python environment build receipt schema identity mismatch")
    if qwen3_asr_import_canary_schema.get("$id") != "runpod_autonomous_qwen3_asr_import_canary.schema.json":
        errors.append("Qwen3-ASR import canary schema identity mismatch")
    if qwen36_dependency_preflight_schema.get("$id") != "runpod_autonomous_qwen36_controller_dependency_preflight.schema.json":
        errors.append("Qwen3.6 controller dependency preflight schema identity mismatch")
    if qwen36_environment_reuse_admission_schema.get("$id") != "runpod_autonomous_qwen36_controller_environment_reuse_admission.schema.json":
        errors.append("Qwen3.6 controller environment reuse admission schema identity mismatch")
    if qwen36_import_canary_schema.get("$id") != "runpod_autonomous_qwen36_controller_import_canary.schema.json":
        errors.append("Qwen3.6 controller import canary schema identity mismatch")
    if qwen36_environment_reuse_decision_schema.get("$id") != "runpod_autonomous_qwen36_controller_environment_reuse_decision.schema.json":
        errors.append("Qwen3.6 controller environment reuse decision schema identity mismatch")
    if qwen36_python_environment_admission_schema.get("$id") != "runpod_autonomous_qwen36_controller_python_environment_admission.schema.json":
        errors.append("Qwen3.6 controller Python environment admission schema identity mismatch")
    if qwen36_python_environment_build_hold.get("status") != "PREPARED_BUILD_HELD_STORAGE_QUOTA":
        errors.append("Qwen3.6 controller environment build hold truth boundary mismatch")
    campaign_roles = {
        role.get("role_id"): role for role in campaign_role_registry.get("roles", [])
    }
    deterministic_role = campaign_roles.get("W64-AQA-ROLE-DETERMINISTIC", {})
    deterministic_certificate_path = ROOT / deterministic_role.get("certificate_path", "")
    deterministic_acceptance_path = ROOT / deterministic_role.get("acceptance_path", "")
    if (
        campaign_role_registry.get("executor_status") != "BLOCKED_UNQUALIFIED"
        or deterministic_role.get("qualification_state") != "QUALIFIED"
        or deterministic_role.get("qualification_scope")
        != "DECLARED_LOCAL_DETERMINISTIC_SCOPE_ONLY"
        or deterministic_role.get("semantic_or_promotion_authority") is not False
    ):
        errors.append("campaign deterministic role scope or executor hold mismatch")
    if (
        not deterministic_certificate_path.is_file()
        or canonical_text_sha256(deterministic_certificate_path)
        != deterministic_role.get("certificate_sha256")
        or not deterministic_acceptance_path.is_file()
        or canonical_text_sha256(deterministic_acceptance_path)
        != deterministic_role.get("acceptance_sha256")
    ):
        errors.append("campaign deterministic role evidence hash binding mismatch")
    reconciliation_effect = campaign_deterministic_role_reconciliation.get(
        "campaign_effect", {}
    )
    if (
        campaign_deterministic_role_reconciliation.get("disposition")
        != "ACCEPTED_CURRENT_MATRIX_BOUND_CERTIFICATE_FOR_EXACT_DECLARED_LOCAL_SCOPE"
        or reconciliation_effect.get("executor_operational") is not False
        or reconciliation_effect.get("other_roles_remain_unqualified") is not True
        or reconciliation_effect.get("multimodal_campaign_admitted") is not False
    ):
        errors.append("campaign deterministic role reconciliation authority mismatch")
    evidence_compiler_role = campaign_roles.get("W64-AQA-ROLE-EVIDENCE-COMPILER", {})
    evidence_compiler_certificate_path = ROOT / evidence_compiler_role.get(
        "certificate_path", ""
    )
    evidence_compiler_acceptance_path = ROOT / evidence_compiler_role.get(
        "acceptance_path", ""
    )
    if (
        evidence_compiler_qualification_bundle_schema.get("$id")
        != "https://comfy-ui-main.local/schemas/runpod_autonomous_evidence_compiler_role_qualification_bundle.schema.json"
        or evidence_compiler_role.get("qualification_state") != "QUALIFIED"
        or evidence_compiler_role.get("qualification_scope")
        != "CONTENT_AGNOSTIC_LOCAL_CPU_EVIDENCE_COMPILATION_ONLY"
        or evidence_compiler_role.get("semantic_or_promotion_authority") is not False
    ):
        errors.append("campaign evidence compiler role scope mismatch")
    if (
        not evidence_compiler_certificate_path.is_file()
        or canonical_text_sha256(evidence_compiler_certificate_path)
        != evidence_compiler_role.get("certificate_sha256")
        or not evidence_compiler_acceptance_path.is_file()
        or canonical_text_sha256(evidence_compiler_acceptance_path)
        != evidence_compiler_role.get("acceptance_sha256")
    ):
        errors.append("campaign evidence compiler evidence hash binding mismatch")
    evidence_compiler_observations = evidence_compiler_qualification_acceptance.get(
        "observations", {}
    )
    if (
        evidence_compiler_qualification_acceptance.get("disposition")
        != "ACCEPTED_CONTENT_AGNOSTIC_LOCAL_CPU_EVIDENCE_COMPILATION_SCOPE_ONLY"
        or evidence_compiler_observations.get("false_accept_rate") != 0
        or evidence_compiler_observations.get("false_reject_rate") != 0
        or evidence_compiler_observations.get("repeatability_rate") != 1
        or evidence_compiler_observations.get("refusal_correctness_rate") != 1
        or evidence_compiler_observations.get("peak_vram_gb") != 0
    ):
        errors.append("campaign evidence compiler acceptance metrics mismatch")
    for binding in evidence_compiler_qualification_acceptance.get("artifacts", {}).values():
        bound_path = ROOT / binding.get("path", "")
        if (
            not bound_path.is_file()
            or canonical_text_sha256(bound_path)
            != binding.get("sha256")
        ):
            errors.append("campaign evidence compiler acceptance artifact drift")
    if role_package_inventory.get("scope") != "REPOSITORY_BACKED_STATIC_AND_SCOPED_RUNTIME_EVIDENCE":
        errors.append("role package inventory must bind static and scoped runtime evidence")
    inventory_runtime = role_package_inventory.get("runtime_policy", {})
    inventory_current_pod = inventory_runtime.get("current_pod_only", {})
    if inventory_runtime.get("current_pod_remains_authoritative") is not True:
        errors.append("role package inventory must keep current pod authoritative")
    if (
        inventory_current_pod.get("pod_id") != "1q4ji0gg1fkhvt"
        or inventory_current_pod.get("physical_vram_mib") != 49140
        or inventory_current_pod.get("shared_coordinator_required") is not True
        or inventory_current_pod.get("sequential_residency_required") is not True
        or inventory_current_pod.get("alternative_hardware_watcher") is not True
        or inventory_current_pod.get("alternative_pod_creation") is not False
        or inventory_current_pod.get("authorized_watcher_candidate_creation") is not True
        or inventory_current_pod.get("authorized_watcher_id") != "runpod-us-wa-1-2xa40-guarded-migration-watcher"
        or inventory_current_pod.get("current_pod_authoritative_until_verified_migration_complete") is not True
        or inventory_current_pod.get("external_inference") is not False
    ):
        errors.append("role package inventory current-pod-only policy mismatch")
    inventory_packages = role_package_inventory.get("packages", [])
    if len(inventory_packages) != 17:
        errors.append("role package inventory must contain 17 exact package records")
    if any(package.get("authority", {}).get("operational") is not False for package in inventory_packages):
        errors.append("role package inventory cannot claim operational authority")
    if role_package_identity_evidence.get("runpod_contacted") is not False:
        errors.append("static role package evidence cannot claim RunPod contact")
    if role_package_identity_evidence.get("planned_official_package_count") != 7:
        errors.append("planned official role package count mismatch")
    if qwen3_asr_install_admission.get("status") != "STORAGE_INSTALL_ADMITTED_EXECUTION_PENDING":
        errors.append("Qwen3-ASR install admission must remain execution-pending")
    if qwen3_asr_install_admission.get("source", {}).get("revision") != "7278e1e70fe206f11671096ffdd38061171dd6e5":
        errors.append("Qwen3-ASR install admission revision mismatch")
    if qwen3_asr_install_admission_evidence.get("download_performed") is not False:
        errors.append("Qwen3-ASR admission evidence cannot claim download")
    if qwen3_asr_install_admission_evidence.get("gpu_or_lease_polled") is not False:
        errors.append("Qwen3-ASR admission evidence cannot claim GPU or lease polling")
    if qwen3_asr_storage_install_evidence.get("disposition") != "INSTALLED_FILE_SET_VERIFIED_ACTIVATION_PENDING":
        errors.append("Qwen3-ASR storage install disposition mismatch")
    if qwen3_asr_storage_install_evidence.get("replay_result") != "REUSED_VERIFIED_INSTALL":
        errors.append("Qwen3-ASR storage install replay is not verified")
    remote_receipt_sha256 = hashlib.sha256(PATHS["qwen3_asr_remote_install_receipt"].read_bytes()).hexdigest()
    if remote_receipt_sha256 != "cd52de9d1c4495d42c007d648dfa0355aa57eec64457cbdf967ba9ef39aa004e":
        errors.append("Qwen3-ASR remote install receipt mirror hash mismatch")
    if qwen3_asr_remote_install_receipt.get("status") != "INSTALLED_BYTES_VERIFIED_NOT_LOADED_OR_ACTIVATED":
        errors.append("Qwen3-ASR remote install receipt status mismatch")
    if any(qwen3_asr_remote_install_receipt.get("runtime_claims", {}).values()):
        errors.append("Qwen3-ASR storage receipt contains a false runtime claim")
    dependency_receipt_sha256 = hashlib.sha256(
        PATHS["qwen3_asr_dependency_preflight_receipt"].read_bytes()
    ).hexdigest()
    if dependency_receipt_sha256 != "ce3e2d78a2bfb13827f0aa4a73cc89d7dc8bb615192b7c3c71fef290d5267b0e":
        errors.append("Qwen3-ASR dependency preflight receipt mirror hash mismatch")
    expected_dependency_gaps = [
        "QWEN_ASR_DISTRIBUTION_MISSING",
        "INSTALLED_TRANSFORMERS_LACKS_QWEN3_ASR_SUPPORT",
    ]
    if qwen3_asr_dependency_preflight_receipt.get("classification") != "CONFIG_IDENTITY_PASS_DEPENDENCY_ACTION_REQUIRED":
        errors.append("Qwen3-ASR dependency preflight classification mismatch")
    if qwen3_asr_dependency_preflight_receipt.get("dependency_gaps") != expected_dependency_gaps:
        errors.append("Qwen3-ASR dependency preflight gaps mismatch")
    if any(qwen3_asr_dependency_preflight_receipt.get("runtime_claims", {}).values()):
        errors.append("Qwen3-ASR dependency preflight contains a false runtime claim")
    if qwen3_asr_dependency_preflight_evidence.get("pushed_preflight_commit") != "b5d996d1ae0f46e9dc08788647d7ac0013264dcb":
        errors.append("Qwen3-ASR dependency preflight commit binding mismatch")
    if qwen3_asr_dependency_preflight_evidence.get("remote_receipt_sha256") != dependency_receipt_sha256:
        errors.append("Qwen3-ASR dependency preflight evidence hash mismatch")
    runtime_receipt_sha256 = hashlib.sha256(
        PATHS["qwen3_asr_runtime_canary_receipt"].read_bytes()
    ).hexdigest()
    if runtime_receipt_sha256 != "fcac29d05809997fbeddd913dca5f988713b5b48cc6375ebd1e3207990b43d33":
        errors.append("Qwen3-ASR runtime canary receipt hash mismatch")
    if qwen3_asr_runtime_canary_receipt.get("status") != "PASS_RUNTIME_TRANSCRIPT_AND_PROCESS_EXIT_CLEANUP":
        errors.append("Qwen3-ASR runtime canary did not pass")
    if qwen3_asr_runtime_canary_receipt.get("transcription", {}).get("text") != "Once upon a midnight.":
        errors.append("Qwen3-ASR exact-fixture transcript mismatch")
    runtime_authority = qwen3_asr_runtime_canary_receipt.get("authority", {})
    if runtime_authority.get("exact_fixture_transcription") is not True:
        errors.append("Qwen3-ASR exact-fixture authority missing")
    if any(
        runtime_authority.get(key) is not False
        for key in (
            "general_asr_quality",
            "forced_alignment",
            "semantic_audio_quality",
            "product_promotion",
        )
    ):
        errors.append("Qwen3-ASR runtime receipt exceeds exact-fixture authority")
    if qwen3_asr_runtime_integration_acceptance.get("disposition") != "PARTIALLY_ADOPTED_EXACT_FIXTURE_ASR_RUNTIME_ONLY":
        errors.append("Qwen3-ASR integration acceptance disposition mismatch")
    if (
        qwen3_asr_runtime_integration_acceptance.get("accepted_receipt", {}).get("sha256")
        != runtime_receipt_sha256
    ):
        errors.append("Qwen3-ASR integration acceptance receipt binding mismatch")
    if qwen3_asr_dependency_preflight_evidence.get("retained_non_authoritative_control_copy", {}).get("authority") != "none":
        errors.append("mistyped Qwen3-ASR control copy must remain non-authoritative")
    if any(qwen3_asr_dependency_preflight_evidence.get("runtime_claims", {}).values()):
        errors.append("Qwen3-ASR dependency evidence contains a false runtime claim")
    dependency_lock_sha256 = hashlib.sha256(PATHS["qwen3_asr_dependency_lock"].read_bytes()).hexdigest()
    environment_resolution = qwen3_asr_environment_admission.get("resolution", {})
    environment_authority = qwen3_asr_environment_admission.get("authority", {})
    if dependency_lock_sha256 != "241dfaab72cea25fe705693ef715e8368d171720ae3dc37e1c17ecc81b18ba22":
        errors.append("Qwen3-ASR dependency lock hash mismatch")
    if qwen3_asr_environment_admission.get("status") != "DEPENDENCY_ENVIRONMENT_BUILD_ADMITTED_EXECUTION_PENDING":
        errors.append("Qwen3-ASR environment build admission status mismatch")
    if environment_resolution.get("package_count") != 105 or environment_resolution.get("wheel_count") != 109:
        errors.append("Qwen3-ASR environment resolution count mismatch")
    if environment_resolution.get("python_version") != "3.12.13":
        errors.append("Qwen3-ASR environment Python version mismatch")
    if any(
        environment_authority.get(key) is not False
        for key in (
            "model_library_import",
            "model_load",
            "tensor_allocation",
            "gpu_or_lease_poll",
            "inference",
            "service_change",
            "role_activation",
            "product_authority",
        )
    ):
        errors.append("Qwen3-ASR environment admission exceeds build authority")
    if qwen3_asr_dependency_lock_evidence.get("lock", {}).get("sha256") != dependency_lock_sha256:
        errors.append("Qwen3-ASR dependency lock evidence hash mismatch")
    if any(qwen3_asr_dependency_lock_evidence.get("execution_claims", {}).values()):
        errors.append("Qwen3-ASR dependency lock evidence contains an execution claim")
    environment_receipt_sha256 = hashlib.sha256(
        PATHS["qwen3_asr_environment_build_receipt"].read_bytes()
    ).hexdigest()
    if environment_receipt_sha256 != "e09c67aee503f511124b50af539067c9f82f1969490ab9b7d5127d9870c9dcd4":
        errors.append("Qwen3-ASR environment build receipt mirror hash mismatch")
    if qwen3_asr_environment_build_receipt.get("status") != "ISOLATED_ENVIRONMENT_INSTALLED_METADATA_VERIFIED_IMPORT_PENDING":
        errors.append("Qwen3-ASR environment build status mismatch")
    if qwen3_asr_environment_build_receipt.get("distribution_count") != 105:
        errors.append("Qwen3-ASR installed distribution count mismatch")
    if qwen3_asr_environment_build_receipt.get("environment_tree", {}).get("sha256") != "6625aa3c76c411424ede40ce6275d0fb378a1d9a017c205f74ffd356386f7c4a":
        errors.append("Qwen3-ASR environment tree digest mismatch")
    if any(qwen3_asr_environment_build_receipt.get("runtime_claims", {}).values()):
        errors.append("Qwen3-ASR environment build receipt contains a false runtime claim")
    if qwen3_asr_environment_build_evidence.get("remote_receipt_sha256") != environment_receipt_sha256:
        errors.append("Qwen3-ASR environment build evidence hash mismatch")
    if qwen3_asr_environment_build_evidence.get("active_comfyui_environment_post_build_signature", {}).get("matches_pre_build_preflight") is not True:
        errors.append("active ComfyUI environment post-build signature mismatch")
    if any(qwen3_asr_environment_build_evidence.get("runtime_claims", {}).values()):
        errors.append("Qwen3-ASR environment build evidence contains a false runtime claim")

    json_docs = (
        requirements,
        evidence,
        capacity_evidence,
        phase_lease_shadow_evidence,
        phase_lease_runtime_canary_evidence,
        strict_model_admission_hold_evidence,
        role_package_inventory,
        role_package_identity_evidence,
        qwen3_asr_install_admission,
        qwen3_asr_install_admission_evidence,
        qwen3_asr_storage_install_evidence,
        qwen3_asr_remote_install_receipt,
        qwen3_asr_dependency_preflight_evidence,
        qwen3_asr_dependency_preflight_receipt,
        qwen3_asr_environment_admission,
        qwen3_asr_dependency_lock_evidence,
        qwen3_asr_environment_build_evidence,
        qwen3_asr_environment_build_receipt,
        tool_executor_qualification,
        workflow_receipt_shadow_evidence,
        workflow_tool_qualification_evidence,
        workflow_candidate_staging_evidence,
        infrastructure_reconciliation_payload,
        s3_object_staging_receipt,
        s3_bundle_transaction_evidence,
        s3_git_binding_payload,
        s3_git_binding_receipt,
        correction_transaction_evidence,
        registry,
    )
    for document in json_docs:
        if document.get("program_id") != PROGRAM:
            errors.append("JSON document has the wrong program_id")

    if (
        phase_lease_runtime_canary_evidence.get("canary_disposition")
        != "PASS_ADMISSION_AND_RELEASE_NO_GENERATION"
    ):
        errors.append("phase lease runtime canary must pass admission and release")
    final_canary_state = phase_lease_runtime_canary_evidence.get(
        "final_controller_state", {}
    )
    if final_canary_state.get("state") != "IDLE" or final_canary_state.get("lease") is not None:
        errors.append("phase lease runtime canary must finish IDLE without a lease")
    if (
        phase_lease_runtime_canary_evidence.get("strict_model_inventory", {}).get(
            "inference_executed"
        )
        is not False
    ):
        errors.append("phase lease admission canary must not claim model inference")
    if phase_lease_runtime_canary_evidence.get("resource_mutations") != []:
        errors.append("phase lease admission canary must not contain resource mutations")
    if strict_model_admission_hold_evidence.get("admission_disposition") != "BLOCKED_NO_ACTION":
        errors.append("strict model admission hold must remain a no-action block")
    required_hold_flags = {
        "inference_executed": False,
        "model_load_executed": False,
        "lease_acquired": False,
        "product_approval_granted": False,
    }
    for key, expected in required_hold_flags.items():
        if strict_model_admission_hold_evidence.get(key) is not expected:
            errors.append(f"strict model admission hold {key} must be {expected}")
    if strict_model_admission_hold_evidence.get("resource_mutations") != []:
        errors.append("strict model admission hold must not contain resource mutations")
    if "ACTIVE_FOREIGN_GPU_WORKLOAD_PRESENT" not in strict_model_admission_hold_evidence.get(
        "blocker_codes", []
    ):
        errors.append("strict model admission hold must bind the observed foreign workload")

    if (
        audio_shadow_evidence.get("overall_disposition")
        != "PASS_DETERMINISTIC_SHADOW_BLOCKED_SEMANTIC_AUDIO_AUTHORITY"
    ):
        errors.append("canonical audio shadow must pass deterministic gates and block semantic authority")
    if audio_shadow_evidence.get("product_promotion_eligible") is not False:
        errors.append("canonical audio shadow must not grant product promotion")
    if audio_shadow_evidence.get("measurement", {}).get("disposition") != "PASS_DETERMINISTIC_GATES":
        errors.append("canonical audio shadow deterministic measurement must pass")
    if audio_shadow_evidence.get("semantic_release_gate", {}).get("runtime_executed") is not False:
        errors.append("canonical audio shadow must not claim semantic runtime execution")
    if audio_shadow_evidence.get("diagnostic_review", {}).get("semantic_audio_review_claimed") is not False:
        errors.append("rendered audio diagnostics must not claim semantic audio review")
    audio_required_roles = set(
        audio_shadow_evidence.get("technical_contract", {})
        .get("quality_profile", {})
        .get("required_approval_roles", [])
    )
    if audio_required_roles != {"W64-AQA-ROLE-DETERMINISTIC"}:
        errors.append("audio technical shadow must require deterministic authority only")
    if (
        av_shadow_evidence.get("overall_disposition")
        != "PASS_DETERMINISTIC_AV_SHADOW_BLOCKED_SEMANTIC_AUTHORITIES"
    ):
        errors.append("canonical AV shadow must pass deterministic gates and block semantic authorities")
    if av_shadow_evidence.get("product_promotion_eligible") is not False:
        errors.append("canonical AV shadow must not grant product promotion")
    if av_shadow_evidence.get("measurement", {}).get("disposition") != "PASS_DETERMINISTIC_GATES":
        errors.append("canonical AV shadow deterministic measurement must pass")
    if av_shadow_evidence.get("decoded_frame_review", {}).get("motion_review_claimed") is not False:
        errors.append("single decoded AV frame must not claim motion review")
    av_metrics = av_shadow_evidence.get("measurement", {}).get("metrics", {})
    if av_metrics.get("av_stream_start_offset_ms") != 0.0:
        errors.append("canonical AV shadow stream start offset must be zero")
    if av_metrics.get("av_stream_duration_delta_ms") != 0.0:
        errors.append("canonical AV shadow stream duration delta must be zero")
    av_required_roles = set(
        av_shadow_evidence.get("technical_contract", {})
        .get("quality_profile", {})
        .get("required_approval_roles", [])
    )
    if av_required_roles != {"W64-AQA-ROLE-DETERMINISTIC"}:
        errors.append("AV technical shadow must require deterministic authority only")
    if (
        image_shadow_evidence.get("overall_disposition")
        != "PASS_DETERMINISTIC_IMAGE_GATES_REJECT_VISUAL_DEFECTS_STRICT_RUNTIME_HELD"
    ):
        errors.append("canonical image shadow must retain deterministic pass and visual rejection")
    if image_shadow_evidence.get("product_promotion_eligible") is not False:
        errors.append("canonical rejected image shadow must not grant product promotion")
    if image_shadow_evidence.get("measurement", {}).get("disposition") != "PASS_DETERMINISTIC_GATES":
        errors.append("canonical image shadow deterministic measurement must pass")
    if image_shadow_evidence.get("codex_visual_review", {}).get("status") != "REJECT_KNOWN_BLOCKING_DEFECTS":
        errors.append("canonical image shadow must retain the whole-image rejection")
    image_defects = set(
        image_shadow_evidence.get("codex_visual_review", {}).get("blocking_findings", [])
    )
    if image_defects != {"contact_placement_not_exact_target", "contact_shadow_not_clear"}:
        errors.append("canonical image shadow blocking defect set changed")
    if image_shadow_evidence.get("strict_model_gate", {}).get("runtime_executed") is not False:
        errors.append("canonical image shadow must not claim held strict-model execution")
    if (
        video_shadow_evidence.get("overall_disposition")
        != "PASS_DETERMINISTIC_VIDEO_GATES_DIAGNOSTIC_CONTACT_SHEET_ONLY_STRICT_RUNTIME_HELD"
    ):
        errors.append("canonical video shadow must pass deterministic gates and retain review limits")
    if video_shadow_evidence.get("product_promotion_eligible") is not False:
        errors.append("canonical video shadow must not grant product promotion")
    if video_shadow_evidence.get("measurement", {}).get("disposition") != "PASS_DETERMINISTIC_GATES":
        errors.append("canonical video shadow deterministic measurement must pass")
    video_metrics = video_shadow_evidence.get("measurement", {}).get("metrics", {})
    if video_metrics.get("frame_count") != 49 or video_metrics.get("sample_count") != 24:
        errors.append("canonical video shadow frame and sample counts changed")
    if video_metrics.get("duplicate_sample_fraction") != 0.0:
        errors.append("canonical video shadow must retain zero sampled duplicates")
    if video_shadow_evidence.get("contact_sheet_review", {}).get("whole_clip_review_claimed") is not False:
        errors.append("video contact sheet must not claim whole-clip review")
    if video_shadow_evidence.get("strict_model_gate", {}).get("runtime_executed") is not False:
        errors.append("canonical video shadow must not claim held strict-model execution")

    runtime = registry.get("runtime_policy", {})
    expected_limits = {
        "max_repair_attempts_per_defect": 2,
        "max_total_generation_attempts": 4,
        "max_no_progress_cycles": 2,
    }
    for key, expected in expected_limits.items():
        if runtime.get(key) != expected:
            errors.append(f"registry {key} must equal {expected}")
    if runtime.get("generation_host") != "runpod_only":
        errors.append("registry must bind generation_host to runpod_only")
    if runtime.get("ec2_forbidden") is not True:
        errors.append("registry must explicitly forbid EC2")
    if runtime.get("phase_safe_exclusive_gpu") is not True:
        errors.append("registry must require phase-safe exclusive GPU use")
    if runtime.get("primary_pod_first_for_every_role") is not True:
        errors.append("registry must target every role to the primary pod first")
    if runtime.get("external_inference_forbidden") is not True:
        errors.append("registry must forbid external inference")
    one_pod = runtime.get("one_pod_capacity_policy", {})
    if one_pod.get("state") != "CURRENT_PRODUCTION_POD_ONLY":
        errors.append("capacity policy must select the current production pod only")
    if one_pod.get("pod_id") != runtime.get("current_pod_id"):
        errors.append("current-pod capacity policy must bind the runtime pod ID")
    if one_pod.get("gpu_type") != runtime.get("gpu") or one_pod.get("gpu_count") != 1:
        errors.append("current-pod capacity policy must bind the one RTX 6000 Ada GPU")
    if one_pod.get("alternative_pod_watcher_enabled") is not True:
        errors.append("authorized alternative-pod watcher must remain enabled")
    if one_pod.get("candidate_creation_enabled") is not False:
        errors.append("project alternative-pod candidate creation must remain disabled")
    if one_pod.get("authorized_watcher_candidate_creation_enabled") is not True:
        errors.append("authorized watcher candidate creation must remain enabled")
    if one_pod.get("authorized_watcher_id") != "runpod-us-wa-1-2xa40-guarded-migration-watcher":
        errors.append("authorized alternative-pod watcher identity mismatch")
    if one_pod.get("current_pod_authoritative_until_verified_migration_complete") is not True:
        errors.append("current pod must remain authoritative until verified migration completion")
    if one_pod.get("external_inference_enabled") is not False:
        errors.append("current-pod capacity policy must forbid external inference")
    if one_pod.get("all_required_roles_target_current_pod") is not True:
        errors.append("every required role must target the current production pod")
    if "secondary_burst_policy" in runtime:
        errors.append("secondary burst policy must be absent under current-pod-only authority")

    roles = {entry.get("role_id"): entry for entry in registry.get("roles", [])}
    required_roles = {
        "W64-AQA-ROLE-GENERATION",
        "W64-AQA-ROLE-DETERMINISTIC",
        "W64-AQA-ROLE-STRICT-VISUAL",
        "W64-AQA-ROLE-FAST-TRIAGE",
        "W64-AQA-ROLE-TEXT-PLANNER",
        "W64-AQA-ROLE-CONTROLLER",
        "W64-AQA-ROLE-PRIMARY-VISUAL",
        "W64-AQA-ROLE-INDEPENDENT-JUROR",
        "W64-AQA-ROLE-AUDIO-SEMANTIC",
        "W64-AQA-ROLE-WORKFLOW-ENGINEER",
        "W64-AQA-ROLE-GOLDEN-MASK",
        "W64-AQA-ROLE-SENIOR-ARBITER",
    }
    if not required_roles.issubset(roles):
        errors.append(f"missing roles: {sorted(required_roles - roles.keys())}")

    strict = roles.get("W64-AQA-ROLE-STRICT-VISUAL", {})
    if strict.get("model") != "qwen2.5vl:32b":
        errors.append("current strict visual role must bind qwen2.5vl:32b")
    if strict.get("product_approval_sufficient") is not False:
        errors.append("strict reviewer alone must not be sufficient for approval")

    triage = roles.get("W64-AQA-ROLE-FAST-TRIAGE", {})
    if triage.get("product_approval_sufficient") is not False:
        errors.append("triage role must not have product approval authority")
    if "PASS_PRODUCT" not in triage.get("forbidden_decisions", []):
        errors.append("triage role must explicitly forbid PASS_PRODUCT")

    arbiter = roles.get("W64-AQA-ROLE-SENIOR-ARBITER", {})
    if arbiter.get("deployment_target") != "current_production_pod_only":
        errors.append("senior arbiter must target the current production pod")
    if arbiter.get("operational") is not False:
        errors.append("unqualified senior arbiter must not be operational")

    workflow = roles.get("W64-AQA-ROLE-WORKFLOW-ENGINEER", {})
    if workflow.get("proposal_only") is not True:
        errors.append("workflow engineer must be proposal-only")

    if tool_gateway_policy.get("decision_only") is not True:
        errors.append("tool gateway must remain decision-only until a separate executor qualifies")
    if tool_gateway_policy.get("external_inference_allowed") is not False:
        errors.append("tool gateway must forbid external inference")
    forbidden_actions = set(tool_gateway_policy.get("forbidden_action_types", []))
    required_forbidden_actions = {"shell", "git", "cloud", "tracker_write", "promotion", "secret_read", "arbitrary_network"}
    if not required_forbidden_actions.issubset(forbidden_actions):
        errors.append("tool gateway forbidden action coverage is incomplete")
    workflow_actions = {
        action_id for action_id, action in tool_gateway_policy.get("allowed_actions", {}).items()
        if "W64-AQA-ROLE-WORKFLOW-ENGINEER" in action.get("roles", [])
    }
    if {"candidate_write", "evidence_append", "shadow_generation_submit"} & workflow_actions:
        errors.append("workflow engineer must not write candidates/evidence or submit generation")
    if tool_executor_policy.get("qualified_actions") != ["artifact_read"]:
        errors.append("tool executor must qualify artifact_read only")
    executor_read_policy = tool_executor_policy.get("artifact_read", {})
    required_executor_controls = {
        "digest_only": True,
        "content_exposure_allowed": False,
        "target_write_allowed": False,
        "network_allowed": False,
        "parameters_required_empty": True,
        "reject_symlinks_and_reparse_points": True,
        "require_stable_identity_before_open_after": True,
    }
    if any(
        executor_read_policy.get(key) is not expected
        for key, expected in required_executor_controls.items()
    ):
        errors.append("tool executor read-only controls are incomplete or weakened")
    if executor_read_policy.get("max_bytes") != 16777216:
        errors.append("tool executor byte ceiling must remain exactly 16 MiB")
    if executor_read_policy.get("max_elapsed_ms") != 5000:
        errors.append("tool executor elapsed-time ceiling must remain exactly five seconds")
    if tool_executor_policy.get("all_other_actions") != "UNQUALIFIED_DENY":
        errors.append("tool executor must deny all unqualified actions")
    if tool_executor_decision.get("admission_disposition") != "ADMIT_FOR_SEPARATE_EXECUTOR":
        errors.append("canonical tool executor decision must be admitted by the decision-only gate")
    receipt_flags = {
        "disposition": "PASS_READ_ONLY_ARTIFACT_DIGEST",
        "execution_performed": True,
        "content_exposed": False,
        "target_write_performed": False,
        "network_used": False,
    }
    for key, expected in receipt_flags.items():
        if tool_executor_receipt.get(key) != expected:
            errors.append(f"canonical tool executor receipt {key} must be {expected}")
    if tool_executor_receipt.get("decision_id") != tool_executor_decision.get("decision_id"):
        errors.append("tool executor receipt is not bound to the canonical decision")
    if tool_executor_receipt.get("request_id") != tool_executor_request.get("request_id"):
        errors.append("tool executor receipt is not bound to the canonical request")
    if tool_executor_decision.get("decision_id") != recompute_self_hash(tool_executor_decision, "decision_id"):
        errors.append("canonical tool executor decision self-hash mismatch")
    if tool_executor_receipt.get("receipt_id") != recompute_self_hash(tool_executor_receipt, "receipt_id"):
        errors.append("canonical tool executor receipt self-hash mismatch")
    if tool_executor_qualification.get("disposition") != "PASS_READ_ONLY_ARTIFACT_DIGEST_EXECUTOR_ONLY":
        errors.append("tool executor qualification must remain limited to read-only artifact digest")
    qualification_runtime = tool_executor_qualification.get("runtime_claims", {})
    if any(qualification_runtime.get(key) is not False for key in (
        "runpod_contacted",
        "gpu_used",
        "comfyui_execution_performed",
        "model_inference_performed",
        "product_promotion_granted",
    )):
        errors.append("tool executor qualification must not claim runtime or promotion authority")
    gateway_policy_sha256 = hashlib.sha256(
        json.dumps(tool_gateway_policy, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    executor_policy_sha256 = hashlib.sha256(
        json.dumps(tool_executor_policy, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    if tool_executor_receipt.get("gateway_policy_sha256") != gateway_policy_sha256:
        errors.append("tool executor receipt gateway policy hash mismatch")
    if tool_executor_receipt.get("executor_policy_sha256") != executor_policy_sha256:
        errors.append("tool executor receipt executor policy hash mismatch")
    fixture_sha256 = hashlib.sha256(PATHS["tool_executor_fixture"].read_bytes()).hexdigest()
    if tool_executor_receipt.get("artifact_sha256") != fixture_sha256:
        errors.append("tool executor receipt artifact hash mismatch")
    source_path = ROOT / tool_executor_fixture.get("source_evidence_path", "")
    if not source_path.is_file():
        errors.append("tool executor qualification source evidence is missing")
    elif hashlib.sha256(source_path.read_bytes()).hexdigest() != tool_executor_fixture.get("source_evidence_sha256"):
        errors.append("tool executor qualification source evidence hash mismatch")
    if workflow_patch_policy.get("copy_on_write_required") is not True:
        errors.append("workflow patching must be copy-on-write")
    if workflow_patch_policy.get("graph_mutation_allowed") is not False:
        errors.append("workflow graph mutation must remain forbidden")
    if workflow_patch_policy.get("threshold_mutation_allowed") is not False:
        errors.append("workflow threshold mutation must remain forbidden")
    if workflow_receipt_shadow_bundle.get("bundle_id") != recompute_self_hash(
        workflow_receipt_shadow_bundle, "bundle_id"
    ):
        errors.append("canonical workflow input receipt bundle self-hash mismatch")
    if workflow_receipt_shadow_validation.get("validation_id") != recompute_self_hash(
        workflow_receipt_shadow_validation, "validation_id"
    ):
        errors.append("canonical receipt-bound workflow validation self-hash mismatch")
    if workflow_receipt_shadow_validation.get("input_binding_disposition") != "PASS_EXECUTOR_RECEIPT_BOUND":
        errors.append("canonical workflow validation must be executor-receipt bound")
    if set(workflow_receipt_shadow_validation.get("input_executor_receipt_ids", {})) != {
        "workflow", "object_info", "contract", "model_inventory"
    }:
        errors.append("canonical workflow validation must bind all four inspector inputs")
    if workflow_receipt_shadow_validation.get("disposition") != "PASS_STATIC_VALIDATION":
        errors.append("canonical receipt-bound workflow validation must pass static gates")
    if workflow_receipt_shadow_validation.get("sandbox_execution_performed") is not False:
        errors.append("canonical receipt-bound workflow shadow must not claim sandbox execution")
    if workflow_receipt_shadow_evidence.get("disposition") != "PASS_RECEIPT_BOUND_STATIC_WORKFLOW_INSPECTION_ONLY":
        errors.append("canonical workflow shadow disposition must remain static-inspection only")
    workflow_runtime_claims = workflow_receipt_shadow_evidence.get("runtime_claims", {})
    if any(workflow_runtime_claims.get(key) is not False for key in (
        "runpod_contacted", "gpu_used", "comfyui_execution_performed",
        "model_inference_performed", "candidate_write_performed", "product_promotion_granted",
    )):
        errors.append("canonical workflow receipt shadow must not claim runtime or promotion authority")
    workflow_shadow_root = PATHS["workflow_receipt_shadow_evidence"].parent
    for relative_path, expected_sha256 in workflow_receipt_shadow_evidence.get(
        "file_manifest_sha256", {}
    ).items():
        bound_path = workflow_shadow_root / relative_path
        if not bound_path.is_file():
            errors.append(f"workflow receipt shadow manifest path missing: {relative_path}")
        elif hashlib.sha256(bound_path.read_bytes()).hexdigest() != expected_sha256:
            errors.append(f"workflow receipt shadow manifest hash mismatch: {relative_path}")
    if set(workflow_tool_executor_policy.get("qualified_actions", {})) != {
        "workflow_inspect", "validator_run"
    }:
        errors.append("workflow logical tool executor exact action set changed")
    if workflow_tool_executor_policy.get("execution_modes") != ["shadow_qualification"]:
        errors.append("workflow logical tool executor must remain shadow-only")
    workflow_tool_mandatory_controls = {
        "parameters_required_empty": True,
        "input_receipt_bundle_required": True,
        "content_exposure_allowed": False,
        "sandbox_execution_allowed": False,
        "target_write_allowed": False,
        "network_allowed": False,
        "all_other_actions": "UNQUALIFIED_DENY",
    }
    if any(
        workflow_tool_executor_policy.get(key) != expected
        for key, expected in workflow_tool_mandatory_controls.items()
    ):
        errors.append("workflow logical tool executor controls are incomplete or weakened")
    expected_logical_receipts = {
        "workflow_inspect": (workflow_inspect_execution_receipt, "workflow.graph"),
        "validator_run": (validator_run_execution_receipt, "validate.workflow.v1"),
    }
    logical_receipt_ids: set[str] = set()
    for action_type, (receipt, logical_target) in expected_logical_receipts.items():
        required_values = {
            "action_type": action_type,
            "logical_target": logical_target,
            "disposition": "PASS_RECEIPT_BOUND_STATIC_WORKFLOW_TOOL",
            "execution_performed": True,
            "content_exposed": False,
            "sandbox_execution_performed": False,
            "target_write_performed": False,
            "network_used": False,
            "input_binding_disposition": "PASS_EXECUTOR_RECEIPT_BOUND",
            "workflow_validation_disposition": "PASS_STATIC_VALIDATION",
        }
        for key, expected in required_values.items():
            if receipt.get(key) != expected:
                errors.append(f"canonical {action_type} receipt {key} mismatch")
        if receipt.get("receipt_id") != recompute_self_hash(receipt, "receipt_id"):
            errors.append(f"canonical {action_type} execution receipt self-hash mismatch")
        logical_receipt_ids.add(receipt.get("receipt_id", ""))
    if len(logical_receipt_ids) != 2:
        errors.append("workflow logical tool execution receipts must be distinct")
    if workflow_tool_qualification_evidence.get("disposition") != "PASS_EXACT_SHADOW_STATIC_WORKFLOW_LOGICAL_ACTIONS_ONLY":
        errors.append("workflow logical tool qualification must remain exact and shadow-only")
    logical_runtime_claims = workflow_tool_qualification_evidence.get("runtime_claims", {})
    if any(logical_runtime_claims.get(key) is not False for key in (
        "runpod_contacted", "gpu_used", "comfyui_execution_performed",
        "sandbox_execution_performed", "model_inference_performed",
        "candidate_write_performed", "content_exposed", "network_used",
        "product_promotion_granted",
    )):
        errors.append("workflow logical tool qualification must not claim runtime or write authority")
    logical_evidence_root = PATHS["workflow_tool_qualification_evidence"].parent
    for relative_path, expected_sha256 in workflow_tool_qualification_evidence.get(
        "file_manifest_sha256", {}
    ).items():
        bound_path = logical_evidence_root / relative_path
        if not bound_path.is_file():
            errors.append(f"workflow logical tool manifest path missing: {relative_path}")
        elif hashlib.sha256(bound_path.read_bytes()).hexdigest() != expected_sha256:
            errors.append(f"workflow logical tool manifest hash mismatch: {relative_path}")
    candidate_stager_mandatory = {
        "qualified_action": "candidate_write",
        "execution_modes": ["shadow_qualification"],
        "target_template": "jobs/{job_id}/candidates/workflow.candidate.json",
        "parameters_required_empty": True,
        "input_receipt_bundle_required": True,
        "typed_patch_required": True,
        "copy_on_write_required": True,
        "immutable_candidate_required": True,
        "base_input_write_allowed": False,
        "overwrite_allowed": False,
        "comfyui_execution_allowed": False,
        "model_inference_allowed": False,
        "network_allowed": False,
        "production_mode_allowed": False,
        "all_other_targets": "UNQUALIFIED_DENY",
    }
    if any(
        workflow_candidate_stager_policy.get(key) != expected
        for key, expected in candidate_stager_mandatory.items()
    ):
        errors.append("workflow candidate stager policy is incomplete or weakened")
    candidate_receipt_required = {
        "disposition": "PASS_TYPED_COPY_ON_WRITE_CANDIDATE_STAGED",
        "candidate_write_performed": True,
        "base_input_write_performed": False,
        "overwrite_performed": False,
        "comfyui_execution_performed": False,
        "model_inference_performed": False,
        "network_used": False,
        "copy_on_write_verified": True,
    }
    for key, expected in candidate_receipt_required.items():
        if workflow_candidate_staging_receipt.get(key) != expected:
            errors.append(f"canonical workflow candidate staging receipt {key} mismatch")
    if workflow_candidate_staging_receipt.get("receipt_id") != recompute_self_hash(
        workflow_candidate_staging_receipt, "receipt_id"
    ):
        errors.append("canonical workflow candidate staging receipt self-hash mismatch")
    if workflow_candidate_staging_evidence.get("disposition") != "PASS_TYPED_COPY_ON_WRITE_CANDIDATE_STAGING_ONLY":
        errors.append("workflow candidate staging evidence disposition changed")
    if workflow_candidate_staging_evidence.get("copy_on_write_verified") is not True:
        errors.append("workflow candidate staging copy-on-write proof missing")
    candidate_runtime_claims = workflow_candidate_staging_evidence.get("runtime_claims", {})
    expected_candidate_claims = {
        "runpod_contacted": False,
        "gpu_used": False,
        "comfyui_execution_performed": False,
        "model_inference_performed": False,
        "candidate_staging_write_performed": True,
        "base_input_write_performed": False,
        "network_used": False,
        "production_promotion_granted": False,
    }
    if any(candidate_runtime_claims.get(key) != expected for key, expected in expected_candidate_claims.items()):
        errors.append("workflow candidate staging runtime claims mismatch")
    candidate_evidence_root = PATHS["workflow_candidate_staging_evidence"].parent
    for relative_path, expected_sha256 in workflow_candidate_staging_evidence.get(
        "file_manifest_sha256", {}
    ).items():
        bound_path = candidate_evidence_root / relative_path
        if not bound_path.is_file():
            errors.append(f"workflow candidate staging manifest path missing: {relative_path}")
        elif hashlib.sha256(bound_path.read_bytes()).hexdigest() != expected_sha256:
            errors.append(f"workflow candidate staging manifest hash mismatch: {relative_path}")
    s3_policy_required = {
        "classification": "LEGACY_AWS_EVIDENCE_LINEAGE_AUDIT_ONLY",
        "active_production_platform": False,
        "runpod_critical_path_dependency": False,
        "automatic_execution_allowed": False,
        "explicit_task_specific_user_authorization_required": True,
        "execution_authority": "CODEX_INTEGRATION_ONLY",
        "bucket": "comfy-ui-main-runtime-029530099913-us-east-1",
        "region": "us-east-1",
        "key_prefix": "evidence/w64-aqa/qualification/objects",
        "content_addressed_key_required": True,
        "if_none_match_star_required": True,
        "checksum_sha256_required": True,
        "server_side_encryption": "AES256",
        "bucket_versioning_required": True,
        "head_verification_required": True,
        "overwrite_allowed": False,
        "delete_allowed": False,
        "s3_presence_is_acceptance": False,
        "product_promotion_allowed": False,
        "credential_values_in_receipts_allowed": False,
        "public_access_block_must_be_known_before_production_promotion": True,
        "public_access_block_requirement_scope": "HISTORICAL_AWS_PROMOTION_PATH_ONLY_NOT_RUNPOD_PRODUCTION",
        "all_other_buckets_or_prefixes": "UNQUALIFIED_DENY",
    }
    if any(s3_evidence_staging_policy.get(key) != expected for key, expected in s3_policy_required.items()):
        errors.append("S3 evidence staging policy is incomplete or weakened")
    if s3_object_staging_receipt.get("receipt_id") != recompute_self_hash(
        s3_object_staging_receipt, "receipt_id"
    ):
        errors.append("S3 object staging receipt self-hash mismatch")
    payload_sha256 = hashlib.sha256(PATHS["infrastructure_reconciliation_payload"].read_bytes()).hexdigest()
    if s3_object_staging_receipt.get("content_sha256") != payload_sha256:
        errors.append("S3 object staging receipt does not bind the reconciliation payload")
    expected_s3_key = f"evidence/w64-aqa/qualification/objects/{payload_sha256}.json"
    if s3_object_staging_receipt.get("key") != expected_s3_key:
        errors.append("S3 object staging key is not content-addressed")
    s3_receipt_required = {
        "server_side_encryption": "AES256",
        "conditional_create_used": True,
        "head_verification_passed": True,
        "metadata_verification_passed": True,
        "overwrite_performed": False,
        "delete_performed": False,
        "s3_presence_is_acceptance": False,
        "product_promotion_granted": False,
        "public_access_block_readable": False,
        "disposition": "PASS_CONTENT_ADDRESSED_S3_OBJECT_STAGING_ONLY",
    }
    if any(s3_object_staging_receipt.get(key) != expected for key, expected in s3_receipt_required.items()):
        errors.append("S3 object staging receipt claims changed")
    s3_bundle_policy_required = {
        "execution_authority": "CODEX_INTEGRATION_ONLY",
        "bucket": "comfy-ui-main-runtime-029530099913-us-east-1",
        "key_prefix": "evidence/w64-aqa/qualification/bundles",
        "content_addressed_objects_required": True,
        "manifest_written_last": True,
        "conditional_create_required": True,
        "head_replay_required": True,
        "resume_by_verified_reuse": True,
        "overwrite_allowed": False,
        "delete_allowed": False,
        "rollback_is_nonpublication": True,
        "s3_presence_is_acceptance": False,
        "product_promotion_allowed": False,
        "all_other_buckets_or_prefixes": "UNQUALIFIED_DENY",
    }
    if any(
        s3_bundle_transaction_policy.get(key) != expected
        for key, expected in s3_bundle_policy_required.items()
    ):
        errors.append("S3 bundle transaction policy is incomplete or weakened")
    for label, receipt in (
        ("first", s3_bundle_transaction_receipt),
        ("replay", s3_bundle_transaction_replay_receipt),
    ):
        if receipt.get("receipt_id") != recompute_self_hash(receipt, "receipt_id"):
            errors.append(f"S3 bundle {label} receipt self-hash mismatch")
        for key, expected in {
            "replay_disposition": "MATCH",
            "manifest_written_last": True,
            "resume_safe": True,
            "overwrite_performed": False,
            "delete_performed": False,
            "s3_presence_is_acceptance": False,
            "product_promotion_granted": False,
            "disposition": "PASS_VERIFIED_RESUMABLE_S3_BUNDLE_STAGING_ONLY",
        }.items():
            if receipt.get(key) != expected:
                errors.append(f"S3 bundle {label} receipt {key} mismatch")
    if (s3_bundle_transaction_receipt.get("created_object_count"), s3_bundle_transaction_receipt.get("reused_object_count")) != (10, 0):
        errors.append("S3 bundle first execution counts changed")
    if (s3_bundle_transaction_replay_receipt.get("created_object_count"), s3_bundle_transaction_replay_receipt.get("reused_object_count")) != (0, 10):
        errors.append("S3 bundle idempotent replay counts changed")
    if s3_bundle_transaction_receipt.get("bundle_id") != s3_bundle_transaction_replay_receipt.get("bundle_id"):
        errors.append("S3 bundle receipts do not bind the same bundle")
    if s3_bundle_transaction_evidence.get("disposition") != "PASS_LIVE_RESUMABLE_S3_BUNDLE_STAGING_ONLY":
        errors.append("S3 bundle transaction evidence disposition changed")
    if s3_bundle_transaction_evidence.get("bundle_decision") != "BLOCKED":
        errors.append("S3 qualification bundle must remain non-product BLOCKED")
    s3_bundle_claims = s3_bundle_transaction_evidence.get("runtime_claims", {})
    expected_bundle_claims = {
        "runpod_contacted": False,
        "gpu_used": False,
        "comfyui_execution_performed": False,
        "semantic_product_review_performed": False,
        "s3_bundle_staging_performed": True,
        "overwrite_performed": False,
        "delete_performed": False,
        "product_promotion_granted": False,
    }
    if any(s3_bundle_claims.get(key) != expected for key, expected in expected_bundle_claims.items()):
        errors.append("S3 bundle transaction runtime claims mismatch")
    s3_bundle_root = PATHS["s3_bundle_transaction_evidence"].parent
    for relative_path, expected_sha256 in s3_bundle_transaction_evidence.get("file_manifest_sha256", {}).items():
        bound_path = s3_bundle_root / relative_path
        if not bound_path.is_file():
            errors.append(f"S3 bundle evidence manifest path missing: {relative_path}")
        elif hashlib.sha256(bound_path.read_bytes()).hexdigest() != expected_sha256:
            errors.append(f"S3 bundle evidence manifest hash mismatch: {relative_path}")
    s3_binding_required = {
        "execution_authority": "CODEX_INTEGRATION_ONLY",
        "pushed_commit_required": True,
        "commit_must_contain_retained_bundle_evidence": True,
        "content_addressed_binding_required": True,
        "conditional_create_required": True,
        "checksum_head_replay_required": True,
        "overwrite_allowed": False,
        "delete_allowed": False,
        "s3_presence_is_acceptance": False,
        "product_promotion_allowed": False,
        "all_other_buckets_or_prefixes": "UNQUALIFIED_DENY",
    }
    if any(s3_git_binding_policy.get(key) != expected for key, expected in s3_binding_required.items()):
        errors.append("S3 Git binding policy is incomplete or weakened")
    binding_payload_sha256 = hashlib.sha256(PATHS["s3_git_binding_payload"].read_bytes()).hexdigest()
    if s3_git_binding_receipt.get("content_sha256") != binding_payload_sha256:
        errors.append("S3 Git binding receipt does not bind payload bytes")
    if s3_git_binding_receipt.get("receipt_id") != recompute_self_hash(s3_git_binding_receipt, "receipt_id"):
        errors.append("S3 Git binding receipt self-hash mismatch")
    if s3_git_binding_payload.get("evidence_commit") != s3_git_binding_receipt.get("evidence_commit"):
        errors.append("S3 Git binding commit mismatch")
    if s3_git_binding_payload.get("bundle_id") != s3_git_binding_receipt.get("bundle_id"):
        errors.append("S3 Git binding bundle mismatch")
    for key, expected in {
        "conditional_create_used": True,
        "head_verification_passed": True,
        "overwrite_performed": False,
        "delete_performed": False,
        "s3_presence_is_acceptance": False,
        "product_promotion_granted": False,
        "disposition": "PASS_PUSHED_GIT_COMMIT_TO_VERIFIED_S3_BUNDLE_BINDING_ONLY",
    }.items():
        if s3_git_binding_receipt.get(key) != expected:
            errors.append(f"S3 Git binding receipt {key} mismatch")
    correction_transaction_required = {
        "execution_modes": ["shadow_qualification"],
        "candidate_staging_disposition": "PASS_TYPED_COPY_ON_WRITE_CANDIDATE_STAGED",
        "measurement_deterministic_required": True,
        "synthetic_sandbox_disposition": "PASS_SYNTHETIC_SANDBOX_FIXTURE_ONLY",
        "comfyui_execution_required_false": True,
        "immutable_state_publish_required": True,
        "immutable_receipt_publish_required": True,
        "resume_by_exact_replay_required": True,
        "overwrite_allowed": False,
        "delete_allowed": False,
        "network_allowed": False,
        "production_mode_allowed": False,
        "promotion_allowed": False,
    }
    if any(
        correction_transaction_policy.get(key) != expected
        for key, expected in correction_transaction_required.items()
    ):
        errors.append("correction transaction policy is incomplete or weakened")
    if correction_transaction_receipt.get("receipt_id") != recompute_self_hash(
        correction_transaction_receipt, "receipt_id"
    ):
        errors.append("correction transaction receipt self-hash mismatch")
    for key, expected in {
        "state_publish_status": "REUSED_EXACT_AFTER_REPLAY",
        "transition_disposition": "REVERT_CANDIDATE_CONTINUE",
        "resume_safe": True,
        "comfyui_execution_performed": False,
        "runtime_measurement_performed": False,
        "network_used": False,
        "overwrite_performed": False,
        "delete_performed": False,
        "promotion_authorized": False,
        "disposition": "PASS_RECEIPT_BOUND_CORRECTION_TRANSACTION_FIXTURE_ONLY",
    }.items():
        if correction_transaction_receipt.get(key) != expected:
            errors.append(f"correction transaction receipt {key} mismatch")
    if correction_transaction_evidence.get("disposition") != "PASS_RECEIPT_BOUND_CORRECTION_CRASH_RESUME_REVERT_FIXTURE_ONLY":
        errors.append("correction transaction evidence disposition changed")
    for key in ("crash_after_state_publish_observed", "completed_replay_exact", "accepted_parent_preserved"):
        if correction_transaction_evidence.get(key) is not True:
            errors.append(f"correction transaction evidence {key} proof missing")
    correction_claims = correction_transaction_evidence.get("runtime_claims", {})
    if any(correction_claims.get(key) is not False for key in (
        "runpod_contacted", "gpu_used", "comfyui_execution_performed",
        "runtime_measurement_performed", "network_used", "overwrite_performed",
        "delete_performed", "product_promotion_granted",
    )):
        errors.append("correction transaction evidence overclaims runtime or promotion")
    correction_root = PATHS["correction_transaction_evidence"].parent
    for relative_path, expected_sha256 in correction_transaction_evidence.get("file_manifest_sha256", {}).items():
        bound_path = correction_root / relative_path
        if not bound_path.is_file():
            errors.append(f"correction transaction manifest path missing: {relative_path}")
        elif hashlib.sha256(bound_path.read_bytes()).hexdigest() != expected_sha256:
            errors.append(f"correction transaction manifest hash mismatch: {relative_path}")
    if migration_policy.get("decision_only") is not True:
        errors.append("migration controller must remain decision-only")
    if migration_policy.get("old_pod_stops_only_after_integration_switch") is not True:
        errors.append("migration policy must forbid old-pod stop before integration switch")
    if migration_policy.get("status") != "GUARDED_2XA40_WATCHER_ACTIVE_CURRENT_POD_AUTHORITATIVE":
        errors.append("guarded 2xA40 migration policy status mismatch")
    if migration_policy.get("migration_candidates_enabled") is not False:
        errors.append("project migration candidates must remain disabled")
    if migration_policy.get("authorized_watcher_candidate_creation_enabled") is not True:
        errors.append("authorized watcher candidate creation must remain enabled")
    if migration_policy.get("stock_watcher_enabled") is not True:
        errors.append("authorized stock watcher must remain enabled")
    if migration_policy.get("authorized_automation_id") != "runpod-us-wa-1-2xa40-guarded-migration-watcher":
        errors.append("guarded migration watcher identity mismatch")
    if migration_policy.get("current_pod_authoritative_until_verified_migration_complete") is not True:
        errors.append("migration policy released current pod authority early")
    if migration_policy.get("watcher_never_touches_aws") is not True:
        errors.append("guarded migration watcher AWS boundary mismatch")
    if migration_policy.get("watcher_never_terminates_pods") is not True:
        errors.append("guarded migration watcher termination boundary mismatch")
    current_profile = migration_policy.get("current_production_profile", {})
    if current_profile.get("pod_id") != runtime.get("current_pod_id"):
        errors.append("guarded migration policy must bind the current production pod")

    modalities = set(schema.get("properties", {}).get("modality", {}).get("enum", []))
    required_modalities = {"image", "video", "audio", "av", "mask", "workflow"}
    if modalities != required_modalities:
        errors.append("decision schema modality coverage is incomplete")

    all_text = "\n".join(path.read_text(encoding="utf-8") for path in PATHS.values())
    required_phrases = (
        "Qwen3-Coder-Next",
        "Qwen3-Omni",
        "Qwen3-ASR-1.7B",
        "Qwen3.5-397B",
        "Qwen3.5-122B",
        "InternVL3.5-241B",
        "InternVL",
        "golden-mask",
        "MaskFactory",
        "workflow",
        "two repair attempts",
        "four total generation attempts",
        "two no-progress",
        "EC2",
        "RunPod",
        "RTX 6000 Ada",
    )
    lowered = all_text.lower()
    for phrase in required_phrases:
        if phrase.lower() not in lowered:
            errors.append(f"required cross-surface concept missing: {phrase}")

    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(all_text):
            errors.append(f"possible secret literal detected: {name}")

    try:
        import jsonschema

        jsonschema.Draft7Validator.check_schema(schema)
        jsonschema.Draft202012Validator.check_schema(role_package_inventory_schema)
        jsonschema.Draft202012Validator(
            role_package_inventory_schema,
            format_checker=jsonschema.FormatChecker(),
        ).validate(role_package_inventory)
        jsonschema.Draft202012Validator(qwen36_dependency_preflight_schema).validate(
            qwen36_dependency_preflight_receipt
        )
        jsonschema.Draft202012Validator(qwen36_environment_reuse_admission_schema).validate(
            qwen36_attempted_environment_reuse_admission
        )
        jsonschema.Draft202012Validator(qwen36_import_canary_schema).validate(
            qwen36_import_canary_receipt
        )
        jsonschema.Draft202012Validator(qwen36_environment_reuse_decision_schema).validate(
            qwen36_environment_reuse_decision
        )
        jsonschema.Draft202012Validator(qwen36_python_environment_admission_schema).validate(
            qwen36_python_environment_admission
        )
        jsonschema.Draft7Validator.check_schema(job_contract_schema)
        jsonschema.Draft7Validator.check_schema(phase_lease_schema)
        jsonschema.Draft7Validator.check_schema(image_measurement_schema)
        jsonschema.Draft7Validator.check_schema(image_shadow_evidence_schema)
        jsonschema.Draft7Validator(
            image_shadow_evidence_schema,
            format_checker=jsonschema.FormatChecker(),
        ).validate(image_shadow_evidence)
        jsonschema.Draft7Validator.check_schema(video_measurement_schema)
        jsonschema.Draft7Validator.check_schema(video_shadow_evidence_schema)
        jsonschema.Draft7Validator(
            video_shadow_evidence_schema,
            format_checker=jsonschema.FormatChecker(),
        ).validate(video_shadow_evidence)
        jsonschema.Draft7Validator.check_schema(audio_measurement_schema)
        jsonschema.Draft7Validator.check_schema(audio_shadow_evidence_schema)
        jsonschema.Draft7Validator(
            audio_shadow_evidence_schema,
            format_checker=jsonschema.FormatChecker(),
        ).validate(audio_shadow_evidence)
        jsonschema.Draft7Validator.check_schema(av_shadow_evidence_schema)
        jsonschema.Draft7Validator(
            av_shadow_evidence_schema,
            format_checker=jsonschema.FormatChecker(),
        ).validate(av_shadow_evidence)
        jsonschema.Draft7Validator.check_schema(mask_measurement_schema)
        jsonschema.Draft7Validator.check_schema(maskfactory_consumer_contract_schema)
        jsonschema.Draft7Validator.check_schema(tool_gateway_request_schema)
        jsonschema.Draft7Validator.check_schema(tool_gateway_decision_schema)
        jsonschema.Draft7Validator.check_schema(tool_executor_receipt_schema)
        jsonschema.Draft7Validator(tool_gateway_request_schema).validate(tool_executor_request)
        jsonschema.Draft7Validator(tool_gateway_decision_schema).validate(tool_executor_decision)
        jsonschema.Draft7Validator(tool_executor_receipt_schema).validate(tool_executor_receipt)
        jsonschema.Draft7Validator.check_schema(workflow_patch_schema)
        jsonschema.Draft7Validator.check_schema(workflow_validation_schema)
        jsonschema.Draft7Validator.check_schema(workflow_input_receipt_bundle_schema)
        jsonschema.Draft7Validator(workflow_input_receipt_bundle_schema).validate(
            workflow_receipt_shadow_bundle
        )
        jsonschema.Draft7Validator(workflow_validation_schema).validate(
            workflow_receipt_shadow_validation
        )
        for receipt in workflow_receipt_shadow_bundle.get("receipts", {}).values():
            jsonschema.Draft7Validator(tool_executor_receipt_schema).validate(receipt)
        jsonschema.Draft7Validator.check_schema(workflow_tool_execution_receipt_schema)
        jsonschema.Draft7Validator(workflow_tool_execution_receipt_schema).validate(
            workflow_inspect_execution_receipt
        )
        jsonschema.Draft7Validator(workflow_tool_execution_receipt_schema).validate(
            validator_run_execution_receipt
        )
        jsonschema.Draft7Validator.check_schema(workflow_candidate_staging_receipt_schema)
        jsonschema.Draft7Validator(workflow_candidate_staging_receipt_schema).validate(
            workflow_candidate_staging_receipt
        )
        jsonschema.Draft7Validator.check_schema(s3_object_staging_receipt_schema)
        jsonschema.Draft7Validator(s3_object_staging_receipt_schema).validate(
            s3_object_staging_receipt
        )
        jsonschema.Draft7Validator.check_schema(s3_bundle_transaction_receipt_schema)
        jsonschema.Draft7Validator(s3_bundle_transaction_receipt_schema).validate(
            s3_bundle_transaction_receipt
        )
        jsonschema.Draft7Validator(s3_bundle_transaction_receipt_schema).validate(
            s3_bundle_transaction_replay_receipt
        )
        jsonschema.Draft7Validator.check_schema(s3_git_binding_receipt_schema)
        jsonschema.Draft7Validator(s3_git_binding_receipt_schema).validate(s3_git_binding_receipt)
        jsonschema.Draft7Validator.check_schema(correction_measurement_receipt_schema)
        jsonschema.Draft7Validator.check_schema(correction_sandbox_receipt_schema)
        jsonschema.Draft7Validator.check_schema(correction_transaction_receipt_schema)
        jsonschema.Draft7Validator(correction_transaction_receipt_schema).validate(
            correction_transaction_receipt
        )
        jsonschema.Draft7Validator.check_schema(correction_attempt_schema)
        jsonschema.Draft7Validator.check_schema(correction_state_schema)
        jsonschema.Draft7Validator.check_schema(evidence_bundle_schema)
        jsonschema.Draft7Validator.check_schema(promotion_transaction_schema)
        jsonschema.Draft7Validator.check_schema(role_qualification_report_schema)
        jsonschema.Draft7Validator.check_schema(role_qualification_certificate_schema)
        jsonschema.Draft7Validator.check_schema(role_drift_decision_schema)
        jsonschema.Draft7Validator.check_schema(migration_event_schema)
        jsonschema.Draft7Validator.check_schema(migration_state_schema)
        jsonschema.Draft7Validator.check_schema(reviewer_observation_schema)
        jsonschema.Draft7Validator.check_schema(review_authority_decision_schema)
        jsonschema.Draft7Validator.check_schema(review_disagreement_decision_schema)
    except ImportError:
        pass
    except Exception as exc:  # pragma: no cover - library supplies exact detail
        errors.append(f"decision schema invalid: {exc}")

    return errors


def main() -> int:
    errors = collect_errors()
    result = {
        "status": "PASS" if not errors else "FAIL",
        "classification": (
            "W64_AQA_CONTROL_PACKAGE_VALID" if not errors else "W64_AQA_CONTROL_PACKAGE_INVALID"
        ),
        "program_id": PROGRAM,
        "validated_files": [str(path.relative_to(ROOT)).replace("\\", "/") for path in PATHS.values()],
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
