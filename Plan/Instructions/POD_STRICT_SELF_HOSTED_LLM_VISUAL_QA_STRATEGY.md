# POD_STRICT_SELF_HOSTED_LLM_VISUAL_QA Strategy

## Binding authority (2026-07-21)

Autonomous ComfyUI climbs on RunPod **must not** rubber-stamp outputs from generation
receipts, weak VLMs, or “pipeline ran” signals.

**Primary visual authority for product / Class A / Proof_Landed / identity GATE CLEARED:**

| Field | Value |
| --- | --- |
| Host | RunPod ONLY (`1q4ji0gg1fkhvt`) |
| Runtime | Self-hosted Ollama on the pod (`WAVE64_VLM_URL=http://127.0.0.1:11434`) |
| Strict model (default) | `qwen2.5vl:32b` via `WAVE64_STRICT_VLM_MODEL` |
| Smoke model (labeled only) | `qwen2.5vl:7b` via `WAVE64_VLM_SMOKE_MODEL` |
| Forbidden as product authority | `qwen2.5vl:7b`, `llava:13b`, `llama3.2-vision:11b`, `qwen3-vl:*` small tags, text-only `qwen2.5:7b-instruct` |
| EC2 | NEVER |
| Local Comfy as runtime | NEVER |

Executable contract:

- Schema: `Plan/08_SCHEMAS/pod_strict_self_hosted_llm_visual_qa_receipt.schema.json`
- Reviewer: `Plan/07_IMPLEMENTATION/scripts/wave64_pod_strict_visual_qa.py`
- Receipt validator: `Plan/07_IMPLEMENTATION/scripts/validate_wave64_pod_strict_visual_qa_receipt.py`
- Shared client: `Plan/07_IMPLEMENTATION/scripts/wave64_autonomous_vlm_client.py`
- Class E dual-gate: `Plan/07_IMPLEMENTATION/scripts/validate_wave64_wan_ti2v_class_e_runtime_proof_claim.py`

## Dual-gate policy (generation ≠ approval)

1. **Generation receipt** (Comfy prompt_id / mp4 exists / bytes) proves only that a job ran.
2. **Visual approval** for product-class claims requires:
   - `strict_pod_llm_review=PASS` from the approved high-end pod model, **and**
   - where already required: `human_frame_read=pass` (Cursor frame Read), **and**
   - existing bytes floors (e.g. Class E Proof_Landed ≥ 250KB).
3. Weak historical path (`qwen2.5vl:7b` panel-v2 / Wan vlm_review.json) is **observation or SMOKE only**.
4. SMOKE canaries may use the weak model but **must** set `lane=SMOKE` and must not claim
   Proof_Landed / Class A product PASS / identity GATE CLEARED / product COMPLETE.

## Strict rubric (default REJECT)

Scores are 0–100. Default decision is **REJECT** unless all applicable cells clear high bars:

| Cell | Min for PASS |
| --- | ---: |
| anatomy_hands_fingers | 90 |
| identity_consistency | 85 |
| skin_realism | 85 |
| motion_temporal (video) | 90 |
| artifacts_cleanliness | 85 |
| prompt_adherence | 85 |
| policy_project | 90 |
| reviewer_confidence | 0.75 |

Any **blocking** defect → REJECT. Unparseable model JSON → BLOCKED (fail closed).
Missing approved model → BLOCKED / fail closed (do not silently fall back to 7b).

Forbidden rubber stamps (must remain true on every receipt):

- `pipeline_ran_is_not_pass`
- `generation_receipt_is_not_pass`
- `weak_vlm_pass_alone_is_not_product_pass`
- `smoke_model_forbidden_for_product`

Correction guidance is mandatory on REJECT/BLOCKED (regenerate cues: hands, motion,
skin, identity, artifacts).

## Historical weak PASS evidence (why this exists)

Known false / weak approvals under `qwen2.5vl:7b`:

- `runpod_wan_ti2v_class_e_motion_20260721T083156Z` — VLM `PASS` claiming “fluid dynamic
  movements” while human temporal review later failed near-static / mushy hands.
