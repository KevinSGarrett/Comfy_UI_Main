# Main Session Integration Handoff — 2026-07-21T04:54-05:00

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- Binding: **RunPod ONLY** (`1q4ji0gg1fkhvt` / `root@195.26.233.100 -p 52077`) — NEVER EC2
- This pass: Row017 Class E RunPod `mf70_teeth` producer + GLOBAL_REVIEW + Ollama `qwen2.5vl:7b` VLM
- Waited for idle `:8188` (Wan/other may hold); did not kill foreign jobs; tournament lock absent
- `row_complete=false`; no COMPLETE; leave Row074 alone; no HOLD 090+
- **Prepared primary localized lane set exhausted** after `mf70_teeth` (18 lanes)

## Landed this pass

| Field | Value |
| --- | --- |
| Region | `mf70_teeth` |
| Producer stamp | `20260721T045222-0500` |
| VLM stamp | `20260721T045325-0500` |
| prompt_id | `9ff09e1c-3bc8-40a8-b1c3-a299d1060070` |
| output sha256 | `766890013f8428cc9e221c72acec50de2d2760ca651bc54e972ab65fd8b296d6` |
| GLOBAL_REVIEW | pass / `VISUAL_QA_PASS_BOUNDED` |
| VLM | `vlm_ok=true` |
| Inventory | `ROW017_RUNPOD_PREPARED_LOCALIZED_LANE_INVENTORY_20260721T045400-0500.json` |

## Exhausted prepared primary set (anti-dupe — do not redo)

`mf70_face_full_instance`, `mf70_face_identity_critical`, `mf70_expression_region`, `mf70_cheeks_skin`, `mf70_forehead_skin`, `mf70_jawline_chin`, `mf70_skin_tone_continuity`, `mf70_under_eye`, `mf70_left_eye`, `mf70_right_eye`, `mf70_eyes_full`, `mf70_eyelids`, `mf70_eyelashes`, `mf70_eyebrows`, `mf70_pupils_iris_sclera`, `mf70_nose`, `mf70_mouth_lips`, `mf70_teeth`

## Exact next action

1. Keep Row017 blocked/non-complete; prepared primary set exhausted — prefer Row010 face-tighter personal-calib re-VLM or product-campaign acceptance path.
2. Leave Row074 alone; no HOLD 090+; no COMPLETE; no Wan re-fetch; no redo consumed 017 lanes.
3. RunPod only for Wave64/Comfy/GPU.
