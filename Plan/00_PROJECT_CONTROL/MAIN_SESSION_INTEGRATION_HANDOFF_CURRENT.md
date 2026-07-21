# Main Session Integration Handoff — CURRENT (2026-07-21T10:22-0500)

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- Binding: **RunPod ONLY** (`1q4ji0gg1fkhvt`) — NEVER EC2; NEVER local Comfy
- HEAD at handoff write: see git tip after push
- Row074: coverage_complete HOLD stamped earlier (`4c7322d3`); guardian `done_hold_stamped`; **leave alone**
- Row076: local PID **31808** still running retained-index reverb/dryness reconcile (`complete=false`; ~10650/39771 at last probe); **leave alone** until `coverage_complete`; do **NOT** start 077
- Latest Row010 climb: PuLID SIDE calib `20260721T151540Z` + VLM `20260721T151831Z` (`RUNTIME_FAIL_LOCK_TRAIT_NOT_IMPROVED` / face_mean 0.7; body 0.8667; solo_lock 0.0; prompt_id `ada7b36f-f85d-4f24-b860-7c70fb768bda`)
- Prior Row010 BODYFORWARD climb retained (`145336Z`/`145516Z` LOCK_TRAIT_NOT_IMPROVED face_mean 0.6)
- Prior Row010 FACE_04 climb retained (`142217Z`/`142428Z` GATE CLEARED face_mean 0.7375)
- `row_complete=false`; no COMPLETE; no HOLD 090+; no invented faces

## Why prior shift looked stopped

1. Coordinator paused after Row084 needed external gold masks (do not invent).
2. Resume agents then hit usage limits.
3. Row017 prepared primary localized set exhausted (18 lanes) — do not redo.

## Anti-Duplication STOP Rules

### GPU authority

- GPU = **RunPod ONLY** pod `1q4ji0gg1fkhvt`
- Do **NOT** start EC2; do **NOT** run local ComfyUI
- Wait idle `:8188` / foreign hand-tournament/SAM2/canary; do not kill foreign jobs

### DO NOT REDO

- Wan TI2V re-fetch 3/3
- Row017 exhausted 18 prepared primaries (`mf70_*` set through `mf70_teeth`)
- Invent body/contact gold for Row084; do not remove compiler hard-fail alone
- False COMPLETE; Row010 stays NONCANONICAL without multi-char pack
- Exhausted Row010 envelopes: FACE_01, FACE_03, FACE_02 face-tighter-v2, FACE_04 face-crop, LOCKFRONT (FACE_01), BODYFORWARD (FACE_04+FRONT), SIDE (FACE_04+C1_USER_AUTHORITY_SIDE this climb)

### OPEN (safe next work)

- Row010: further identity / product-campaign acceptance path still NONCANONICAL (solo_lock 0.0; multi-char pack absent). Prefer unused envelope (e.g. product-campaign stage / rear authority) — not a redo of exhausted list above
- Row084: blocked on external gold masks — do not invent
- Row074: leave alone (HOLD coverage_complete)
- Row076: leave alone until coverage_complete; no 077 start

## Exact next action

1. Prefer next unused Row010 identity envelope or product-campaign acceptance path (still not COMPLETE).
2. Leave Row074 HOLD and Row076 PID 31808 alone; no HOLD 090+; no COMPLETE; no Wan re-fetch; no redo 017; no invent 084 gold.
3. RunPod only for Wave64/Comfy/GPU.