- Row010 panel-v2 identity climbs used `qwen2.5vl:7b` as a bounded calibration scorer;
  that path is **not** product COMPLETE authority and is subordinate to the strict model
  for any future product-campaign visual approval.

Later mitigations (bytes ≥ 250KB, `human_frame_read=pass`) remain in force and are
**additive**, not replacements for strict pod LLM review.

## VRAM arbitration (RTX 6000 Ada ~48GB)

Observed coexistence problem: Comfy with Wan/Flux weights often holds ~27–32 GiB, leaving
~16–21 GiB free — insufficient to safely co-reside with `qwen2.5vl:32b` (~21 GiB weights).

**Required sequence for product strict review:**

1. Confirm Comfy queue idle (`GET :8188/queue` running=0 pending=0).
2. `POST :8188/free` with `{"unload_models":true,"free_memory":true}`.
3. Run `wave64_pod_strict_visual_qa.py` (loads strict Ollama model).
4. Unload VLM after review (`WAVE64_STRICT_VLM_KEEP_ALIVE=0` / generate keep_alive=0).
5. Only then reload Comfy models for the next generation.

Do **not** kill unrelated local Row076 watchers. Do **not** kill foreign Comfy jobs;
wait for idle. Document free MiB before/after unload on the receipt (`vram_arbitration`).

If a larger tag (e.g. `qwen2.5vl:72b` quantized) is adopted later, keep the same sequential
unload contract and update `WAVE64_STRICT_VLM_MODEL` plus the approved-model allow-list.

## Wiring expectations (producers / climbs)

| Path | Required |
| --- | --- |
| Wan Class E Proof_Landed / Class A product climbs | `strict_pod_llm_review` dual-gate + human_frame_read where gated |
| Row017 GLOBAL_REVIEW product promotion | Prefer strict receipt; schema validator remains; weak VLM observation ≠ pass |
| Row010 identity GATE CLEARED (product campaign) | Strict model for product approval; panel-v2 7b remains calib/SMOKE-labeled only |
| Smoke / canary | `lane=SMOKE` allowed on weak model; never claim product COMPLETE |

## Operator commands (pod)

```bash
source /workspace/paths.env
export OLLAMA_MODELS=/workspace/ollama
export WAVE64_VLM_URL=http://127.0.0.1:11434
export WAVE64_STRICT_VLM_MODEL=qwen2.5vl:32b
export WAVE64_STRICT_VLM_NUM_CTX=8192   # required: default 128k vision ctx OOMs on 48GB

# Ensure model present (fail closed if missing)
ollama show qwen2.5vl:32b
# If absent: ollama pull qwen2.5vl:32b

# Queue idle → unload Comfy → review → unload VLM
curl -s http://127.0.0.1:8188/queue
curl -s -X POST http://127.0.0.1:8188/free -H 'Content-Type: application/json' \
  -d '{"unload_models":true,"free_memory":true}'

python3 /workspace/wave64_repo_scripts/wave64_pod_strict_visual_qa.py \
  --lane PROOF_LANDED \
  --media-kind video_frames \
  --intent "Wan TI2V living motion with sharp separated hands" \
  --images /path/frame_01.png /path/frame_05.png \
  --out /workspace/tmp/strict_review_receipt.json
```

Self-test contract (landed 2026-07-21 on pod `1q4ji0gg1fkhvt`):

- Known-bad Wan frames from historical weak PASS `083156Z` → **REJECT** under `qwen2.5vl:32b`
  (blocking `LACK_OF_LIVING_MOTION`, major mushy fingers).
- Known-better sharp-hand still → may still **REJECT** under high bars (skin/policy); that is
  allowed and proves bars were not weakened to chase PASS.

## Status language (Tracker / Items)

Allowed after landing this capability:

- `..._Strict_Pod_Llm_Visual_Qa_Capability_Landed` suffix on blocked product statuses
- Evidence decision: `pod_strict_self_hosted_llm_visual_qa_capability_landed_policy_binding`

Forbidden:

- Product `COMPLETE` solely because the strict reviewer script exists
- Claiming Wan/Row010/Row084 product COMPLETE from this control landing alone
