# ControlNet Asset Transfer Dry-Run Bundle

- created_at: 2026-07-10T12:32:16-05:00
- result: pass_local_only_controlnet_asset_transfer_dry_run_bundle_validated
- lane_id: sdxl_realvisxl_controlnet_lineart_lane
- control_map_type: lineart
- child_artifact_count: 6
- failed_check_count: 0
- target_runtime_proof: false
- certification_claimed: false
- execute_allowed_now: false

## Child Artifacts

- checkpoint_s3_publish_dry_run: dry_run_ready_to_upload_model (Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_CONTROLNET_LINEART_CHECKPOINT_S3_PUBLISH_DRY_RUN_20260710T123201-0500.json)
- controlnet_s3_publish_dry_run: dry_run_ready_to_upload_model (Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_CONTROLNET_LINEART_MODEL_S3_PUBLISH_DRY_RUN_20260710T123201-0500.json)
- input_s3_publish_dry_run: dry_run_ready_to_upload_input_asset (Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_CONTROLNET_LINEART_INPUT_S3_PUBLISH_DRY_RUN_20260710T123201-0500.json)
- checkpoint_ec2_install_dry_run: dry_run_model_install_plan (Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_CONTROLNET_LINEART_CHECKPOINT_EC2_INSTALL_DRY_RUN_20260710T123201-0500.json)
- controlnet_ec2_install_dry_run: dry_run_model_install_plan (Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_CONTROLNET_LINEART_MODEL_EC2_INSTALL_DRY_RUN_20260710T123201-0500.json)
- input_ec2_install_dry_run: dry_run_input_asset_install_plan (Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_CONTROLNET_LINEART_INPUT_EC2_INSTALL_DRY_RUN_20260710T123201-0500.json)

## Checks

- supported_controlnet_lane: pass
- requirements_lane_matches: pass
- required_asset_contracts: pass
- control_map_type_matches_lane: pass
- local_asset_files_present: pass
- checkpoint_hash_matches: pass
- controlnet_hash_matches: pass
- control_image_hash_matches: pass
- source_artifact_hash_matches: pass
- s3_base_uris_valid: pass
- checkpoint_publish_dry_run: pass
- controlnet_publish_dry_run: pass
- input_publish_dry_run: pass
- checkpoint_install_dry_run: pass
- controlnet_install_dry_run: pass
- input_install_dry_run: pass

## Boundary

Local ControlNet asset-transfer dry-run bundle only. This does not upload assets, start EC2, install remotely, contact ComfyUI, execute generation, prove target runtime, promote the lane, complete Items/Tracker rows, or claim certification.

## Next Action

Keep EC2 stopped. Use these pinned URIs and hashes only after explicit live intent, current AWS auth, clean Git/deploy gates, and bounded target-runtime authorization.
