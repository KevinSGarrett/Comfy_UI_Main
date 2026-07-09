# Selected S3 Publish Readiness Plan

- created_at: 2026-07-09T12:46:23-05:00
- result: pass_local_only_selected_s3_publish_readiness_dry_run_ready_execute_blocked
- selected_lane_id: sdxl_realvisxl_inpaint_detail_lane
- selected_rebuild_ready_after_clean_checkpoint: True
- expected_manifest_exists_now: True
- expected_zip_exists_now: True
- selected_deploy_bundle_s3_publish_dry_run_result: dry_run_ready_to_upload
- s3_runtime_transfer_readiness_result: ready_local_only
- s3_base_uri_present: True
- ready_for_s3_publish_after_rebuild: True
- ready_for_s3_publish_now_local_dry_run: True

## Publish Dry Run Command

`powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Publish-DeployBundleToS3.ps1 -BundleManifestFile C:\Comfy_UI_Main\runtime_artifacts\deploy_bundles\si_sc_20260709T123317\DEPLOY_BUNDLE_MANIFEST.json -S3BaseUri s3://comfy-ui-main-runtime-029530099913-us-east-1/deploy-bundles -Region us-east-1 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_SELECTED_DEPLOY_BUNDLE_S3_PUBLISH_DRY_RUN_<timestamp>.json
`

## Boundary

Selected S3 publish readiness plan only. This artifact does not stage, commit, push, reset, checkout, rebuild deploy bundles, upload to S3, contact AWS, start EC2, post prompts, generate, write runtime markers, promote masks, rerun Wave70 gates, switch to Jira bookkeeping, or activate Wave71+.

## Next Action

Deploy-bundle S3 publish is locally dry-run ready. Actual S3 upload, EC2 install, and runtime proof remain blocked until explicit live execution intent and live gates.
