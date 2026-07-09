# Active Runtime Queue Package Deploy Matrix

- created_at: 2026-07-09T05:31:53-05:00
- result: pass_local_only_active_runtime_queue_package_deploy_matrix_ec2_blocked
- lane_count: 9
- local_package_deploy_ready_count: 9
- dirty_source_bundle_count: 9
- target_runtime_launch_allowed: false

## Rows

- 1. sdxl_low_risk_fallback_lane: package=True, deploy=True, clean_source=False
- 2. sdxl_realvisxl_base_lane: package=True, deploy=True, clean_source=False
- 3. sdxl_realvisxl_controlnet_canny_lane: package=True, deploy=True, clean_source=False
- 4. sdxl_realvisxl_inpaint_detail_lane: package=True, deploy=True, clean_source=False
- 5. sdxl_realvisxl_controlnet_depth_lane: package=True, deploy=True, clean_source=False
- 6. sdxl_realvisxl_controlnet_lineart_lane: package=True, deploy=True, clean_source=False
- 7. sdxl_realvisxl_controlnet_openpose_lane: package=True, deploy=True, clean_source=False
- 8. sdxl_realvisxl_controlnet_normal_lane: package=True, deploy=True, clean_source=False
- 9. sdxl_realesrgan_upscale_polish_lane: package=True, deploy=True, clean_source=False

## Boundary

Local active-runtime queue package/deploy matrix only. This does not authorize or perform live upload, marker write, EC2 start, generation, target-runtime proof, final certification, mask promotion, Wave70 hard-gate rerun, Jira bookkeeping, or Wave71+ activation.
