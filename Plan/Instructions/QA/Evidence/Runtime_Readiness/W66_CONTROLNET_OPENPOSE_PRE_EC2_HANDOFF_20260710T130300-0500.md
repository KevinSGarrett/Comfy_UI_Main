# ControlNet Pre-EC2 Handoff Bundle

- created_at: 2026-07-10T12:47:18-05:00
- lane_id: sdxl_realvisxl_controlnet_openpose_lane
- result: pass_local_only_controlnet_pre_ec2_handoff_ready_live_blocked
- failed_check_count: 0
- execute_allowed_now: false
- target_runtime_launch_allowed: false
- target_runtime_proof: false
- certification_claimed: false

## Checks

- supported_controlnet_lane: pass
- lane_identity_alignment: pass
- package_deploy_contract: pass
- deploy_bundle_contract: pass
- deploy_publish_dry_run_contract: pass
- asset_transfer_dry_run_contract: pass
- current_clean_git_gate: pass

## Boundary

Local ControlNet pre-EC2 handoff validation only. This does not upload, start EC2, install remotely, write active markers, execute generation, prove target runtime, promote the lane, complete Items/Tracker rows, or claim certification.

## Next Action

Keep EC2 stopped. Use this handoff only after explicit live-window selection and fresh live gates; otherwise continue local orchestration for another lane.
