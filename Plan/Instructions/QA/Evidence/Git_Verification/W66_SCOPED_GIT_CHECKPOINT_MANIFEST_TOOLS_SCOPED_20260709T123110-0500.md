# Scoped Git Checkpoint Manifest

- created_at: 2026-07-09T12:31:10-05:00
- result: blocked_scoped_checkpoint_manifest_required_roots_missing
- ready_for_checkpoint_execute_after_explicit_intent: False
- checkpoint_intent_required: True
- dry_run_result: blocked_git_checkpoint_invalid_scope_manifest
- dry_run_scope_changed_path_count: 138
- dry_run_scope_excluded_changed_path_count: 41

## Include Paths

- Plan

## Exclude Paths

- runtime_artifacts

## Boundary

Manifest evidence only. This artifact does not stage, commit, push, reset, checkout, rebuild deploy bundles, upload to S3, start EC2, post prompts, generate, write runtime markers, promote masks, rerun Wave70 gates, switch to Jira bookkeeping, or activate Wave71+.

## Next Action

Resolve the manifest blocker before any checkpoint execute path.
