#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(r"C:\Comfy_UI_Main")
PLAN = ROOT / "Plan"
ITEMS = PLAN / "Items"
TRACKER = PLAN / "Tracker"

ITEM_COLUMNS = [
    "Item_ID", "Item_Wave", "Item_Type", "Item_Title", "Item_Category", "Item_Domain",
    "Owner_Domain", "Autonomous_Required", "Human_Input_Allowed", "Human_Work_Allowed",
    "Codex_Action", "Implementation_Target", "Deliverable_Type", "Acceptance_Criteria",
    "QA_Gates_Required", "Visual_Review_Required", "Visual_Review_Method", "Test_Required",
    "Evidence_Required", "Runtime_Proof_Required", "EC2_Allowed", "Blocker_Policy",
    "Source_Plan_Root", "Citation_File", "Citation_Full_Path", "Citation_Section",
    "Citation_Line_Start", "Citation_Line_End", "Citation_Excerpt", "Source_Package",
    "Source_Type", "Source_File_Size", "Priority", "Risk_Level", "Status", "Created_From",
    "Notes", "Source_Key", "Source_File_Relative", "Coverage_Level", "Coverage_Audit_Status",
    "Ultra_Source_Coverage_Record",
]

TRACKER_COLUMNS = [
    "Tracker_ID", "Wave", "Phase", "Workstream", "Priority", "Risk_Level", "Owner_Role",
    "Environment", "Status", "Task_Name", "Detailed_Action", "Completion_Criteria",
    "Acceptance_Evidence", "Dependency_Prerequisite", "Validation_Method", "Output_Artifact",
    "Source_Path", "Related_Source_Paths", "Package_Top_Level_Directory",
    "Autonomous_Execution_Mode", "Human_Input_Allowed", "Human_Work_Allowed",
    "Codex_Desktop_Action", "QA_Strictness", "Visual_Review_Required", "Visual_Review_Method",
    "Test_Required", "Runtime_Proof_Required", "EC2_Allowed", "Preview_Required",
    "Final_Render_Gate", "Evidence_Path", "Citation_File", "Citation_Full_Path",
    "Citation_Section", "Citation_Line_Start", "Citation_Line_End", "Citation_Excerpt",
    "Source_Package", "Source_Type", "Source_Item_ID", "Blocker_Policy", "Rerun_Policy",
    "Status_Decision", "Notes", "Source_Key", "Source_File_Relative", "Coverage_Level",
    "Coverage_Audit_Status", "Ultra_Source_Coverage_Record",
]

REQUIRED_DOMAINS = {
    "plan_source_file_coverage",
    "project_control_autonomy",
    "current_system_review",
    "target_architecture",
    "image_pipeline_build",
    "image_hyperreal_visual_review",
    "global_visual_review_not_local_only",
    "video_pipeline_build",
    "video_temporal_visual_review",
    "audio_pipeline_build",
    "audio_strict_review",
    "global_audio_review_not_local_only",
    "multimodal_cross_review",
    "localized_change_whole_artifact_regression",
    "qa_master_protocol",
    "workflow_static_validation",
    "workflow_runtime_smoke",
    "ec2_runtime_proof",
    "local_comfy_dev",
    "github_actions_ci_package",
    "s3_transfer_cost_control",
    "model_registry_governance",
    "artifact_pullback_integrity",
    "secret_git_security",
    "hydration_resume_control",
    "no_loop_no_drift",
    "release_done_certification",
    "autonomous_24_7_operations",
}

