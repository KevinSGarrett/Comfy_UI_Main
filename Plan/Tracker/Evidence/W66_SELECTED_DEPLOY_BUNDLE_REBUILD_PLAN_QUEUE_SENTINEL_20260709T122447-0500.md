# Selected Deploy Bundle Rebuild Plan

- created_at: 2026-07-09T12:24:48-05:00
- result: selected_deploy_bundle_rebuild_plan_ready_after_clean_checkpoint
- selected_lane_id: sdxl_realvisxl_inpaint_detail_lane
- run_package_pass_local_only: True
- existing_deploy_bundle_source_git_clean: False
- current_git_clean: False
- ready_to_rebuild_after_clean_checkpoint: True

## Rebuild Command

`powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-EC2DeployBundle.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId sdxl_realvisxl_inpaint_detail_lane -RunPackageManifestFile C:\Comfy_UI_Main\runtime_artifacts/g9_20260709T030509/r/sdxl_realvisxl_inpaint_detail_lane_ci_preflight/RUN_PACKAGE_MANIFEST.json -BundleName deploy_bundle_sdxl_realvisxl_inpaint_detail_lane_<timestamp> -OutDir C:\Comfy_UI_Main\runtime_artifacts/deploy_bundles/deploy_bundle_sdxl_realvisxl_inpaint_detail_lane_<timestamp>
`

## Boundary

Selected deploy-bundle rebuild plan only. This artifact does not stage, commit, push, reset, checkout, rebuild deploy bundles, upload to S3, start EC2, post prompts, generate, write runtime markers, promote masks, rerun Wave70 gates, switch to Jira bookkeeping, or activate Wave71+.

## Next Action

After explicit manifest-scoped checkpoint and clean Git proof, run the rebuild command, then rerun package/deploy matrix and S3/runtime gates before any EC2 proof.
