# Main Session Integration Handoff — CURRENT (2026-07-21T04:54-0500)

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- Binding: **RunPod ONLY** (`1q4ji0gg1fkhvt`) — NEVER EC2; NEVER local Comfy
- Latest Row017 climb: `mf70_teeth` producer `20260721T045222-0500` + VLM `20260721T045325-0500` (`vlm_ok`)
- **Prepared primary localized lane set exhausted** (18 lanes) — see inventory `20260721T045400-0500`
- `row_complete=false`; no COMPLETE; leave Row074 alone; no HOLD 090+

## Anti-Duplication STOP Rules

### GPU authority

- GPU = **RunPod ONLY** pod `1q4ji0gg1fkhvt`
- Do **NOT** start EC2; do **NOT** run local ComfyUI
- Wait idle `:8188` if Wan/bitrate-retry holds; do not kill foreign jobs

### DO NOT REDO (consumed prepared primaries)

`mf70_face_full_instance`, `mf70_face_identity_critical`, `mf70_expression_region`, `mf70_cheeks_skin`, `mf70_forehead_skin`, `mf70_jawline_chin`, `mf70_skin_tone_continuity`, `mf70_under_eye`, `mf70_left_eye`, `mf70_right_eye`, `mf70_eyes_full`, `mf70_eyelids`, `mf70_eyelashes`, `mf70_eyebrows`, `mf70_pupils_iris_sclera`, `mf70_nose`, `mf70_mouth_lips`, `mf70_teeth`

Also: no Wan re-fetch; no redo consumed 017 climbs.

### OPEN (safe next work)

- Row017: prepared primary set exhausted — prefer Row010 face-tighter personal-calib re-VLM or product-campaign acceptance path (still not COMPLETE)
- Row074: **leave alone**

## Exact next action

1. Prefer Row010 face-tighter personal-calib re-VLM or product-campaign acceptance path for Row017 Class E residual.
2. Leave Row074 alone; no HOLD 090+; no COMPLETE.
3. RunPod only for Wave64/Comfy/GPU.
