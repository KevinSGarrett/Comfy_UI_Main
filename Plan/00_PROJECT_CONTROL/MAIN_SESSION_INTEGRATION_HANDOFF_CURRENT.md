# Main Session Integration Handoff — 2026-07-20T23:42-05:00

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- This pass: Row010 RunPod Flux **face-tighter** personal-calib + qwen2.5vl:7b panel-v2 re-score (below face gate; noncanonical)
- Tip evidence: `Plan/Instructions/QA/Evidence/Wave64/TRK-W64-010_RUNPOD_C1_FACE_TIGHTER_VLM_20260721T043808Z.json`
- Calib: `Plan/Instructions/QA/Evidence/Wave64/TRK-W64-010_RUNPOD_C1_FACE_TIGHTER_CALIB_20260721T043424Z.json`
- Pullback: `Plan/Instructions/Operations/Pulled_Back_Artifacts/runpod_c1_face_tighter_vlm_20260721T043808Z`
- Aggregate: face_consistency_mean **0.475** (gate 0.55 fail), body **0.9**, solo lock **0.95** → `RUNTIME_SCORED_PERSONAL_CALIBRATION_FACE_TIGHTER_VLM_BELOW_GATE_NONCANONICAL`
- `row_complete=false`; no COMPLETE; no invented faces; Row074 untouched; no HOLD 090+; CSV deferred
- Does **not** clear generic multi-character USER_AUTHORITY portable reference chain

## Exact next action

1. Prefer PuLID+Scenes face-ref personal-calib follow-on on RunPod when GPU free (still noncanonical).
2. Leave Row074 alone; CSV via mutator only; do not claim Row010 COMPLETE.
