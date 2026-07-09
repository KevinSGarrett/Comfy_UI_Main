# Dirty Git Checkpoint Review Resolution

- created_at: 2026-07-09T08:14:13-05:00
- result: checkpoint_review_resolved_workflow_gap_remaining
- ready_for_guarded_checkpoint_dry_run: False
- checkpoint_workflow_gap_present: True
- include_candidate_path_count: 1266
- preserve_local_do_not_stage_path_count: 37
- do_not_stage_path_count: 2
- checkpoint_workflow_gap_path_count: 30

## Resolutions

- project_plan_ledger_candidate: 1236, resolution=include_candidate, action=include_in_intended_checkpoint
- runtime_artifacts_review: 31, resolution=exclude_from_checkpoint_for_now, action=preserve_local_do_not_stage
- runtime_orchestration_candidate: 30, resolution=include_candidate_with_checkpoint_workflow_gap, action=include_after_guarded_checkpoint_supports_non_plan_paths
- reference_or_mask_asset_review: 5, resolution=local_dependency_do_not_checkpoint_by_default, action=preserve_local_do_not_stage
- archive_or_temp_defer: 2, resolution=exclude_or_cleanup_candidate, action=do_not_stage
- jira_control_plane_review: 1, resolution=exclude_from_active_build_checkpoint, action=preserve_local_do_not_stage

## Boundary

Review resolution only. This artifact does not stage, commit, push, reset, checkout, rebuild deploy bundles, upload to S3, start EC2, post prompts, generate, write runtime markers, promote masks, rerun Wave70 gates, switch to Jira bookkeeping, or activate Wave71+.

## Next Action

Patch or replace the guarded checkpoint workflow so an explicit include/exclude manifest can cover Plan plus runtime-orchestration roots without staging preserved local assets; then rerun review resolution before checkpoint dry-run.