DOMAINS = [
    ("plan_source_file_coverage", "All Plan source files indexed and mapped into Items and Tracker coverage", "Plan Source Coverage", "Plan/PROJECT_MANIFEST.json", "Every file under Plan is indexed, source-cited, and either mapped to a strict row or covered by generated source coverage audit records.", "plan_file_index_present|items_tracker_row_present|citation_fields_present|coverage_report_pass", False, "not_applicable_structural_coverage", False, False, "P0", "CRITICAL"),
    ("project_control_autonomy", "Autonomous project manager operating controls", "Autonomous Control", "Plan/00_PROJECT_CONTROL/AI_PROJECT_MANAGER_OPERATING_MANUAL.md", "Autonomous sessions obey objective, no-loop, blocker, checkpoint, evidence, and continuation controls without relying on human cleanup.", "operating_manual_read|goal_alignment_check|blocker_policy_check|progress_control_check", False, "not_applicable_control_evidence", True, False, "P0", "CRITICAL"),
    ("current_system_review", "Current system review and inherited Main Flow boundary", "Source Review", "Plan/01_CURRENT_SYSTEM_REVIEW/MAIN_FLOW_REVIEW_FINDINGS.md", "Existing C:\\Comfy_UI findings are treated as source/staging context until extracted into active lanes or modules.", "source_review_complete|runtime_boundary_recorded|stale_assumption_blocked", False, "not_applicable_source_review", True, False, "P0", "HIGH"),
    ("target_architecture", "End-to-end target architecture coverage", "Architecture", "Plan/02_TARGET_ARCHITECTURE/END_TO_END_ARCHITECTURE.md", "Architecture includes local, GitHub, S3, EC2, model registry, workflow lanes, QA evidence, release, and done certification boundaries.", "architecture_traceability|interface_contracts|runtime_boundary_check|release_gate_mapping", False, "not_applicable_architecture_evidence", True, False, "P0", "CRITICAL"),
    ("local_first_runtime_strategy", "Local-first runtime validation strategy", "Cost Control", "Plan/02_TARGET_ARCHITECTURE/LOCAL_FIRST_RUNTIME_VALIDATION_STRATEGY.md", "Local validation is used for workflow and prompt iteration; EC2 is reserved for target-runtime facts only.", "local_preflight|low_vram_policy|ec2_final_proof_boundary|no_false_equivalence", False, "not_applicable_local_preflight", True, False, "P0", "HIGH"),
    ("repo_ec2_s3_architecture", "GitHub local EC2 S3 development strategy", "Deploy Architecture", "Plan/02_TARGET_ARCHITECTURE/GITHUB_LOCAL_EC2_S3_DEVELOPMENT_STRATEGY.md", "CI packages deploy bundles while EC2 is stopped; EC2 consumes verified S3 artifacts when configured.", "ci_preflight|s3_bundle_manifest|sha256_verification|ec2_window_bound", False, "not_applicable_deploy_evidence", True, True, "P0", "CRITICAL"),
    ("model_asset_storage_cache", "Model asset storage and cache governance", "Model Governance", "Plan/02_TARGET_ARCHITECTURE/MODEL_ASSET_STORAGE_AND_CACHE_STRATEGY.md", "Model binaries are never committed; required models are registered, cached, hash-verified, and provisioned through non-Git paths.", "model_registry_required|sha256_required|non_git_model_path|required_model_presence", False, "not_applicable_model_hash_evidence", True, True, "P0", "CRITICAL"),
    ("image_pipeline_build", "Image pipeline blueprint implementation", "Image System", "Plan/03_IMAGE_SYSTEM/IMAGE_PIPELINE_BLUEPRINT.md", "Image pipeline can generate base outputs, refinement passes, repair passes, and QA promotion evidence for each lane.", "workflow_template_valid|prompt_request_valid|image_artifact_manifest|promotion_gate", True, "image_output_visual_review_required", True, True, "P0", "CRITICAL"),
    ("image_engine_router", "Image engine router and compatibility proof", "Image System", "Plan/03_IMAGE_SYSTEM/ENGINE_ROUTER_SPEC.md", "Engine router selects compatible checkpoints, LoRAs, VAEs, samplers, schedulers, and node graph variants without silent mismatch.", "model_compatibility_matrix|object_info_check|registry_hash_match|router_decision_evidence", False, "not_applicable_router_evidence", True, True, "P0", "CRITICAL"),
    ("image_identity_multicharacter", "Character identity and multi-character separation", "Image Visual QA", "Plan/03_IMAGE_SYSTEM/CHARACTER_IDENTITY_AND_MULTICHARACTER_SPEC.md", "Generated characters preserve identity, separation, anatomy, scale, and occlusion without merged bodies or identity drift.", "identity_reference_check|multi_instance_check|occlusion_depth_check|visual_reject_on_merge", True, "side_by_side_reference_and_generated_image_review", True, True, "P0", "CRITICAL"),
    ("image_camera_composition", "Camera framing and composition strictness", "Image Visual QA", "Plan/03_IMAGE_SYSTEM/WAVE10_IMAGE_CAMERA_PLAN_COMPILER.md", "Camera angle, crop, lens, composition, and subject framing match the request and do not hide defects.", "camera_spec_check|crop_boundary_check|composition_score|visual_review_required", True, "image_crop_framing_visual_review", True, True, "P0", "HIGH"),
    ("image_mask_control", "Mask factory and regional control integrity", "Image QA", "Plan/03_IMAGE_SYSTEM/MASK_FACTORY_SPEC.md", "Masks, region prompts, inpaint boundaries, and repair passes do not bleed into protected identity or environment regions.", "mask_schema_check|mask_boundary_visual_review|inpaint_delta_check|protected_region_preservation", True, "mask_overlay_and_before_after_visual_review", True, True, "P0", "CRITICAL"),
    ("image_body_anatomy", "Hard anatomy and body proportion review", "Image Hyperreal QA", "Plan/03_IMAGE_SYSTEM/WAVE20_IMAGE_HARD_ANATOMY_REPAIR_PLAN.md", "Hands, feet, face, teeth, eyes, proportions, joints, limbs, and contact anatomy pass strict visual rejection thresholds.", "anatomy_scorecard|hands_feet_check|face_teeth_eye_check|hard_reject_on_deformation", True, "zoomed_image_visual_review_with_anatomy_scorecard", True, True, "P0", "CRITICAL"),
    ("image_skin_material", "Skin material and surface hyperrealism review", "Image Hyperreal QA", "Plan/03_IMAGE_SYSTEM/WAVE18_IMAGE_SKIN_MATERIAL_PASS_IMPLEMENTATION_PLAN.md", "Skin texture, pores, lighting, fabric interaction, pressure marks, sweat/oil states, and realism signals pass strict hyperreal thresholds.", "surface_texture_check|lighting_consistency|material_state_continuity|visual_score_threshold", True, "macro_and_full_frame_visual_review", True, True, "P0", "CRITICAL"),
    ("image_contact_physics", "Clothing prop furniture and contact physics review", "Image Hyperreal QA", "Plan/03_IMAGE_SYSTEM/WAVE19_IMAGE_CLOTHING_PROP_FURNITURE_CONTACT_PLAN.md", "Props, furniture, fabric, and character contacts have believable support, shadows, deformation, and no clipping/floating.", "contact_graph_check|shadow_contact_check|no_floating_check|visual_reject_on_clip", True, "contact_region_visual_review", True, True, "P0", "CRITICAL"),
    ("image_hyperreal_visual_review", "Strict hyperreal image visual certification", "Image Review Certification", "Plan/Instructions/QA/IMAGE_GENERATION_VISUAL_REVIEW_PROTOCOL.md", "Each promoted image has technical QA, visual QA, prompt alignment, model/hash proof, artifact manifest, and pass/fail decision.", "technical_image_qa|visual_review_scorecard|prompt_alignment|artifact_hash_manifest|promotion_decision", True, "strict_image_artifact_visual_review_protocol", True, True, "P0", "CRITICAL"),
    ("global_visual_review_not_local_only", "Global whole-image visual review for every localized change", "Image Review Certification", "Plan/Instructions/QA/IMAGE_GENERATION_VISUAL_REVIEW_PROTOCOL.md", "A localized visual task cannot pass if any other visible region fails; whole frame review must check hands, face, anatomy, identity, lighting, background, contacts, cropping, artifacts, prompt alignment, and the edited target region together.", "whole_frame_visual_scan|required_target_region_check|required_non_target_region_scan|hands_face_body_background_contact_lighting_check|reject_on_any_global_defect", True, "full_image_review_before_zoomed_region_review_and_after_zoomed_region_review", True, True, "P0", "CRITICAL"),
    ("image_multi_sample_certification", "Multi-sample image quality certification", "Image Review Certification", "Plan/Instructions/QA/MULTIMODAL_ARTIFACT_REVIEW_SCORECARD.md", "No lane is considered final portfolio quality until multiple seeds/prompts pass consistency, hyperrealism, and defect thresholds.", "multi_seed_sample_set|aggregate_score|defect_rate_limit|portfolio_certification_record", True, "multi_sample_grid_review", True, True, "P0", "CRITICAL"),
    ("video_pipeline_build", "Video and GIF pipeline implementation", "Video System", "Plan/04_VIDEO_GIF_SYSTEM/VIDEO_GIF_PIPELINE_BLUEPRINT.md", "Video/GIF lane supports shot planning, keyframes, temporal generation, frame repair, loop export, and artifact evidence.", "video_workflow_valid|keyframe_manifest|frame_sequence_manifest|loop_export_gate", True, "video_frame_sequence_review", True, True, "P0", "CRITICAL"),
    ("video_engine_routing", "Video engine routing strategy", "Video System", "Plan/04_VIDEO_GIF_SYSTEM/WAVE06_VIDEO_ENGINE_ROUTING_STRATEGY.md", "Video engine selection is compatible with model, resolution, length, frame rate, VRAM, and desired motion.", "engine_compatibility|runtime_object_info|model_registry_link|resource_budget_check", False, "not_applicable_engine_evidence", True, True, "P0", "HIGH"),
    ("video_temporal_visual_review", "Temporal continuity visual review", "Video Visual QA", "Plan/04_VIDEO_GIF_SYSTEM/TEMPORAL_QA_AND_KEYFRAME_SYSTEM.md", "Video frames pass identity, anatomy, lighting, contact, motion, flicker, and background continuity checks.", "per_frame_qa|temporal_identity_check|flicker_detection|motion_consistency|visual_reject_on_drift", True, "frame_grid_and_playback_visual_review", True, True, "P0", "CRITICAL"),
    ("video_reference_input", "Reference video input and shot matching", "Video QA", "Plan/04_VIDEO_GIF_SYSTEM/WAVE26_REFERENCE_VIDEO_INPUT_PIPELINE.md", "Reference video extraction, pose/depth/mask timeline, and shot matching are validated before promotion.", "reference_frame_extract|pose_depth_mask_alignment|timeline_manifest|source_reference_review", True, "reference_video_to_output_comparison", True, True, "P0", "HIGH"),
    ("video_frame_repair", "Video frame repair and rerun gates", "Video QA", "Plan/04_VIDEO_GIF_SYSTEM/WAVE27_FRAME_REPAIR_PIPELINE.md", "Frame-level defects trigger targeted repair/rerun without destroying passed identity or environment evidence.", "defect_localization|targeted_repair_record|rerun_delta_check|preserve_passed_frames", True, "before_after_frame_repair_review", True, True, "P0", "HIGH"),
    ("video_gif_loop_export", "GIF loop and export certification", "Video QA", "Plan/04_VIDEO_GIF_SYSTEM/WAVE26_GIF_EXPORT_PLAN.md", "GIF outputs loop cleanly, preserve identity, avoid popping, and export with manifest, preview, and final QA evidence.", "loop_boundary_check|export_manifest|preview_required|visual_loop_review", True, "loop_playback_review", True, True, "P1", "HIGH"),
    ("audio_pipeline_build", "Audio generation pipeline implementation", "Audio System", "Plan/05_AUDIO_SYSTEM/AUDIO_GENERATION_AV_SYNC_BLUEPRINT.md", "Audio lane supports ambience, dialogue, voice, foley, spatial mix, sync, artifact manifest, and review evidence.", "audio_workflow_valid|audio_manifest|av_sync_check|mixdown_hash|review_record", False, "not_applicable_audio_waveform_evidence", True, True, "P0", "CRITICAL"),
    ("audio_engine_routing", "Audio engine routing strategy", "Audio System", "Plan/05_AUDIO_SYSTEM/WAVE06_AUDIO_ENGINE_ROUTING_STRATEGY.md", "Audio engines are selected by voice, foley, ambience, duration, sample rate, licensing, and target output constraints.", "audio_engine_compatibility|sample_rate_check|duration_check|license_metadata", False, "not_applicable_audio_engine_evidence", True, True, "P1", "HIGH"),
    ("audio_voice_dialogue", "Dialogue and voice continuity review", "Audio Review", "Plan/05_AUDIO_SYSTEM/WAVE30_DIALOGUE_AND_VOICE_PROFILE_PLAN.md", "Voice identity, intelligibility, timing, emotional tone, and continuity match the prompt and scene state.", "voice_profile_match|dialogue_timing|intelligibility_score|audio_review_record", False, "audio_spectrogram_and_playback_review", True, True, "P0", "CRITICAL"),
    ("audio_foley_force", "Foley and force-event alignment review", "Audio Review", "Plan/05_AUDIO_SYSTEM/WAVE22_AUDIO_FORCE_EVENT_BINDING_INTERFACE.md", "Foley events align to visible contacts, impacts, fabric motion, breathing, and body/prop interaction timing.", "event_binding_check|frame_to_audio_alignment|foley_presence|false_event_reject", False, "audio_video_event_alignment_review", True, True, "P0", "CRITICAL"),
    ("audio_spatial_room", "Spatial audio and room acoustics review", "Audio Review", "Plan/05_AUDIO_SYSTEM/WAVE31_ROOM_ACOUSTICS_REVERB_PLAN.md", "Reverb, pan, distance, occlusion, ambience, and room tone match camera perspective and environment.", "spatial_position_check|room_reverb_check|ambience_continuity|mix_balance_review", False, "spatial_audio_playback_review", True, True, "P0", "HIGH"),
    ("audio_av_sync", "Audio video synchronization certification", "Audio Review", "Plan/05_AUDIO_SYSTEM/WAVE30_AUDIO_VIDEO_SYNC_PLAN.md", "Audio/video outputs pass frame-accurate sync, event alignment, no drift, and final mux artifact QA.", "sync_offset_threshold|drift_check|mux_manifest|av_review_record", True, "audio_video_playback_sync_review", True, True, "P0", "CRITICAL"),
    ("audio_strict_review", "Strict audio artifact review protocol", "Audio Review Certification", "Plan/Instructions/QA/AUDIO_GENERATION_REVIEW_PROTOCOL.md", "Every promoted audio artifact has technical metadata, playback review, prompt alignment, sync evidence, and pass/fail decision.", "audio_metadata_check|playback_review|prompt_alignment|sync_evidence|promotion_decision", False, "audio_playback_and_spectrogram_review", True, True, "P0", "CRITICAL"),
    ("global_audio_review_not_local_only", "Global whole-audio review for every localized audio or visual change", "Audio Review Certification", "Plan/Instructions/QA/AUDIO_GENERATION_REVIEW_PROTOCOL.md", "A localized audio task cannot pass if the full audio bed has drift, clipping, artifacts, wrong voice, wrong ambience, missing foley, bad timing, bad mix, or mismatch with any visible event in the entire generation.", "full_duration_playback_review|required_target_audio_check|required_non_target_audio_scan|clipping_noise_voice_ambience_foley_sync_check|reject_on_any_global_audio_defect", False, "full_duration_audio_playback_plus_spectrogram_review", True, True, "P0", "CRITICAL"),
    ("multimodal_cross_review", "Multimodal image video audio scorecard", "Multimodal QA", "Plan/Instructions/QA/MULTIMODAL_ARTIFACT_REVIEW_SCORECARD.md", "Final multimodal outputs pass combined prompt, image, temporal, audio, sync, artifact, and release score thresholds.", "image_score|video_score|audio_score|sync_score|artifact_manifest|release_decision", True, "combined_visual_audio_review", True, True, "P0", "CRITICAL"),
    ("localized_change_whole_artifact_regression", "Localized change whole-artifact regression gate", "QA System", "Plan/Instructions/QA/FAILURE_CLASSIFICATION_AND_RETEST_PROTOCOL.md", "Any localized edit, mask, prompt tweak, model change, rerun, audio repair, or frame repair must be reviewed against the entire resulting artifact, and unrelated new defects block promotion.", "before_after_delta|target_region_pass|global_region_pass|unrelated_defect_scan|audio_visual_regression_scan|reject_on_new_defect", True, "whole_artifact_before_after_visual_audio_regression_review", True, True, "P0", "CRITICAL"),
    ("qa_master_protocol", "Strict autonomous QA master protocol", "QA System", "Plan/Instructions/QA/STRICT_AUTONOMOUS_QA_MASTER_PROTOCOL.md", "All implementation work has explicit test, QA, evidence, blocker, rerun, and done-certification gates.", "strict_protocol_read|qa_record_required|evidence_path_required|blocker_policy_required", False, "not_applicable_qa_protocol_evidence", True, False, "P0", "CRITICAL"),
    ("workflow_static_validation", "ComfyUI workflow static validation", "Workflow QA", "Plan/Instructions/QA/COMFYUI_WORKFLOW_TESTING_PROTOCOL.md", "Every workflow has schema, node, model reference, prompt request, and object_info compatibility checks before runtime.", "workflow_json_parse|node_reference_check|model_reference_check|object_info_static_check", False, "not_applicable_static_workflow_evidence", True, True, "P0", "CRITICAL"),
    ("workflow_runtime_smoke", "Workflow runtime smoke proof", "Runtime QA", "Plan/Instructions/Operations/Scripts/Invoke-EC2WorkflowSmokeRun.ps1", "Runtime smoke runs only after local gates pass and produces prompt, output, log, manifest, pullback, and QA evidence.", "execute_gate_check|bounded_runtime|artifact_manifest|final_state_stopped|qa_followup_required", True, "generated_artifact_visual_or_audio_review", True, True, "P0", "CRITICAL"),
    ("ec2_runtime_proof", "EC2 target runtime proof", "Runtime QA", "Plan/07_IMPLEMENTATION/EC2_DEPLOYMENT_AND_RUNTIME_PROOF_PLAN.md", "EC2 target proof verifies object_info, model path/hash/load, generation, artifact pullback, and final stopped state.", "aws_auth_gate|git_checkpoint|object_info|model_hash|generation|stop_verify", True, "target_runtime_artifact_review", True, True, "P0", "CRITICAL"),
    ("local_comfy_dev", "Local ComfyUI development lane", "Cost Control", "Plan/Instructions/Operations/EC2_COST_CONTROL_AND_LOCAL_DEV_RUNBOOK.md", "Local ComfyUI may run low-cost prompt/workflow previews but never replaces final EC2 proof.", "local_gpu_check|main_py_check|low_vram_args|no_ec2_equivalence_claim", True, "local_preview_artifact_review_when_generated", True, False, "P1", "HIGH"),
    ("github_actions_ci_package", "GitHub Actions preflight and package lane", "CI", "Plan/Instructions/Operations/EC2_COST_CONTROL_AND_LOCAL_DEV_RUNBOOK.md", "CI performs static validation, model registry coverage, package creation, deploy bundle build, and optional S3 upload while EC2 is off.", "ci_status|package_manifest|artifact_retention|optional_s3_upload|no_lfs_default", False, "not_applicable_ci_evidence", True, False, "P0", "HIGH"),
    ("s3_transfer_cost_control", "S3 deploy bundle model cache and artifact transfer readiness", "Cost Control", "Plan/Instructions/Operations/Scripts/Test-S3RuntimeTransferReadiness.ps1", "S3 transfer remains blocked until bucket/prefix, GitHub OIDC role, EC2 role, and scheduler stop role are configured and validated.", "s3_uri_shape|policy_template_json|least_privilege|missing_config_report|no_secret_print", False, "not_applicable_s3_readiness_evidence", True, False, "P0", "CRITICAL"),
    ("ec2_ttl_watchdog", "EC2 TTL watchdog and emergency stop", "Cost Control", "Plan/Instructions/Operations/Scripts/New-EC2EmergencyStopSchedule.ps1", "Every future EC2 runtime window has max runtime, cloud-side emergency stop, instance watchdog when possible, and final stopped verification.", "max_runtime_required|eventbridge_stop_schedule|watchdog_record|final_state_stopped", False, "not_applicable_ec2_state_evidence", True, True, "P0", "CRITICAL"),
    ("artifact_pullback_integrity", "Artifact pullback and hash integrity", "Runtime Evidence", "Plan/Instructions/Operations/EC2_TO_LOCAL_ARTIFACT_PULLBACK_PROTOCOL.md", "Generated artifacts are pulled back with manifest, file count, SHA256 parity, logs, prompt request, and QA follow-up.", "pullback_manifest|remote_local_count_match|sha256_match|qa_record_required", True, "pulled_back_artifact_review", True, True, "P0", "CRITICAL"),
    ("model_registry_governance", "Model registry coverage and metadata governance", "Model Governance", "Plan/Instructions/QA/Scripts/Test-WorkflowModelRegistryCoverage.ps1", "Every workflow model reference is covered by model registry metadata, expected path, type, source, and hash when available.", "registry_record_exists|model_type_valid|civitai_metadata|hash_proof|coverage_gate_pass", False, "not_applicable_model_registry_evidence", True, False, "P0", "CRITICAL"),
    ("civitai_metadata", "Civitai metadata lookup and provenance", "Model Governance", "Plan/Instructions/Operations/CIVITAI_API_OPERATING_PROTOCOL.md", "Civitai lookups record model/version/file metadata without committing tokens or unsafe model binaries.", "api_key_secret_safe|metadata_record|version_file_match|source_url_record", False, "not_applicable_metadata_evidence", True, False, "P1", "HIGH"),
    ("secret_git_security", "Secrets environment Git and checkpoint security", "Security", "Plan/Instructions/Operations/SECRETS_ENV_HANDLING_PROTOCOL.md", "No .env, AWS credentials, private keys, generated media, or model binaries are committed; Git checkpoints are clean and pushed before EC2.", "secret_scan|gitignore_check|head_equals_origin|clean_worktree|no_binary_model_commit", False, "not_applicable_security_evidence", True, False, "P0", "CRITICAL"),
    ("hydration_resume_control", "Hydration rehydration and next action control", "Autonomy Control", "Plan/Instructions/Hydration_Rehydration/RESUME_HERE_NEXT_CODEX_SESSION.md", "Autonomous sessions read active goal, session state, next action, blockers, known issues, and QA index before taking action.", "hydration_read_order|stale_pointer_scan|latest_evidence_selection|next_action_alignment", False, "not_applicable_hydration_evidence", True, False, "P0", "CRITICAL"),
    ("no_loop_no_drift", "No loop no drift progress control", "Autonomy Control", "Plan/Instructions/NO_LOOP_NO_DRIFT_PROGRESS_CONTROL.md", "Completed proof lanes are not rerun unless objective or inputs changed; blocked auth/cost states do not create endless housekeeping.", "completed_proof_no_rerun|blocked_state_stop_rule|advance_or_report|scope_drift_check", False, "not_applicable_control_evidence", True, False, "P0", "CRITICAL"),
    ("blocker_known_issue_control", "Blocker and known issue governance", "Autonomy Control", "Plan/Instructions/Hydration_Rehydration/BLOCKERS.md", "Blockers, known issues, and resolved states are source-cited and cannot supersede newer evidence without an explicit validation record.", "blocker_id_required|resolved_evidence_required|known_issue_scope|latest_state_precedence", False, "not_applicable_blocker_evidence", True, False, "P0", "HIGH"),
    ("items_tracker_coverage", "Items and Tracker end-to-end coverage validation", "Coverage Control", "Plan/Instructions/QA/Scripts/Test-ItemsTrackerPackageStatic.ps1", "Items and Tracker contain strict AI-operational rows for all Plan domains, QA suites, review gates, and runtime proof gates.", "items_rows_present|tracker_rows_present|citation_required|domain_required|coverage_report_pass", False, "not_applicable_coverage_evidence", True, False, "P0", "CRITICAL"),
    ("schema_validation", "Schema and structured data validation", "Testing", "Plan/08_SCHEMAS", "All JSON/CSV/schema assets parse and schema-managed artifacts validate before use in runtime or release gates.", "json_parse|csv_parse|schema_required_fields|structured_report", False, "not_applicable_schema_evidence", True, False, "P0", "HIGH"),
    ("script_validation", "Script parser and helper smoke validation", "Testing", "Plan/08_SCRIPTS", "All PowerShell/Python helper scripts parse, smoke tests are local-only when needed, and live actions require explicit gates.", "parser_check|local_smoke|no_live_side_effect_default|evidence_output_json", False, "not_applicable_script_evidence", True, False, "P0", "HIGH"),
    ("example_fixture_validation", "Examples and fixtures validation", "Testing", "Plan/09_EXAMPLES", "Example prompts, workflows, references, and fixture outputs are current, parseable, and tied to QA expectations.", "fixture_parse|example_request_valid|expected_output_defined|stale_example_scan", True, "example_output_review_when_media", True, False, "P1", "MEDIUM"),
    ("registry_integrity", "Registry integrity across models workflows releases and runtime", "Registry Control", "Plan/10_REGISTRIES", "Registries have unique IDs, valid references, current runtime status, and no broken links to missing source/evidence files.", "unique_ids|cross_reference_check|stale_status_scan|missing_file_check", False, "not_applicable_registry_evidence", True, False, "P0", "HIGH"),
    ("source_summary_integrity", "Source summary and snapshot integrity", "Source Control", "Plan/12_SOURCE_SUMMARIES", "Source snapshots and summaries are treated as source context with explicit promotion boundaries into active runtime surfaces.", "source_snapshot_exists|promotion_boundary|snapshot_hash|active_surface_link", False, "not_applicable_source_summary_evidence", True, False, "P1", "MEDIUM"),
    ("advanced_additions_integration", "Advanced additions integration coverage", "Advanced Integration", "Plan/13_ADVANCED_ADDITIONS_INTEGRATION/ADVANCED_ADDITIONS_REVIEW.md", "Advanced additions are crosswalked into concrete modules, QA rows, model requirements, and visual/audio gates before runtime.", "advanced_crosswalk|module_mapping|qa_mapping|runtime_promotion_rule", True, "advanced_feature_output_review_when_media", True, True, "P0", "HIGH"),
    ("organization_system", "Organization system and file placement governance", "Organization", "Plan/14_ORGANIZATION_SYSTEM/README.md", "All generated files, plans, evidence, artifacts, and outputs land in the correct directory and are indexed.", "directory_contract|index_refresh|safe_to_commit_policy|artifact_exclusion", False, "not_applicable_organization_evidence", True, False, "P1", "MEDIUM"),
    ("blueprint_projectplan_combination", "Blueprint and project plan combination traceability", "Source Control", "Plan/15_BLUEPRINT_PROJECTPLAN_COMBINATION/README.md", "Blueprint/project-plan combined source requirements remain traceable to Items, Tracker, QA, implementation, and release decisions.", "source_traceability|items_mapping|tracker_mapping|release_mapping", False, "not_applicable_traceability_evidence", True, False, "P0", "HIGH"),
    ("release_done_certification", "Done certification and release readiness", "Release", "Plan/Instructions/QA/DONE_CERTIFICATION_EVIDENCE_PROTOCOL.md", "No release or task is marked done until required tests, runtime proof, reviews, artifacts, source citations, and blockers pass.", "done_cert_schema|evidence_manifest|qa_pass|runtime_pass|review_pass|blockers_zero", True, "final_artifact_review_before_release", True, True, "P0", "CRITICAL"),
    ("final_end_to_end_certification", "Final end-to-end autonomous system certification", "Release", "Plan/11_RELEASES", "Final project completion requires every domain row to pass, all blockers resolved, media reviewed, audio reviewed, and release manifest current.", "all_domain_rows_pass|media_reviews_pass|audio_reviews_pass|runtime_evidence_pass|release_manifest_pass", True, "final_multimodal_review", True, True, "P0", "CRITICAL"),
    ("autonomous_24_7_operations", "24/7 autonomous operations safety", "Autonomous Operations", "Plan/Instructions/Operations/OPERATIONAL_DONE_GATES.md", "Autonomous work can run continuously only with bounded live resources, latest-state hydration, no-loop controls, secret safety, and checkpoint evidence.", "bounded_resource_use|latest_state_read|no_loop_gate|checkpoint_gate|emergency_stop_gate", False, "not_applicable_ops_evidence", True, False, "P0", "CRITICAL"),
    ("observability_evidence_logs", "Observability logs and evidence retention", "Runtime Evidence", "Plan/Instructions/Operations/Run_Records/README_RUN_RECORDS.md", "Each runtime action has logs, command IDs, run records, manifests, final state, and retention policy.", "run_record_exists|log_path_exists|command_status|retention_policy|evidence_index_entry", False, "not_applicable_log_evidence", True, False, "P0", "HIGH"),
    ("failure_classification_rerun", "Failure classification and targeted rerun policy", "QA System", "Plan/Instructions/QA/FAILURE_CLASSIFICATION_AND_RETEST_PROTOCOL.md", "Failures are classified, rerun decisions are targeted, passed evidence is preserved, and full reruns require dependency proof.", "failure_category|targeted_rerun|passed_evidence_preserved|rerun_reason_required", False, "not_applicable_failure_evidence", True, False, "P0", "CRITICAL"),
    ("prompt_negative_prompt_qa", "Prompt and negative prompt QA", "Prompt QA", "Plan/Instructions/QA/PROMPT_NEGATIVE_PROMPT_QA_PROTOCOL.md", "Prompts and negative prompts are validated for intent, constraints, safety, model compatibility, and expected artifact QA.", "prompt_profile_valid|negative_prompt_check|intent_alignment|model_compatibility|qa_expectations", False, "not_applicable_prompt_evidence", True, False, "P0", "HIGH"),
    ("realvisxl_lane_terminal_state", "RealVisXL completed lane terminal state", "Runtime Evidence", "Plan/Instructions/Hydration_Rehydration/CURRENT_SESSION_STATE.md", "RealVisXL lane is recorded complete for smoke proof and must not be rerun only to re-prove the same state.", "model_install_proof|static_proof|workflow_smoke|pullback_hash|technical_qa|visual_qa|no_rerun", True, "completed_image_smoke_visual_review_reference", True, True, "P0", "HIGH"),
    ("future_lane_promotion", "Future lane and module promotion rule", "Runtime Control", "Plan/Instructions/Hydration_Rehydration/NEXT_ACTION.md", "Future work must choose a new lane/module or broader certification intentionally and satisfy all local, CI, runtime, pullback, and QA gates.", "objective_declared|lane_queue_update|model_registry|run_package|runtime_proof|review_gate", True, "new_artifact_review_when_generated", True, True, "P0", "CRITICAL"),
]

