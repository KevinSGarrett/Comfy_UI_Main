# Active Runtime Queue Local Support Certification

- created_at: 2026-07-09T03:37:55-05:00
- local_support_result: pass_local_active_runtime_queue_support_certification
- final_certification_result: blocked_final_certification_missing_target_runtime_or_final_review
- lane_count: 9

## Lane Results

- sdxl_low_risk_fallback_lane: pass_local_support; final status final_certification_possible; support evidence 3
- sdxl_realvisxl_base_lane: pass_local_support; final status local_support_pass_final_certification_blocked; support evidence 19
- sdxl_realvisxl_controlnet_canny_lane: pass_local_support; final status local_support_pass_final_certification_blocked; support evidence 46
- sdxl_realvisxl_inpaint_detail_lane: pass_local_support; final status local_support_pass_final_certification_blocked; support evidence 41
- sdxl_realvisxl_controlnet_depth_lane: pass_local_support; final status local_support_pass_final_certification_blocked; support evidence 25
- sdxl_realvisxl_controlnet_lineart_lane: pass_local_support; final status local_support_pass_final_certification_blocked; support evidence 43
- sdxl_realvisxl_controlnet_openpose_lane: pass_local_support; final status local_support_pass_final_certification_blocked; support evidence 39
- sdxl_realvisxl_controlnet_normal_lane: pass_local_support; final status local_support_pass_final_certification_blocked; support evidence 30
- sdxl_realesrgan_upscale_polish_lane: pass_local_support; final status local_support_pass_final_certification_blocked; support evidence 8

## Boundary

Local active runtime queue support only. This does not run ComfyUI, start EC2, upload to S3, rerun Wave70 hard gates, consume candidate masks as truth, promote masks, or certify target-runtime/final image quality.

## Evidence

- Plan/07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json
- Workflows/base_generation/ACTIVE_LANES.json
- Plan/Instructions/QA/Evidence/Done_Certifications/W66_ACTIVE_RUNTIME_QUEUE_LOCAL_SUPPORT_CERTIFICATION_20260709T033754-0500.json
