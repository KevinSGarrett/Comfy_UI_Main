# Main Session Integration Handoff — CURRENT (2026-07-21T12:12-0500)

## Continuous autonomy binding (do not false-stop)

- **Binding rule:** `.cursor/rules/continuous-autonomous-until-project-complete.mdc` (`alwaysApply: true`)
- Interactive Cursor shifts continue until tracker/project **end-to-end** complete — not until one row, one blocker, or one successful increment.
- When one lane blocks: switch immediately to next highest-value unblocked work; leave exclusive owners running; land blockers; keep going.
- Genuine stop only if user ends shift, or zero unblocked work remains with blockers + CURRENT handoff recorded (prefer monitoring long jobs over silence).

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- Binding: **RunPod ONLY** (`1q4ji0gg1fkhvt`) — NEVER EC2; NEVER local Comfy
- **NEW BINDING:** Autonomous climbs require **strict pod self-hosted LLM visual approval** (`strict_pod_llm_review=PASS` via `qwen2.5vl:32b`). Generation receipt ≠ visual approval. Weak `qwen2.5vl:7b` is SMOKE/observation only.
- **Producers wired:** Row010 / Wan TI2V / Row017 GLOBAL_REVIEW climb paths now call shared `wave64_climb_strict_visual_gate.py` (fail closed without `strict_pod_llm_review=PASS`; smoke may keep 7b only when labeled SMOKE).
- Strategy: `Plan/Instructions/POD_STRICT_SELF_HOSTED_LLM_VISUAL_QA_STRATEGY.md`
- Row074: coverage_complete HOLD — **leave alone**
- Row076: **coverage_complete HOLD** `39771/39771` PID 31808 clean_exit; Status `Blocked_Library_Thresholds_And_Room_Calibration_Absent_Reconcile_Complete`; no product COMPLETE
- Row077: **RUNNING** exclusive index-retained library embed — owner PID **41608** (parent 25092), `runtime_artifacts/embeddings/row077_library_20260720`; progress advancing (~10k+/39771 at last peek); **do not kill**; resume only if dead.
- `row_complete=false`; no COMPLETE; no HOLD 090+; no invented faces / 084 gold

## Why prior shift looked stopped / known gap closed now

1. Coordinator paused after Row084 needed external gold masks (do not invent).
2. Resume agents then hit usage limits.
3. Row017 prepared primary localized set exhausted (18 lanes) — do not redo.
4. Strict visual QA capability landed earlier (`qwen2.5vl:32b` + dual-gate). **This pass:** climb producers/templates for Row010 PuLID, Wan TI2V Class E/A, and GLOBAL_REVIEW deepen are wired to the shared gate; pod smoke on known-bad Wan `083156Z` frames → `REJECT` via `wave64_wan_ti2v_climb_visual.py`.
5. **Row076 gate closed previously:** exclusive reconcile reached `coverage_complete`; Notes synced HOLD.
6. **Row077:** index-retained library embed runner landed and is **running** under exclusive PID 41608 — leave alone; do not invent alternate start; resume only if dead.

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
- Invent a second Row077 start while PID 41608 is alive; do not kill 074/076/077 owners

### OPEN (safe next work) — gates

1. **Row076:** HOLD after coverage_complete — room/source calibration + threshold unfreeze before acceptance/Row079 unlock; no COMPLETE.
2. **Row077:** exclusive embed RUNNING — monitor/resume-if-dead only; no COMPLETE until coverage_complete + acceptance path.
3. **Row010 gate:** portable multi-character reference pack still ABSENT; any product visual approval must use strict pod LLM dual-gate (not 7b panel-v2 alone).
4. **Row084 gate:** blocked on external production gold contact/body masks — do not invent gold.
5. **Row074:** leave alone (HOLD coverage_complete).
6. **Row017 / Wan:** exhausted / do not re-fetch; future climbs must call wired strict gate helpers.
7. **Strict visual QA:** capability + producer wiring landed; historical ad-hoc `tmp_row010_*` / `tmp_row017_*` 7b deepen scripts remain unwired until replaced by the durable helpers on the next climb.

## Exact next action

1. Leave Row074/076 HOLD alone; leave Row077 PID 41608 running; no HOLD 090+; no Wan re-fetch; no redo 017; no invent 084 gold; no weak-VLM product PASS.
2. New climbs: `wave64_climb_strict_visual_gate.py` / Row010|Wan|Row017 wrappers; fail closed without `strict_pod_llm_review=PASS`.
3. Prefer next unblocked RunPod climb or multi-char / product-campaign intake if external assets arrive; otherwise land docs/tooling that unblocks without false COMPLETE.
4. RunPod only for Wave64/Comfy/GPU.
5. Continuous autonomy: never stop after one increment — see `.cursor/rules/continuous-autonomous-until-project-complete.mdc`.