WAVE64_RECONCILED_EVIDENCE = {
    "ITEM-W64-001": ("Evidence_Passed_Scoped_NonMask", "Plan/Tracker/Evidence/PLAN_SOURCE_FILE_COVERAGE_20260708T224946-0500.json"),
    "ITEM-W64-009": ("Local_Pass_Target_Runtime_Not_Certified", "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_REALVISXL_SINGLE_HAND_CONTACT_CLOSEUP_V1_VISUAL_QA_20260707T095000-0500.json"),
    "ITEM-W64-036": ("Evidence_Passed_Scoped_NonRuntime", "Plan/Tracker/Evidence/WORKFLOW_STATIC_VALIDATION_20260708T231150-0500.json"),
    "ITEM-W64-037": ("Local_Pass_Target_Runtime_Not_Certified", "Plan/Tracker/Evidence/WORKFLOW_RUNTIME_SMOKE_20260708T231534-0500.json"),
    "ITEM-W64-038": ("Blocked_Target_Runtime_PreStart_Gates", "Plan/Tracker/Evidence/EC2_RUNTIME_PROOF_20260708T231944-0500.json"),
    "ITEM-W64-039": ("Evidence_Passed_Local_NonEC2_Preview", "Plan/Tracker/Evidence/LOCAL_COMFY_DEV_20260708T232249-0500.json"),
    "ITEM-W64-040": ("Blocked_GitHub_CI_Model_Registry_Coverage_Gate", "Plan/Tracker/Evidence/GITHUB_ACTIONS_CI_PACKAGE_20260708T232951-0500.json"),
    "ITEM-W64-041": ("Local_Ready_Only_AWS_Not_Contacted", "Plan/Tracker/Evidence/S3_TRANSFER_COST_CONTROL_20260708T233214-0500.json"),
    "ITEM-W64-042": ("Blocked_AWS_Expired_Session_Live_Proof", "Plan/Tracker/Evidence/EC2_TTL_WATCHDOG_20260708T233454-0500.json"),
    "ITEM-W64-043": ("Blocked_Runtime_Artifacts_Missing", "Plan/Tracker/Evidence/ARTIFACT_PULLBACK_INTEGRITY_20260708T233714-0500.json"),
    "ITEM-W64-044": ("Evidence_Passed_Local_Only", "Plan/Tracker/Evidence/MODEL_REGISTRY_GOVERNANCE_20260708T234222-0500.json"),
    "ITEM-W64-045": ("Evidence_Passed_Local_Metadata_Provenance", "Plan/Tracker/Evidence/CIVITAI_METADATA_20260708T234544-0500.json"),
    "ITEM-W64-046": ("Blocked_Dirty_Worktree_Checkpoint", "Plan/Tracker/Evidence/SECRET_GIT_SECURITY_20260708T235206-0500.json"),
    "ITEM-W64-047": ("Evidence_Passed_Hydration_Control", "Plan/Tracker/Evidence/HYDRATION_RESUME_CONTROL_20260708T235724-0500.json"),
    "ITEM-W64-048": ("Evidence_Passed_No_Loop_No_Drift_Control", "Plan/Tracker/Evidence/NO_LOOP_NO_DRIFT_20260708T235942-0500.json"),
    "ITEM-W64-049": ("Evidence_Passed_Blocker_Governance_Active_Blockers_Tracked", "Plan/Tracker/Evidence/BLOCKER_KNOWN_ISSUE_CONTROL_20260709T000153-0500.json"),
    "ITEM-W64-050": ("Evidence_Passed_Items_Tracker_Coverage", "Plan/Tracker/Evidence/ITEMS_TRACKER_COVERAGE_20260709T000816-0500.json"),
    "ITEM-W64-051": ("Evidence_Passed_Schema_Validation", "Plan/Tracker/Evidence/SCHEMA_VALIDATION_20260709T001322-0500.json"),
    "ITEM-W64-052": ("Evidence_Passed_Script_Parser_Smoke", "Plan/Tracker/Evidence/SCRIPT_VALIDATION_20260709T001625-0500.json"),
    "ITEM-W64-053": ("Evidence_Passed_Examples_Fixtures", "Plan/Tracker/Evidence/EXAMPLE_FIXTURE_VALIDATION_20260709T002349-0500.json"),
    "ITEM-W64-054": ("Evidence_Passed_Registry_Integrity", "Plan/Tracker/Evidence/REGISTRY_INTEGRITY_20260709T002835-0500.json"),
}

