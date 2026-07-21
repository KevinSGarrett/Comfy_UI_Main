# Main Session Integration Handoff — CURRENT (2026-07-21T12:13-0500)

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- Binding: **RunPod ONLY** (`1q4ji0gg1fkhvt`) — NEVER EC2; NEVER local Comfy
- **STRICT VISUAL QA BINDING:** Product climbs require `strict_pod_llm_review=PASS` via `qwen2.5vl:32b` through `wave64_climb_strict_visual_gate` / durable helpers. Generation receipt ≠ visual approval. Weak `qwen2.5vl:7b` is SMOKE only.
- Row074: coverage_complete HOLD — **leave alone**
- Row076: coverage_complete HOLD — **leave alone**
- Row077: **library embed IN PROGRESS** — exclusive owner PID **41608** (`compile_wave64_semantic_audio_embeddings.py --mode index-retained --resume --retained-runtime-dir runtime_artifacts/embeddings/row077_library_20260720`); peek ~10925/39771 @ land; **do not kill / do not invent COMPLETE**
- `row_complete=false`; no COMPLETE; no HOLD 090+; no invented faces / 084 gold

## Why prior coordinator looked stopped (corrected)

Coordinator wrongly treated strict-VLM producer wiring as “shift done” and sat on Row077 watcher only. Wrong — other unblocked GPU/product work continues when `:8188` is free.

## This increment (landed)

1. Peeked Row077: owner PID 41608 ALIVE; progress advancing (~10.9k/39771 at land). No resume needed.
2. Ran one real RunPod Wan Class A motion-stronger climb exercising the NEW strict 32b path:
   - prompt_id `6a5e81b8-b751-459e-a3cc-b9cb257a08f1`
   - stamp `20260721T164856Z` / seed `2272893` / 704x1280x81 / bit_depth=10
   - helper `wave64_wan_ti2v_climb_visual.py --class-ladder class_a` → `wave64_climb_strict_visual_gate` → `qwen2.5vl:32b`
   - **Honest verdict: `strict_pod_llm_review=REJECT`** (motion_temporal≈40; MUSHY_HANDS; PLASTIC_SKIN). No COMPLETE.
3. Fixed pod client mismatch (`chat_with_images` missing `num_ctx`) by syncing current `wave64_autonomous_vlm_client.py` before gate rerun.
4. Waited through foreign hand-tournament MVC bursts (did not kill).

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/TRK-W64-019_023_MOTION_STRONGER_STRICT_CLASS_A_REJECT_20260721T164856Z.json`
- `Plan/Instructions/Operations/Pulled_Back_Artifacts/runpod_motion_stronger_strict_class_a_20260721T164856Z/`
- fixture: `Plan/Instructions/QA/Evidence/Wave64/fixtures/motion_stronger_20260721T164856Z_strict_class_a_receipt.json`

## Anti-Duplication STOP Rules

### GPU authority

- GPU = **RunPod ONLY** pod `1q4ji0gg1fkhvt`
- Do **NOT** start EC2; do **NOT** run local ComfyUI
- Wait idle `:8188` / foreign hand-tournament MVC; do not kill foreign jobs
- Before strict VLM: Comfy queue idle → `POST /free` → `qwen2.5vl:32b` → unload VLM (`keep_alive=0`) before next gen

### DO NOT REDO

- Wan TI2V re-fetch 3/3
- Row017 exhausted 18 prepared primaries
- Invent body/contact gold for Row084
- False COMPLETE; Row010 stays NONCANONICAL without multi-char pack
- Exhausted Row010 envelopes / another PuLID lock-trait climb on those axes
- Rubber-stamp product PASS with `qwen2.5vl:7b`
- Kill / restart Row077 PID 41608 while alive

### OPEN (safe next work)

1. **Row077:** leave exclusive embed owner running to coverage_complete; no COMPLETE.
2. **Row076 / Row074:** HOLD — leave alone.
3. **Wan Class A:** still OPEN after strict REJECT — later motion/hand/skin climb must still call durable strict gate.
4. **Row010:** multi-char pack ABSENT; any product visual approval must use strict 32b dual-gate.
5. **Row084:** blocked on external gold — do not invent.

## Exact next action

1. Leave Row074/076 HOLD and Row077 PID 41608 alone unless dead (then `--resume`).
2. Next product climb only when `:8188` free of foreign tournament; must invoke strict 32b path; land honest PASS/REJECT; never COMPLETE from generation alone.
3. Prefer non-GPU tracker work if GPU blocked (076 room calibration docs, multi-char pack intake if assets arrive).
