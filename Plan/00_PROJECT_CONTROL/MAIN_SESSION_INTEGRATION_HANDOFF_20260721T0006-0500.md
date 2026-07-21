# Main Session Integration Handoff — 2026-07-21T00:06-05:00

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- Runtime authority: **RunPod ONLY** (`1q4ji0gg1fkhvt`) — no EC2
- This pass: **ITEM/TRK-W64-010** PuLID+Scenes FACE_03 personal-calib + qwen2.5vl:7b panel-v2 re-score
- Calib: `Plan/Instructions/QA/Evidence/Wave64/TRK-W64-010_RUNPOD_C1_PULID_FACE03_CALIB_20260721T045449Z.json`
- Tip evidence: `Plan/Instructions/QA/Evidence/Wave64/TRK-W64-010_RUNPOD_C1_PULID_FACE03_VLM_20260721T045654Z.json`
- Pullback: `Plan/Instructions/Operations/Pulled_Back_Artifacts/runpod_c1_pulid_face03_vlm_20260721T045654Z`
- Stack: `pulid_flux_v0.9.1` + FACE_03 + `character1_flux_calibration`/`balhaw_test` LoRAs + Scenes locks
- Aggregate: face_consistency_mean **0.775** (gate 0.55 pass), body **0.9**, solo lock **0.0** (lock_ok false) → `RUNTIME_PASS_BOUNDED_PERSONAL_CALIBRATION_PULID_FACE03_VLM_NONCANONICAL` (`runtime_pass_bounded=true`)
- Candidate sha256: `7fe521c083a0dca03a274820f6fc0c1c814dd385475a0e2fc906f58624825573`
- `row_complete=false`; no COMPLETE; no invented faces; Row074 untouched; no HOLD 090+; CSV via mutator
- Does **not** clear generic multi-character USER_AUTHORITY portable reference chain

## Exact next action

1. Optional: lock-trait prompt tighten / alternate FACE ref PuLID climb on RunPod when GPU free (still noncanonical).
2. Leave Row074 alone; CSV via mutator only; do not claim Row010 COMPLETE.
3. Never route this lane through EC2.
