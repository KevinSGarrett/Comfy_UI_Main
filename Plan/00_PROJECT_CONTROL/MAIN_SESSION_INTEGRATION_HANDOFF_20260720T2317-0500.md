# Main Session Integration Handoff — 2026-07-20T23:17-05:00

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- This pass: RunPod `1q4ji0gg1fkhvt` durable self-hosted Ollama VLM/LLM reviewer **UP** + Flux canary VLM smoke-score **PASS_WITH_NOTES**
- Tip evidence: `Plan/Instructions/QA/Evidence/Runtime_Readiness/RUNPOD_1q4ji0gg1fkhvt_OLLAMA_VLM_FLUX_CANARY_SMOKE_PASS_20260721T041729Z.json`
- Receipt bundle: `Plan/Instructions/QA/Evidence/Runtime_Readiness/RunPod_1q4ji0gg1fkhvt/`
- Endpoint: `WAVE64_VLM_URL=http://127.0.0.1:11434` (model `llava:13b`; LLM `qwen2.5:7b-instruct`)
- Durability: nohup + watchdog loop + `/start.sh` hook (systemd/cron unavailable on pod image)
- Boundaries: Row074 PCM left alone; no wipe/DAZ; no local Comfy start

## Endpoint

| Field | Value |
|-------|-------|
| WAVE64_VLM_URL | `http://127.0.0.1:11434` |
| WAVE64_VLM_MODEL | `llava:13b` |
| WAVE64_LLM_MODEL | `qwen2.5:7b-instruct` |
| SSH | `root@195.26.233.100 -p 52077` |
| paths.env | sourced from `/workspace/paths.env` |

## Flux canary smoke (live-verified)

| Field | Value |
|-------|-------|
| Image | `FLUX_CANARY_20260721_034826_00001_.png` SHA256 `786884e5c8fe5369d11ba2e91769b2f88919977dc4cdaf4981c6edbf42f2a14e` |
| Score | overall_score `0.54`, verdict `pass`, smoke_verdict `PASS_WITH_NOTES` |
| LLM smoke | `WAVE64_LLM_OK` **PASS** |

## Exact next action

1. Route Wave64 visual review through pod loopback `WAVE64_VLM_URL=http://127.0.0.1:11434`.
2. Leave Row074 PCM alone until explicitly authorized.
