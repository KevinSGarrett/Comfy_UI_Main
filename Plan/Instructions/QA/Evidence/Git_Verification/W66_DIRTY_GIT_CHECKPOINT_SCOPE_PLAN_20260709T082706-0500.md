# Dirty Git Checkpoint Scope Plan

- created_at: 2026-07-09T08:27:09-05:00
- result: checkpoint_scope_runtime_ready
- inventory_matches_current: True
- porcelain_count: 1316
- include_candidate_count: 1277
- review_before_checkpoint_count: 37
- defer_or_exclude_candidate_count: 2
- scope_ready_for_checkpoint: False

## Categories

- project_plan_ledger_candidate: 1247, disposition=include_candidate
- runtime_artifacts_review: 31, disposition=review_before_checkpoint
- runtime_orchestration_candidate: 30, disposition=include_candidate
- reference_or_mask_asset_review: 5, disposition=review_before_checkpoint
- archive_or_temp_defer: 2, disposition=defer_or_exclude_candidate
- jira_control_plane_review: 1, disposition=review_before_checkpoint

## Boundary

Scope plan only. This artifact does not stage, commit, push, reset, checkout, rebuild deploy bundles, upload to S3, start EC2, post prompts, generate, write runtime markers, promote masks, rerun Wave70 gates, switch to Jira bookkeeping, or activate Wave71+.

## Next Action

Review review_before_checkpoint and defer_or_exclude_candidate groups, decide the checkpoint scope, then run the guarded checkpoint workflow only when ready.
