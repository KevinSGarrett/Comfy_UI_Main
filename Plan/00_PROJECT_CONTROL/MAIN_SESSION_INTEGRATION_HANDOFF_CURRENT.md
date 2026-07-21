# Main Session Integration Handoff — CURRENT (2026-07-21T12:30-0500)

## Continuous autonomy binding (do not false-stop)

- **Binding rule:** `.cursor/rules/continuous-autonomous-until-project-complete.mdc` (`alwaysApply: true`) — committed `31417dff`
- Interactive Cursor shifts continue until tracker/project **end-to-end** complete — not until one row, one blocker, or one successful increment.
- When one lane blocks: switch immediately to next highest-value unblocked work; leave exclusive owners running; land blockers; keep going.
- Genuine stop only if user ends shift, or zero unblocked work remains with blockers + CURRENT handoff recorded (prefer monitoring long jobs over silence).

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- Binding: **RunPod ONLY** (`1q4ji0gg1fkhvt`) — NEVER EC2; NEVER local Comfy
- **STRICT VISUAL QA BINDING:** Product climbs require `strict_pod_llm_review=PASS` via `qwen2.5vl:32b` through `wave64_climb_strict_visual_gate` / durable helpers. Generation receipt ≠ visual approval. Weak `qwen2.5vl:7b` is SMOKE only.
- **Ollama on pod:** must run with `OLLAMA_MODELS=/workspace/ollama` (54G blobs). Empty `ollama list` usually means serve started without that env — restart with paths.env, do not pull onto 20G root overlay.
- Row074: coverage_complete HOLD — **leave alone**
- Row076: coverage_complete HOLD — **leave alone**
- Row077: **library embed RESUMED** — exclusive owner PID **19488** (resumed from dead 41608 at ~18350/39771); **do not kill / do not invent COMPLETE**
- Row019/023: next Class A climb **IN FLIGHT** `prompt_id=f19ac102-2274-442a-9439-cd87a93087cd` stamp `20260721T172950Z` (STATIC_MOTION+MUSHY_HANDS retry); wait_extract_strict bg on pod
- `row_complete=false`; no COMPLETE; no HOLD 090+; no invented faces / 084 gold

## This increment (landed)

1. Created continuous-autonomy Cursor rule + AGENTS one-liner; pushed `31417dff`.
2. Row077: was ALIVE → later found DEAD at ~18350/39771 → **resumed** exclusive owner PID **19488** (same `--mode index-retained --resume` command). Leave alone.
3. Prior Class A climb `6a5e81b8` / `164856Z` → honest `REJECT` (motion≈40; MUSHY_HANDS; PLASTIC_SKIN).
4. Corrected follow-up Class A climb (no Wan re-fetch) `af3d4927` / `171649Z` / seed `2273017`:
   - Ollama models path restored (`OLLAMA_MODELS=/workspace/ollama`) after empty list blocked gate
   - **Honest verdict: `strict_pod_llm_review=REJECT`** via `qwen2.5vl:32b` — `MUSHY_HANDS` + `STATIC_MOTION`; rubric motion 65 / skin 70 / hands 80 / identity 95. No COMPLETE. Pushed `7972ab7e`.
5. Landed fail-closed Row010 portable multi-char pack intake gate → still **ABSENT**. No invent faces.
6. Launched next Class A retry `f19ac102` / `172950Z` (stronger motion/hands; still no Wan re-fetch) with pod wait_extract_strict background — monitoring.

Evidence:
- `Plan/Instructions/QA/Evidence/Wave64/TRK-W64-019_023_MOTION_STRONGER_STRICT_CLASS_A_REJECT_20260721T171649Z.json`
- `Plan/Instructions/Operations/Pulled_Back_Artifacts/runpod_motion_stronger_strict_class_a_20260721T171649Z/`
- fixture: `Plan/Instructions/QA/Evidence/Wave64/fixtures/motion_stronger_20260721T171649Z_strict_class_a_receipt.json`
- `Plan/07_IMPLEMENTATION/scripts/validate_wave64_portable_multi_character_pack_intake.py`
- `Plan/Instructions/QA/Evidence/Wave64/TRK-W64-010_PORTABLE_MULTI_CHAR_PACK_INTAKE_GATE_20260721T171936Z.json`

## Anti-Duplication STOP Rules

### GPU authority

- GPU = **RunPod ONLY** pod `1q4ji0gg1fkhvt`
- Do **NOT** start EC2; do **NOT** run local ComfyUI
- Wait idle `:8188` / foreign hand-tournament MVC; do not kill foreign jobs
- Before strict VLM: Comfy queue idle → `POST /free` → ensure `OLLAMA_MODELS=/workspace/ollama` → `qwen2.5vl:32b` → unload VLM (`keep_alive=0`) before next gen

### DO NOT REDO

- Wan TI2V re-fetch 3/3
- Row017 exhausted 18 prepared primaries
- Invent body/contact gold for Row084
- False COMPLETE; Row010 stays NONCANONICAL without multi-char pack
- Exhausted Row010 envelopes / another PuLID lock-trait climb on those axes
- Rubber-stamp product PASS with `qwen2.5vl:7b`
- Kill / restart Row077 PID 41608 while alive
- Invent multi-char pack faces

### OPEN (safe next work)

1. **Row077:** leave exclusive embed owner running to coverage_complete; no COMPLETE.
2. **Row076 / Row074:** HOLD — leave alone.
3. **Wan Class A:** still OPEN after strict REJECT — next climb must target STATIC_MOTION + MUSHY_HANDS under durable strict 32b gate (no re-fetch).
4. **Row010:** multi-char pack ABSENT; re-run intake gate when external assets arrive; any product visual approval must use strict 32b.
5. **Row084:** blocked on external gold — do not invent.

## Exact next action

1. Leave Row074/076 HOLD and Row077 PID 41608 alone unless dead (then `--resume`).
2. Next product climb when `:8188` free; must invoke strict 32b path with `OLLAMA_MODELS=/workspace/ollama`; land honest PASS/REJECT; never COMPLETE from generation alone.
3. Prefer non-GPU tracker work if GPU blocked (076 room calibration docs, multi-char pack intake if assets arrive).
4. Continuous autonomy: never stop after one increment — see `.cursor/rules/continuous-autonomous-until-project-complete.mdc`.
