# Selected S3 Publish Readiness Plan

- created_at: 2026-07-09T14:40:26-05:00
- result: blocked_selected_s3_publish_readiness_waiting_for_clean_rebuild
- selected_lane_id: sdxl_realvisxl_inpaint_detail_lane
- selected_rebuild_ready_after_clean_checkpoint: True
- expected_manifest_exists_now: False
- expected_zip_exists_now: False
- selected_deploy_bundle_s3_publish_dry_run_result: missing
- s3_runtime_transfer_readiness_result: ready_local_only
- s3_base_uri_present: True
- ready_for_s3_publish_after_rebuild: False
- ready_for_s3_publish_now_local_dry_run: False

## Publish Dry Run Command

`powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Publish-DeployBundleToS3.ps1 -BundleManifestFile C:\Comfy_UI_Main\runtime_artifacts/deploy_bundles/deploy_bundle_sdxl_realvisxl_inpaint_detail_lane_<timestamp>/DEPLOY_BUNDLE_MANIFEST.json -S3BaseUri s3://comfy-ui-main-runtime-029530099913-us-east-1/deploy-bundles -Region us-east-1 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_SELECTED_DEPLOY_BUNDLE_S3_PUBLISH_DRY_RUN_<timestamp>.json
`

## Boundary

Selected S3 publish readiness plan only. This artifact does not stage, commit, push, reset, checkout, rebuild deploy bundles, upload to S3, contact AWS, start EC2, post prompts, generate, write runtime markers, promote masks, rerun Wave70 gates, switch to Jira bookkeeping, or activate Wave71+.

## Next Action

After explicit manifest-scoped checkpoint and selected deploy-bundle rebuild, rerun S3 runtime transfer readiness and then run Publish-DeployBundleToS3.ps1 dry-run against the concrete rebuilt manifest before any upload execute or EC2 proof.