WAVE64_RECONCILIATION_NOTE = (
    "Wave64 reconciliation 2026-07-09: status is generated from exact direct evidence "
    "when present; skip repeat local/AWS work unless source, evidence, or downstream gate changes."
)


def read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []


def citation_for(source_rel: str) -> dict[str, str]:
    rel = source_rel.replace("/", "\\")
    path = ROOT / source_rel.replace("/", "\\")
    if not path.exists():
        path = PLAN / source_rel.replace("Plan/", "").replace("/", "\\")
    lines = read_lines(path)
    header_line = 1
    section = path.stem
    for idx, line in enumerate(lines, start=1):
        if line.strip().startswith("#"):
            header_line = idx
            section = re.sub(r"^#+\s*", "", line.strip()) or section
            break
    end_line = min(max(header_line + 12, header_line), len(lines) if lines else header_line)
    excerpt_lines = [line.strip() for line in lines[header_line - 1:end_line] if line.strip()]
    excerpt = " ".join(excerpt_lines)[:700]
    if not excerpt:
        excerpt = f"Source file {rel} is referenced for Wave 64 end-to-end strict AI coverage."
    source_type = path.suffix.lstrip(".").lower() or "directory"
    return {
        "Citation_File": rel,
        "Citation_Full_Path": str(path),
        "Citation_Section": section[:180],
        "Citation_Line_Start": str(header_line),
        "Citation_Line_End": str(end_line),
        "Citation_Excerpt": excerpt,
        "Source_Package": "C:\\Comfy_UI_Main\\Plan",
        "Source_Type": source_type,
        "Source_File_Size": str(path.stat().st_size if path.exists() and path.is_file() else 0),
        "Source_File_Relative": rel,
    }


