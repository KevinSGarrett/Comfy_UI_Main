# Selected Input Asset Install Readiness Plan

- created_at: 2026-07-09T20:15:42-05:00
- result: blocked_selected_input_asset_install_readiness_waiting_for_s3_publish_and_live_gates
- selected_lane_id: sdxl_realvisxl_inpaint_detail_lane
- required_input_asset_count: 2
- input_asset_local_hash_all_pass: True
- s3_runtime_transfer_readiness_result: ready_local_only
- input_asset_s3_base_uri_present: True
- ready_for_input_asset_publish: True
- ready_for_ec2_input_asset_install_execute: False
- exact_blockers: explicit_user_target_runtime_selection_required, input_assets_not_yet_published_to_s3_for_selected_lane, ec2_input_asset_install_execute_requires_explicit_intent

## Assets

- source_image: sdxl_inpaint_detail_source_canny_v1.png, local_hash_match=True, source_s3_uri=s3://comfy-ui-main-runtime-029530099913-us-east-1/model-cache/input-assets/sdxl_inpaint_detail_source_canny_v1.png
- mask_image: sdxl_inpaint_detail_micro_nomouth_v4.png, local_hash_match=True, source_s3_uri=s3://comfy-ui-main-runtime-029530099913-us-east-1/model-cache/input-assets/sdxl_inpaint_detail_micro_nomouth_v4.png

## Boundary

Selected input-asset install readiness plan only. This artifact does not upload assets, contact AWS/S3, start EC2, post prompts, run generation, stage, commit, push, reset, checkout, rebuild deploy bundles, consume or promote masks, rerun Wave70 gates, switch to Jira bookkeeping, or activate Wave71+.

## Next Action

When live gates are later selected and clean, run publish dry-runs for the listed source/mask assets, publish them to the recorded S3 URIs after explicit intent, run dry-run install plans, then run Install-EC2InputAssetFromS3.ps1 -Execute for each asset before bounded workflow smoke.
