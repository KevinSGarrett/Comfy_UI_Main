# Selected Model Cache Readiness Plan

- created_at: 2026-07-09T13:44:55-05:00
- result: blocked_selected_model_cache_readiness_waiting_for_s3_publish_and_live_gates
- selected_lane_id: sdxl_realvisxl_inpaint_detail_lane
- required_model_count: 1
- model_local_hash_all_pass_from_object_info: True
- s3_runtime_transfer_readiness_result: ready_local_only
- model_cache_s3_base_uri_present: True
- ready_for_model_cache_publish: True
- ready_for_ec2_model_install_execute: False
- exact_blockers: explicit_user_target_runtime_selection_required, git_checkpoint_gate_not_clean_for_ec2_execute, model_not_yet_published_to_s3_for_selected_lane, ec2_model_install_execute_requires_explicit_intent

## Models

- checkpoint: realvisxlV50_v50Bakedvae.safetensors, local_hash_match_from_object_info=True, source_s3_uri=s3://comfy-ui-main-runtime-029530099913-us-east-1/model-cache/realvisxlV50_v50Bakedvae.safetensors

## Boundary

Selected model-cache readiness plan only. This artifact does not upload models, contact AWS/S3, start EC2, post prompts, run generation, stage, commit, push, reset, checkout, rebuild deploy bundles, consume or promote masks, rerun Wave70 gates, switch to Jira bookkeeping, or activate Wave71+.

## Next Action

When live gates are later selected and clean, run model publish dry-run, publish the model to the recorded S3 URI after explicit intent, run model install dry-run, then run Install-EC2ModelFromS3.ps1 -Execute before bounded EC2 static proof.
