# Selected Target Runtime Lane Package Readiness

- created_at: 2026-07-09T05:04:04-05:00
- result: blocked_selected_target_runtime_lane_package_readiness_object_info_refresh_required
- lane_id: sdxl_realvisxl_inpaint_detail_lane
- selected_work_order_id: WO-W66-SDXL_REALVISXL_INPAINT_DETAIL_LANE-TARGET-RUNTIME-PROOF
- package_readiness_pass: False
- target_runtime_execution_allowed: false
- full_project_certification_allowed: false
- deploy_bundle_zip_sha256: 583065c17d44ff5ec9d4a1e52c41ede8930dd63e5dc6adbc623af7d504bba70f

## Checks

- target_plan_selects_lane_and_blocks_execution: pass
- run_package_passes_local_only: pass
- run_package_hashes_and_dry_run_pass: pass
- deploy_bundle_passes_local_only_and_zip_hashes: pass
- deploy_bundle_records_dirty_git_as_blocker: pass
- runtime_requirements_match_local_object_info: fail
- model_hash_matches_runtime_requirement: pass
- source_and_mask_assets_match_manifests: pass

## Boundary

Local selected-lane package readiness only. This does not authorize or perform live upload, marker write, EC2 start, generation, target-runtime proof, final certification, mask promotion, Wave70 hard-gate rerun, Jira bookkeeping, or Wave71+ activation.

## Evidence

- Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_ACTIVE_RUNTIME_QUEUE_TARGET_RUNTIME_EXECUTION_PLAN_20260709T045509-0500.json
- runtime_artifacts/g9_20260709T030509/r/sdxl_realvisxl_inpaint_detail_lane_ci_preflight/RUN_PACKAGE_MANIFEST.json
- runtime_artifacts/g9_20260709T030509/d/sdxl_realvisxl_inpaint_detail_lane_ci_preflight/DEPLOY_BUNDLE_MANIFEST.json
- Plan/Instructions/QA/Evidence/Runtime_Readiness/W69_LOCAL_OBJECT_INFO_INPAINT_DETAIL_NOMOUTH_V4_20260707T045500-0500.json
- Plan/Instructions/Operations/Prepared_Input_Assets/sdxl_inpaint_detail_micro_nomouth_v4_20260707T034500-0500/INPAINT_MICRO_NOMOUTH_INPUT_ASSET_MANIFEST.json
