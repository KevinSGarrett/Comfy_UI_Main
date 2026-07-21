# Main Session Integration Handoff — 2026-07-21T02:04-05:00

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- Tip: `f2cc6bd1` (ahead of anti-dupe audit baseline `c2b4c509`)
- Binding: **RunPod ONLY** (`1q4ji0gg1fkhvt`) — NEVER EC2; NEVER local Comfy
- EC2 hygiene: `ACTIVE_EC2_RUNTIME_WINDOW.json` cleared/archived EXPIRED; `i-0560bf8d143f93bb1` STOPPED; RunPod sole GPU authority
- Row084 Class E advance (receipt only): `prompt_id=8681ba01-58a4-4a92-92cf-171d5c2daaf3`
- **ROW084-011 Class E remains FAIL/OPEN** (not cleared; no COMPLETE from receipt 8681ba01)
- ROW084-012 Class C OPEN_HOLD unchanged (`0e0c3d86`)
- Row074 exclusive PCM: **leave alone**
- `row_complete=false`; no COMPLETE claims

## Anti-Duplication STOP Rules (shift constraints)

### GPU authority

- GPU = **RunPod ONLY** pod `1q4ji0gg1fkhvt`
- Do **NOT** start EC2 (`i-0560bf8d143f93bb1`)
- Do **NOT** run local ComfyUI

### DO NOT REDO (consumed / closed / immutable)

- EC2 Canny/matrix lanes
- EC2 Wan Row023
- Wan TI2V fetch 3/3 (except `-StatusOnly` read-only checks)
- Row073 full-library PCM/decode restart
- Row075 threshold unfreeze
- Row017 consumed prepared localized lanes (tip inventory `20260721T015630-0500`):
  - `mf70_face_full_instance`, `mf70_face_identity_critical`, `mf70_expression_region`, `mf70_cheeks_skin`, `mf70_forehead_skin`, `mf70_jawline_chin`, `mf70_skin_tone_continuity`, `mf70_under_eye`, `mf70_left_eye`, `mf70_right_eye`
- FLUX.2 EC2 re-qualification
- Immutable S3 deploy bundles (no re-fetch/rebuild without explicit new gate)

### OPEN (safe next work when queue idle)

- Row017: next **unconsumed** prepared localized lane — prefer `mf70_eyes_full` if not yet landed (then eyelids/eyelashes/eyebrows/pupils per inventory)
- Row084-011: FAIL honest follow-through — production mux/cut/camera/visual authority + compiler hard-fail removal; **no COMPLETE** from receipt `8681ba01`
- Row084-012: HOLD (`0e0c3d86`) — do not advance without explicit gate
- Rows 085–089: no invented runtime; schema/planning only unless tracker-authorized
- Body/contact gold: **ABSENT** — do not claim or fabricate
- Row074: **leave alone** (exclusive PCM)

### Hygiene completed this shift

- Stale `ACTIVE_EC2_RUNTIME_WINDOW.json` archived to `runtime_artifacts/ec2_runtime_windows/history/character1-flux-turnaround-20260718T174200.20260721T070400-0500.json` with `status=EXPIRED`; active marker removed

## Exact next action

1. When Row017 queue idle: climb `mf70_eyes_full` (or next unused lane from inventory); leave Row074 alone.
2. Keep ROW084-011 FAIL/OPEN; do not claim COMPLETE from single-image gen receipt.
3. RunPod only for Wave64/Comfy/GPU. Do not rewrite broad Tracker CSVs solely for this audit.