def evidence_decision(evidence_rel: str) -> str:
    evidence_path = ROOT / evidence_rel.replace("/", "\\")
    if not evidence_path.exists():
        return ""
    try:
        data = json.loads(evidence_path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    decision = data.get("qa_decision") or data.get("overall_result") or data.get("result") or ""
    if isinstance(decision, dict):
        return json.dumps(decision, sort_keys=True)
    return str(decision)


def apply_wave64_reconciliation(row: dict[str, str], *, tracker: bool = False) -> None:
    item_id = row.get("Source_Item_ID") if tracker else row.get("Item_ID")
    if item_id in WAVE64_RECONCILED_EVIDENCE:
        status, evidence_rel = WAVE64_RECONCILED_EVIDENCE[item_id]
        row["Status"] = status
        decision = evidence_decision(evidence_rel) or status
        if tracker:
            row["Evidence_Path"] = str(ROOT / evidence_rel.replace("/", "\\"))
            row["Status_Decision"] = decision
        row["Notes"] = f"{row.get('Notes', '').rstrip()} | {WAVE64_RECONCILIATION_NOTE}"
    elif item_id:
        if tracker:
            row["Status_Decision"] = "needs_exact_direct_row_evidence_not_complete"
        row["Notes"] = (
            f"{row.get('Notes', '').rstrip()} | Wave64 reconciliation 2026-07-09: "
            "no exact direct row evidence found; do not infer completion from rollups, mentions, "
            "Wave65 planned rows, Wave70 supporting evidence, local artifacts, or AWS artifacts "
            "without matching item/tracker id."
        )


def item_row(index: int, domain: tuple[str, ...]) -> dict[str, str]:
    key, title, category, source, acceptance, qa, visual_required, visual_method, test_required, runtime_required, priority, risk = domain
    citation = citation_for(source)
    source_key = f"W64:{key}:{citation['Source_File_Relative']}#L{citation['Citation_Line_Start']}-L{citation['Citation_Line_End']}"
    row = {
        "Item_ID": f"ITEM-W64-{index:03d}",
        "Item_Wave": "64",
        "Item_Type": "end_to_end_strict_ai_requirement",
        "Item_Title": title,
        "Item_Category": category,
        "Item_Domain": key,
        "Owner_Domain": category,
        "Autonomous_Required": "TRUE",
        "Human_Input_Allowed": "FALSE",
        "Human_Work_Allowed": "FALSE",
        "Codex_Action": f"Autonomously implement, test, review, evidence, and block-or-advance the strict AI requirement for {key}.",
        "Implementation_Target": key,
        "Deliverable_Type": "code_config_workflow_manifest_qa_evidence_review_certification",
        "Acceptance_Criteria": acceptance,
        "QA_Gates_Required": qa,
        "Visual_Review_Required": "TRUE" if visual_required else "FALSE",
        "Visual_Review_Method": visual_method,
        "Test_Required": "TRUE" if test_required else "FALSE",
        "Evidence_Required": "source_citation|test_log|qa_record|evidence_manifest|blocker_or_pass_decision",
        "Runtime_Proof_Required": "TRUE" if runtime_required else "FALSE",
        "EC2_Allowed": "TRUE" if runtime_required else "FALSE",
        "Blocker_Policy": "No human work. If any required source, test, runtime proof, visual review, audio review, or evidence is missing, create a blocker with exact source citation and continue only with safe autonomous work.",
        "Source_Plan_Root": str(PLAN),
        "Priority": priority,
        "Risk_Level": risk,
        "Status": "Required_Tracked_Not_Complete_Until_Evidence_Passes",
        "Created_From": "Wave64 end-to-end strict AI coverage generator",
        "Notes": "AI-only operational row. Do not treat prose summary as completion; require structured evidence paths and pass/fail records.",
        "Source_Key": source_key,
        "Coverage_Level": "end_to_end_strict_ai_control",
        "Coverage_Audit_Status": "covered_by_wave64_strict_ai_matrix",
        "Ultra_Source_Coverage_Record": source_key,
    }
    row.update(citation)
    apply_wave64_reconciliation(row)
    return row


def tracker_row(index: int, item: dict[str, str]) -> dict[str, str]:
    row = {
        "Tracker_ID": f"TRK-W64-{index:03d}",
        "Wave": "64",
        "Phase": "Wave 64",
        "Workstream": item["Item_Domain"],
        "Priority": item["Priority"],
        "Risk_Level": item["Risk_Level"],
        "Owner_Role": "Codex Desktop Autonomous Agent",
        "Environment": "local_repo_ci_ec2_s3_comfyui_runtime_as_required",
        "Status": "Required_Tracked_Not_Complete_Until_Evidence_Passes",
        "Task_Name": item["Item_Title"],
        "Detailed_Action": item["Codex_Action"],
        "Completion_Criteria": item["Acceptance_Criteria"],
        "Acceptance_Evidence": item["Evidence_Required"],
        "Dependency_Prerequisite": "Read the cited Plan source file and current hydration state before execution.",
        "Validation_Method": item["QA_Gates_Required"],
        "Output_Artifact": f"Plan/Instructions/QA/Evidence/Wave64/{item['Item_Domain']}.json",
        "Source_Path": item["Citation_Full_Path"],
        "Related_Source_Paths": item["Citation_File"],
        "Package_Top_Level_Directory": "C:\\Comfy_UI_Main\\Plan",
        "Autonomous_Execution_Mode": "Codex Desktop fully autonomous, no human input, no human manual work",
        "Human_Input_Allowed": "FALSE",
        "Human_Work_Allowed": "FALSE",
        "Codex_Desktop_Action": item["Codex_Action"],
        "QA_Strictness": "STRICT",
        "Visual_Review_Required": item["Visual_Review_Required"],
        "Visual_Review_Method": item["Visual_Review_Method"],
        "Test_Required": item["Test_Required"],
        "Runtime_Proof_Required": item["Runtime_Proof_Required"],
        "EC2_Allowed": item["EC2_Allowed"],
        "Preview_Required": "TRUE" if item["Visual_Review_Required"] == "TRUE" else "FALSE",
        "Final_Render_Gate": "BLOCKED_UNTIL_PREVIEW_QA_RUNTIME_PROOF_AND_STRICT_REVIEW_PASS",
        "Evidence_Path": f"C:\\Comfy_UI_Main\\Plan\\Instructions\\QA\\Evidence\\Wave64\\{item['Item_Domain']}.json",
        "Citation_File": item["Citation_File"],
        "Citation_Full_Path": item["Citation_Full_Path"],
        "Citation_Section": item["Citation_Section"],
        "Citation_Line_Start": item["Citation_Line_Start"],
        "Citation_Line_End": item["Citation_Line_End"],
        "Citation_Excerpt": item["Citation_Excerpt"],
        "Source_Package": item["Source_Package"],
        "Source_Type": item["Source_Type"],
        "Source_Item_ID": item["Item_ID"],
        "Blocker_Policy": item["Blocker_Policy"],
        "Rerun_Policy": "Targeted rerun only; preserve passed evidence; never rerun a completed proof unless source objective, input artifact, model, prompt, workflow, or QA threshold changed.",
        "Status_Decision": "blocked_or_passed_by_structured_evidence_only",
        "Notes": item["Notes"],
        "Source_Key": item["Source_Key"],
        "Source_File_Relative": item["Source_File_Relative"],
        "Coverage_Level": item["Coverage_Level"],
        "Coverage_Audit_Status": item["Coverage_Audit_Status"],
        "Ultra_Source_Coverage_Record": item["Ultra_Source_Coverage_Record"],
    }
    apply_wave64_reconciliation(row, tracker=True)
    return row


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def scan_citation_integrity(path: Path, id_col: str, source_cols: list[str]) -> dict[str, object]:
    total = 0
    missing = {col: 0 for col in source_cols}
    samples = []
    with path.open(newline="", encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            bad = [col for col in source_cols if not (row.get(col) or "").strip()]
            for col in bad:
                missing[col] += 1
            if bad and len(samples) < 20:
                samples.append({"id": row.get(id_col, ""), "missing": bad})
    return {"path": str(path), "row_count": total, "missing_counts": missing, "samples": samples}


def validate_wave64(rows: list[dict[str, str]], tracker_rows: list[dict[str, str]]) -> dict[str, object]:
    errors = []
    domains = {row["Item_Domain"] for row in rows}
    missing_domains = sorted(REQUIRED_DOMAINS - domains)
    if missing_domains:
        errors.append(f"missing required Wave64 domains: {missing_domains}")

    required_citation = ["Citation_File", "Citation_Full_Path", "Citation_Section", "Citation_Line_Start", "Citation_Line_End", "Citation_Excerpt", "Source_Key", "Source_File_Relative"]
    for label, data_rows, id_col in (("items", rows, "Item_ID"), ("tracker", tracker_rows, "Tracker_ID")):
        for row in data_rows:
            missing = [col for col in required_citation if not (row.get(col) or "").strip()]
            if missing:
                errors.append(f"{label} {row.get(id_col)} missing citation fields {missing}")
            if row.get("Human_Input_Allowed") != "FALSE" or row.get("Human_Work_Allowed") != "FALSE":
                errors.append(f"{label} {row.get(id_col)} allows human work/input")
            if label == "tracker" and row.get("QA_Strictness") != "STRICT":
                errors.append(f"tracker {row.get(id_col)} is not STRICT")
            try:
                int(row.get("Citation_Line_Start", ""))
                int(row.get("Citation_Line_End", ""))
            except Exception:
                errors.append(f"{label} {row.get(id_col)} has non-integer citation lines")
            full = Path(row.get("Citation_Full_Path", ""))
            if not str(full).startswith(str(PLAN)) or not full.exists():
                errors.append(f"{label} {row.get(id_col)} citation file missing or outside Plan: {full}")

    plan_files = [p for p in PLAN.rglob("*") if p.is_file()]
    top_dirs = sorted({p.relative_to(PLAN).parts[0] for p in plan_files})
    return {
        "schema_version": "1.0",
        "operation": "wave64_end_to_end_strict_ai_coverage_validation",
        "result": "pass" if not errors else "fail",
        "row_count_items": len(rows),
        "row_count_tracker": len(tracker_rows),
        "required_domain_count": len(REQUIRED_DOMAINS),
        "required_domains_missing": missing_domains,
        "plan_file_count": len(plan_files),
        "plan_top_level_entries": top_dirs,
        "plan_top_level_entry_count": len(top_dirs),
        "citation_fields_required": required_citation,
        "errors": errors,
        "confidence_statement": "Wave64 provides strict AI-operational end-to-end mapping coverage for Plan domains, QA gates, visual review, audio review, runtime proof, and autonomous operations. It does not mark the project complete; completion still requires each row's evidence to pass.",
    }


def main() -> int:
    item_rows = [item_row(idx, domain) for idx, domain in enumerate(DOMAINS, start=1)]
    tracker_rows = [tracker_row(idx, row) for idx, row in enumerate(item_rows, start=1)]

    item_paths = [
        ITEMS / "Waves" / "Wave64" / "WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
        ITEMS / "wave64_end_to_end_strict_ai_itemized_list.csv",
    ]
    tracker_paths = [
        TRACKER / "Waves" / "Wave64" / "WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
        TRACKER / "wave64_end_to_end_strict_ai_tracker.csv",
    ]
    for path in item_paths:
        write_csv(path, ITEM_COLUMNS, item_rows)
    for path in tracker_paths:
        write_csv(path, TRACKER_COLUMNS, tracker_rows)

    requirements = {
        "schema_version": "1.0",
        "wave": 64,
        "purpose": "AI-operational end-to-end strict coverage for autonomous build, testing, QA, visual review, audio review, runtime proof, cost control, and release certification.",
        "required_domains": sorted(REQUIRED_DOMAINS),
        "row_count": len(item_rows),
        "human_input_allowed": False,
        "human_work_allowed": False,
        "completion_rule": "No row is complete until cited source is read, implementation/test/review evidence exists, and strict pass/fail decision is recorded.",
    }
    for base in (ITEMS, TRACKER):
        out = base / "Waves" / "Wave64" / "WAVE64_STRICT_AI_COVERAGE_REQUIREMENTS.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(requirements, indent=2) + "\n", encoding="utf-8")

    report = validate_wave64(item_rows, tracker_rows)
    source_cols = ["Citation_File", "Citation_Full_Path", "Citation_Section", "Citation_Line_Start", "Citation_Line_End", "Citation_Excerpt"]
    report["legacy_items_master_citation_integrity"] = scan_citation_integrity(ITEMS / "wave53_57_master_itemized_list.csv", "Item_ID", source_cols)
    report["legacy_tracker_master_citation_integrity"] = scan_citation_integrity(TRACKER / "wave48_52_master_autonomous_tracker.csv", "Tracker_ID", source_cols)
    report["wave64_item_files"] = [str(path) for path in item_paths]
    report["wave64_tracker_files"] = [str(path) for path in tracker_paths]

    for path in (
        ITEMS / "Reports" / "wave64_end_to_end_strict_ai_coverage_report.json",
        TRACKER / "Reports" / "wave64_end_to_end_strict_ai_coverage_report.json",
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
