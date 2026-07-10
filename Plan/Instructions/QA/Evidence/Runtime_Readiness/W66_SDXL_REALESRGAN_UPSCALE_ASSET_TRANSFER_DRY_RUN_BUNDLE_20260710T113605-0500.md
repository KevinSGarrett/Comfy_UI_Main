# RealESRGAN Asset Transfer Dry-Run Bundle

- created_at: 2026-07-10T11:36:07-05:00
- result: pass_local_only_realesrgan_asset_transfer_dry_run_bundle_validated
- lane_id: sdxl_realesrgan_upscale_polish_lane
- target_runtime_proof: false
- certification_claimed: false
- execute_allowed_now: false
- failed_check_count: 0

## Child Artifacts

- model_s3_publish_dry_run: dry_run_ready_to_upload_model (Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_REALESRGAN_MODEL_S3_PUBLISH_DRY_RUN_20260710T113605-0500.json)
- input_s3_publish_dry_run: dry_run_ready_to_upload_input_asset (Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_REALESRGAN_INPUT_S3_PUBLISH_DRY_RUN_20260710T113605-0500.json)
- model_ec2_install_dry_run: dry_run_model_install_plan (Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_REALESRGAN_MODEL_EC2_INSTALL_DRY_RUN_20260710T113605-0500.json)
- input_ec2_install_dry_run: dry_run_input_asset_install_plan (Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_REALESRGAN_INPUT_EC2_INSTALL_DRY_RUN_20260710T113605-0500.json)

## Checks

- lane_is_realesrgan_upscale: pass
- model_filename_matches_requirements: pass
- input_filename_matches_requirements: pass
- model_hash_matches_requirements: pass
- input_hash_matches_requirements: pass
- provisioning_evidence_matches_model_hash: pass
- model_s3_uri_valid: pass
- input_s3_uri_valid: pass
- model_publish_dry_run_pass: pass
- input_publish_dry_run_pass: pass
- model_install_dry_run_pass: pass
- input_install_dry_run_pass: pass

## Boundary

Local RealESRGAN asset-transfer dry-run bundle only. This does not upload assets, start EC2, install remotely, contact ComfyUI, execute generation, prove target runtime, promote the lane, or claim certification.

## Next Action

Keep EC2 stopped. Use these pinned model/input URIs and hashes only after explicit live intent, current AWS auth, clean Git/deploy gates, and bounded target-runtime authorization.
