# Selected Target Runtime Pre-EC2 Handoff Bundle

- created_at: 2026-07-09T07:11:35-05:00
- result: pass_local_only_selected_target_runtime_pre_ec2_handoff_bundle_ready_ec2_blocked
- lane_id: sdxl_realvisxl_inpaint_detail_lane
- selected_work_order_id: WO-W66-SDXL_REALVISXL_INPAINT_DETAIL_LANE-TARGET-RUNTIME-PROOF
- target_runtime_launch_allowed: false
- execute_allowed_now: false
- allowed_local_recheck_step_count: 6
- blocked_live_step_count: 7
- exact_blockers: git_checkpoint_gate_not_clean_for_ec2_execute, explicit_user_target_runtime_selection_required, deploy_bundle_source_git_dirty_rebuild_required_before_ec2, runtime_handoff_git_gate_not_passing, target_runtime_or_final_certification_not_proven, target_runtime_proof_evidence_missing, queue_status_not_final_certified:local_runtime_smoke_visual_qa_pass_with_notes_plus_wave25_contact_refine_robustness_pass_with_notes_pending_target_runtime, required_next_runtime_gate_still_requires_target_or_final_review

## Allowed Local Rechecks

- 2. closure_rollup_recheck
- 3. git_checkpoint_recheck
- 4. runtime_unblock_handoff_recheck
- 5. active_runtime_queue_local_support_recheck
- 6. runtime_lane_queue_recheck
- 7. model_registry_coverage_recheck

## Blocked Live Steps

- 1. explicit_target_runtime_selection
- 8. lane_runtime_readiness_recheck
- 9. deploy_bundle_build
- 10. deploy_bundle_s3_publish
- 11. active_runtime_marker_plan_or_write
- 12. ec2_static_proof_execute
- 13. workflow_smoke_execute

## Checks

- target_plan_is_latest_authority_for_selected_inpaint_lane: pass
- selected_package_ready_but_execution_blocked: pass
- launch_gate_blocks_target_runtime_launch: pass
- package_deploy_matrix_has_selected_lane_dirty_bundle: pass
- handoff_command_partition_is_fail_closed: pass
- required_blockers_are_preserved: pass

## Boundary

Local pre-EC2 handoff bundle only. Allowed local rechecks are listed, but live upload, S3 publish with Execute, marker write, EC2 start, prompt post, generation, final certification, mask promotion, Wave70 hard-gate rerun, Jira bookkeeping, and Wave71+ activation remain blocked.

## Evidence

- Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_ACTIVE_RUNTIME_QUEUE_TARGET_RUNTIME_EXECUTION_PLAN_20260709T065516-0500.json
- Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_SELECTED_TARGET_RUNTIME_LANE_PACKAGE_READINESS_20260709T051227-0500.json
- Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_SELECTED_TARGET_RUNTIME_LAUNCH_GATE_20260709T052434-0500.json
- Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_ACTIVE_RUNTIME_QUEUE_PACKAGE_DEPLOY_MATRIX_20260709T053152-0500.json
- runtime_artifacts/g9_20260709T030509/r/sdxl_realvisxl_inpaint_detail_lane_ci_preflight/RUN_PACKAGE_MANIFEST.json
- runtime_artifacts/g9_20260709T030509/d/sdxl_realvisxl_inpaint_detail_lane_ci_preflight/DEPLOY_BUNDLE_MANIFEST.json
