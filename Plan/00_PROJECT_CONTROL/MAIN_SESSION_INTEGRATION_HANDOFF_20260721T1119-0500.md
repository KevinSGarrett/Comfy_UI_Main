# Main Session Integration Handoff — CURRENT (2026-07-21T11:05-0500)

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- Binding: **RunPod ONLY** (`1q4ji0gg1fkhvt`) — NEVER EC2; NEVER local Comfy
- **NEW BINDING:** Autonomous climbs require **strict pod self-hosted LLM visual approval** (`strict_pod_llm_review=PASS` via `qwen2.5vl:32b`). Generation receipt ≠ visual approval. Weak `qwen2.5vl:7b` is SMOKE/observation only.
- Strategy: `Plan/Instructions/POD_STRICT_SELF_HOSTED_LLM_VISUAL_QA_STRATEGY.md`
- Row074: coverage_complete HOLD — **leave alone**
- Row076: local PID **31808** retained-index reconcile — **leave alone** (do NOT kill; do NOT start 077)
- `row_complete=false`; no COMPLETE; no HOLD 090+; no invented faces / 084 gold

## Why prior shift looked stopped / known gap closed now

1. Coordinator paused after Row084 needed external gold masks (do not invent).
2. Resume agents then hit usage limits.
3. Row017 prepared primary localized set exhausted (18 lanes) — do not redo.
4. **Gap (this shift):** climbs used `qwen2.5vl:7b` which PASSed Wan clips human frame Read FAILed (near-static / mushy hands). Bytes + human_frame_read gates were added, but user requires high-end self-hosted LLM strictness as primary visual authority — **implemented now** (capability landed / policy binding; not product COMPLETE).

## Anti-Duplication STOP Rules

### GPU authority

- GPU = **RunPod ONLY** pod `1q4ji0gg1fkhvt`
- Do **NOT** start EC2; do **NOT** run local ComfyUI
- Wait idle `:8188` / foreign hand-tournament/SAM2/canary; do not kill foreign jobs
- Before strict VLM review: Comfy queue idle → `POST /free` unload → run `qwen2.5vl:32b` → unload VLM (`keep_alive=0`) before next gen

### DO NOT REDO

- Wan TI2V re-fetch 3/3
- Row017 exhausted 18 prepared primaries (`mf70_*` set through `mf70_teeth`)
- Invent body/contact gold for Row084; do not remove compiler hard-fail alone
- False COMPLETE; Row010 stays NONCANONICAL without multi-char pack
- Exhausted Row010 envelopes: FACE_01, FACE_03, FACE_02 face-tighter-v2, FACE_04 face-crop, LOCKFRONT (FACE_01), BODYFORWARD (FACE_04+FRONT), SIDE (FACE_04+C1_USER_AUTHORITY_SIDE), REAR (FACE_04+C1_REAR_AUTHORITY_PRIMARY/ASS)
- Another PuLID lock-trait climb that will re-hit `solo_lock=0.0` on the exhausted axis list above
- Rubber-stamp product PASS with `qwen2.5vl:7b` / `llava:13b`

### OPEN (safe next work) — gates

1. **Row076 gate:** wait PID 31808 → `coverage_complete`; then Notes sync + optional 077 start ranking; no kill; no COMPLETE until authority criteria met.
2. **Row010 gate:** portable multi-character reference pack still ABSENT; any product visual approval must use strict pod LLM dual-gate (not 7b panel-v2 alone).
3. **Row084 gate:** blocked on external production gold contact/body masks — do not invent gold.
4. **Row074:** leave alone (HOLD coverage_complete).
5. **Row017 / Wan:** exhausted / do not re-fetch; future climbs must call `wave64_pod_strict_visual_qa.py`.
6. **Strict visual QA:** capability landed; use for all new PRODUCT/CLASS_A/PROOF_LANDED/IDENTITY_GATE climbs.

## Exact next action

1. Leave Row074 HOLD and Row076 PID alone; no HOLD 090+; no COMPLETE; no Wan re-fetch; no redo 017; no invent 084 gold; no weak-VLM product PASS.
2. New autonomous visual approvals: `WAVE64_STRICT_VLM_MODEL=qwen2.5vl:32b` via `wave64_pod_strict_visual_qa.py`; fail closed if model missing.
3. Prefer waiting 076 coverage_complete, or non-COMPLETE product-campaign / multi-char pack intake if external assets arrive.
4. RunPod only for Wave64/Comfy/GPU.
