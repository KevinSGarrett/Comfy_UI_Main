# Main Session Integration Handoff — 2026-07-20T23:42-05:00

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- This pass: **ITEM/TRK-W64-010** RunPod Flux **face-tighter** personal-calib + qwen2.5vl:7b panel-v2 re-score
- Calib evidence: `Plan/Instructions/QA/Evidence/Wave64/TRK-W64-010_RUNPOD_C1_FACE_TIGHTER_CALIB_20260721T043424Z.json`
- VLM tip: `Plan/Instructions/QA/Evidence/Wave64/TRK-W64-010_RUNPOD_C1_FACE_TIGHTER_VLM_20260721T043808Z.json`
- Pullback: `Plan/Instructions/Operations/Pulled_Back_Artifacts/runpod_c1_face_tighter_vlm_20260721T043808Z`
- Candidate sha256: `c682a820239d344544e251f34338d0230ef56d16c143b803f39814c8e08a2c5b`
- Aggregates: face_consistency_mean **0.475** (gate 0.55 fail), body **0.9** (ok), solo lock **0.95** (ok)
- Status: `RUNTIME_SCORED_PERSONAL_CALIBRATION_FACE_TIGHTER_VLM_BELOW_GATE_NONCANONICAL`
- `row_complete=false`; no COMPLETE; no invented faces; Row074 untouched; no HOLD 090+; CSV deferred
- Does **not** clear generic multi-character USER_AUTHORITY portable reference chain

## Exact next action

1. Prefer PuLID+Scenes face-ref personal-calib when GPU free (still noncanonical), or alternate seed face-tighter if VRAM allows.
2. Leave Row074 alone; CSV via mutator only; do not claim Row010 COMPLETE.
3. Multi-character USER_AUTHORITY reference pack remains human/external Class F/A blocker.
