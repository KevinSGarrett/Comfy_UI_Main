# Scoped Git Checkpoint Manifest

- created_at: 2026-07-09T12:31:36-05:00
- result: scoped_git_checkpoint_manifest_ready_pending_explicit_intent
- ready_for_checkpoint_execute_after_explicit_intent: True
- checkpoint_intent_required: True
- dry_run_result: blocked_git_checkpoint_dirty_worktree
- dry_run_scope_changed_path_count: 144
- dry_run_scope_excluded_changed_path_count: 40

## Include Paths

- Plan
- .github
- PromptProfiles
- Workflows
- config
- PROJECT_ROOT_MANIFEST.json
- tools

## Exclude Paths

- runtime_artifacts
- Ref_Image_1
- Ref_Image_2
- Ref_Image_Canonical_Body
- Reference_Images
- masks
- Jira
- Plan.zip
- _ci_w64_20260708T232900-0500

## Boundary

Manifest evidence only. This artifact does not stage, commit, push, reset, checkout, rebuild deploy bundles, upload to S3, start EC2, post prompts, generate, write runtime markers, promote masks, rerun Wave70 gates, switch to Jira bookkeeping, or activate Wave71+.

## Next Action

Use this manifest for one guarded checkpoint dry-run or execute path only after explicit checkpoint intent; then revalidate clean Git, deploy bundle, and runtime gates.
